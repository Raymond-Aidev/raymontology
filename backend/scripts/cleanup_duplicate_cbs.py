"""
CB(전환사채) 중복 데이터 정제 스크립트

문제: 동일한 (company_id, bond_name) 조합이 여러 레코드로 저장되어
      인수자 투자 이력이 중복 표시됨

전략:
1. 백업 테이블 생성
2. 대표 CB 선정 (issue_date 있는 것 우선)
3. 삭제 대상 CB의 인수자를 대표 CB로 재연결
4. 중복 인수자 제거
5. 중복 CB 삭제
6. 검증

롤백: backup 테이블에서 복원 가능

사용법:
    # DRY RUN (실제 변경 없음)
    python cleanup_duplicate_cbs.py --dry-run

    # 실제 실행
    python cleanup_duplicate_cbs.py --execute

    # 롤백
    python cleanup_duplicate_cbs.py --rollback
"""

import asyncio
import argparse
import sys
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_duplicate_stats(session: AsyncSession) -> dict:
    """현재 중복 상태 통계"""
    result = await session.execute(text("""
        SELECT
            COUNT(*) as total_cbs,
            COUNT(DISTINCT (company_id, bond_name)) as unique_pairs,
            COUNT(*) - COUNT(DISTINCT (company_id, bond_name)) as duplicates
        FROM convertible_bonds
    """))
    row = result.fetchone()
    return {
        "total_cbs": row.total_cbs,
        "unique_pairs": row.unique_pairs,
        "duplicates": row.duplicates
    }


