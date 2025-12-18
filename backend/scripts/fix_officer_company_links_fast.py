#!/usr/bin/env python3
"""
임원-회사 연결 고속 수정 (SQL 기반)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import AsyncSessionLocal

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def fix_links_with_sql():
    """SQL을 사용하여 빠르게 임원-회사 연결"""
    logger.info("=" * 60)
    logger.info("임원-회사 연결 수정 시작 (SQL 기반)")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        # 1. Disclosures 테이블을 통한 매핑
        # properties->>'source_report'가 disclosures.rcept_no와 매칭되고
        # disclosures.corp_code가 companies.corp_code와 매칭
        logger.info("Disclosures 테이블을 통한 매핑 시도 중...")

        update_query = text("""
            UPDATE officers o
            SET current_company_id = c.id
            FROM companies c
            WHERE o.properties->>'source_report' IN (
                SELECT d.rcept_no
                FROM disclosures d
                WHERE d.corp_code = c.corp_code
            )
            AND o.current_company_id IS NULL
        """)

        try:
            result = await db.execute(update_query)
            await db.commit()
            logger.info(f"✓ Disclosures 매핑: {result.rowcount:,}명 업데이트")
        except Exception as e:
            logger.error(f"Disclosures 매핑 실패: {e}")
            await db.rollback()

        # 2. 매칭 결과 확인
        check_query = text("""
            SELECT
                COUNT(*) as total,
                COUNT(current_company_id) as matched
            FROM officers
        """)

        result = await db.execute(check_query)
        row = result.first()

        logger.info("=" * 60)
        logger.info(f"총 임원: {row.total:,}명")
        logger.info(f"매칭된 임원: {row.matched:,}명 ({row.matched/row.total*100:.1f}%)")
        logger.info("=" * 60)

        # 3. 회사별 임원 수 TOP 10
        top_query = text("""
            SELECT
                c.name as company_name,
                COUNT(o.id) as officer_count
            FROM officers o
            JOIN companies c ON o.current_company_id = c.id
            GROUP BY c.name
            ORDER BY officer_count DESC
            LIMIT 10
        """)

        result = await db.execute(top_query)
        top_companies = result.all()

        if top_companies:
            logger.info("임원이 많은 회사 TOP 10:")
            for company_name, count in top_companies:
                logger.info(f"  {company_name}: {count}명")
        logger.info("=" * 60)


async def main():
    await fix_links_with_sql()


if __name__ == "__main__":
    asyncio.run(main())
