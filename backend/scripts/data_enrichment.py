#!/usr/bin/env python3
"""
데이터 보완 스크립트

팔란티어 온톨로지 분석을 위한 데이터 품질 개선:
1. 임원: birth_date, gender 추가
2. 전환사채: issue_date, maturity_date, interest_rate, conversion_price 추가
3. 계열사: ownership_ratio, voting_rights_ratio 추가
4. 회사: sector, market 추가
5. 중복 레코드 정리
"""
import asyncio
import aiohttp
import asyncpg
import logging
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DART API 설정
DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DART_BASE_URL = "https://opendart.fss.or.kr/api"

# DB 설정
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')


class DataEnrichment:
    """데이터 보완 클래스"""

    def __init__(self):
        self.stats = {
            'officers_updated': 0,
            'cb_updated': 0,
            'affiliates_updated': 0,
            'companies_updated': 0,
            'duplicates_removed': 0,
            'errors': 0
        }

    async def run_all(self, conn: asyncpg.Connection, session: aiohttp.ClientSession):
        """모든 보완 작업 실행"""
        logger.info("=" * 80)
        logger.info("데이터 보완 작업 시작")
        logger.info("=" * 80)

        # 1. 회사 정보 보완 (sector, market)
        await self.enrich_companies(conn, session)

        # 2. 임원 정보 보완 (birth_date, gender)
        await self.enrich_officers(conn, session)

        # 3. 전환사채 정보 보완
        await self.enrich_convertible_bonds(conn, session)

        # 4. 계열사 정보 보완
        await self.enrich_affiliates(conn, session)

        # 5. 중복 레코드 정리
        await self.cleanup_duplicates(conn)

        # 최종 통계
        self.print_stats()

    async def enrich_companies(self, conn: asyncpg.Connection, session: aiohttp.ClientSession):
        """회사 정보 보완 (sector, market)"""
        logger.info("\n[1/5] 회사 정보 보완 (sector, market)")

        # sector, market이 없는 회사 조회
        companies = await conn.fetch("""
            SELECT id, corp_code, ticker, name
            FROM companies
            WHERE corp_code IS NOT NULL
            AND (sector IS NULL OR market IS NULL)
            LIMIT 500
        """)

        logger.info(f"보완 대상 회사: {len(companies)}개")

        for i, company in enumerate(companies):
            try:
                # DART 기업 개황 API 호출
                params = {
                    'crtfc_key': DART_API_KEY,
                    'corp_code': company['corp_code']
                }

                async with session.get(f"{DART_BASE_URL}/company.json", params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get('status') == '000':
                            # 업종 (sector)
                            sector = data.get('induty_code', '')  # 업종코드
                            industry = data.get('adres', '')[:100] if data.get('adres') else None

                            # 시장 구분
                            corp_cls = data.get('corp_cls', '')
                            market = None
                            if corp_cls == 'Y':
                                market = 'KOSPI'
                            elif corp_cls == 'K':
                                market = 'KOSDAQ'
                            elif corp_cls == 'N':
                                market = 'KONEX'
                            elif corp_cls == 'E':
                                market = 'ETF'

                            # 업데이트
                            await conn.execute("""
                                UPDATE companies
                                SET sector = COALESCE($1, sector),
                                    market = COALESCE($2, market),
                                    industry = COALESCE($3, industry),
                                    updated_at = NOW()
                                WHERE id = $4
                            """, sector, market, industry, company['id'])

                            self.stats['companies_updated'] += 1

                # API rate limit
                await asyncio.sleep(0.3)

                if (i + 1) % 50 == 0:
                    logger.info(f"  진행: {i + 1}/{len(companies)}")

            except Exception as e:
                logger.error(f"회사 {company['name']} 보완 실패: {e}")
                self.stats['errors'] += 1

        logger.info(f"  완료: {self.stats['companies_updated']}개 업데이트")

    async def enrich_officers(self, conn: asyncpg.Connection, session: aiohttp.ClientSession):
        """임원 정보 보완 (birth_date, gender)"""
        logger.info("\n[2/5] 임원 정보 보완 (birth_date, gender)")

        # birth_date가 없는 임원 조회
        officers = await conn.fetch("""
            SELECT o.id, o.name, o.position, op.company_id, op.metadata
            FROM officers o
            JOIN officer_positions op ON o.id = op.officer_id
            WHERE o.birth_date IS NULL
            AND op.metadata IS NOT NULL
            LIMIT 5000
        """)

        logger.info(f"보완 대상 임원: {len(officers)}명")

        updated = 0
        for officer in officers:
            try:
                metadata = officer['metadata']
                if isinstance(metadata, str):
                    import json
                    metadata = json.loads(metadata)

                birth_date = metadata.get('birth_year_month') or metadata.get('birth_date')
                gender = metadata.get('gender')

                if birth_date or gender:
                    await conn.execute("""
                        UPDATE officers
                        SET birth_date = COALESCE($1, birth_date),
                            gender = COALESCE($2, gender),
                            updated_at = NOW()
                        WHERE id = $3
                    """, birth_date, gender, officer['id'])

                    # officer_positions에도 저장
                    await conn.execute("""
                        UPDATE officer_positions
                        SET birth_date = COALESCE($1, birth_date),
                            gender = COALESCE($2, gender)
                        WHERE officer_id = $3
                    """, birth_date, gender, officer['id'])

                    updated += 1

            except Exception as e:
                logger.error(f"임원 {officer['name']} 보완 실패: {e}")
                self.stats['errors'] += 1

        self.stats['officers_updated'] = updated
        logger.info(f"  완료: {updated}명 업데이트")

        # DART API로 추가 보완 (사업보고서에서 임원 정보 다시 파싱)
        await self._enrich_officers_from_dart(conn, session)

    async def _enrich_officers_from_dart(self, conn: asyncpg.Connection, session: aiohttp.ClientSession):
        """DART API로 임원 정보 추가 보완"""
        logger.info("  DART API로 임원 정보 추가 보완 중...")

        # birth_date가 없는 임원이 있는 회사 조회
        companies = await conn.fetch("""
            SELECT DISTINCT c.id, c.corp_code, c.name
            FROM companies c
            JOIN officer_positions op ON op.company_id = c.id
            JOIN officers o ON o.id = op.officer_id
            WHERE c.corp_code IS NOT NULL
            AND o.birth_date IS NULL
            LIMIT 100
        """)

        for company in companies:
            try:
                # 임원 현황 API
                params = {
                    'crtfc_key': DART_API_KEY,
                    'corp_code': company['corp_code'],
                    'bsns_year': '2024',
                    'reprt_code': '11011'  # 사업보고서
                }

                async with session.get(f"{DART_BASE_URL}/exctvSttus.json", params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get('status') == '000':
                            for exec_info in data.get('list', []):
                                name = exec_info.get('nm', '').strip()
                                birth_ym = exec_info.get('birth_ym', '')  # 출생년월
                                gender = exec_info.get('sexdstn', '')  # 성별

                                if name and (birth_ym or gender):
                                    # 해당 임원 찾아서 업데이트
                                    await conn.execute("""
                                        UPDATE officers o
                                        SET birth_date = COALESCE($1, o.birth_date),
                                            gender = COALESCE($2, o.gender),
                                            updated_at = NOW()
                                        FROM officer_positions op
                                        WHERE o.id = op.officer_id
                                        AND op.company_id = $3
                                        AND o.name = $4
                                        AND o.birth_date IS NULL
                                    """, birth_ym, gender, company['id'], name)

                                    self.stats['officers_updated'] += 1

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"회사 {company['name']} 임원 보완 실패: {e}")
                self.stats['errors'] += 1

    async def enrich_convertible_bonds(self, conn: asyncpg.Connection, session: aiohttp.ClientSession):
        """전환사채 정보 보완"""
        logger.info("\n[3/5] 전환사채 정보 보완")

        # 상세 정보가 없는 CB 조회
        cbs = await conn.fetch("""
            SELECT cb.id, cb.company_id, cb.source_disclosure_id, cb.bond_name,
                   c.corp_code, c.name as company_name
            FROM convertible_bonds cb
            JOIN companies c ON cb.company_id = c.id
            WHERE (cb.issue_date IS NULL OR cb.maturity_date IS NULL OR cb.conversion_price IS NULL)
            AND cb.source_disclosure_id IS NOT NULL
            LIMIT 500
        """)

        logger.info(f"보완 대상 전환사채: {len(cbs)}개")

        for i, cb in enumerate(cbs):
            try:
                # 공시 문서 다운로드
                params = {
                    'crtfc_key': DART_API_KEY,
                    'rcept_no': cb['source_disclosure_id']
                }

                async with session.get(f"{DART_BASE_URL}/document.xml", params=params) as response:
                    if response.status == 200:
                        content = await response.read()

                        # ZIP 해제 및 파싱
                        try:
                            import zipfile
                            import io

                            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                                xml_filename = zf.namelist()[0]
                                xml_bytes = zf.read(xml_filename)

                                try:
                                    text = xml_bytes.decode('euc-kr')
                                except:
                                    text = xml_bytes.decode('utf-8', errors='ignore')

                                # CB 정보 파싱
                                cb_data = self._parse_cb_details(text)

                                if cb_data:
                                    await conn.execute("""
                                        UPDATE convertible_bonds
                                        SET issue_date = COALESCE($1, issue_date),
                                            maturity_date = COALESCE($2, maturity_date),
                                            interest_rate = COALESCE($3, interest_rate),
                                            conversion_price = COALESCE($4, conversion_price),
                                            updated_at = NOW()
                                        WHERE id = $5
                                    """,
                                        cb_data.get('issue_date'),
                                        cb_data.get('maturity_date'),
                                        cb_data.get('interest_rate'),
                                        cb_data.get('conversion_price'),
                                        cb['id']
                                    )
                                    self.stats['cb_updated'] += 1

                        except zipfile.BadZipFile:
                            pass

                await asyncio.sleep(1.0)  # API rate limit

                if (i + 1) % 50 == 0:
                    logger.info(f"  진행: {i + 1}/{len(cbs)}")

            except Exception as e:
                logger.error(f"CB {cb['source_disclosure_id']} 보완 실패: {e}")
                self.stats['errors'] += 1

        logger.info(f"  완료: {self.stats['cb_updated']}개 업데이트")

    def _parse_cb_details(self, text: str) -> Optional[Dict]:
        """CB 상세 정보 파싱"""
        result = {}

        # 발행일
        issue_patterns = [
            r'발행일\s*[:\s]*(\d{4})[년.-]?\s*(\d{1,2})[월.-]?\s*(\d{1,2})',
            r'발행일자\s*[:\s]*(\d{4})[년.-]?\s*(\d{1,2})[월.-]?\s*(\d{1,2})',
        ]
        for pattern in issue_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    y, m, d = match.groups()
                    result['issue_date'] = datetime(int(y), int(m), int(d)).date()
                    break
                except:
                    pass

        # 만기일
        maturity_patterns = [
            r'만기일\s*[:\s]*(\d{4})[년.-]?\s*(\d{1,2})[월.-]?\s*(\d{1,2})',
            r'상환일\s*[:\s]*(\d{4})[년.-]?\s*(\d{1,2})[월.-]?\s*(\d{1,2})',
        ]
        for pattern in maturity_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    y, m, d = match.groups()
                    result['maturity_date'] = datetime(int(y), int(m), int(d)).date()
                    break
                except:
                    pass

        # 이자율
        interest_patterns = [
            r'이자율\s*[:\s]*([0-9.]+)\s*%',
            r'표면이자율\s*[:\s]*([0-9.]+)\s*%',
            r'표면금리\s*[:\s]*([0-9.]+)\s*%',
        ]
        for pattern in interest_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    result['interest_rate'] = float(match.group(1))
                    break
                except:
                    pass

        # 전환가액
        conversion_patterns = [
            r'전환가(?:액|격)\s*[:\s]*([0-9,]+)\s*원',
            r'전환가\s*[:\s]*([0-9,]+)\s*원',
        ]
        for pattern in conversion_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    result['conversion_price'] = int(match.group(1).replace(',', ''))
                    break
                except:
                    pass

        return result if result else None

    async def enrich_affiliates(self, conn: asyncpg.Connection, session: aiohttp.ClientSession):
        """계열사 정보 보완"""
        logger.info("\n[4/5] 계열사 정보 보완 (지분율, 재무정보)")

        # 지분율이 없는 계열사 관계 조회
        affiliates = await conn.fetch("""
            SELECT a.id, a.parent_company_id, a.affiliate_name, a.source_date,
                   c.corp_code, c.name as parent_name
            FROM affiliates a
            JOIN companies c ON a.parent_company_id = c.id
            WHERE a.ownership_ratio IS NULL
            AND c.corp_code IS NOT NULL
            LIMIT 500
        """)

        logger.info(f"보완 대상 계열사: {len(affiliates)}개")

        processed_parents = set()

        for affiliate in affiliates:
            parent_id = str(affiliate['parent_company_id'])

            # 이미 처리한 모회사는 스킵
            if parent_id in processed_parents:
                continue

            processed_parents.add(parent_id)

            try:
                # DART 계열회사 현황 API
                params = {
                    'crtfc_key': DART_API_KEY,
                    'corp_code': affiliate['corp_code'],
                    'bsns_year': '2024',
                    'reprt_code': '11011'
                }

                async with session.get(f"{DART_BASE_URL}/affiliates.json", params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get('status') == '000':
                            for aff_info in data.get('list', []):
                                aff_name = aff_info.get('aflt_nm', '').strip()

                                if aff_name:
                                    ownership = self._parse_float(aff_info.get('h_rate'))
                                    voting_rights = self._parse_float(aff_info.get('vote_rate'))
                                    total_assets = self._parse_bigint(aff_info.get('tot_aset'))
                                    revenue = self._parse_bigint(aff_info.get('revenue'))
                                    net_income = self._parse_bigint(aff_info.get('net_income'))

                                    # 업데이트
                                    result = await conn.execute("""
                                        UPDATE affiliates
                                        SET ownership_ratio = COALESCE($1, ownership_ratio),
                                            voting_rights_ratio = COALESCE($2, voting_rights_ratio),
                                            total_assets = COALESCE($3, total_assets),
                                            revenue = COALESCE($4, revenue),
                                            net_income = COALESCE($5, net_income),
                                            updated_at = NOW()
                                        WHERE parent_company_id = $6
                                        AND affiliate_name = $7
                                    """,
                                        ownership, voting_rights, total_assets,
                                        revenue, net_income, affiliate['parent_company_id'], aff_name
                                    )

                                    if 'UPDATE 1' in str(result):
                                        self.stats['affiliates_updated'] += 1

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"계열사 {affiliate['affiliate_name']} 보완 실패: {e}")
                self.stats['errors'] += 1

        logger.info(f"  완료: {self.stats['affiliates_updated']}개 업데이트")

    def _parse_float(self, value) -> Optional[float]:
        """문자열을 float로 변환"""
        if not value or value == '-':
            return None
        try:
            cleaned = str(value).replace(',', '').strip()
            return float(cleaned) if cleaned else None
        except:
            return None

    def _parse_bigint(self, value) -> Optional[int]:
        """문자열을 bigint로 변환 (백만원 → 원)"""
        if not value or value == '-':
            return None
        try:
            cleaned = str(value).replace(',', '').strip()
            if cleaned:
                return int(float(cleaned) * 1000000)
            return None
        except:
            return None

    async def cleanup_duplicates(self, conn: asyncpg.Connection):
        """중복 레코드 정리"""
        logger.info("\n[5/5] 중복 레코드 정리")

        # 1. 임원 중복 정리 (같은 회사, 같은 이름, 같은 직책)
        duplicates = await conn.fetch("""
            SELECT o.name, op.company_id, op.position, COUNT(*) as cnt
            FROM officers o
            JOIN officer_positions op ON o.id = op.officer_id
            GROUP BY o.name, op.company_id, op.position
            HAVING COUNT(*) > 1
            LIMIT 100
        """)

        logger.info(f"  임원 중복 그룹: {len(duplicates)}개")

        for dup in duplicates:
            try:
                # 가장 최근 레코드만 남기고 삭제
                # birth_date가 있는 레코드 우선
                await conn.execute("""
                    DELETE FROM officer_positions
                    WHERE id IN (
                        SELECT op.id
                        FROM officer_positions op
                        JOIN officers o ON o.id = op.officer_id
                        WHERE o.name = $1
                        AND op.company_id = $2
                        AND op.position = $3
                        AND op.id NOT IN (
                            SELECT op2.id
                            FROM officer_positions op2
                            JOIN officers o2 ON o2.id = op2.officer_id
                            WHERE o2.name = $1
                            AND op2.company_id = $2
                            AND op2.position = $3
                            ORDER BY o2.birth_date NULLS LAST, op2.created_at DESC
                            LIMIT 1
                        )
                    )
                """, dup['name'], dup['company_id'], dup['position'])

                self.stats['duplicates_removed'] += (dup['cnt'] - 1)

            except Exception as e:
                logger.error(f"중복 정리 실패 ({dup['name']}): {e}")
                self.stats['errors'] += 1

        # 2. 고아 officers 레코드 정리 (officer_positions가 없는)
        result = await conn.execute("""
            DELETE FROM officers
            WHERE id NOT IN (
                SELECT DISTINCT officer_id FROM officer_positions
            )
        """)
        orphan_count = int(result.split()[-1]) if 'DELETE' in result else 0
        logger.info(f"  고아 임원 레코드 정리: {orphan_count}개")

        logger.info(f"  완료: {self.stats['duplicates_removed']}개 중복 제거")

    def print_stats(self):
        """최종 통계 출력"""
        logger.info("\n" + "=" * 80)
        logger.info("데이터 보완 작업 완료")
        logger.info("=" * 80)
        logger.info(f"회사 정보 업데이트: {self.stats['companies_updated']}개")
        logger.info(f"임원 정보 업데이트: {self.stats['officers_updated']}명")
        logger.info(f"전환사채 정보 업데이트: {self.stats['cb_updated']}개")
        logger.info(f"계열사 정보 업데이트: {self.stats['affiliates_updated']}개")
        logger.info(f"중복 레코드 제거: {self.stats['duplicates_removed']}개")
        logger.info(f"오류: {self.stats['errors']}건")


async def main():
    """메인 함수"""
    enrichment = DataEnrichment()

    conn = await asyncpg.connect(DB_URL)

    try:
        async with aiohttp.ClientSession() as session:
            await enrichment.run_all(conn, session)

        # 최종 데이터 현황 확인
        logger.info("\n" + "=" * 80)
        logger.info("최종 데이터 현황")
        logger.info("=" * 80)

        # 회사 통계
        company_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(sector) as has_sector,
                COUNT(market) as has_market
            FROM companies
        """)
        logger.info(f"회사: 총 {company_stats['total']}개, sector {company_stats['has_sector']}개, market {company_stats['has_market']}개")

        # 임원 통계
        officer_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(birth_date) as has_birth_date,
                COUNT(gender) as has_gender
            FROM officers
        """)
        logger.info(f"임원: 총 {officer_stats['total']}명, birth_date {officer_stats['has_birth_date']}명, gender {officer_stats['has_gender']}명")

        # CB 통계
        cb_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(issue_date) as has_issue_date,
                COUNT(maturity_date) as has_maturity_date,
                COUNT(interest_rate) as has_interest_rate,
                COUNT(conversion_price) as has_conversion_price
            FROM convertible_bonds
        """)
        logger.info(f"CB: 총 {cb_stats['total']}개, issue_date {cb_stats['has_issue_date']}개, conversion_price {cb_stats['has_conversion_price']}개")

        # 계열사 통계
        aff_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(ownership_ratio) as has_ownership,
                COUNT(total_assets) as has_assets
            FROM affiliates
        """)
        logger.info(f"계열사: 총 {aff_stats['total']}개, ownership_ratio {aff_stats['has_ownership']}개, total_assets {aff_stats['has_assets']}개")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