async def create_backup_tables(session: AsyncSession, dry_run: bool = True):
    """백업 테이블 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    queries = [
        f"""
        CREATE TABLE IF NOT EXISTS convertible_bonds_backup_{timestamp} AS
        SELECT * FROM convertible_bonds
        """,
        f"""
        CREATE TABLE IF NOT EXISTS cb_subscribers_backup_{timestamp} AS
        SELECT * FROM cb_subscribers
        """
    ]

    if dry_run:
        print(f"\n[DRY RUN] Would create backup tables:")
        print(f"  - convertible_bonds_backup_{timestamp}")
        print(f"  - cb_subscribers_backup_{timestamp}")
        return timestamp

    for query in queries:
        await session.execute(text(query))

    await session.commit()
    print(f"\n[BACKUP] Created backup tables with timestamp: {timestamp}")
    return timestamp


async def identify_duplicates(session: AsyncSession) -> list:
    """중복 CB 그룹 식별 및 대표 CB 선정"""
    result = await session.execute(text("""
        WITH ranked_cbs AS (
            SELECT
                id,
                company_id,
                bond_name,
                issue_date,
                issue_amount,
                ROW_NUMBER() OVER (
                    PARTITION BY company_id, bond_name
                    ORDER BY issue_date DESC NULLS LAST, issue_amount DESC NULLS LAST, id
                ) as rn
            FROM convertible_bonds
        ),
        duplicate_groups AS (
            SELECT company_id, bond_name
            FROM convertible_bonds
            GROUP BY company_id, bond_name
            HAVING COUNT(*) > 1
        )
        SELECT
            r.id::text,
            r.company_id::text,
            r.bond_name,
            r.issue_date::text,
            r.rn,
            CASE WHEN r.rn = 1 THEN 'KEEP' ELSE 'REMOVE' END as action
        FROM ranked_cbs r
        WHERE (r.company_id, r.bond_name) IN (SELECT company_id, bond_name FROM duplicate_groups)
        ORDER BY r.company_id, r.bond_name, r.rn
    """))

    duplicates = []
    for row in result.fetchall():
        duplicates.append({
            "id": row[0],
            "company_id": row[1],
            "bond_name": row[2],
            "issue_date": row[3],
            "rank": row[4],
            "action": row[5]
        })

    return duplicates


async def get_reassignment_plan(session: AsyncSession) -> list:
    """인수자 재연결 계획 조회"""
    result = await session.execute(text("""
        WITH keep_cbs AS (
            SELECT DISTINCT ON (company_id, bond_name)
                id as keep_id, company_id, bond_name
            FROM convertible_bonds
            ORDER BY company_id, bond_name, issue_date DESC NULLS LAST, issue_amount DESC NULLS LAST
        ),
        remove_cbs AS (
            SELECT cb.id as remove_id, k.keep_id, cb.bond_name
            FROM convertible_bonds cb
            JOIN keep_cbs k ON cb.company_id = k.company_id AND cb.bond_name = k.bond_name
            WHERE cb.id != k.keep_id
        )
        SELECT
            s.id::text as subscriber_id,
            s.subscriber_name,
            r.remove_id::text,
            r.keep_id::text,
            r.bond_name
        FROM cb_subscribers s
        JOIN remove_cbs r ON s.cb_id = r.remove_id
        ORDER BY r.bond_name, s.subscriber_name
    """))

    return [dict(row._mapping) for row in result.fetchall()]


async def execute_cleanup(session: AsyncSession, dry_run: bool = True):
    """정제 실행"""

    # Step 1: 통계 확인
    print("\n" + "="*60)
    print("CB 중복 데이터 정제")
    print("="*60)

    stats_before = await get_duplicate_stats(session)
    print(f"\n[현재 상태]")
    print(f"  총 CB 레코드: {stats_before['total_cbs']}")
    print(f"  유니크 (회사, 회차): {stats_before['unique_pairs']}")
    print(f"  중복 레코드: {stats_before['duplicates']}")

    if stats_before['duplicates'] == 0:
        print("\n[완료] 중복 레코드가 없습니다.")
        return

    # Step 2: 백업 생성
    if not dry_run:
        backup_ts = await create_backup_tables(session, dry_run=False)
    else:
        backup_ts = await create_backup_tables(session, dry_run=True)

    # Step 3: 중복 식별
    duplicates = await identify_duplicates(session)
    keep_count = sum(1 for d in duplicates if d['action'] == 'KEEP')
    remove_count = sum(1 for d in duplicates if d['action'] == 'REMOVE')

    print(f"\n[중복 분석]")
    print(f"  유지할 CB (대표): {keep_count}")
    print(f"  삭제할 CB (중복): {remove_count}")

    # Step 4: 인수자 재연결 계획
    reassignments = await get_reassignment_plan(session)
    print(f"\n[인수자 재연결]")
    print(f"  재연결 대상: {len(reassignments)}명")

    if dry_run:
        print(f"\n[DRY RUN] 샘플 재연결 (최대 10건):")
        for r in reassignments[:10]:
            print(f"    {r['subscriber_name'][:20]:20} | {r['bond_name'][:30]}")
        if len(reassignments) > 10:
            print(f"    ... 외 {len(reassignments) - 10}건")

    if dry_run:
        print("\n" + "="*60)
        print("[DRY RUN 완료] 실제 변경 없음")
        print("실행하려면: python cleanup_duplicate_cbs.py --execute")
        print("="*60)
        return

    # Step 5: 실제 실행
    print("\n[실행 중...]")

    # 5-0: 삭제 대상 CB에 연결된 모든 인수자 삭제
    # (단, 대표 CB에 동일 이름이 없는 경우만 나중에 재생성)
    # 가장 안전한 방법: 삭제 대상 CB의 인수자를 먼저 모두 삭제하고,
    # 중복되지 않는 것만 대표 CB로 INSERT

    # 5-0-1: 대표 CB에 없는 인수자만 저장할 임시 테이블 생성
    await session.execute(text("""
        CREATE TEMP TABLE subscribers_to_migrate AS
        WITH keep_cbs AS (
            SELECT DISTINCT ON (company_id, bond_name)
                id as keep_id, company_id, bond_name
            FROM convertible_bonds
            ORDER BY company_id, bond_name, issue_date DESC NULLS LAST, issue_amount DESC NULLS LAST
        ),
        remove_cbs AS (
            SELECT cb.id as remove_id, k.keep_id
            FROM convertible_bonds cb
            JOIN keep_cbs k ON cb.company_id = k.company_id AND cb.bond_name = k.bond_name
            WHERE cb.id != k.keep_id
        )
        SELECT DISTINCT ON (r.keep_id, s.subscriber_name)
            r.keep_id as new_cb_id,
            s.subscriber_name,
            s.subscriber_type,
            s.is_related_party,
            s.relationship_to_company,
            s.subscription_amount,
            s.subscription_quantity
        FROM cb_subscribers s
        JOIN remove_cbs r ON s.cb_id = r.remove_id
        -- 대표 CB에 동일 이름 인수자가 없는 경우만
        WHERE NOT EXISTS (
            SELECT 1 FROM cb_subscribers s2
            WHERE s2.cb_id = r.keep_id AND s2.subscriber_name = s.subscriber_name
        )
        ORDER BY r.keep_id, s.subscriber_name, s.subscription_amount DESC NULLS LAST
    """))

    # 5-0-2: 삭제 대상 CB의 인수자 모두 삭제
    delete_subscribers = await session.execute(text("""
        WITH keep_cbs AS (
            SELECT DISTINCT ON (company_id, bond_name) id as keep_id
            FROM convertible_bonds
            ORDER BY company_id, bond_name, issue_date DESC NULLS LAST, issue_amount DESC NULLS LAST
        ),
        remove_cbs AS (
            SELECT id FROM convertible_bonds WHERE id NOT IN (SELECT keep_id FROM keep_cbs)
        )
        DELETE FROM cb_subscribers WHERE cb_id IN (SELECT id FROM remove_cbs)
    """))
    print(f"  삭제 대상 CB 인수자 제거: {delete_subscribers.rowcount}건")

    # 5-0-3: 저장해둔 고유 인수자를 대표 CB에 삽입 (UUID 생성 포함)
    insert_result = await session.execute(text("""
        INSERT INTO cb_subscribers (id, cb_id, subscriber_name, subscriber_type, is_related_party, relationship_to_company, subscription_amount, subscription_quantity)
        SELECT gen_random_uuid(), new_cb_id, subscriber_name, subscriber_type, is_related_party, relationship_to_company, subscription_amount, subscription_quantity
        FROM subscribers_to_migrate
    """))
    print(f"  인수자 마이그레이션: {insert_result.rowcount}건")

    # 5-0-4: 임시 테이블 삭제
    await session.execute(text("DROP TABLE IF EXISTS subscribers_to_migrate"))

    # 5-3: 중복 CB 삭제
    delete_cb_result = await session.execute(text("""
        DELETE FROM convertible_bonds
        WHERE id NOT IN (
            SELECT DISTINCT ON (company_id, bond_name) id
            FROM convertible_bonds
            ORDER BY company_id, bond_name, issue_date DESC NULLS LAST, issue_amount DESC NULLS LAST
        )
    """))
    print(f"  중복 CB 삭제: {delete_cb_result.rowcount}건")

    await session.commit()

    # Step 6: 결과 검증
    stats_after = await get_duplicate_stats(session)
    print(f"\n[정제 완료]")
    print(f"  CB 레코드: {stats_before['total_cbs']} → {stats_after['total_cbs']}")
    print(f"  중복 레코드: {stats_before['duplicates']} → {stats_after['duplicates']}")

    # 인수자 수 확인
    sub_result = await session.execute(text("SELECT COUNT(*) FROM cb_subscribers"))
    sub_count = sub_result.scalar()
    print(f"  인수자 레코드: {sub_count}")

    print(f"\n[롤백 방법]")
    print(f"  python cleanup_duplicate_cbs.py --rollback --timestamp {backup_ts}")


async def rollback(session: AsyncSession, timestamp: str):
    """롤백 실행"""
    print(f"\n[롤백] timestamp: {timestamp}")

    # 백업 테이블 존재 확인
    check = await session.execute(text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'convertible_bonds_backup_{timestamp}'
        )
    """))
    if not check.scalar():
        print(f"[오류] 백업 테이블을 찾을 수 없습니다: convertible_bonds_backup_{timestamp}")
        return

    # 롤백 실행
    await session.execute(text("TRUNCATE cb_subscribers CASCADE"))
    await session.execute(text("TRUNCATE convertible_bonds CASCADE"))

    await session.execute(text(f"""
        INSERT INTO convertible_bonds SELECT * FROM convertible_bonds_backup_{timestamp}
    """))
    await session.execute(text(f"""
        INSERT INTO cb_subscribers SELECT * FROM cb_subscribers_backup_{timestamp}
    """))

    await session.commit()

    # 확인
    stats = await get_duplicate_stats(session)
    print(f"[롤백 완료]")
    print(f"  CB 레코드: {stats['total_cbs']}")
    print(f"  중복 레코드: {stats['duplicates']}")


