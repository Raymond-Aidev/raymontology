#!/usr/bin/env python3
"""
임원 포지션 통합 스크립트

목표: 동일 임원 + 동일 회사 + 동일 임기의 중복 레코드를 1개로 통합
      직책 변동 이력은 position_history JSONB 컬럼에 보존

문제 상황:
- 현재 Unique 제약: (officer_id, company_id, term_start_date, source_disclosure_id)
- source_disclosure_id가 포함되어 공시마다 새 레코드가 생성됨
- 예: 이성욱 @ 세아메카닉스 → 7개 레코드 (상무→전무→부대표→대표이사 승진 이력)

해결 방안:
1. 동일 임원 + 동일 회사 + 동일 임기(term_start_date) 그룹 식별
2. 각 그룹에서 최신 공시 기준 레코드를 primary로 선정
3. 나머지 레코드의 직책을 position_history JSONB에 보존
4. 중복 레코드 삭제
5. Unique 제약 조건 변경 (source_disclosure_id 제외)

사용법:
    python scripts/maintenance/consolidate_officer_positions.py --dry-run  # 테스트 (변경 없음)
    python scripts/maintenance/consolidate_officer_positions.py            # 실제 실행
"""

import asyncio
import asyncpg
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")


async def get_duplicate_groups(conn) -> list:
    """
    동일 임원 + 동일 회사 + 동일 임기(term_start_date)의 중복 그룹 식별

    Returns:
        list of dict: 각 중복 그룹의 정보
    """
    query = '''
        SELECT
            officer_id,
            company_id,
            term_start_date,
            array_agg(id ORDER BY source_disclosure_id DESC) as position_ids,
            array_agg(position ORDER BY source_disclosure_id DESC) as positions,
            array_agg(source_disclosure_id ORDER BY source_disclosure_id DESC) as disclosures,
            array_agg(term_end_date ORDER BY source_disclosure_id DESC) as term_ends,
            COUNT(*) as duplicate_count
        FROM officer_positions
        GROUP BY officer_id, company_id, term_start_date
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
    '''

    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def get_officer_company_names(conn, officer_id: str, company_id: str) -> tuple:
    """임원명과 회사명 조회"""
    query = '''
        SELECT o.name as officer_name, c.name as company_name
        FROM officers o, companies c
        WHERE o.id = $1 AND c.id = $2
    '''
    row = await conn.fetchrow(query, officer_id, company_id)
    if row:
        return row['officer_name'], row['company_name']
    return 'Unknown', 'Unknown'


async def consolidate_group(conn, group: dict, dry_run: bool = False) -> dict:
    """
    단일 중복 그룹 통합

    Args:
        conn: DB 연결
        group: 중복 그룹 정보
        dry_run: True면 실제 변경 없이 시뮬레이션

    Returns:
        dict: 통합 결과 (deleted_count, history_items)
    """
    position_ids = group['position_ids']
    positions = group['positions']
    disclosures = group['disclosures']
    term_ends = group['term_ends']

    # 첫 번째 레코드가 primary (가장 최신 공시 기준)
    primary_id = position_ids[0]
    primary_position = positions[0]

    # 나머지 레코드들의 직책을 history로 수집
    history = []
    ids_to_delete = []

    for i in range(1, len(position_ids)):
        pos_id = position_ids[i]
        position = positions[i]
        disclosure_id = disclosures[i]
        term_end = term_ends[i]

        # 직책이 다른 경우만 history에 추가 (동일 직책은 중복이므로 제외)
        if position != primary_position:
            history.append({
                'position': position,
                'source_disclosure_id': disclosure_id,
                'term_end_date': str(term_end) if term_end else None
            })

        ids_to_delete.append(pos_id)

    if not dry_run:
        # 1. history 업데이트 (기존 history와 병합)
        if history:
            await conn.execute('''
                UPDATE officer_positions
                SET position_history = position_history || $1::jsonb,
                    updated_at = NOW()
                WHERE id = $2
            ''', json.dumps(history), primary_id)

        # 2. 중복 레코드 삭제
        for pos_id in ids_to_delete:
            await conn.execute('DELETE FROM officer_positions WHERE id = $1', pos_id)

    return {
        'primary_id': str(primary_id),
        'primary_position': primary_position,
        'deleted_count': len(ids_to_delete),
        'history_items': len(history)
    }


