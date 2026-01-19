#!/usr/bin/env python3
"""회사 market/sector 정보 보강 (DART API 기업개황)"""
import asyncio
import aiohttp
import asyncpg
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DART_BASE_URL = "https://opendart.fss.or.kr/api"
DB_URL = 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev'


async def get_company_info(session, corp_code):
    """DART 기업개황 조회"""
    try:
        params = {'crtfc_key': DART_API_KEY, 'corp_code': corp_code}
        async with session.get(f"{DART_BASE_URL}/company.json", params=params) as r:
            if r.status == 200:
                data = await r.json()
                if data.get('status') == '000':
                    return data
    except:
        pass
    return None


async def main():
    logger.info("=" * 80)
    logger.info("회사 market/sector 정보 보강 시작")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)
    
    try:
        # market이 없는 회사 조회
        companies = await conn.fetch("""
            SELECT id, corp_code, name FROM companies
            WHERE corp_code IS NOT NULL AND market IS NULL
        """)
        
        logger.info(f"보강 대상: {len(companies)}개")
        
        updated = 0
        async with aiohttp.ClientSession() as session:
            for i, company in enumerate(companies):
                info = await get_company_info(session, company['corp_code'])
                
                if info:
                    corp_cls = info.get('corp_cls', '')
                    market = None
                    if corp_cls == 'Y':
                        market = 'KOSPI'
                    elif corp_cls == 'K':
                        market = 'KOSDAQ'
                    elif corp_cls == 'N':
                        market = 'KONEX'
                    elif corp_cls == 'E':
                        market = 'ETF'
                    
                    if market:
                        await conn.execute("""
                            UPDATE companies SET 
                                market = $1,
                                sector = COALESCE($2, sector),
                                updated_at = NOW()
                            WHERE id = $3
                        """, market, info.get('induty_code'), company['id'])
                        updated += 1
                
                if (i + 1) % 100 == 0:
                    logger.info(f"진행: {i + 1}/{len(companies)} - 업데이트: {updated}")
                
                await asyncio.sleep(0.3)  # API rate limit
        
        logger.info(f"\n완료: {updated}개 업데이트")
        
        # 결과 확인
        stats = await conn.fetchrow("""
            SELECT COUNT(*) as total, COUNT(market) as has_market
            FROM companies
        """)
        logger.info(f"Companies: 총 {stats['total']}개, market {stats['has_market']}개 ({100*stats['has_market']/stats['total']:.1f}%)")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
