#!/usr/bin/env python3
"""
Priority 1-1: disclosures 테이블 채우기
DART API에서 공시 목록을 수집하여 disclosures 테이블에 적재
"""
import asyncio
import aiohttp
import asyncpg
import logging
import os
from datetime import datetime, timedelta
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DART_BASE_URL = "https://opendart.fss.or.kr/api"
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')


class DisclosureCollector:
    def __init__(self):
        self.stats = {'fetched': 0, 'saved': 0, 'errors': 0, 'skipped': 0}

    async def fetch_disclosures(self, session, bgn_de, end_de, page=1):
        """DART 공시 목록 조회"""
        try:
            params = {
                'crtfc_key': DART_API_KEY,
                'bgn_de': bgn_de,
                'end_de': end_de,
                'page_no': str(page),
                'page_count': '100'
            }
            async with session.get(f"{DART_BASE_URL}/list.json", params=params) as r:
                if r.status == 200:
                    data = await r.json()
                    if data.get('status') == '000':
                        return data.get('list', []), int(data.get('total_page', 1))
        except Exception as e:
            logger.error(f"공시 목록 조회 실패: {e}")
        return [], 0

    async def save_disclosures(self, conn, disclosures):
        """공시 저장"""
        saved = 0
        for d in disclosures:
            try:
                # 이미 존재하는지 확인
                exists = await conn.fetchval(
                    "SELECT 1 FROM disclosures WHERE rcept_no = $1",
                    d.get('rcept_no')
                )
                if exists:
                    self.stats['skipped'] += 1
                    continue

                # 회사가 존재하는지 확인
                company_exists = await conn.fetchval(
                    "SELECT 1 FROM companies WHERE corp_code = $1",
                    d.get('corp_code')
                )
                if not company_exists:
                    self.stats['skipped'] += 1
                    continue

                await conn.execute("""
                    INSERT INTO disclosures (
                        id, rcept_no, corp_code, corp_name, stock_code,
                        report_nm, rcept_dt, flr_nm, rm, crawled_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (rcept_no) DO NOTHING
                """,
                    str(uuid.uuid4()),
                    d.get('rcept_no'),
                    d.get('corp_code'),
                    d.get('corp_name'),
                    d.get('stock_code') if d.get('stock_code') != ' ' else None,
                    d.get('report_nm'),
                    d.get('rcept_dt'),
                    d.get('flr_nm'),
                    d.get('rm'),
                    datetime.now()
                )
                saved += 1
                self.stats['saved'] += 1
            except Exception as e:
                logger.error(f"저장 실패 {d.get('rcept_no')}: {e}")
                self.stats['errors'] += 1
        return saved

    async def collect_period(self, session, conn, start_date, end_date):
        """기간별 공시 수집"""
        bgn_de = start_date.strftime('%Y%m%d')
        end_de = end_date.strftime('%Y%m%d')

        logger.info(f"수집 기간: {bgn_de} ~ {end_de}")

        # 첫 페이지로 전체 페이지 수 확인
        disclosures, total_pages = await self.fetch_disclosures(session, bgn_de, end_de, 1)

        if disclosures:
            await self.save_disclosures(conn, disclosures)
            self.stats['fetched'] += len(disclosures)

        # 나머지 페이지 수집
        for page in range(2, min(total_pages + 1, 100)):  # 최대 100페이지
            await asyncio.sleep(0.3)  # rate limit
            disclosures, _ = await self.fetch_disclosures(session, bgn_de, end_de, page)
            if disclosures:
                await self.save_disclosures(conn, disclosures)
                self.stats['fetched'] += len(disclosures)

            if page % 10 == 0:
                logger.info(f"  페이지 {page}/{total_pages} 완료")


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365, help="수집할 기간 (일)")
    parser.add_argument("--chunk-days", type=int, default=30, help="청크 크기 (일)")
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("DART 공시 목록 수집 시작")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)
    collector = DisclosureCollector()

    try:
        # 기간별로 나눠서 수집 (DART API 제한)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)

        current = start_date
        async with aiohttp.ClientSession() as session:
            while current < end_date:
                chunk_end = min(current + timedelta(days=args.chunk_days), end_date)
                await collector.collect_period(session, conn, current, chunk_end)
                current = chunk_end + timedelta(days=1)
                await asyncio.sleep(1)

        # 결과
        logger.info("\n" + "=" * 80)
        logger.info("공시 수집 완료")
        logger.info(f"조회: {collector.stats['fetched']:,}개")
        logger.info(f"저장: {collector.stats['saved']:,}개")
        logger.info(f"스킵: {collector.stats['skipped']:,}개")
        logger.info(f"오류: {collector.stats['errors']:,}개")

        # 현재 상태
        count = await conn.fetchval("SELECT COUNT(*) FROM disclosures")
        logger.info(f"\n현재 disclosures 테이블: {count:,}개")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
