#!/usr/bin/env python3
"""
상장사 사업보고서 기반 임원 데이터 종합 보강

핵심 기능:
1. 임원 부족 상장사 (0~10명) 대상 사업보고서 파싱
2. 신규 임원 생성 + 기존 임원 정보 보강
3. 임기(term_start_date, term_end_date), 생년월일 완전 수집
4. source_report_date 저장으로 프론트엔드 기간별 조회 지원
"""
import asyncio
import aiohttp
import asyncpg
import logging
import os
import re
import uuid
import zipfile
import io
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DART_API_KEY = os.getenv('DART_API_KEY', '1fd0cd12ae5260eafb7de3130ad91f16aa61911b')
DART_BASE_URL = "https://opendart.fss.or.kr/api"
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')


class OfficerEnricher:
    """사업보고서 기반 임원 종합 보강"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stats = {
            'companies_processed': 0,
            'reports_downloaded': 0,
            'officers_created': 0,
            'officers_updated': 0,
            'positions_created': 0,
            'errors': 0
        }

    async def get_business_reports(
        self,
        session: aiohttp.ClientSession,
        corp_code: str,
        years: List[str]
    ) -> List[Dict]:
        """사업보고서 목록 조회"""
        reports = []

        for year in years:
            try:
                # 해당 연도 +1년까지 조회 (사업보고서는 익년 3월 제출)
                end_year = int(year) + 1
                params = {
                    'crtfc_key': self.api_key,
                    'corp_code': corp_code,
                    'bgn_de': f'{year}0101',
                    'end_de': f'{end_year}0430',
                    'pblntf_ty': 'A',
                    'page_count': '20'
                }

                async with session.get(f"{DART_BASE_URL}/list.json", params=params) as r:
                    if r.status == 200:
                        data = await r.json()
                        if data.get('status') == '000':
                            for item in data.get('list', []):
                                report_nm = item.get('report_nm', '')
                                if '사업보고서' in report_nm and '분기' not in report_nm and '반기' not in report_nm:
                                    reports.append({
                                        'rcept_no': item.get('rcept_no'),
                                        'rcept_dt': item.get('rcept_dt'),
                                        'report_nm': report_nm,
                                        'fiscal_year': year
                                    })
                                    break

                await asyncio.sleep(0.3)
            except Exception as e:
                logger.debug(f"사업보고서 목록 조회 실패 {corp_code}/{year}: {e}")

        return reports

    async def download_report(self, session: aiohttp.ClientSession, rcept_no: str) -> Optional[str]:
        """사업보고서 XML 다운로드"""
        try:
            params = {'crtfc_key': self.api_key, 'rcept_no': rcept_no}

            async with session.get(f"{DART_BASE_URL}/document.xml", params=params) as r:
                if r.status == 200:
                    raw = await r.read()

                    try:
                        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                            # 가장 큰 XML 파일 선택
                            xml_files = [(n, zf.getinfo(n).file_size) for n in zf.namelist() if n.endswith('.xml')]
                            if xml_files:
                                main_xml = max(xml_files, key=lambda x: x[1])[0]
                                xml_bytes = zf.read(main_xml)
                                for enc in ['euc-kr', 'utf-8', 'cp949']:
                                    try:
                                        return xml_bytes.decode(enc)
                                    except:
                                        continue
                    except zipfile.BadZipFile:
                        for enc in ['euc-kr', 'utf-8', 'cp949']:
                            try:
                                return raw.decode(enc)
                            except:
                                continue
            return None
        except Exception as e:
            logger.debug(f"다운로드 실패 {rcept_no}: {e}")
            return None

    def parse_officers(self, xml_content: str, rcept_dt: str) -> List[Dict]:
        """임원 현황 파싱 - 이름, 직위, 성별, 출생년월, 임기 추출"""
        officers = []

        # 연도 추출 (사업보고서 기준일)
        report_year = rcept_dt[:4] if rcept_dt else str(datetime.now().year)

        try:
            # 1. 임원 현황 테이블 찾기 (다양한 패턴)
            table_patterns = [
                r'<TABLE-GROUP[^>]*ACLASS="SH5_DRCT_STT"[^>]*>(.*?)</TABLE-GROUP>',
                r'<TABLE-GROUP[^>]*>.*?임원\s*현황.*?</TABLE-GROUP>',
                r'<TABLE[^>]*>.*?성명.*?출생년월.*?</TABLE>',
            ]

            table_content = None
            for pattern in table_patterns:
                match = re.search(pattern, xml_content, re.DOTALL | re.IGNORECASE)
                if match:
                    table_content = match.group(0)
                    break

            if not table_content:
                return officers

            # 2. 행 추출
            rows = re.findall(r'<TR[^>]*>(.*?)</TR>', table_content, re.DOTALL | re.IGNORECASE)

            for row in rows:
                officer = self._parse_officer_row(row, report_year)
                if officer and officer.get('name'):
                    officers.append(officer)

        except Exception as e:
            logger.debug(f"임원 파싱 실패: {e}")

        return officers

    def _parse_officer_row(self, row_xml: str, report_year: str) -> Optional[Dict]:
        """단일 임원 행 파싱"""
        try:
            # 1. 성명 추출
            name = None
            name_patterns = [
                r'ACODE="SH5_NM[^"]*"[^>]*>([^<]+)</T[EU]>',
                r'<TD[^>]*>([가-힣]{2,5}(?:\([^)]*\))?)</TD>',
                r'<TE[^>]*>([가-힣]{2,5})</TE>',
            ]
            for pattern in name_patterns:
                match = re.search(pattern, row_xml)
                if match:
                    n = match.group(1).strip()
                    # 유효성 검증: 2-5글자 한글, 숫자로만 구성 안됨
                    if n and 2 <= len(re.sub(r'\([^)]*\)', '', n)) <= 10:
                        if re.search(r'[가-힣]', n) and not n.replace('-', '').isdigit():
                            name = n
                            break

            if not name:
                return None

            # 2. 성별
            gender = None
            gender_match = re.search(r'[>]([남여])[<]', row_xml)
            if gender_match:
                gender = gender_match.group(1)

            # 3. 출생년월
            birth_date = None
            birth_patterns = [
                r'(\d{4})[년.\-/]\s*(\d{1,2})',  # 1969년 05 또는 1969.05
                r'(\d{4})(\d{2})',  # 196905
                r'AUNIT="SH5_BIH"[^>]*>([^<]+)</TU>',
            ]
            for pattern in birth_patterns:
                match = re.search(pattern, row_xml)
                if match:
                    if len(match.groups()) >= 2:
                        year, month = match.groups()[:2]
                        if 1930 <= int(year) <= 2005:
                            birth_date = f"{year}.{int(month):02d}"
                            break
                    else:
                        raw = match.group(1).strip()
                        if raw and len(raw) >= 4:
                            birth_date = raw
                            break

            # 4. 직위
            position = None
            position_patterns = [
                r'ACODE="SH5_LEV"[^>]*>([^<]+)</TE>',
                r'AUNIT="SH5_REG_DRCT"[^>]*>([^<]+)</TU>',
                r'<TD[^>]*>(대표이사|이사|감사|사외이사|사내이사|상무|전무|부사장|부회장|회장|사장|본부장)[^<]*</TD>',
            ]
            for pattern in position_patterns:
                match = re.search(pattern, row_xml)
                if match:
                    p = match.group(1).strip()
                    if p and p != '-' and len(p) <= 50:
                        position = p
                        break

            # 5. 임기 시작/종료
            term_start = None
            term_end = None

            # 취임일/임기시작
            start_patterns = [
                r'취임일[^<]*[:\s]*(\d{4})[년.\-/]?\s*(\d{1,2})[월.\-/]?\s*(\d{1,2})',
                r'AUNIT="SH5_TKF_DT"[^>]*>(\d{4})[.\-/]?(\d{2})[.\-/]?(\d{2})</TU>',
            ]
            for pattern in start_patterns:
                match = re.search(pattern, row_xml)
                if match:
                    try:
                        y, m, d = match.groups()
                        term_start = date(int(y), int(m), int(d))
                        break
                    except:
                        pass

            # 임기만료/종료
            end_patterns = [
                r'임기만료[^<]*[:\s]*(\d{4})[년.\-/]?\s*(\d{1,2})[월.\-/]?\s*(\d{1,2})',
                r'AUNIT="SH5_TRM_ED_DT"[^>]*>(\d{4})[.\-/]?(\d{2})[.\-/]?(\d{2})</TU>',
            ]
            for pattern in end_patterns:
                match = re.search(pattern, row_xml)
                if match:
                    try:
                        y, m, d = match.groups()
                        term_end = date(int(y), int(m), int(d))
                        break
                    except:
                        pass

            return {
                'name': name,
                'gender': gender,
                'birth_date': birth_date,
                'position': position or '임원',
                'term_start_date': term_start,
                'term_end_date': term_end
            }

        except Exception as e:
            return None

    async def save_officers(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        officers: List[Dict],
        rcept_no: str,
        rcept_dt: str,
        fiscal_year: str
    ) -> Tuple[int, int, int]:
        """임원 데이터 저장 - 신규 생성 또는 업데이트"""
        created = 0
        updated = 0
        positions = 0

        # source_report_date 계산 (결산일 기준)
        try:
            source_report_date = date(int(fiscal_year), 12, 31)
        except:
            source_report_date = None

        for officer in officers:
            if not officer.get('name'):
                continue

            try:
                # 1. 기존 임원 검색 (회사 + 이름)
                existing = await conn.fetchrow("""
                    SELECT o.id, o.birth_date, o.gender
                    FROM officers o
                    JOIN officer_positions op ON o.id = op.officer_id
                    WHERE op.company_id = $1 AND o.name = $2
                    LIMIT 1
                """, company_id, officer['name'])

                if existing:
                    officer_id = existing['id']

                    # 기존 임원 정보 보강
                    if officer.get('birth_date') or officer.get('gender'):
                        await conn.execute("""
                            UPDATE officers SET
                                birth_date = COALESCE($1, birth_date),
                                gender = COALESCE($2, gender),
                                updated_at = NOW()
                            WHERE id = $3
                        """, officer.get('birth_date'), officer.get('gender'), officer_id)
                        updated += 1
                else:
                    # 2. 신규 임원 생성
                    officer_id = str(uuid.uuid4())
                    await conn.execute("""
                        INSERT INTO officers (id, name, birth_date, gender, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, NOW(), NOW())
                    """, officer_id, officer['name'], officer.get('birth_date'), officer.get('gender'))
                    created += 1

                # 3. officer_positions 생성/업데이트
                # 중복 확인 (같은 회사, 같은 임원, 같은 source_report_date)
                pos_exists = await conn.fetchval("""
                    SELECT 1 FROM officer_positions
                    WHERE officer_id = $1 AND company_id = $2
                    AND source_disclosure_id = $3
                """, officer_id, company_id, rcept_no)

                if not pos_exists:
                    await conn.execute("""
                        INSERT INTO officer_positions (
                            id, officer_id, company_id, position,
                            term_start_date, term_end_date, is_current,
                            source_disclosure_id, source_report_date,
                            birth_date, gender, created_at, updated_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW()
                        )
                    """,
                        str(uuid.uuid4()),
                        officer_id,
                        company_id,
                        officer.get('position', '임원'),
                        officer.get('term_start_date'),
                        officer.get('term_end_date'),
                        True,  # is_current (나중에 갱신)
                        rcept_no,
                        source_report_date,
                        officer.get('birth_date'),
                        officer.get('gender')
                    )
                    positions += 1
                else:
                    # 기존 position 업데이트
                    await conn.execute("""
                        UPDATE officer_positions SET
                            position = COALESCE($1, position),
                            term_start_date = COALESCE($2, term_start_date),
                            term_end_date = COALESCE($3, term_end_date),
                            birth_date = COALESCE($4, birth_date),
                            gender = COALESCE($5, gender),
                            updated_at = NOW()
                        WHERE officer_id = $6 AND company_id = $7
                        AND source_disclosure_id = $8
                    """,
                        officer.get('position'),
                        officer.get('term_start_date'),
                        officer.get('term_end_date'),
                        officer.get('birth_date'),
                        officer.get('gender'),
                        officer_id,
                        company_id,
                        rcept_no
                    )

            except Exception as e:
                logger.debug(f"임원 저장 실패 {officer.get('name')}: {e}")

        return created, updated, positions

    async def process_company(
        self,
        session: aiohttp.ClientSession,
        conn: asyncpg.Connection,
        company: Dict,
        years: List[str]
    ) -> Dict:
        """단일 회사 처리"""
        result = {'created': 0, 'updated': 0, 'positions': 0}

        # 1. 사업보고서 목록 조회
        reports = await self.get_business_reports(session, company['corp_code'], years)

        if not reports:
            return result

        for report in reports:
            try:
                # 2. 사업보고서 다운로드
                await asyncio.sleep(0.5)
                xml = await self.download_report(session, report['rcept_no'])

                if not xml:
                    continue

                self.stats['reports_downloaded'] += 1

                # 3. 임원 파싱
                officers = self.parse_officers(xml, report['rcept_dt'])

                if not officers:
                    continue

                # 4. DB 저장
                created, updated, positions = await self.save_officers(
                    conn,
                    str(company['id']),
                    officers,
                    report['rcept_no'],
                    report['rcept_dt'],
                    report['fiscal_year']
                )

                result['created'] += created
                result['updated'] += updated
                result['positions'] += positions

            except Exception as e:
                logger.error(f"보고서 처리 실패 {report['rcept_no']}: {e}")
                self.stats['errors'] += 1

        return result


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="상장사 임원 데이터 종합 보강")
    parser.add_argument("--years", default="2022,2023,2024", help="대상 연도")
    parser.add_argument("--limit", type=int, default=100, help="처리할 회사 수")
    parser.add_argument("--max-officers", type=int, default=10, help="현재 임원 수 최대값 (이하만 처리)")
    parser.add_argument("--corp-code", help="특정 회사 corp_code만 처리")
    args = parser.parse_args()

    years = args.years.split(',')

    logger.info("=" * 80)
    logger.info("상장사 임원 데이터 종합 보강")
    logger.info(f"대상 연도: {years}, 최대 임원 수: {args.max_officers}명 이하")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)
    enricher = OfficerEnricher(DART_API_KEY)

    try:
        # 대상 회사 조회 (임원 부족 회사)
        if args.corp_code:
            companies = await conn.fetch("""
                SELECT id, corp_code, name, ticker
                FROM companies
                WHERE corp_code = $1
            """, args.corp_code)
        else:
            companies = await conn.fetch("""
                WITH officer_counts AS (
                    SELECT c.id, c.corp_code, c.name, c.ticker, c.market,
                           COUNT(op.id) as officer_count
                    FROM companies c
                    LEFT JOIN officer_positions op ON op.company_id = c.id
                    WHERE c.market IN ('KOSPI', 'KOSDAQ')
                    AND c.corp_code IS NOT NULL
                    GROUP BY c.id, c.corp_code, c.name, c.ticker, c.market
                )
                SELECT id, corp_code, name, ticker
                FROM officer_counts
                WHERE officer_count <= $1
                ORDER BY officer_count ASC, name
                LIMIT $2
            """, args.max_officers, args.limit)

        logger.info(f"처리 대상 회사: {len(companies)}개")

        async with aiohttp.ClientSession() as session:
            for i, company in enumerate(companies):
                result = await enricher.process_company(session, conn, dict(company), years)

                enricher.stats['companies_processed'] += 1
                enricher.stats['officers_created'] += result['created']
                enricher.stats['officers_updated'] += result['updated']
                enricher.stats['positions_created'] += result['positions']

                if (i + 1) % 10 == 0 or result['created'] > 0:
                    logger.info(
                        f"[{i+1}/{len(companies)}] {company['name']}: "
                        f"신규 {result['created']}, 업데이트 {result['updated']}, "
                        f"포지션 {result['positions']}"
                    )

                await asyncio.sleep(1)

        # is_current 플래그 업데이트
        logger.info("\nis_current 플래그 업데이트 중...")
        await conn.execute("""
            WITH latest_positions AS (
                SELECT DISTINCT ON (officer_id, company_id)
                    id, officer_id, company_id, source_report_date
                FROM officer_positions
                ORDER BY officer_id, company_id, source_report_date DESC NULLS LAST
            )
            UPDATE officer_positions op
            SET is_current = (
                EXISTS (SELECT 1 FROM latest_positions lp WHERE lp.id = op.id)
            )
        """)

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("임원 데이터 보강 완료")
        logger.info("=" * 80)
        logger.info(f"처리 회사: {enricher.stats['companies_processed']}개")
        logger.info(f"다운로드 보고서: {enricher.stats['reports_downloaded']}개")
        logger.info(f"신규 임원: {enricher.stats['officers_created']}명")
        logger.info(f"업데이트 임원: {enricher.stats['officers_updated']}명")
        logger.info(f"생성 포지션: {enricher.stats['positions_created']}개")
        logger.info(f"오류: {enricher.stats['errors']}건")

        # 현재 상태
        stats = await conn.fetchrow("""
            SELECT
                COUNT(DISTINCT o.id) as total_officers,
                COUNT(DISTINCT CASE WHEN o.birth_date IS NOT NULL THEN o.id END) as has_birth,
                COUNT(*) as total_positions,
                COUNT(CASE WHEN op.source_report_date IS NOT NULL THEN 1 END) as has_report_date
            FROM officers o
            LEFT JOIN officer_positions op ON o.id = op.officer_id
        """)
        logger.info(f"\n현재 상태:")
        logger.info(f"  총 임원: {stats['total_officers']:,}명 (생년월일: {stats['has_birth']:,}명)")
        logger.info(f"  총 포지션: {stats['total_positions']:,}개 (보고서기준일: {stats['has_report_date']:,}개)")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
