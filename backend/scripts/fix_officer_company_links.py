#!/usr/bin/env python3
"""
기존 임원 데이터에 company_id 연결
"""
import asyncio
import sys
import json
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.officers import Officer
from app.models.companies import Company

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OfficerCompanyLinker:
    """임원-회사 연결 수정기"""

    def __init__(self):
        self.stats = {
            "total_officers": 0,
            "officers_with_source": 0,
            "meta_files_found": 0,
            "companies_matched": 0,
            "officers_updated": 0,
            "no_stock_code": 0,
            "no_company_found": 0,
        }
        # 회사 캐시 (ticker -> company_id)
        self.company_cache: Dict[str, str] = {}
        self.data_dir = Path("./data/dart")

    async def load_company_cache(self, db: AsyncSession):
        """회사 ticker 캐시 로드"""
        result = await db.execute(
            select(Company.id, Company.ticker).where(Company.ticker.isnot(None))
        )
        companies = result.all()

        for company_id, ticker in companies:
            self.company_cache[ticker] = str(company_id)

        logger.info(f"✓ {len(self.company_cache):,}개 회사 캐시 로드 완료")

    async def fix_links(self):
        """임원-회사 링크 수정"""
        logger.info("=" * 60)
        logger.info("임원-회사 연결 수정 시작")
        logger.info("=" * 60)

        async with AsyncSessionLocal() as db:
            # 1. 회사 캐시 로드
            await self.load_company_cache(db)

            # 2. 모든 임원 조회
            result = await db.execute(select(Officer))
            officers = result.scalars().all()
            self.stats["total_officers"] = len(officers)

            logger.info(f"총 {len(officers):,}명 임원 처리 중...")

            batch_size = 1000
            for i in range(0, len(officers), batch_size):
                batch = officers[i:i + batch_size]
                await self._process_batch(db, batch)

                # 중간 진행 상황 출력
                if (i + batch_size) % 10000 == 0:
                    logger.info(f"  진행: {i + batch_size:,}/{len(officers):,}명")

            # 커밋
            await db.commit()

        # 최종 통계
        self._print_stats()

    async def _process_batch(self, db: AsyncSession, officers: list):
        """배치 처리"""
        for officer in officers:
            source_report = officer.properties.get('source_report') if officer.properties else None

            if not source_report:
                continue

            self.stats["officers_with_source"] += 1

            # 메타 파일 찾기
            meta_files = list(self.data_dir.rglob(f"{source_report}*_meta.json"))

            if not meta_files:
                continue

            self.stats["meta_files_found"] += 1

            try:
                with open(meta_files[0], 'r') as f:
                    meta_data = json.load(f)

                stock_code = meta_data.get("stock_code")

                if not stock_code:
                    self.stats["no_stock_code"] += 1
                    continue

                # 캐시에서 회사 찾기
                company_id = self.company_cache.get(stock_code)

                if not company_id:
                    self.stats["no_company_found"] += 1
                    continue

                # 임원 업데이트
                if officer.current_company_id != company_id:
                    officer.current_company_id = company_id
                    self.stats["officers_updated"] += 1
                    self.stats["companies_matched"] += 1

            except Exception as e:
                logger.error(f"Failed to process officer {officer.name}: {e}")

    def _print_stats(self):
        """통계 출력"""
        logger.info("=" * 60)
        logger.info("임원-회사 연결 수정 완료")
        logger.info("=" * 60)
        logger.info(f"총 임원 수:             {self.stats['total_officers']:,}명")
        logger.info(f"source_report 있음:     {self.stats['officers_with_source']:,}명")
        logger.info(f"meta 파일 발견:         {self.stats['meta_files_found']:,}건")
        logger.info(f"stock_code 없음:        {self.stats['no_stock_code']:,}건")
        logger.info(f"회사 매칭 성공:         {self.stats['companies_matched']:,}명")
        logger.info(f"회사 매칭 실패:         {self.stats['no_company_found']:,}건")
        logger.info(f"임원 업데이트:          {self.stats['officers_updated']:,}명")
        logger.info("=" * 60)


async def main():
    linker = OfficerCompanyLinker()
    await linker.fix_links()


if __name__ == "__main__":
    asyncio.run(main())
