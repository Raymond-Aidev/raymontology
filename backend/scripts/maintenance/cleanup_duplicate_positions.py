"""
cleanup_duplicate_positions.py - 중복 officer_positions 레코드 정리

문제: 동일 임원이 동일 회사에서 분기별로 중복 레코드가 생성됨
해결: 동일 (officer_id, company_id) 조합에서 최신 source_report_date 레코드만 유지

사용법:
    # 테스트 (삭제하지 않고 확인만)
    python scripts/maintenance/cleanup_duplicate_positions.py --dry-run

    # 실제 삭제 실행
    python scripts/maintenance/cleanup_duplicate_positions.py

    # 특정 회사만 정리
    python scripts/maintenance/cleanup_duplicate_positions.py --company "한미반도체"
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

import asyncpg

# 환경 변수에서 DATABASE_URL 가져오기
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def get_duplicate_stats(conn: asyncpg.Connection, company_name: str = None) -> dict:
    """중복 레코드 통계 조회"""
    if company_name:
        query = """
            SELECT
                c.name as company_name,
                o.name as officer_name,
                COUNT(*) as record_count
            FROM officer_positions op
            JOIN officers o ON op.officer_id = o.id
            JOIN companies c ON op.company_id = c.id
            WHERE c.name = $1
            GROUP BY c.id, c.name, o.id, o.name
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """
        rows = await conn.fetch(query, company_name)
    else:
        query = """
            SELECT
                c.name as company_name,
                o.name as officer_name,
                COUNT(*) as record_count
            FROM officer_positions op
            JOIN officers o ON op.officer_id = o.id
            JOIN companies c ON op.company_id = c.id
            GROUP BY c.id, c.name, o.id, o.name
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 50
        """
        rows = await conn.fetch(query)

    total_duplicates = sum(row['record_count'] - 1 for row in rows)

    return {
        "duplicate_pairs": len(rows),
        "records_to_delete": total_duplicates,
        "top_duplicates": rows[:10]
    }


async def cleanup_duplicates(conn: asyncpg.Connection, dry_run: bool = True, company_name: str = None) -> dict:
    """중복 레코드 정리

    각 (officer_id, company_id) 조합에서 source_report_date가 가장 최신인 레코드만 유지
    """
    # 삭제 대상 조회
    if company_name:
        count_query = """
            SELECT COUNT(*) FROM officer_positions op1
            WHERE EXISTS (
                SELECT 1 FROM officer_positions op2
                JOIN companies c ON op2.company_id = c.id
                WHERE op2.officer_id = op1.officer_id
                  AND op2.company_id = op1.company_id
                  AND op2.id != op1.id
                  AND c.name = $1
                  AND (
                      op2.source_report_date > op1.source_report_date
                      OR (op2.source_report_date = op1.source_report_date AND op2.is_current = true AND op1.is_current = false)
                      OR (op2.source_report_date = op1.source_report_date AND op2.is_current = op1.is_current AND op2.id > op1.id)
                  )
            )
        """
        delete_count = await conn.fetchval(count_query, company_name)
    else:
        count_query = """
            SELECT COUNT(*) FROM officer_positions op1
            WHERE EXISTS (
                SELECT 1 FROM officer_positions op2
                WHERE op2.officer_id = op1.officer_id
                  AND op2.company_id = op1.company_id
                  AND op2.id != op1.id
                  AND (
                      op2.source_report_date > op1.source_report_date
                      OR (op2.source_report_date = op1.source_report_date AND op2.is_current = true AND op1.is_current = false)
                      OR (op2.source_report_date = op1.source_report_date AND op2.is_current = op1.is_current AND op2.id > op1.id)
                  )
            )
        """
        delete_count = await conn.fetchval(count_query)

    logger.info(f"삭제 대상 레코드: {delete_count}건")

    if dry_run:
        logger.info("DRY RUN 모드 - 실제 삭제 없이 종료")
        return {"deleted": 0, "would_delete": delete_count}

    # 실제 삭제 실행
    if company_name:
        delete_query = """
            DELETE FROM officer_positions op1
            WHERE EXISTS (
                SELECT 1 FROM officer_positions op2
                JOIN companies c ON op2.company_id = c.id
                WHERE op2.officer_id = op1.officer_id
                  AND op2.company_id = op1.company_id
                  AND op2.id != op1.id
                  AND c.name = $1
                  AND (
                      op2.source_report_date > op1.source_report_date
                      OR (op2.source_report_date = op1.source_report_date AND op2.is_current = true AND op1.is_current = false)
                      OR (op2.source_report_date = op1.source_report_date AND op2.is_current = op1.is_current AND op2.id > op1.id)
                  )
            )
        """
        result = await conn.execute(delete_query, company_name)
    else:
        delete_query = """
            DELETE FROM officer_positions op1
            WHERE EXISTS (
                SELECT 1 FROM officer_positions op2
                WHERE op2.officer_id = op1.officer_id
                  AND op2.company_id = op1.company_id
                  AND op2.id != op1.id
                  AND (
                      op2.source_report_date > op1.source_report_date
                      OR (op2.source_report_date = op1.source_report_date AND op2.is_current = true AND op1.is_current = false)
                      OR (op2.source_report_date = op1.source_report_date AND op2.is_current = op1.is_current AND op2.id > op1.id)
                  )
            )
        """
        result = await conn.execute(delete_query)

    deleted = int(result.split()[-1]) if result else 0
    logger.info(f"삭제 완료: {deleted}건")

    return {"deleted": deleted}


async def main():
    parser = argparse.ArgumentParser(description="중복 officer_positions 레코드 정리")
    parser.add_argument("--dry-run", action="store_true", help="실제 삭제 없이 테스트만 실행")
    parser.add_argument("--company", type=str, help="특정 회사만 정리 (회사명)")
    parser.add_argument("--stats-only", action="store_true", help="통계만 조회")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("officer_positions 중복 레코드 정리 스크립트")
    logger.info(f"실행 시간: {datetime.now().isoformat()}")
    logger.info(f"모드: {'DRY RUN' if args.dry_run else '실제 삭제'}")
    if args.company:
        logger.info(f"대상 회사: {args.company}")
    logger.info("=" * 60)

    # asyncpg URL 변환
    db_url = DATABASE_URL.replace("postgresql://", "").replace("postgres://", "")
    if "@" in db_url:
        auth, host_part = db_url.rsplit("@", 1)
        user, password = auth.split(":", 1)
        host_port, database = host_part.rsplit("/", 1)
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 5432

    conn = await asyncpg.connect(
        host=host, port=port, user=user, password=password, database=database
    )

    try:
        # 통계 조회
        stats = await get_duplicate_stats(conn, args.company)
        logger.info(f"중복 발생 임원-회사 조합: {stats['duplicate_pairs']}개")
        logger.info(f"삭제 예정 레코드: {stats['records_to_delete']}건")

        if stats['top_duplicates']:
            logger.info("\n상위 중복 현황:")
            for row in stats['top_duplicates']:
                logger.info(f"  {row['company_name']} - {row['officer_name']}: {row['record_count']}개 레코드")

        if args.stats_only:
            return

        # 정리 실행
        result = await cleanup_duplicates(conn, dry_run=args.dry_run, company_name=args.company)

        if args.dry_run:
            logger.info(f"\n[DRY RUN] 삭제 예정: {result['would_delete']}건")
            logger.info("실제 삭제를 원하면 --dry-run 옵션 없이 실행하세요")
        else:
            logger.info(f"\n[완료] 삭제된 레코드: {result['deleted']}건")

            # 정리 후 통계 재확인
            after_stats = await get_duplicate_stats(conn, args.company)
            logger.info(f"정리 후 남은 중복: {after_stats['duplicate_pairs']}개 조합")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
