#!/usr/bin/env python3
"""
임원-회사 연결 수정 V2 (메모리 캐싱 + 배치 업데이트)
"""
import asyncio
import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from app.database import AsyncSessionLocal
from app.models.officers import Officer
from app.models.companies import Company

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def fix_links():
    """메모리 캐싱을 사용한 빠른 매핑"""
    logger.info("=" * 60)
    logger.info("임원-회사 연결 수정 V2")
    logger.info("=" * 60)

    # 1. 메타 파일에서 rcept_no -> stock_code 매핑 생성
    logger.info("[1/5] 메타 파일 읽기 중...")
    data_dir = Path("./data/dart")
    rcept_to_stock = {}

    meta_files = list(data_dir.rglob("*_meta.json"))
    logger.info(f"발견한 메타 파일: {len(meta_files):,}개")

    for i, meta_file in enumerate(meta_files):
        if i % 10000 == 0 and i > 0:
            logger.info(f"  진행: {i:,}/{len(meta_files):,} 파일")

        try:
            with open(meta_file, 'r') as f:
                meta_data = json.load(f)
                rcept_no = meta_data.get("rcept_no")
                stock_code = meta_data.get("stock_code")

                if rcept_no and stock_code:
                    rcept_to_stock[rcept_no] = stock_code
        except Exception:
            continue

    logger.info(f"✓ {len(rcept_to_stock):,}개 매핑 생성 완료")

    async with AsyncSessionLocal() as db:
        # 2. stock_code -> company_id 매핑 생성
        logger.info("[2/5] Companies 로드 중...")
        result = await db.execute(
            select(Company.id, Company.ticker)
            .where(Company.ticker.isnot(None))
        )
        companies = result.all()

        stock_to_company_id = {ticker: str(company_id) for company_id, ticker in companies}
        logger.info(f"✓ {len(stock_to_company_id):,}개 회사 로드 완료")

        # 3. 임원 데이터 배치 업데이트
        logger.info("[3/5] 임원 데이터 로드 및 매핑 중...")
        result = await db.execute(select(Officer))
        officers = result.scalars().all()

        update_count = 0
        matched_count = 0

        for officer in officers:
            source_report = officer.properties.get('source_report') if officer.properties else None
            if not source_report:
                continue

            # source_report -> stock_code -> company_id
            stock_code = rcept_to_stock.get(source_report)
            if stock_code:
                company_id = stock_to_company_id.get(stock_code)
                if company_id:
                    officer.current_company_id = company_id
                    update_count += 1
                    matched_count += 1

        logger.info(f"✓ {matched_count:,}명 매칭 완료")

        # 4. 커밋
        logger.info("[4/5] DB에 저장 중...")
        await db.commit()
        logger.info(f"✓ {update_count:,}명 업데이트 완료")

        # 5. 결과 확인
        logger.info("[5/5] 결과 확인 중...")
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

        # 회사별 임원 수 TOP 10
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
    await fix_links()


if __name__ == "__main__":
    asyncio.run(main())
