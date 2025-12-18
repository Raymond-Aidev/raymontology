#!/usr/bin/env python3
"""
사업보고서 파싱 - 임원 정보 추출

DART API에서 사업보고서를 다운로드하고:
1. 임원 현황에서 이름, 출생년월, 성별, 직책 추출
2. officers, officer_positions 테이블 업데이트
"""
import asyncio
import aiohttp
import asyncpg
import logging
import sys
import os
import re
import zipfile
import io
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
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')


class BusinessReportParser:
    """사업보고서 파싱 클래스"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stats = {
            'reports_processed': 0,
            'officers_updated': 0,
            'errors': 0
        }

    async def get_report_list(
        self,
        session: aiohttp.ClientSession,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = '11011'  # 사업보고서
    ) -> Optional[str]:
        """사업보고서 접수번호 조회"""
        try:
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bgn_de': f'{bsns_year}0101',
                'end_de': f'{bsns_year}1231',
                'pblntf_ty': 'A',  # 정기공시
                'page_no': '1',
                'page_count': '10'
            }

            async with session.get(f"{DART_BASE_URL}/list.json", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == '000':
                        for item in data.get('list', []):
                            report_nm = item.get('report_nm', '')
                            # 사업보고서 찾기
                            if '사업보고서' in report_nm and '분기' not in report_nm and '반기' not in report_nm:
                                return item.get('rcept_no')
            return None
        except Exception as e:
            logger.error(f"사업보고서 목록 조회 실패: {e}")
            return None

    async def download_report(
        self,
        session: aiohttp.ClientSession,
        rcept_no: str
    ) -> Optional[str]:
        """사업보고서 문서 다운로드"""
        try:
            params = {
                'crtfc_key': self.api_key,
                'rcept_no': rcept_no
            }

            async with session.get(f"{DART_BASE_URL}/document.xml", params=params) as response:
                if response.status == 200:
                    raw_content = await response.read()

                    try:
                        with zipfile.ZipFile(io.BytesIO(raw_content)) as zf:
                            # 가장 큰 XML 파일 찾기
                            max_size = 0
                            main_xml = None
                            for name in zf.namelist():
                                if name.endswith('.xml'):
                                    info = zf.getinfo(name)
                                    if info.file_size > max_size:
                                        max_size = info.file_size
                                        main_xml = name

                            if main_xml:
                                xml_bytes = zf.read(main_xml)
                                for encoding in ['euc-kr', 'utf-8', 'cp949']:
                                    try:
                                        return xml_bytes.decode(encoding)
                                    except:
                                        continue
                    except zipfile.BadZipFile:
                        for encoding in ['euc-kr', 'utf-8', 'cp949']:
                            try:
                                return raw_content.decode(encoding)
                            except:
                                continue

            return None
        except Exception as e:
            logger.error(f"사업보고서 다운로드 실패 {rcept_no}: {e}")
            return None

    def parse_officers(self, xml_content: str) -> List[Dict]:
        """임원 현황 파싱"""
        officers = []

        try:
            # 임원 현황 테이블 찾기 (SH5_DRCT_STT)
            pattern = r'<TABLE-GROUP[^>]*ACLASS="SH5_DRCT_STT"[^>]*>.*?</TABLE-GROUP>'
            matches = re.findall(pattern, xml_content, re.DOTALL | re.IGNORECASE)

            if not matches:
                # 대체 패턴: 임원 현황 텍스트 기반
                pattern = r'임원\s*현황.*?<TABLE[^>]*>.*?</TABLE>'
                matches = re.findall(pattern, xml_content, re.DOTALL | re.IGNORECASE)

            for table_content in matches:
                # 데이터 행 추출
                tr_pattern = r'<TR[^>]*>.*?</TR>'
                rows = re.findall(tr_pattern, table_content, re.DOTALL)

                for row in rows:
                    officer = self._parse_officer_row(row)
                    if officer:
                        officers.append(officer)

        except Exception as e:
            logger.error(f"임원 파싱 실패: {e}")

        return officers

    def _parse_officer_row(self, row_xml: str) -> Optional[Dict]:
        """임원 행 파싱"""
        try:
            # 성명 추출
            name_patterns = [
                r'ACODE="SH5_NM[^"]*"[^>]*>([^<]+)</T[EU]>',
                r'<T[DEU][^>]*>([가-힣]{2,4})</T[DEU]>',  # 한글 이름
            ]
            name = None
            for pattern in name_patterns:
                match = re.search(pattern, row_xml)
                if match:
                    name = match.group(1).strip()
                    if name and len(name) >= 2 and not any(c.isdigit() for c in name):
                        break
                    name = None

            if not name:
                return None

            # 성별 추출
            gender_patterns = [
                r'AUNIT="SH5_SEX"[^>]*>([^<]+)</TU>',
                r'<TU[^>]*>([남여])</TU>',
            ]
            gender = None
            for pattern in gender_patterns:
                match = re.search(pattern, row_xml)
                if match:
                    g = match.group(1).strip()
                    if g in ['남', '여', '남성', '여성']:
                        gender = '남' if '남' in g else '여'
                        break

            # 출생년월 추출
            birth_patterns = [
                r'AUNIT="SH5_BIH"[^>]*>([^<]+)</TU>',
                r'(\d{4})[년.\-/]?\s*(\d{1,2})[월]?',
            ]
            birth_date = None
            for pattern in birth_patterns:
                match = re.search(pattern, row_xml)
                if match:
                    if len(match.groups()) == 1:
                        birth_date = match.group(1).strip()
                    else:
                        year, month = match.groups()
                        birth_date = f"{year}년 {int(month):02d}월"
                    if birth_date and ('년' in birth_date or len(birth_date) >= 6):
                        break
                    birth_date = None

            # 직위 추출
            position_patterns = [
                r'ACODE="SH5_LEV"[^>]*>([^<]+)</TE>',
                r'AUNIT="SH5_REG_DRCT"[^>]*>([^<]+)</TU>',
            ]
            position = None
            for pattern in position_patterns:
                match = re.search(pattern, row_xml)
                if match:
                    position = match.group(1).strip()
                    if position and position != '-':
                        break
                    position = None

            return {
                'name': name,
                'gender': gender,
                'birth_date': birth_date,
                'position': position
            }

        except Exception as e:
            return None

    async def update_officers(
        self,
        conn: asyncpg.Connection,
        company_id: str,
        officers: List[Dict],
        report_date: str
    ):
        """임원 정보 업데이트"""
        updated = 0

        for officer in officers:
            if not officer.get('name'):
                continue

            try:
                # 해당 회사의 동일 이름 임원 찾기
                result = await conn.fetch("""
                    SELECT o.id, o.name, o.birth_date, o.gender
                    FROM officers o
                    JOIN officer_positions op ON o.id = op.officer_id
                    WHERE op.company_id = $1
                    AND o.name = $2
                """, company_id, officer['name'])

                if result:
                    for row in result:
                        # birth_date 또는 gender가 없는 경우 업데이트
                        if officer.get('birth_date') or officer.get('gender'):
                            await conn.execute("""
                                UPDATE officers
                                SET birth_date = COALESCE($1, birth_date),
                                    gender = COALESCE($2, gender),
                                    updated_at = NOW()
                                WHERE id = $3
                                AND (birth_date IS NULL OR gender IS NULL)
                            """, officer.get('birth_date'), officer.get('gender'), row['id'])

                            # officer_positions도 업데이트
                            await conn.execute("""
                                UPDATE officer_positions
                                SET birth_date = COALESCE($1, birth_date),
                                    gender = COALESCE($2, gender),
                                    source_report_date = COALESCE($3, source_report_date)
                                WHERE officer_id = $4
                                AND company_id = $5
                            """, officer.get('birth_date'), officer.get('gender'),
                                datetime.strptime(report_date, '%Y%m%d').date() if report_date else None,
                                row['id'], company_id)

                            updated += 1

            except Exception as e:
                logger.error(f"임원 {officer['name']} 업데이트 실패: {e}")

        return updated

    async def process_company(
        self,
        session: aiohttp.ClientSession,
        conn: asyncpg.Connection,
        company: Dict,
        years: List[str]
    ) -> int:
        """회사별 사업보고서 처리"""
        total_updated = 0

        for year in years:
            try:
                # 사업보고서 접수번호 조회
                rcept_no = await self.get_report_list(session, company['corp_code'], year)

                if not rcept_no:
                    continue

                # 사업보고서 다운로드
                await asyncio.sleep(0.5)  # API rate limit
                xml_content = await self.download_report(session, rcept_no)

                if not xml_content:
                    continue

                # 임원 정보 파싱
                officers = self.parse_officers(xml_content)

                if officers:
                    # DB 업데이트
                    updated = await self.update_officers(
                        conn,
                        str(company['id']),
                        officers,
                        f"{year}0331"  # 사업보고서 기준일
                    )
                    total_updated += updated

                self.stats['reports_processed'] += 1

            except Exception as e:
                logger.error(f"회사 {company['name']} {year}년 처리 실패: {e}")
                self.stats['errors'] += 1

        return total_updated


async def main():
    """메인 함수"""
    import argparse

    parser_arg = argparse.ArgumentParser(description="사업보고서 임원 정보 파싱")
    parser_arg.add_argument("--years", default="2022,2023,2024", help="처리할 연도 (쉼표 구분)")
    parser_arg.add_argument("--limit", type=int, default=100, help="처리할 회사 수")

    args = parser_arg.parse_args()
    years = args.years.split(',')

    logger.info("=" * 80)
    logger.info("사업보고서 임원 정보 파싱 시작")
    logger.info(f"대상 연도: {years}")
    logger.info("=" * 80)

    parser = BusinessReportParser(DART_API_KEY)
    conn = await asyncpg.connect(DB_URL)

    try:
        # birth_date가 없는 임원이 있는 회사 조회
        companies = await conn.fetch("""
            SELECT DISTINCT c.id, c.corp_code, c.name
            FROM companies c
            JOIN officer_positions op ON op.company_id = c.id
            JOIN officers o ON o.id = op.officer_id
            WHERE c.corp_code IS NOT NULL
            AND o.birth_date IS NULL
            LIMIT $1
        """, args.limit)

        logger.info(f"처리 대상 회사: {len(companies)}개")

        async with aiohttp.ClientSession() as session:
            for i, company in enumerate(companies):
                updated = await parser.process_company(
                    session, conn, dict(company), years
                )
                parser.stats['officers_updated'] += updated

                if (i + 1) % 10 == 0:
                    logger.info(
                        f"진행: {i + 1}/{len(companies)} - "
                        f"보고서: {parser.stats['reports_processed']}, "
                        f"임원 업데이트: {parser.stats['officers_updated']}"
                    )

                await asyncio.sleep(1)  # API rate limit

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("사업보고서 파싱 완료")
        logger.info("=" * 80)
        logger.info(f"처리된 보고서: {parser.stats['reports_processed']}개")
        logger.info(f"업데이트된 임원: {parser.stats['officers_updated']}명")
        logger.info(f"오류: {parser.stats['errors']}건")

        # 현재 상태 확인
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(birth_date) as has_birth_date,
                COUNT(gender) as has_gender
            FROM officers
        """)
        logger.info(f"\n임원 현황: 총 {stats['total']:,}명, "
                    f"birth_date {stats['has_birth_date']:,}명, "
                    f"gender {stats['has_gender']:,}명")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
