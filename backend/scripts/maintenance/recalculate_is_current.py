#!/usr/bin/env python3
"""
recalculate_is_current.py - is_current 필드 재계산

문제: 기존 파싱에서 is_current를 date.today() 기준으로 계산하여
     과거 데이터가 잘못된 is_current 값을 가지고 있음

해결: source_report_date 기준으로 is_current 재계산
     - term_end_date가 NULL이면 is_current = true
     - term_end_date >= source_report_date이면 is_current = true
     - 그 외 is_current = false

사용법:
    # 테스트 (수정하지 않고 확인만)
    python scripts/maintenance/recalculate_is_current.py --dry-run

    # 실제 수정 실행
    python scripts/maintenance/recalculate_is_current.py

    # 특정 회사만 수정
    python scripts/maintenance/recalculate_is_current.py --company "한미반도체"
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway"
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def get_current_stats(conn: asyncpg.Connection) -> dict:
    """현재 is_current 상태 통계"""
    stats = await conn.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN is_current = true THEN 1 END) as current_true,
            COUNT(CASE WHEN is_current = false THEN 1 END) as current_false,
            COUNT(CASE WHEN source_report_date IS NULL THEN 1 END) as no_report_date
        FROM officer_positions
    """)
    return dict(stats)


async def get_mismatched_records(conn: asyncpg.Connection, company_name: str = None, limit: int = 100) -> list:
    """잘못된 is_current 값을 가진 레코드 조회"""
    if company_name:
        query = """
            SELECT
                op.id,
                c.name as company_name,
                o.name as officer_name,
                op.position,
                op.term_end_date,
                op.source_report_date,
                op.is_current as current_value,
                CASE
                    WHEN op.term_end_date IS NULL THEN true
                    WHEN op.source_report_date IS NULL THEN op.is_current  -- 변경 불가
                    WHEN op.term_end_date >= op.source_report_date THEN true
                    ELSE false
                END as correct_value
            FROM officer_positions op
            JOIN officers o ON op.officer_id = o.id
            JOIN companies c ON op.company_id = c.id
            WHERE c.name = $1
            AND op.source_report_date IS NOT NULL
            AND (
                (op.term_end_date IS NULL AND op.is_current = false)
                OR (op.term_end_date IS NOT NULL AND op.term_end_date >= op.source_report_date AND op.is_current = false)
                OR (op.term_end_date IS NOT NULL AND op.term_end_date < op.source_report_date AND op.is_current = true)
            )
            ORDER BY c.name, o.name
            LIMIT $2
        """
        return await conn.fetch(query, company_name, limit)
    else:
        query = """
            SELECT
                op.id,
                c.name as company_name,
                o.name as officer_name,
                op.position,
                op.term_end_date,
                op.source_report_date,
                op.is_current as current_value,
                CASE
                    WHEN op.term_end_date IS NULL THEN true
                    WHEN op.source_report_date IS NULL THEN op.is_current
                    WHEN op.term_end_date >= op.source_report_date THEN true
                    ELSE false
                END as correct_value
            FROM officer_positions op
            JOIN officers o ON op.officer_id = o.id
            JOIN companies c ON op.company_id = c.id
            WHERE op.source_report_date IS NOT NULL
            AND (
                (op.term_end_date IS NULL AND op.is_current = false)
                OR (op.term_end_date IS NOT NULL AND op.term_end_date >= op.source_report_date AND op.is_current = false)
                OR (op.term_end_date IS NOT NULL AND op.term_end_date < op.source_report_date AND op.is_current = true)
            )
            ORDER BY c.name, o.name
            LIMIT $1
        """
        return await conn.fetch(query, limit)


async def count_mismatched(conn: asyncpg.Connection, company_name: str = None) -> int:
    """잘못된 레코드 수 카운트"""
    if company_name:
        query = """
            SELECT COUNT(*)
            FROM officer_positions op
            JOIN companies c ON op.company_id = c.id
            WHERE c.name = $1
            AND op.source_report_date IS NOT NULL
            AND (
                (op.term_end_date IS NULL AND op.is_current = false)
                OR (op.term_end_date IS NOT NULL AND op.term_end_date >= op.source_report_date AND op.is_current = false)
                OR (op.term_end_date IS NOT NULL AND op.term_end_date < op.source_report_date AND op.is_current = true)
            )
        """
        return await conn.fetchval(query, company_name)
    else:
        query = """
            SELECT COUNT(*)
            FROM officer_positions
            WHERE source_report_date IS NOT NULL
            AND (
                (term_end_date IS NULL AND is_current = false)
                OR (term_end_date IS NOT NULL AND term_end_date >= source_report_date AND is_current = false)
                OR (term_end_date IS NOT NULL AND term_end_date < source_report_date AND is_current = true)
            )
        """
        return await conn.fetchval(query)


