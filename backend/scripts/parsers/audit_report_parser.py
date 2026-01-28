"""
AuditReportParser - DART 감사보고서 재무제표 파서 (v1.0)

감사보고서 전용 파서:
- HTML TABLE 형식의 재무제표 파싱
- 신규 상장 기업의 감사보고서에서 재무데이터 추출
- 기존 FinancialParser의 ACCOUNT_MAPPING 재사용

사용법:
    from scripts.parsers.audit_report_parser import AuditReportParser

    parser = AuditReportParser()
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            await parser.parse_and_save(conn, zip_path, meta)

v1.0 (2026-01-25):
- 초기 구현: HTML TABLE 형식 재무제표 파싱
- 대한조선, 명인제약 등 45개 신규 상장 기업 대상
"""

import asyncpg
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .base import BaseParser
from .financial import FinancialParser

logger = logging.getLogger(__name__)


class AuditReportParser(BaseParser):
    """DART 감사보고서 재무제표 파서 (v1.0)

    감사보고서는 사업보고서와 다른 XML 구조를 가짐:
    - 사업보고서: <TITLE>4-1. 재무상태표</TITLE> 형식
    - 감사보고서: HTML TABLE 내 <TD>재 무 상 태 표</TD> 형식
    """

    # 재무제표 섹션 마커 (공백 포함 패턴)
    # 연결/별도 재무제표 모두 매칭
    SECTION_MARKERS = {
        'balance_sheet': [
            r'(?:연\s*결\s*)?재\s*무\s*상\s*태\s*표',
            r'대\s*차\s*대\s*조\s*표',
        ],
        'income_statement': [
            r'(?:연\s*결\s*)?손\s*익\s*계\s*산\s*서',
            r'(?:연\s*결\s*)?포\s*괄\s*손\s*익\s*계\s*산\s*서',
        ],
        'cash_flow': [
            r'(?:연\s*결\s*)?현\s*금\s*흐\s*름\s*표',
        ]
    }

    # FinancialParser의 ACCOUNT_MAPPING 재사용
    ACCOUNT_MAPPING = FinancialParser.ACCOUNT_MAPPING

    def __init__(self, database_url: Optional[str] = None, skip_db_check: bool = False):
        if skip_db_check:
            # 테스트 모드: DB 연결 없이 파서만 사용
            self.database_url = None
            self.stats = {
                'files_processed': 0,
                'records_created': 0,
                'records_updated': 0,
                'errors': 0,
            }
        else:
            super().__init__(database_url)
        self.company_cache = {}  # corp_code -> company_id

    async def load_companies(self, conn: asyncpg.Connection):
        """회사 캐시 로드"""
        rows = await conn.fetch("SELECT id, corp_code FROM companies WHERE corp_code IS NOT NULL")
        self.company_cache = {r['corp_code']: str(r['id']) for r in rows}
        logger.info(f"회사 캐시 로드: {len(self.company_cache)}개")

    def is_audit_report(self, xml_content: str) -> bool:
        """감사보고서 여부 확인

        감사보고서 특징:
        - "독립된 감사인의 감사보고서" 포함
        - "(첨부)재 무 제 표" 포함
        - TITLE 태그에 "4-1. 재무상태표" 형식이 아닌 TABLE 형식
        """
        audit_markers = [
            r'독립된\s*감사인의\s*감사보고서',
            r'\(첨부\)재\s*무\s*제\s*표',
            r'감사보고서\s*\(\d{4}\.\d+\)',
        ]

        for marker in audit_markers:
            if re.search(marker, xml_content):
                return True

        # 사업보고서 TITLE 패턴이 없으면 감사보고서로 판단
        business_patterns = [
            r'<TITLE[^>]*>4-1\.\s*재\s*무\s*상\s*태\s*표</TITLE>',
            r'<TITLE[^>]*>Ⅲ\.\s*재무에\s*관한\s*사항</TITLE>',
        ]

        for pattern in business_patterns:
            if re.search(pattern, xml_content):
                return False  # 사업보고서

        return True  # 기본적으로 감사보고서로 판단

    def _extract_table_section(self, xml_content: str, section_name: str) -> Optional[str]:
        """HTML TABLE 섹션 추출

        두 가지 감사보고서 형식 지원:
        1. TD-based: <TD>재 무 상 태 표</TD> 형식 (대한조선 등)
        2. TITLE-based: <TITLE>재 무 상 태 표</TITLE> 형식 (젬 등)

        중요: 여러 매칭이 있을 경우 가장 큰 테이블 선택 (노타/쎄크 형식 대응)

        Args:
            xml_content: 전체 XML 내용
            section_name: 'balance_sheet', 'income_statement', 'cash_flow'

        Returns:
            해당 섹션의 TABLE 내용
        """
        markers = self.SECTION_MARKERS.get(section_name, [])
        candidate_tables = []  # 모든 후보 테이블 수집

        for marker in markers:
            # 1. TD 기반 형식 (예: 대한조선, 노타)
            td_pattern = rf'<TD[^>]*>\s*{marker}\s*</TD>'
            td_matches = list(re.finditer(td_pattern, xml_content, re.IGNORECASE))

            for td_match in td_matches:
                start_pos = td_match.end()
                table_start = xml_content.find('<TABLE', start_pos)
                if table_start != -1:
                    table_end = self._find_table_end(xml_content, table_start)
                    if table_end != -1:
                        table_content = xml_content[table_start:table_end]
                        candidate_tables.append(table_content)

            # 2. TITLE 기반 형식 (예: 젬)
            title_pattern = rf'<TITLE[^>]*>\s*{marker}\s*</TITLE>'
            title_matches = list(re.finditer(title_pattern, xml_content, re.IGNORECASE))

            for title_match in title_matches:
                start_pos = title_match.end()
                # ACLASS="FINANCE" TABLE 찾기 (실제 재무 데이터)
                finance_pattern = r'<TABLE[^>]*ACLASS="FINANCE"[^>]*>'
                finance_match = re.search(finance_pattern, xml_content[start_pos:start_pos+5000])

                if finance_match:
                    table_start = start_pos + finance_match.start()
                    table_end = self._find_table_end(xml_content, table_start)
                    if table_end != -1:
                        table_content = xml_content[table_start:table_end]
                        candidate_tables.append(table_content)
                else:
                    # FINANCE TABLE 없으면 일반 TABLE
                    table_start = xml_content.find('<TABLE', start_pos)
                    if table_start != -1:
                        table_end = self._find_table_end(xml_content, table_start)
                        if table_end != -1:
                            table_content = xml_content[table_start:table_end]
                            candidate_tables.append(table_content)

        if not candidate_tables:
            return None

        # 가장 큰 테이블 선택 (실제 재무 데이터가 있는 테이블)
        # 최소 크기 필터 (1000 bytes 이상만 유효한 데이터 테이블)
        valid_tables = [t for t in candidate_tables if len(t) >= 1000]

        if valid_tables:
            # 가장 큰 테이블 선택
            best_table = max(valid_tables, key=len)
            logger.debug(f"Selected table: {len(best_table)} bytes (from {len(candidate_tables)} candidates)")
            return best_table
        elif candidate_tables:
            # 유효한 테이블 없으면 가장 큰 것 선택 (fallback)
            return max(candidate_tables, key=len)

        return None

    def _find_table_end(self, content: str, start_pos: int) -> int:
        """중첩 TABLE을 고려한 TABLE 끝 위치 찾기

        Args:
            content: 전체 문서
            start_pos: <TABLE 태그 시작 위치

        Returns:
            </TABLE> 태그 끝 위치 (실패 시 -1)
        """
        # 간단한 방법: <TABLE> 개수와 </TABLE> 개수 추적
        depth = 1  # 시작 TABLE 카운트
        pos = start_pos + 6  # <TABLE 다음부터 검색

        while pos < len(content) and depth > 0:
            # 다음 태그 찾기
            next_open = content.find('<TABLE', pos)
            next_close = content.find('</TABLE>', pos)

            if next_close == -1:
                return -1  # 닫는 태그 없음

            # 중첩 TABLE이 있고 닫는 태그보다 먼저 나오면
            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + 6
            else:
                # 닫는 태그 발견
                depth -= 1
                if depth == 0:
                    return next_close + 8  # </TABLE> 끝 위치
                pos = next_close + 8

        return -1

    def _detect_unit_from_table(self, table_content: str) -> int:
        """TABLE 내 단위 감지

        Returns:
            1: 원
            1000: 천원
            1000000: 백만원
        """
        # 1. AUNITVALUE 속성 (XBRL 형식) - 우선
        aunit_match = re.search(r'AUNITVALUE="(\d+)"', table_content)
        if aunit_match:
            aunit_value = int(aunit_match.group(1))
            if aunit_value == 1:
                return 1
            elif aunit_value == 1000:
                return 1_000
            elif aunit_value == 1000000:
                return 1_000_000

        # 2. 텍스트 패턴
        unit_patterns = [
            (r'단위\s*:\s*백만원', 1_000_000),
            (r'단위\s*:\s*천원', 1_000),
            (r'단위\s*:\s*원', 1),
        ]

        for pattern, multiplier in unit_patterns:
            if re.search(pattern, table_content):
                return multiplier

        # 기본값: 원 (감사보고서는 대부분 원 단위)
        return 1

    def _parse_table_rows(self, table_content: str, unit_multiplier: int = 1) -> Dict[str, int]:
        """TABLE에서 재무 항목 파싱

        두 가지 형식 지원:
        1. TD 기반 (대한조선 형식):
           - Cell 0: 계정과목명
           - Cell 1: 주석 번호
           - Cell 2: 당기 세부값
           - Cell 3: 당기 소계

        2. TE 기반 XBRL 형식 (젬 형식):
           - Cell 0 (ADELIM=0): 계정과목명
           - Cell 1 (ADELIM=1): 당기 세부값
           - Cell 2 (ADELIM=2): 당기 소계

        Args:
            table_content: TABLE HTML 내용
            unit_multiplier: 단위 배수

        Returns:
            {field_name: value} 딕셔너리
        """
        values = {}

        # TR 단위로 분리
        rows = re.findall(r'<TR[^>]*>(.*?)</TR>', table_content, re.DOTALL | re.IGNORECASE)

        for row in rows:
            # TE 태그 (XBRL 형식) 먼저 시도
            te_cells = re.findall(r'<TE[^>]*>(.*?)</TE>', row, re.DOTALL | re.IGNORECASE)

            if te_cells and len(te_cells) >= 2:
                # TE 기반 형식 (젬 등)
                account_name = self._clean_text(te_cells[0])

                if not account_name:
                    continue

                # 당기 값 추출: Cell 1 (세부값) 우선, 없으면 Cell 2 (소계)
                value = None
                if len(te_cells) > 1:
                    value = self._extract_number(te_cells[1])
                if value is None and len(te_cells) > 2:
                    value = self._extract_number(te_cells[2])

                if value is not None:
                    field_name = self._map_account_to_field(account_name)
                    if field_name and field_name not in values:
                        values[field_name] = value * unit_multiplier
                        logger.debug(f"Parsed (TE): {account_name} -> {field_name} = {value * unit_multiplier:,}")
                continue

            # TD 태그 (일반 형식)
            cells = re.findall(r'<TD[^>]*>(.*?)</TD>', row, re.DOTALL | re.IGNORECASE)

            if len(cells) < 3:
                continue

            # 첫 번째 셀: 계정과목명
            account_name = self._clean_text(cells[0])

            if not account_name:
                continue

            # 당기 값 추출: Cell 2 (세부값) 우선, 없으면 Cell 3 (소계)
            value = None

            # Cell 2: 당기 세부값 (개별 항목)
            if len(cells) > 2:
                value = self._extract_number(cells[2])

            # Cell 3: 당기 소계 (합계 항목) - 세부값이 없으면 사용
            if value is None and len(cells) > 3:
                value = self._extract_number(cells[3])

            if value is None:
                continue

            # 계정과목명 -> 필드명 매핑
            field_name = self._map_account_to_field(account_name)

            if field_name and field_name not in values:
                values[field_name] = value * unit_multiplier
                logger.debug(f"Parsed (TD): {account_name} -> {field_name} = {value * unit_multiplier:,}")

        return values

    def _clean_text(self, html: str) -> str:
        """HTML 태그 제거 및 텍스트 정리

        '유 동 자 산' -> '유동자산' 등 공백 제거
        """
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', html)
        # 한글 사이 공백 제거 (예: "유 동 자 산" -> "유동자산")
        text = re.sub(r'([가-힣])\s+([가-힣])', r'\1\2', text)
        # 반복 적용 (3글자 이상에서 필요)
        while re.search(r'([가-힣])\s+([가-힣])', text):
            text = re.sub(r'([가-힣])\s+([가-힣])', r'\1\2', text)
        # 공백 정리
        text = re.sub(r'\s+', ' ', text).strip()
        # 로마숫자/번호 접두사 제거
        text = re.sub(r'^[IⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ\d]+\.\s*', '', text)
        return text

    def _extract_number(self, html: str) -> Optional[int]:
        """HTML에서 숫자 추출

        지원 형식:
        - 1,234,567
        - (1,234,567) : 음수
        - -1,234,567 : 음수
        - - : None (값 없음)
        """
        text = re.sub(r'<[^>]+>', '', html).strip()

        # 빈 값 또는 "-" 만 있는 경우
        if not text or text == '-':
            return None

        # 괄호로 둘러싸인 음수: (1,234,567)
        negative_match = re.search(r'\((\d{1,3}(?:,\d{3})*(?:\.\d+)?)\)', text)
        if negative_match:
            num_str = negative_match.group(1).replace(',', '')
            return -int(float(num_str))

        # 일반 숫자 또는 음수: 1,234,567 또는 -1,234,567
        num_match = re.search(r'(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?)', text)
        if num_match:
            num_str = num_match.group(1).replace(',', '')
            return int(float(num_str))

        return None

    def _map_account_to_field(self, account_name: str) -> Optional[str]:
        """계정과목명을 필드명으로 매핑

        ACCOUNT_MAPPING을 역으로 사용하여 한글 계정명 -> 영문 필드명 변환
        """
        # 공백 제거 및 정규화
        normalized = re.sub(r'\s+', '', account_name)

        for field_name, aliases in self.ACCOUNT_MAPPING.items():
            for alias in aliases:
                # 공백 제거 후 비교
                normalized_alias = re.sub(r'\s+', '', alias)
                if normalized == normalized_alias:
                    return field_name
                # 부분 매칭 (접두사/접미사 제거 후)
                if normalized.endswith(normalized_alias) or normalized_alias.endswith(normalized):
                    return field_name

        return None

    def _extract_fiscal_year(self, xml_content: str, rcept_no: str, report_nm: str) -> Optional[int]:
        """회계연도 추출

        우선순위:
        1. report_nm에서 추출: "감사보고서 (2024.12)" -> 2024
        2. XML 내 "제 38 기 2024년" 패턴
        3. rcept_no 앞 4자리 - 1
        """
        # 1. report_nm에서 추출
        year_match = re.search(r'\((\d{4})\.\d+\)', report_nm)
        if year_match:
            return int(year_match.group(1))

        # 2. XML 내 연도 패턴
        xml_year_match = re.search(r'제\s*\d+\s*기\s*(\d{4})년', xml_content)
        if xml_year_match:
            return int(xml_year_match.group(1))

        # 3. rcept_no에서 추출 (제출연도 - 1)
        if rcept_no and len(rcept_no) >= 4:
            try:
                submit_year = int(rcept_no[:4])
                return submit_year - 1
            except ValueError:
                pass

        return None

    async def parse(self, zip_path: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
        """감사보고서에서 재무 데이터 파싱

        Args:
            zip_path: DART 보고서 ZIP 파일 경로
            meta: 메타데이터 (corp_code, rcept_no, report_nm 등)

        Returns:
            {
                'success': bool,
                'data': {field_name: value, ...},
                'errors': [],
                'meta': {...},
                'target_year': int
            }
        """
        result = {
            'success': False,
            'data': {},
            'errors': [],
        }

        # ZIP에서 XML 추출
        xml_content = self.extract_xml_from_zip(zip_path)
        if not xml_content:
            result['errors'].append('XML extraction failed')
            return result

        # 감사보고서 확인
        if not self.is_audit_report(xml_content):
            result['errors'].append('Not an audit report - use FinancialParser instead')
            return result

        # 회계연도 추출
        rcept_no = meta.get('rcept_no', '')
        report_nm = meta.get('report_nm', '')
        target_year = self._extract_fiscal_year(xml_content, rcept_no, report_nm)

        if not target_year:
            result['errors'].append('Could not determine fiscal year')
            return result

        # 재무제표 섹션별 파싱
        all_values = {}

        for section_name in ['balance_sheet', 'income_statement', 'cash_flow']:
            table_content = self._extract_table_section(xml_content, section_name)

            if not table_content:
                logger.debug(f"Section not found: {section_name}")
                continue

            # 단위 감지
            unit_multiplier = self._detect_unit_from_table(table_content)
            logger.debug(f"{section_name}: unit = {unit_multiplier}")

            # 값 파싱
            section_values = self._parse_table_rows(table_content, unit_multiplier)

            # 중복 방지하며 병합
            for field, value in section_values.items():
                if field not in all_values:
                    all_values[field] = value

        if all_values:
            result['data'] = all_values
            result['success'] = True
            result['meta'] = {
                'corp_code': meta.get('corp_code'),
                'rcept_no': meta.get('rcept_no'),
                'report_nm': meta.get('report_nm'),
                'report_type': 'audit',  # 감사보고서 표시
            }
            result['target_year'] = target_year

            logger.info(f"Parsed {len(all_values)} fields from audit report for {meta.get('corp_code')}")
        else:
            result['errors'].append('No financial data extracted')

        return result

    async def parse_and_save(self, conn: asyncpg.Connection, zip_path: Path, meta: Dict[str, Any]) -> bool:
        """감사보고서 파싱 및 DB 저장

        Args:
            conn: DB 연결
            zip_path: ZIP 파일 경로
            meta: 메타데이터

        Returns:
            성공 여부
        """
        # 회사 캐시 로드 (필요시)
        if not self.company_cache:
            await self.load_companies(conn)

        # 파싱
        result = await self.parse(zip_path, meta)

        if not result['success']:
            logger.warning(f"Parse failed: {result['errors']}")
            return False

        # company_id 조회
        corp_code = meta.get('corp_code')
        company_id = self.company_cache.get(corp_code)

        if not company_id:
            logger.warning(f"Company not found for corp_code: {corp_code}")
            return False

        # financial_details 테이블에 UPSERT
        data = result['data']
        target_year = result['target_year']

        # 기존 컬럼만 사용 (financial_details 테이블 스키마에 맞춤)
        valid_columns = await self._get_valid_columns(conn)

        # unique constraint: (company_id, fiscal_year, fiscal_quarter, fs_type)
        insert_data = {
            'id': str(uuid.uuid4()),
            'company_id': company_id,
            'fiscal_year': target_year,
            'fiscal_quarter': None,  # 감사보고서는 연간 데이터 (None = annual)
            'fs_type': 'OFS',  # 기본값: 개별 재무제표 (OFS = Own Financial Statements)
            'source_type': 'audit_report',  # 감사보고서 출처 표시
        }

        # 연결감사보고서인 경우 fs_type 변경
        report_nm = meta.get('report_nm', '')
        if '연결' in report_nm:
            insert_data['fs_type'] = 'CFS'  # CFS = Consolidated Financial Statements

        for field, value in data.items():
            if field in valid_columns:
                insert_data[field] = value

        # UPSERT 쿼리
        columns = list(insert_data.keys())
        placeholders = [f'${i+1}' for i in range(len(columns))]

        # ON CONFLICT 처리 (company_id, fiscal_year, fiscal_quarter, fs_type가 unique constraint)
        update_clause = ', '.join([
            f"{col} = EXCLUDED.{col}"
            for col in columns
            if col not in ('id', 'company_id', 'fiscal_year', 'fiscal_quarter', 'fs_type')
        ])

        query = f"""
            INSERT INTO financial_details ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (company_id, fiscal_year, fiscal_quarter, fs_type)
            DO UPDATE SET {update_clause}
        """

        try:
            await conn.execute(query, *[insert_data[col] for col in columns])
            logger.info(f"Saved financial_details for company_id={company_id}, year={target_year}")
            return True
        except Exception as e:
            logger.error(f"DB save failed: {e}")
            return False

    async def _get_valid_columns(self, conn: asyncpg.Connection) -> set:
        """financial_details 테이블의 유효한 컬럼 목록 조회"""
        rows = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'financial_details'
        """)
        return {row['column_name'] for row in rows}

    async def save_to_db(self, conn, data: Dict[str, Any]) -> bool:
        """파싱 결과 DB 저장 (BaseParser 추상 메서드 구현)

        parse_and_save 메서드가 이 기능을 수행하므로, 이 메서드는 간단히 구현
        """
        if not data.get('success'):
            return False

        # 실제 저장은 parse_and_save에서 수행
        # 이 메서드는 인터페이스 준수를 위한 구현
        logger.warning("Use parse_and_save() for full DB save functionality")
        return True


# CLI 테스트용
async def test_parser(zip_path: str, corp_code: str, report_nm: str = "감사보고서"):
    """파서 테스트"""
    parser = AuditReportParser(skip_db_check=True)

    meta = {
        'corp_code': corp_code,
        'rcept_no': Path(zip_path).stem,
        'report_nm': report_nm,
    }

    result = await parser.parse(Path(zip_path), meta)

    if result['success']:
        print(f"\n=== Parsed Financial Data ===")
        print(f"Fiscal Year: {result['target_year']}")
        print(f"Fields: {len(result['data'])}")
        print()
        for field, value in sorted(result['data'].items()):
            print(f"  {field}: {value:,}")
    else:
        print(f"Parse failed: {result['errors']}")

    return result


if __name__ == '__main__':
    import asyncio
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m scripts.parsers.audit_report_parser <zip_path> <corp_code>")
        sys.exit(1)

    zip_path = sys.argv[1]
    corp_code = sys.argv[2]
    report_nm = sys.argv[3] if len(sys.argv) > 3 else "감사보고서"

    asyncio.run(test_parser(zip_path, corp_code, report_nm))