async def list_backups(session: AsyncSession):
    """백업 테이블 목록"""
    result = await session.execute(text("""
        SELECT table_name,
               pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
        FROM information_schema.tables
        WHERE table_name LIKE 'convertible_bonds_backup_%'
           OR table_name LIKE 'cb_subscribers_backup_%'
        ORDER BY table_name DESC
    """))

    backups = result.fetchall()
    if not backups:
        print("\n[백업 없음]")
        return

    print("\n[백업 테이블 목록]")
    for b in backups:
        print(f"  {b[0]} ({b[1]})")


async def main():
    parser = argparse.ArgumentParser(description="CB 중복 데이터 정제")
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 시뮬레이션만 실행")
    parser.add_argument("--execute", action="store_true", help="실제 정제 실행")
    parser.add_argument("--rollback", action="store_true", help="롤백 실행")
    parser.add_argument("--timestamp", type=str, help="롤백할 백업 timestamp")
    parser.add_argument("--list-backups", action="store_true", help="백업 테이블 목록")

    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        if args.list_backups:
            await list_backups(session)
        elif args.rollback:
            if not args.timestamp:
                print("[오류] --timestamp 필수")
                await list_backups(session)
                return
            await rollback(session, args.timestamp)
        elif args.execute:
            confirm = input("\n정말 실행하시겠습니까? (yes/no): ")
            if confirm.lower() == "yes":
                await execute_cleanup(session, dry_run=False)
            else:
                print("취소됨")
        else:
            # 기본: dry-run
            await execute_cleanup(session, dry_run=True)


if __name__ == "__main__":
    asyncio.run(main())
