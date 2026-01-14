#!/usr/bin/env python3
"""
재무제표 데이터 수집 - 최근 2년치
- DART API fnlttSinglAcnt 사용
- 2023, 2024년 재무제표 수집
"""
import asyncio
import aiohttp
import asyncpg
import logging
import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DART_API_KEY = "1fd0cd12ae5260eafb7de3130ad91f16aa61911b"
FINANCIAL_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"


class FinancialCollector:
    def __init__(self, api_key):
        self.api_key = api_key
        self.stats = {'processed': 0, 'saved': 0, 'errors': 0, 'no_data': 0}

    async def get_financial(self, session, corp_code, year):
        try:
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bsns_year': year,
                'reprt_code': '11011',
                'fs_div': 'CFS'
            }
            async with session.get(FINANCIAL_URL, params=params) as r:
                if r.status != 200:
                    self.stats['errors'] += 1
                    return None
                data = await r.json()
                if data.get('status') != '000':
                    if data.get('status') == '013':
                        self.stats['no_data'] += 1
                    else:
                        self.stats['errors'] += 1
                    return None
                return data.get('list', [])
        except Exception as e:
            logger.error(f"Error: {e}")
            self.stats['errors'] += 1
            return None

    def parse_data(self, statements):
        result = {}
        account_map = {
            '자산총계': 'total_assets',
            '부채총계': 'total_liabilities',
            '자본총계': 'total_equity',
            '매출액': 'revenue',
            '영업이익': 'operating_profit',
            '당기순이익': 'net_income'
        }
        for stmt in statements:
            name = stmt.get('account_nm', '').strip()
            amt = stmt.get('thstrm_amount', '').replace(',', '').strip()
            if not amt or amt == '-':
                continue
            try:
                amount = int(amt)
                for key, field in account_map.items():
                    if key in name:
                        result[field] = amount
                        break
            except:
                pass
        return result

    async def save_fs(self, conn, company_id, year, data):
        try:
            await conn.execute("""
                INSERT INTO financial_statements (
                    id, company_id, fiscal_year, quarter, statement_date, report_type,
                    total_assets, total_liabilities, total_equity,
                    revenue, operating_profit, net_income,
                    created_at, updated_at
                )
                VALUES (
                    uuid_generate_v4(), $1, $2, 'Q4', $3, 'ANNUAL',
                    $4, $5, $6, $7, $8, $9, NOW(), NOW()
                )
                ON CONFLICT (company_id, fiscal_year, quarter, report_type)
                DO UPDATE SET
                    total_assets = EXCLUDED.total_assets,
                    total_liabilities = EXCLUDED.total_liabilities,
                    total_equity = EXCLUDED.total_equity,
                    revenue = EXCLUDED.revenue,
                    operating_profit = EXCLUDED.operating_profit,
                    net_income = EXCLUDED.net_income,
                    updated_at = NOW()
            """, company_id, year, datetime.date(int(year), 12, 31),
                data.get('total_assets'), data.get('total_liabilities'),
                data.get('total_equity'), data.get('revenue'),
                data.get('operating_profit'), data.get('net_income'))
            self.stats['saved'] += 1
        except Exception as e:
            logger.error(f"Save error: {e}")
            self.stats['errors'] += 1

    async def collect_all(self, companies, years=['2023', '2024']):
        async with aiohttp.ClientSession() as session:
            for year in years:
                logger.info(f"\n{year}년 재무제표 수집 중...")
                for i in range(0, len(companies), 3):
                    batch = companies[i:i+3]
                    tasks = [self.get_financial(session, c['corp_code'], year) for c in batch]
                    results = await asyncio.gather(*tasks)
                    
                    import os
                    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev').replace('postgresql+asyncpg://', 'postgresql://')
                    conn = await asyncpg.connect(db_url)
                    try:
                        for c, stmts in zip(batch, results):
                            if stmts:
                                data = self.parse_data(stmts)
                                if data:
                                    await self.save_fs(conn, c['id'], int(year), data)
                    finally:
                        await conn.close()
                    
                    self.stats['processed'] += len(batch)
                    if self.stats['processed'] % 100 == 0:
                        logger.info(f"Progress: {self.stats['processed']}/{len(companies)} - Saved: {self.stats['saved']}")
                    await asyncio.sleep(1)


async def main():
    logger.info("="*80)
    logger.info("재무제표 데이터 수집 (2023-2024)")
    logger.info("="*80)
    
    import os
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)
    
    try:
        companies = await conn.fetch("SELECT id, corp_code, name FROM companies WHERE corp_code IS NOT NULL")
        logger.info(f"기업 수: {len(companies)}")
        
        collector = FinancialCollector(DART_API_KEY)
        await collector.collect_all([dict(c) for c in companies])
        
        logger.info("\n"+"="*80)
        logger.info(f"완료: {collector.stats['saved']}개 저장, {collector.stats['errors']}개 오류")
        logger.info("="*80)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