async def run_consolidation_sql(conn, dry_run: bool = False) -> dict:
    """
    SQL 기반 배치 통합 (훨씬 빠름)

    전략:
    1. 임시 테이블에 각 그룹의 primary 레코드 ID 계산
    2. 단일 DELETE로 중복 레코드 제거
    3. 단일 UPDATE로 position_history 업데이트
    """
    logger.info("SQL 기반 배치 통합 시작...")

    # Step 1: 각 중복 그룹에서 유지할 primary 레코드 식별 (최신 공시 기준)
    # ROW_NUMBER를 사용하여 각 그룹에서 rn=1인 것이 primary
    create_temp = '''
        CREATE TEMP TABLE primary_positions AS
        SELECT id, officer_id, company_id, term_start_date, position, source_disclosure_id
        FROM (
            SELECT
                id, officer_id, company_id, term_start_date, position, source_disclosure_id,
                ROW_NUMBER() OVER (
                    PARTITION BY officer_id, company_id, term_start_date
                    ORDER BY source_disclosure_id DESC
                ) as rn
            FROM officer_positions
        ) ranked
        WHERE rn = 1
    '''

    # Step 2: 삭제할 레코드 수 계산
    count_to_delete = '''
        SELECT COUNT(*) FROM officer_positions op
        WHERE NOT EXISTS (
            SELECT 1 FROM primary_positions pp WHERE pp.id = op.id
        )
    '''

    # Step 3: position_history 생성 쿼리 (각 primary에 대해 이전 직책 수집)
    # JSONB 배열로 집계
    update_history = '''
        WITH history_data AS (
            SELECT
                pp.id as primary_id,
                jsonb_agg(
                    jsonb_build_object(
                        'position', op.position,
                        'source_disclosure_id', op.source_disclosure_id,
                        'term_end_date', op.term_end_date::text
                    )
                    ORDER BY op.source_disclosure_id DESC
                ) FILTER (WHERE op.position != pp.position) as history
            FROM primary_positions pp
            JOIN officer_positions op ON
                op.officer_id = pp.officer_id
                AND op.company_id = pp.company_id
                AND (op.term_start_date = pp.term_start_date
                     OR (op.term_start_date IS NULL AND pp.term_start_date IS NULL))
                AND op.id != pp.id
            GROUP BY pp.id
        )
        UPDATE officer_positions op
        SET position_history = COALESCE(hd.history, '[]'::jsonb),
            updated_at = NOW()
        FROM history_data hd
        WHERE op.id = hd.primary_id
    '''

    # Step 4: 중복 레코드 삭제
    delete_duplicates = '''
        DELETE FROM officer_positions op
        WHERE NOT EXISTS (
            SELECT 1 FROM primary_positions pp WHERE pp.id = op.id
        )
    '''

    if dry_run:
        # Dry-run: 임시 테이블만 생성하고 수만 세기
        await conn.execute(create_temp)
        delete_count = await conn.fetchval(count_to_delete)
        await conn.execute('DROP TABLE IF EXISTS primary_positions')
        return {'deleted': delete_count, 'updated': 0}

    # 실제 실행
    async with conn.transaction():
        # 임시 테이블 생성
        await conn.execute(create_temp)

        # 삭제할 레코드 수 확인
        delete_count = await conn.fetchval(count_to_delete)
        logger.info(f"삭제 예정 레코드 수: {delete_count:,}")

        # history 업데이트
        await conn.execute(update_history)
        logger.info("position_history 업데이트 완료")

        # 중복 삭제
        await conn.execute(delete_duplicates)
        logger.info(f"중복 레코드 {delete_count:,}개 삭제 완료")

        # 임시 테이블 정리
        await conn.execute('DROP TABLE IF EXISTS primary_positions')

    return {'deleted': delete_count}


