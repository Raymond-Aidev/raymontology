#!/usr/bin/env python3
"""
계열사 관계 데이터 수집
- DART API affiliate (계열회사 현황) 사용
- affiliates 테이블에 저장
"""
import asyncio
import aiohttp
import asyncpg
import logging
import sys
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DART_API_KEY = "1fd0cd12ae5260eafb7de3130ad91f16aa61911b"
AFFILIATE_URL = "https://opendart.fss.or.kr/api/affiliates.json"


class AffiliateCollector:
    """계열사 데이터 수집기"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stats = {
            'companies_processed': 0,
            'affiliates_found': 0,
            'affiliates_saved': 0,
            'errors': 0,
            'no_data': 0
        }

    async def get_affiliates(
        self,
        session: aiohttp.ClientSession,
        corp_code: str,
        corp_name: str
    ):
        """특정 기업의 계열사 현황 조회"""
        try:
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bsns_year': '2024',  # 최근 사업연도
                'reprt_code': '11011'  # 사업보고서
            }

            async with session.get(AFFILIATE_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"{corp_name} ({corp_code}): HTTP {response.status}")
                    self.stats['errors'] += 1
                    return []

                data = await response.json()

                # API 응답 확인
                if data.get('status') != '000':
                    # 013: 데이터 없음 (정상)
                    if data.get('status') == '013':
                        self.stats['no_data'] += 1
                    else:
                        logger.debug(f"{corp_name}: {data.get('message', 'Unknown error')}")
                        self.stats['errors'] += 1
                    return []

                affiliates = data.get('list', [])
                self.stats['affiliates_found'] += len(affiliates)

                return affiliates

        except Exception as e:
            logger.error(f"Error getting affiliates for {corp_name}: {e}")
            self.stats['errors'] += 1
            return []

    async def save_affiliates(
        self,
        conn: asyncpg.Connection,
        parent_company_id: str,
        parent_corp_code: str,
        affiliates: list
    ):
        """계열사 데이터 저장"""
        for aff in affiliates:
            try:
                # 계열사 회사 정보
                affiliate_name = aff.get('aflt_nm', '').strip()
                if not affiliate_name:
                    continue

                # 계열사 회사가 companies 테이블에 있는지 확인
                # 없으면 생성
                affiliate_corp_code = aff.get('aflt_corp_code')

                # 계열사 회사 ID 조회 또는 생성
                if affiliate_corp_code:
                    affiliate_company_id = await conn.fetchval("""
                        SELECT id FROM companies WHERE corp_code = $1
                    """, affiliate_corp_code)

                    if not affiliate_company_id:
                        # 계열사 회사 생성
                        affiliate_company_id = await conn.fetchval("""
                            INSERT INTO companies (
                                id, name, corp_code, created_at, updated_at
                            )
                            VALUES (uuid_generate_v4(), $1, $2, NOW(), NOW())
                            ON CONFLICT (corp_code) DO UPDATE
                            SET name = EXCLUDED.name,
                                updated_at = NOW()
                            RETURNING id
                        """, affiliate_name, affiliate_corp_code)
                else:
                    # corp_code 없으면 이름으로만 조회/생성
                    affiliate_company_id = await conn.fetchval("""
                        SELECT id FROM companies WHERE name = $1
                    """, affiliate_name)

                    if not affiliate_company_id:
                        affiliate_company_id = await conn.fetchval("""
                            INSERT INTO companies (
                                id, name, created_at, updated_at
                            )
                            VALUES (uuid_generate_v4(), $1, NOW(), NOW())
                            RETURNING id
                        """, affiliate_name)

                # 계열사 관계 저장
                await conn.execute("""
                    INSERT INTO affiliates (
                        id,
                        parent_company_id,
                        affiliate_company_id,
                        affiliate_name,
                        business_number,
                        relationship_type,
                        is_listed,
                        ownership_ratio,
                        voting_rights_ratio,
                        total_assets,
                        revenue,
                        net_income,
                        source_date,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        uuid_generate_v4(),
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW()
                    )
                    ON CONFLICT (parent_company_id, affiliate_company_id)
                    DO UPDATE SET
                        affiliate_name = EXCLUDED.affiliate_name,
                        business_number = EXCLUDED.business_number,
                        relationship_type = EXCLUDED.relationship_type,
                        is_listed = EXCLUDED.is_listed,
                        ownership_ratio = EXCLUDED.ownership_ratio,
                        voting_rights_ratio = EXCLUDED.voting_rights_ratio,
                        total_assets = EXCLUDED.total_assets,
                        revenue = EXCLUDED.revenue,
                        net_income = EXCLUDED.net_income,
                        source_date = EXCLUDED.source_date,
                        updated_at = NOW()
                """,
                    parent_company_id,
                    affiliate_company_id,
                    affiliate_name,
                    aff.get('bsns_no'),  # 사업자등록번호
                    aff.get('aflt_gbn'),  # 계열회사구분
                    aff.get('lst_yn') == 'Y',  # 상장여부
                    self._parse_float(aff.get('h_rate')),  # 지분율
                    self._parse_float(aff.get('vote_rate')),  # 의결권비율
                    self._parse_bigint(aff.get('tot_aset')),  # 총자산
                    self._parse_bigint(aff.get('revenue')),  # 매출액
                    self._parse_bigint(aff.get('net_income')),  # 당기순이익
                    '2024'  # source_date
                )

                self.stats['affiliates_saved'] += 1

            except Exception as e:
                logger.error(f"Error saving affiliate {affiliate_name}: {e}")
                self.stats['errors'] += 1

    def _parse_float(self, value):
        """문자열을 float로 변환"""
        if not value or value == '-':
            return None
        try:
            # 쉼표 제거
            cleaned = str(value).replace(',', '').strip()
            return float(cleaned) if cleaned else None
        except:
            return None

    def _parse_bigint(self, value):
        """문자열을 bigint로 변환"""
        if not value or value == '-':
            return None
        try:
            # 쉼표 제거, 백만원 단위 → 원 단위 변환
            cleaned = str(value).replace(',', '').strip()
            if cleaned:
                # DART API는 백만원 단위로 제공
                return int(float(cleaned) * 1000000)
            return None
        except:
            return None

    async def collect_all(self, companies: list, batch_size: int = 5):
        """모든 기업의 계열사 정보 수집"""
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(companies), batch_size):
                batch = companies[i:i + batch_size]

                tasks = []
                for comp in batch:
                    task = self.get_affiliates(
                        session,
                        comp['corp_code'],
                        comp['name']
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks)

                # 결과 저장
                import os
                db_url = os.getenv(
                    'DATABASE_URL',
                    'postgresql://postgres:dev_password@postgres:5432/raymontology_dev'
                )
                db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
                conn = await asyncpg.connect(db_url)

                try:
                    for comp, affiliates in zip(batch, results):
                        if affiliates:
                            await self.save_affiliates(
                                conn,
                                comp['id'],
                                comp['corp_code'],
                                affiliates
                            )
                finally:
                    await conn.close()

                self.stats['companies_processed'] += len(batch)

                # 진행 상황 출력
                if self.stats['companies_processed'] % 100 == 0:
                    logger.info(
                        f"Progress: {self.stats['companies_processed']}/{len(companies)} - "
                        f"Affiliates found: {self.stats['affiliates_found']}, "
                        f"Saved: {self.stats['affiliates_saved']}, "
                        f"No data: {self.stats['no_data']}, "
                        f"Errors: {self.stats['errors']}"
                    )

                # API rate limit (초당 5개)
                await asyncio.sleep(1)


async def main():
    """메인 함수"""
    logger.info("=" * 80)
    logger.info("계열사 관계 데이터 수집")
    logger.info("=" * 80)

    # PostgreSQL 연결
    import os
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dev_password@postgres:5432/raymontology_dev'
    )
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        # 상장 기업 목록 조회 (corp_code 있는 기업만)
        companies = await conn.fetch("""
            SELECT id, corp_code, name, ticker, market
            FROM companies
            WHERE corp_code IS NOT NULL
            ORDER BY market, ticker
        """)

        logger.info(f"Total companies to process: {len(companies)}")

        # 계열사 수집기 생성
        collector = AffiliateCollector(DART_API_KEY)

        # 계열사 데이터 수집
        await collector.collect_all([dict(c) for c in companies], batch_size=5)

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("계열사 데이터 수집 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 기업: {collector.stats['companies_processed']:,}")
        logger.info(f"발견된 계열사: {collector.stats['affiliates_found']:,}")
        logger.info(f"저장된 계열사: {collector.stats['affiliates_saved']:,}")
        logger.info(f"계열사 없음: {collector.stats['no_data']:,}")
        logger.info(f"오류: {collector.stats['errors']:,}")

        # 저장된 데이터 확인
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_affiliates,
                COUNT(DISTINCT parent_company_id) as companies_with_affiliates,
                COUNT(DISTINCT affiliate_company_id) as unique_affiliates,
                AVG(ownership_ratio) as avg_ownership,
                SUM(total_assets) as total_assets
            FROM affiliates
        """)

        logger.info(f"\nDB 저장 현황:")
        logger.info(f"  총 계열사 관계: {stats['total_affiliates']:,}")
        logger.info(f"  계열사 보유 기업: {stats['companies_with_affiliates']:,}")
        logger.info(f"  고유 계열사: {stats['unique_affiliates']:,}")
        if stats['avg_ownership']:
            logger.info(f"  평균 지분율: {stats['avg_ownership']:.2f}%")
        if stats['total_assets']:
            logger.info(f"  총 자산: {stats['total_assets']:,.0f} 원")

        # 샘플 확인
        samples = await conn.fetch("""
            SELECT
                pc.name as parent_name,
                a.affiliate_name,
                a.ownership_ratio,
                a.is_listed
            FROM affiliates a
            JOIN companies pc ON a.parent_company_id = pc.id
            WHERE a.ownership_ratio IS NOT NULL
            ORDER BY a.ownership_ratio DESC
            LIMIT 5
        """)

        logger.info(f"\n계열사 샘플 (지분율 높은 순):")
        for row in samples:
            logger.info(
                f"  {row['parent_name']} → {row['affiliate_name']} "
                f"(지분율: {row['ownership_ratio']:.2f}%, "
                f"상장: {'Y' if row['is_listed'] else 'N'})"
            )

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
