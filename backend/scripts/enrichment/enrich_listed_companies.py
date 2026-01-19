#!/usr/bin/env python3
"""
Priority 2: 상장사 데이터 완성
- 530개 상장사 임원 데이터 수집 (사업보고서 파싱)
- 58개 상장사 재무제표 재수집
- 12,411명 임원 birth_date 보강
"""
import asyncio
import aiohttp
import asyncpg
import logging
import os
import re
import zipfile
import io
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DART_BASE_URL = "https://opendart.fss.or.kr/api"
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')


class ListedCompanyEnricher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stats = {
            'officers_created': 0,
            'officers_updated': 0,
            'fs_created': 0,
            'errors': 0
        }

    async def get_business_report(self, session: aiohttp.ClientSession, corp_code: str, year: str) -> Optional[str]:
        """사업보고서 접수번호 조회"""
        try:
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bgn_de': f'{year}0101',
                'end_de': f'{year}1231',
                'pblntf_ty': 'A',
                'page_count': '10'
            }
            async with session.get(f"{DART_BASE_URL}/list.json", params=params) as r:
                if r.status == 200:
                    data = await r.json()
                    if data.get('status') == '000':
                        for item in data.get('list', []):
                            if '사업보고서' in item.get('report_nm', '') and '분기' not in item.get('report_nm', ''):
                                return item.get('rcept_no')
        except Exception as e:
            logger.debug(f"사업보고서 조회 실패 {corp_code}: {e}")
        return None

    async def download_report(self, session: aiohttp.ClientSession, rcept_no: str) -> Optional[str]:
        """사업보고서 XML 다운로드"""
        try:
            params = {'crtfc_key': self.api_key, 'rcept_no': rcept_no}
            async with session.get(f"{DART_BASE_URL}/document.xml", params=params) as r:
                if r.status == 200:
                    content = await r.read()
                    try:
                        with zipfile.ZipFile(io.BytesIO(content)) as zf:
                            for name in zf.namelist():
                                if name.endswith('.xml'):
                                    xml_bytes = zf.read(name)
                                    for enc in ['euc-kr', 'utf-8', 'cp949']:
                                        try:
                                            return xml_bytes.decode(enc)
                                        except:
                                            continue
                    except zipfile.BadZipFile:
                        for enc in ['euc-kr', 'utf-8', 'cp949']:
                            try:
                                return content.decode(enc)
                            except:
                                continue
        except Exception as e:
            logger.debug(f"문서 다운로드 실패: {e}")
        return None

    def parse_officers(self, xml_content: str) -> List[Dict]:
        """임원 현황 파싱"""
        officers = []
        try:
            # 임원 테이블 찾기
            patterns = [
                r'<TABLE-GROUP[^>]*ACLASS="SH5_DRCT_STT"[^>]*>.*?</TABLE-GROUP>',
                r'임원\s*현황.*?<TABLE[^>]*>.*?</TABLE>'
            ]
            for pattern in patterns:
                matches = re.findall(pattern, xml_content, re.DOTALL | re.IGNORECASE)
                if matches:
                    break

            for table in matches:
                rows = re.findall(r'<TR[^>]*>.*?</TR>', table, re.DOTALL)
                for row in rows:
                    officer = self._parse_row(row)
                    if officer and officer.get('name'):
                        officers.append(officer)
        except Exception as e:
            logger.debug(f"임원 파싱 오류: {e}")
        return officers

    def _parse_row(self, row: str) -> Optional[Dict]:
        """행 파싱"""
        try:
            # 이름
            name = None
            for pattern in [r'ACODE="SH5_NM[^"]*"[^>]*>([^<]+)</T[EU]>', r'>([가-힣]{2,4})</T[DEU]>']:
                m = re.search(pattern, row)
                if m:
                    n = m.group(1).strip()
                    if len(n) >= 2 and not any(c.isdigit() for c in n):
                        name = n
                        break

            if not name:
                return None

            # 성별
            gender = None
            m = re.search(r'>([남여])</TU>', row)
            if m:
                gender = m.group(1)

            # 출생년월
            birth_date = None
            m = re.search(r'(\d{4})[년./-]?\s*(\d{1,2})', row)
            if m:
                birth_date = f"{m.group(1)}년 {int(m.group(2)):02d}월"

            # 직위
            position = None
            for pattern in [r'ACODE="SH5_LEV"[^>]*>([^<]+)</TE>', r'>([가-힣]+이사|대표[가-힣]*|사[내외][가-힣]*)</T']:
                m = re.search(pattern, row)
                if m:
                    position = m.group(1).strip()
                    if position and position != '-':
                        break

            return {'name': name, 'gender': gender, 'birth_date': birth_date, 'position': position}
        except:
            return None

    async def get_financial_statements(self, session: aiohttp.ClientSession, corp_code: str, year: str) -> Optional[Dict]:
        """재무제표 조회"""
        try:
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bsns_year': year,
                'reprt_code': '11011',
                'fs_div': 'CFS'
            }
            async with session.get(f"{DART_BASE_URL}/fnlttSinglAcnt.json", params=params) as r:
                if r.status == 200:
                    data = await r.json()
                    if data.get('status') == '000':
                        return self._parse_financial(data.get('list', []))
        except Exception as e:
            logger.debug(f"재무제표 조회 실패: {e}")
        return None

    def _parse_financial(self, statements: List[Dict]) -> Dict:
        """재무제표 파싱"""
        result = {}
        mapping = {
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
                for key, field in mapping.items():
                    if key in name:
                        result[field] = amount
                        break
            except:
                pass
        return result

    async def enrich_company(
        self,
        session: aiohttp.ClientSession,
        conn: asyncpg.Connection,
        company: Dict,
        years: List[str]
    ):
        """회사 데이터 보강"""
        for year in years:
            # 1. 사업보고서로 임원 데이터 수집
            rcept_no = await self.get_business_report(session, company['corp_code'], year)
            if rcept_no:
                await asyncio.sleep(0.3)
                xml = await self.download_report(session, rcept_no)
                if xml:
                    officers = self.parse_officers(xml)
                    for o in officers:
                        await self._save_officer(conn, company['id'], o)

            # 2. 재무제표 수집
            await asyncio.sleep(0.3)
            fs = await self.get_financial_statements(session, company['corp_code'], year)
            if fs:
                await self._save_financial(conn, company['id'], int(year), fs)

    async def _save_officer(self, conn: asyncpg.Connection, company_id: str, officer: Dict):
        """임원 저장/업데이트"""
        try:
            # 기존 임원 찾기
            existing = await conn.fetchrow("""
                SELECT o.id, o.birth_date, o.gender
                FROM officers o
                JOIN officer_positions op ON o.id = op.officer_id
                WHERE op.company_id = $1 AND o.name = $2
                LIMIT 1
            """, company_id, officer['name'])

            if existing:
                # birth_date나 gender가 없으면 업데이트
                if (not existing['birth_date'] and officer.get('birth_date')) or \
                   (not existing['gender'] and officer.get('gender')):
                    await conn.execute("""
                        UPDATE officers
                        SET birth_date = COALESCE($1, birth_date),
                            gender = COALESCE($2, gender),
                            updated_at = NOW()
                        WHERE id = $3
                    """, officer.get('birth_date'), officer.get('gender'), existing['id'])
                    self.stats['officers_updated'] += 1
            else:
                # 새 임원 생성
                import uuid
                officer_id = uuid.uuid4()
                await conn.execute("""
                    INSERT INTO officers (id, name, birth_date, gender, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, NOW(), NOW())
                """, officer_id, officer['name'], officer.get('birth_date'), officer.get('gender'))

                await conn.execute("""
                    INSERT INTO officer_positions (id, officer_id, company_id, position, is_current, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, true, NOW(), NOW())
                """, uuid.uuid4(), officer_id, company_id, officer.get('position'))
                self.stats['officers_created'] += 1

        except Exception as e:
            logger.debug(f"임원 저장 실패 {officer.get('name')}: {e}")
            self.stats['errors'] += 1

    async def _save_financial(self, conn: asyncpg.Connection, company_id: str, year: int, data: Dict):
        """재무제표 저장"""
        if not data:
            return
        try:
            import uuid
            from datetime import date
            await conn.execute("""
                INSERT INTO financial_statements (
                    id, company_id, fiscal_year, quarter, statement_date, report_type,
                    total_assets, total_liabilities, total_equity,
                    revenue, operating_profit, net_income,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, 'Q4', $4, 'ANNUAL', $5, $6, $7, $8, $9, $10, NOW(), NOW())
                ON CONFLICT (company_id, fiscal_year, quarter, report_type)
                DO UPDATE SET
                    total_assets = COALESCE(EXCLUDED.total_assets, financial_statements.total_assets),
                    total_liabilities = COALESCE(EXCLUDED.total_liabilities, financial_statements.total_liabilities),
                    total_equity = COALESCE(EXCLUDED.total_equity, financial_statements.total_equity),
                    revenue = COALESCE(EXCLUDED.revenue, financial_statements.revenue),
                    operating_profit = COALESCE(EXCLUDED.operating_profit, financial_statements.operating_profit),
                    net_income = COALESCE(EXCLUDED.net_income, financial_statements.net_income),
                    updated_at = NOW()
            """,
                uuid.uuid4(), company_id, year, date(year, 12, 31),
                data.get('total_assets'), data.get('total_liabilities'), data.get('total_equity'),
                data.get('revenue'), data.get('operating_profit'), data.get('net_income'))
            self.stats['fs_created'] += 1
        except Exception as e:
            logger.debug(f"재무제표 저장 실패: {e}")


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=['officers', 'fs', 'all'], default='all')
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("상장사 데이터 보강 시작")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)
    enricher = ListedCompanyEnricher(DART_API_KEY)

    try:
        if args.target in ['officers', 'all']:
            # 임원 없는 상장사
            companies = await conn.fetch("""
                SELECT c.id, c.corp_code, c.name
                FROM companies c
                WHERE c.market IN ('KOSPI', 'KOSDAQ')
                AND c.corp_code IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM officer_positions op WHERE op.company_id = c.id)
                LIMIT $1
            """, args.limit)
            logger.info(f"임원 없는 상장사: {len(companies)}개")

            async with aiohttp.ClientSession() as session:
                for i, c in enumerate(companies):
                    await enricher.enrich_company(session, conn, dict(c), ['2023', '2024'])
                    if (i + 1) % 50 == 0:
                        logger.info(f"진행: {i+1}/{len(companies)}")
                    await asyncio.sleep(1)

        if args.target in ['fs', 'all']:
            # 재무제표 없는 상장사
            companies = await conn.fetch("""
                SELECT c.id, c.corp_code, c.name
                FROM companies c
                WHERE c.market IN ('KOSPI', 'KOSDAQ')
                AND c.corp_code IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM financial_statements fs WHERE fs.company_id = c.id)
                LIMIT $1
            """, args.limit)
            logger.info(f"재무제표 없는 상장사: {len(companies)}개")

            async with aiohttp.ClientSession() as session:
                for i, c in enumerate(companies):
                    await enricher.enrich_company(session, conn, dict(c), ['2023', '2024'])
                    if (i + 1) % 50 == 0:
                        logger.info(f"진행: {i+1}/{len(companies)}")
                    await asyncio.sleep(1)

        # birth_date 없는 상장사 임원 보강
        companies = await conn.fetch("""
            SELECT DISTINCT c.id, c.corp_code, c.name
            FROM companies c
            JOIN officer_positions op ON op.company_id = c.id
            JOIN officers o ON o.id = op.officer_id
            WHERE c.market IN ('KOSPI', 'KOSDAQ')
            AND c.corp_code IS NOT NULL
            AND o.birth_date IS NULL
            LIMIT $1
        """, args.limit)
        logger.info(f"birth_date 보강 대상 회사: {len(companies)}개")

        async with aiohttp.ClientSession() as session:
            for i, c in enumerate(companies):
                await enricher.enrich_company(session, conn, dict(c), ['2023', '2024'])
                if (i + 1) % 100 == 0:
                    logger.info(f"진행: {i+1}/{len(companies)} - 업데이트: {enricher.stats['officers_updated']}")
                await asyncio.sleep(0.5)

        # 결과
        logger.info("\n" + "=" * 80)
        logger.info("보강 완료")
        logger.info(f"임원 생성: {enricher.stats['officers_created']:,}명")
        logger.info(f"임원 업데이트: {enricher.stats['officers_updated']:,}명")
        logger.info(f"재무제표 생성: {enricher.stats['fs_created']:,}개")
        logger.info(f"오류: {enricher.stats['errors']:,}건")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