async def run_consolidation(dry_run: bool = False):
    """메인 통합 프로세스"""
    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}임원 포지션 통합 시작")

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # 1. 현재 상태 확인
        total_before = await conn.fetchval('SELECT COUNT(*) FROM officer_positions')
        logger.info(f"현재 총 레코드 수: {total_before:,}")

        # 2. 중복 그룹 수 확인
        duplicate_count = await conn.fetchval('''
            SELECT COUNT(*) FROM (
                SELECT officer_id, company_id, term_start_date
                FROM officer_positions
                GROUP BY officer_id, company_id, term_start_date
                HAVING COUNT(*) > 1
            ) sub
        ''')
        logger.info(f"중복 그룹 수: {duplicate_count:,}")

        if duplicate_count == 0:
            logger.info("중복 그룹이 없습니다. 종료합니다.")
            return

        # 3. 상위 10개 그룹 상세 출력
        duplicate_groups = await get_duplicate_groups(conn)
        logger.info("\n=== 상위 10개 중복 그룹 ===")
        for i, group in enumerate(duplicate_groups[:10]):
            officer_name, company_name = await get_officer_company_names(
                conn, str(group['officer_id']), str(group['company_id'])
            )
            logger.info(
                f"  {i+1}. {officer_name} @ {company_name}: "
                f"{group['duplicate_count']}개 → 직책: {group['positions']}"
            )

        # 4. SQL 배치 통합 실행 (훨씬 빠름)
        result = await run_consolidation_sql(conn, dry_run=dry_run)

        # 5. 결과 확인
        total_after = await conn.fetchval('SELECT COUNT(*) FROM officer_positions')

        logger.info("\n=== 통합 결과 ===")
        logger.info(f"{'[DRY-RUN] ' if dry_run else ''}처리된 중복 그룹: {duplicate_count:,}")
        logger.info(f"{'[DRY-RUN] ' if dry_run else ''}삭제된 레코드: {result['deleted']:,}")
        logger.info(f"레코드 수 변화: {total_before:,} → {total_after:,} ({total_after - total_before:+,})")

        # 6. 통합 후 검증 (position_count > 3인 케이스 재확인)
        high_count_query = '''
            SELECT o.name, c.name as company, COUNT(*) as cnt
            FROM officer_positions op
            JOIN officers o ON op.officer_id = o.id
            JOIN companies c ON op.company_id = c.id
            GROUP BY o.name, c.name
            HAVING COUNT(*) > 3
            ORDER BY cnt DESC
            LIMIT 10
        '''
        high_count_rows = await conn.fetch(high_count_query)

        if high_count_rows:
            logger.warning(f"\n⚠️ 여전히 position_count > 3인 케이스: {len(high_count_rows)}개")
            for row in high_count_rows:
                logger.warning(f"  - {row['name']} @ {row['company']}: {row['cnt']}개")
        else:
            logger.info("\n✅ position_count > 3인 케이스: 0개 (목표 달성)")

    finally:
        await conn.close()


async def verify_backup():
    """백업 테이블 존재 여부 확인"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.fetchval('''
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'officer_positions_backup_20260104'
        ''')
        return result > 0
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='임원 포지션 중복 통합')
    parser.add_argument('--dry-run', action='store_true', help='실제 변경 없이 시뮬레이션')
    parser.add_argument('--skip-backup-check', action='store_true', help='백업 확인 건너뛰기')
    args = parser.parse_args()

    # 백업 확인
    if not args.skip_backup_check and not args.dry_run:
        if not asyncio.run(verify_backup()):
            logger.error("❌ 백업 테이블 'officer_positions_backup_20260104'이 없습니다.")
            logger.error("   먼저 백업을 생성하세요:")
            logger.error("   CREATE TABLE officer_positions_backup_20260104 AS SELECT * FROM officer_positions;")
            sys.exit(1)
        logger.info("✅ 백업 테이블 확인 완료")

    asyncio.run(run_consolidation(dry_run=args.dry_run))


if __name__ == '__main__':
    main()