async def recalculate_is_current(conn: asyncpg.Connection, dry_run: bool = True, company_name: str = None) -> dict:
    """is_current 필드 재계산"""

    # 수정 전 통계
    before_stats = await get_current_stats(conn)
    mismatch_count = await count_mismatched(conn, company_name)

    logger.info("=" * 60)
    logger.info("is_current 재계산")
    logger.info("=" * 60)
    logger.info(f"수정 전 통계:")
    logger.info(f"  - 전체 레코드: {before_stats['total']:,}")
    logger.info(f"  - is_current=true: {before_stats['current_true']:,}")
    logger.info(f"  - is_current=false: {before_stats['current_false']:,}")
    logger.info(f"  - source_report_date 없음: {before_stats['no_report_date']:,}")
    logger.info(f"  - 수정 필요 레코드: {mismatch_count:,}")

    if mismatch_count == 0:
        logger.info("수정이 필요한 레코드가 없습니다.")
        return {"before": before_stats, "updated": 0}

    # 샘플 출력
    samples = await get_mismatched_records(conn, company_name, limit=10)
    if samples:
        logger.info("\n수정 대상 샘플:")
        for s in samples[:5]:
            logger.info(
                f"  - {s['company_name']} / {s['officer_name']} / {s['position']}: "
                f"term_end={s['term_end_date']}, report={s['source_report_date']}, "
                f"현재={s['current_value']} → 수정={s['correct_value']}"
            )

    if dry_run:
        logger.info("\n[DRY-RUN] 실제 수정하지 않음")
        return {"before": before_stats, "updated": 0, "would_update": mismatch_count}

    # 실제 수정 실행
    if company_name:
        update_query = """
            UPDATE officer_positions op
            SET is_current = CASE
                WHEN op.term_end_date IS NULL THEN true
                WHEN op.term_end_date >= op.source_report_date THEN true
                ELSE false
            END,
            updated_at = NOW()
            FROM companies c
            WHERE op.company_id = c.id
            AND c.name = $1
            AND op.source_report_date IS NOT NULL
            AND (
                (op.term_end_date IS NULL AND op.is_current = false)
                OR (op.term_end_date IS NOT NULL AND op.term_end_date >= op.source_report_date AND op.is_current = false)
                OR (op.term_end_date IS NOT NULL AND op.term_end_date < op.source_report_date AND op.is_current = true)
            )
        """
        result = await conn.execute(update_query, company_name)
    else:
        update_query = """
            UPDATE officer_positions
            SET is_current = CASE
                WHEN term_end_date IS NULL THEN true
                WHEN term_end_date >= source_report_date THEN true
                ELSE false
            END,
            updated_at = NOW()
            WHERE source_report_date IS NOT NULL
            AND (
                (term_end_date IS NULL AND is_current = false)
                OR (term_end_date IS NOT NULL AND term_end_date >= source_report_date AND is_current = false)
                OR (term_end_date IS NOT NULL AND term_end_date < source_report_date AND is_current = true)
            )
        """
        result = await conn.execute(update_query)

    updated_count = int(result.split()[-1])

    # 수정 후 통계
    after_stats = await get_current_stats(conn)

    logger.info(f"\n수정 완료: {updated_count:,}개 레코드")
    logger.info(f"수정 후 통계:")
    logger.info(f"  - is_current=true: {before_stats['current_true']:,} → {after_stats['current_true']:,}")
    logger.info(f"  - is_current=false: {before_stats['current_false']:,} → {after_stats['current_false']:,}")

    return {"before": before_stats, "after": after_stats, "updated": updated_count}


async def main():
    parser = argparse.ArgumentParser(description="is_current 필드 재계산")
    parser.add_argument("--dry-run", action="store_true", help="실제 수정하지 않고 확인만")
    parser.add_argument("--company", type=str, help="특정 회사만 수정")
    args = parser.parse_args()

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        result = await recalculate_is_current(conn, dry_run=args.dry_run, company_name=args.company)

        if args.dry_run:
            logger.info(f"\n실제 수정하려면: python {sys.argv[0]}")
        else:
            logger.info("\n재계산 완료!")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
