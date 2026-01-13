"""
ShareholderParser - 대주주 및 특수관계인 파서

DART 보고서에서 '최대주주 및 특수관계인의 주식소유 현황' 테이블 파싱.

파싱 대상:
- VII. 주주에 관한 사항
  └── 가. 최대주주 및 특수관계인의 주식소유 현황

추출 필드:
- SH5_NM_T: 성명 (shareholder_name)
- SH5_END_CNT: 기말 주식수 (share_count)
- SH5_END_RT: 기말 지분율 (share_ratio)
- SH5_RET: 관계 (relationship - 최대주주, 특수관계인 등)

사용법:
    from scripts.parsers import ShareholderParser

    parser = ShareholderParser(database_url)
    result = await parser.parse(zip_path, meta)
    if result['success']:
        await parser.save_to_db(conn, result)
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import BaseParser

logger = logging.getLogger(__name__)


# 무효한 주주명 패턴 (테이블 헤더, 주식 종류, 합계 등)
INVALID_SHAREHOLDER_PATTERNS = [
    # 테이블 헤더
    r'^(주식수|지분율|성명|관계|비고|성명순|비율|수량)$',
    # 주식 종류
    r'^(보통주|우선주|종류주|자기주)[\s식]*$',
    r'^의결권[\s]*(없는|없는[\s]*|이[\s]*없는)[\s]*주식$',
    r'^의결권[\s]*없는[\s]*주식$',
    # 합계/소계
    r'^(합계|소계|계|총계|총[\s]*계)$',
    # 숫자만
    r'^[\d,.\s]+$',
    # 기타 무효 패턴
    r'^(기타주주|기타|-)$',
    r'^[―—]+$',
]


def is_valid_shareholder_name(name: str) -> bool:
    """유효한 주주명인지 검증 (헤더, 주식종류, 합계 등 제외)

    Args:
        name: 주주명 문자열

    Returns:
        유효하면 True, 무효하면 False
    """
    if not name:
        return False

    # 공백 제거
    name = name.strip()

    # 너무 짧은 이름 (1글자)
    if len(name) < 2:
        return False

    # 무효 패턴 체크
    for pattern in INVALID_SHAREHOLDER_PATTERNS:
        if re.match(pattern, name, re.IGNORECASE):
            return False

    return True


def normalize_shareholder_name(name: str) -> str:
    """주주명 정규화 (검색용)

    - 공백 제거
    - (주), 주식회사 정규화
    - 소문자 변환
    """
    if not name:
        return ''

    normalized = name.strip()

    # (주) → 주식회사 통일
    normalized = re.sub(r'\(주\)', '주식회사', normalized)
    normalized = re.sub(r'\（주\）', '주식회사', normalized)  # 전각 괄호

    # 연속 공백 제거
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized.strip()


def detect_shareholder_type(name: str, relationship: str) -> str:
    """주주 유형 추론

    Args:
        name: 주주명
        relationship: 관계 (최대주주, 특수관계인 등)

    Returns:
        'individual' | 'corporation' | 'institution'
    """
    # 법인 키워드
    corp_keywords = [
        '주식회사', '(주)', '㈜', '유한회사', '유한책임회사',
        'Co.', 'Corp.', 'Inc.', 'Ltd.', 'LLC',
        '투자조합', '사모펀드', '펀드', '조합', '재단', '기금',
    ]

    # 기관투자자 키워드
    inst_keywords = [
        '연금', '금고', '공제회', '신탁', '보험', '은행', '증권',
        '자산운용', '투자신탁', '투자자문',
    ]

    for keyword in inst_keywords:
        if keyword in name:
            return 'institution'

    for keyword in corp_keywords:
        if keyword in name:
            return 'corporation'

    # 관계 필드에서 추론
    if '법인' in relationship or '회사' in relationship:
        return 'corporation'

    # 기본값: 개인
    return 'individual'


class ShareholderParser(BaseParser):
    """대주주 및 특수관계인 파서"""

    # ACODE 매핑 (다양한 보고서 형식 지원)
    SHAREHOLDER_CODES = {
        'name': ['SH5_NM_T', 'SH5_NM', 'NM'],
        'share_count': ['SH5_END_CNT', 'SH5_CNT', 'END_CNT'],
        'share_ratio': ['SH5_END_RT', 'SH5_RT', 'END_RT'],
        'relationship': ['SH5_RET', 'RET', 'RELATION'],
        'stock_type': ['STK_KND', 'STK_TYPE'],
    }

    # 섹션 TITLE 패턴
    SECTION_PATTERNS = [
        r'VII\.\s*주주에\s*관한\s*사항',
        r'가\.\s*최대주주\s*및\s*특수관계인의\s*주식소유\s*현황',
        r'최대주주\s*및\s*특수관계인',
        r'Matters\s+Related\s+to\s+Shareholders',
    ]

    # 테이블 클래스
    TABLE_CLASS = 'BSH_SPCL'

    def __init__(self, database_url: Optional[str] = None):
        super().__init__(database_url)
        self._companies_cache: Dict[str, str] = {}  # corp_code -> company_id

    async def load_companies(self, conn) -> None:
        """회사 캐시 로드 (corp_code -> company_id)"""
        query = "SELECT id::text, corp_code FROM companies WHERE corp_code IS NOT NULL"
        rows = await conn.fetch(query)
        self._companies_cache = {row['corp_code']: row['id'] for row in rows}
        logger.info(f"Loaded {len(self._companies_cache)} companies into cache")

    def _find_shareholder_section(self, xml_content: str) -> Optional[str]:
        """주주 관련 섹션 찾기"""
        # TABLE-GROUP ACLASS="BSH_SPCL" 찾기
        pattern = rf'<TABLE-GROUP\s+ACLASS="{self.TABLE_CLASS}"[^>]*>(.*?)</TABLE-GROUP>'
        match = re.search(pattern, xml_content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)

        # 폴백: 섹션 TITLE로 찾기
        return self._extract_statement_section(xml_content, self.SECTION_PATTERNS)

    def _extract_cell_value(self, row: str, acodes: List[str]) -> Optional[str]:
        """테이블 행에서 특정 ACODE 값 추출"""
        for acode in acodes:
            # TE 태그에서 추출
            pattern = rf'<TE[^>]*ACODE="{acode}"[^>]*>([^<]*)</TE>'
            match = re.search(pattern, row, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value and value != '-':
                    return value

            # TU 태그에서 추출 (단위 포함)
            pattern = rf'<TU[^>]*ACODE="{acode}"[^>]*>([^<]*)</TU>'
            match = re.search(pattern, row, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value and value != '-':
                    return value

        return None

    def _parse_shareholders_from_table(self, section: str) -> List[Dict[str, Any]]:
        """테이블에서 주주 정보 추출"""
        shareholders = []

        # TR 태그로 행 분리
        rows = re.findall(r'<TR[^>]*>(.*?)</TR>', section, re.DOTALL | re.IGNORECASE)

        for row in rows:
            # THEAD 행 스킵
            if '<TH' in row:
                continue

            # 각 필드 추출
            name = self._extract_cell_value(row, self.SHAREHOLDER_CODES['name'])
            if not name or not is_valid_shareholder_name(name):
                continue

            share_count_str = self._extract_cell_value(row, self.SHAREHOLDER_CODES['share_count'])
            share_ratio_str = self._extract_cell_value(row, self.SHAREHOLDER_CODES['share_ratio'])
            relationship = self._extract_cell_value(row, self.SHAREHOLDER_CODES['relationship']) or ''
            stock_type = self._extract_cell_value(row, self.SHAREHOLDER_CODES['stock_type']) or '보통주'

            # 보통주가 아닌 경우 스킵 (우선주, 종류주 등)
            if stock_type and '보통' not in stock_type:
                continue

            # 숫자 파싱
            share_count = None
            if share_count_str:
                try:
                    share_count = int(re.sub(r'[^\d]', '', share_count_str))
                except (ValueError, TypeError):
                    pass

            share_ratio = None
            if share_ratio_str:
                try:
                    share_ratio = float(re.sub(r'[^\d.]', '', share_ratio_str))
                except (ValueError, TypeError):
                    pass

            # 주주 유형 추론
            shareholder_type = detect_shareholder_type(name, relationship)

            # 최대주주 여부
            is_largest = '최대주주' in relationship and '최대주주의' not in relationship

            # 특수관계인 여부
            is_related = '특수관계' in relationship or '임원' in relationship

            shareholders.append({
                'shareholder_name': name,
                'shareholder_name_normalized': normalize_shareholder_name(name),
                'shareholder_type': shareholder_type,
                'share_count': share_count,
                'share_ratio': share_ratio,
                'is_largest_shareholder': is_largest,
                'is_related_party': is_related,
                'relationship': relationship,
            })

        return shareholders

    async def parse(self, zip_path: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
        """보고서에서 대주주 정보 파싱

        Args:
            zip_path: ZIP 파일 경로
            meta: 메타 정보 (corp_code, rcept_no 등)

        Returns:
            {'success': bool, 'shareholders': [...], 'corp_code': str, ...}
        """
        result = {
            'success': False,
            'shareholders': [],
            'corp_code': meta.get('corp_code'),
            'rcept_no': meta.get('rcept_no'),
            'report_date': None,
            'report_year': None,
            'report_quarter': None,
        }

        try:
            # XML 추출
            xml_content = self.extract_xml_from_zip(zip_path)
            if not xml_content:
                logger.warning(f"No XML content: {zip_path}")
                return result

            # 주주 섹션 찾기
            section = self._find_shareholder_section(xml_content)
            if not section:
                logger.debug(f"No shareholder section found: {zip_path}")
                return result

            # 기준일 추출
            date_match = re.search(r'AUNITVALUE="(\d{8})"', section)
            if date_match:
                date_str = date_match.group(1)
                try:
                    report_date = datetime.strptime(date_str, '%Y%m%d').date()
                    result['report_date'] = report_date
                    result['report_year'] = report_date.year

                    # 분기 추론
                    month = report_date.month
                    if month <= 3:
                        result['report_quarter'] = 4  # 전년도 사업보고서
                        result['report_year'] -= 1
                    elif month <= 5:
                        result['report_quarter'] = 1  # 1분기
                    elif month <= 8:
                        result['report_quarter'] = 2  # 반기
                    elif month <= 11:
                        result['report_quarter'] = 3  # 3분기
                    else:
                        result['report_quarter'] = 4  # 사업보고서
                except ValueError:
                    pass

            # 메타에서 연도/분기 추출 (폴백)
            if not result['report_year']:
                report_type = meta.get('report_type', '')
                if 'q3' in report_type.lower() or '3분기' in report_type:
                    result['report_quarter'] = 3
                elif 'q1' in report_type.lower() or '1분기' in report_type:
                    result['report_quarter'] = 1
                elif '반기' in report_type or 'q2' in report_type.lower():
                    result['report_quarter'] = 2
                else:
                    result['report_quarter'] = 4  # 사업보고서

                # 연도 추출
                year_match = re.search(r'(\d{4})', str(meta.get('report_type', '')))
                if year_match:
                    result['report_year'] = int(year_match.group(1))
                else:
                    # rcept_no에서 추출 (YYYYMMDD...)
                    rcept_no = meta.get('rcept_no', '')
                    if len(rcept_no) >= 8:
                        try:
                            result['report_year'] = int(rcept_no[:4])
                        except ValueError:
                            pass

            # 주주 정보 파싱
            shareholders = self._parse_shareholders_from_table(section)

            if shareholders:
                result['success'] = True
                result['shareholders'] = shareholders
                logger.debug(f"Parsed {len(shareholders)} shareholders from {zip_path.name}")

        except Exception as e:
            logger.error(f"Parse error {zip_path}: {e}")
            self.stats['errors'] += 1

        return result

    async def save_to_db(self, conn, data: Dict[str, Any]) -> int:
        """파싱 결과 DB 저장 (UPSERT)

        Args:
            conn: asyncpg connection
            data: parse() 결과

        Returns:
            저장된 레코드 수
        """
        if not data.get('success') or not data.get('shareholders'):
            return 0

        corp_code = data.get('corp_code')
        if not corp_code:
            return 0

        # company_id 조회
        company_id = self._companies_cache.get(corp_code)
        if not company_id:
            # 캐시 미스 시 직접 조회
            query = "SELECT id::text FROM companies WHERE corp_code = $1"
            row = await conn.fetchrow(query, corp_code)
            if row:
                company_id = row['id']
                self._companies_cache[corp_code] = company_id
            else:
                logger.warning(f"Company not found: {corp_code}")
                return 0

        saved_count = 0

        for sh in data['shareholders']:
            try:
                # UPSERT (company_id + shareholder_name + report_year + report_quarter)
                query = """
                    INSERT INTO major_shareholders (
                        company_id, shareholder_name, shareholder_name_normalized,
                        shareholder_type, share_count, share_ratio,
                        is_largest_shareholder, is_related_party,
                        report_date, report_year, report_quarter,
                        source_rcept_no, updated_at
                    ) VALUES (
                        $1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, now()
                    )
                    ON CONFLICT (company_id, shareholder_name, report_year, report_quarter)
                    DO UPDATE SET
                        shareholder_name_normalized = EXCLUDED.shareholder_name_normalized,
                        shareholder_type = EXCLUDED.shareholder_type,
                        share_count = EXCLUDED.share_count,
                        share_ratio = EXCLUDED.share_ratio,
                        is_largest_shareholder = EXCLUDED.is_largest_shareholder,
                        is_related_party = EXCLUDED.is_related_party,
                        report_date = EXCLUDED.report_date,
                        source_rcept_no = EXCLUDED.source_rcept_no,
                        updated_at = now()
                """

                await conn.execute(
                    query,
                    company_id,
                    sh['shareholder_name'],
                    sh['shareholder_name_normalized'],
                    sh['shareholder_type'],
                    sh['share_count'],
                    sh['share_ratio'],
                    sh['is_largest_shareholder'],
                    sh['is_related_party'],
                    data['report_date'],
                    data['report_year'],
                    data['report_quarter'],
                    data['rcept_no'],
                )
                saved_count += 1

            except Exception as e:
                logger.error(f"DB save error for {sh['shareholder_name']}: {e}")
                self.stats['errors'] += 1

        self.stats['records_created'] += saved_count
        return saved_count

    def find_quarterly_reports(
        self,
        year: int,
        quarter: int,
        sample: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """분기별 보고서 검색 (Q3 2025 데이터 지원)

        Args:
            year: 연도 (2025)
            quarter: 분기 (1, 2, 3, 4)
            sample: 샘플 개수 (테스트용)

        Returns:
            [{'meta': dict, 'zip_path': Path, 'corp_code': str}, ...]
        """
        reports = []

        # Q3 2025 특별 경로
        if year == 2025 and quarter == 3:
            q3_dir = self.DART_DATA_DIR.parent / 'q3_reports_2025'
            if q3_dir.exists():
                for corp_dir in sorted(q3_dir.iterdir()):
                    if not corp_dir.is_dir():
                        continue

                    for meta_file in corp_dir.glob('*_meta.json'):
                        meta = self.load_meta(meta_file)
                        if not meta:
                            continue

                        zip_file = meta_file.with_name(
                            meta_file.name.replace('_meta.json', '.zip')
                        )
                        if zip_file.exists():
                            reports.append({
                                'meta': meta,
                                'zip_path': zip_file,
                                'corp_code': meta.get('corp_code'),
                            })

                        if sample and len(reports) >= sample:
                            break

                    if sample and len(reports) >= sample:
                        break
        else:
            # 기존 경로: data/dart/quarterly/{year}/{quarter}/
            quarter_dir = self.DART_DATA_DIR / 'quarterly' / str(year) / f'Q{quarter}'
            if quarter_dir.exists():
                for corp_dir in sorted(quarter_dir.iterdir()):
                    if not corp_dir.is_dir():
                        continue

                    for meta_file in corp_dir.glob('*_meta.json'):
                        meta = self.load_meta(meta_file)
                        if not meta:
                            continue

                        zip_file = meta_file.with_name(
                            meta_file.name.replace('_meta.json', '.zip')
                        )
                        if zip_file.exists():
                            reports.append({
                                'meta': meta,
                                'zip_path': zip_file,
                                'corp_code': meta.get('corp_code'),
                            })

                        if sample and len(reports) >= sample:
                            break

                    if sample and len(reports) >= sample:
                        break

        logger.info(f"Found {len(reports)} Q{quarter} {year} reports")
        return reports


# CLI 실행
async def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description='대주주 파서 CLI')
    parser.add_argument('--year', type=int, required=True, help='연도 (예: 2025)')
    parser.add_argument('--quarter', type=int, required=True, help='분기 (1-4)')
    parser.add_argument('--sample', type=int, help='샘플 개수')
    parser.add_argument('--dry-run', action='store_true', help='DB 저장 없이 테스트')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    import asyncpg

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL 환경변수가 설정되지 않았습니다")
        return

    shareholder_parser = ShareholderParser(database_url)

    # 보고서 검색
    reports = shareholder_parser.find_quarterly_reports(
        year=args.year,
        quarter=args.quarter,
        sample=args.sample
    )

    if not reports:
        print(f"Q{args.quarter} {args.year} 보고서를 찾을 수 없습니다")
        return

    print(f"Found {len(reports)} reports")

    # DB 연결
    conn = await asyncpg.connect(database_url)

    try:
        await shareholder_parser.load_companies(conn)

        total_saved = 0
        for i, report in enumerate(reports):
            if (i + 1) % 100 == 0:
                print(f"Progress: {i+1}/{len(reports)}")

            result = await shareholder_parser.parse(
                report['zip_path'],
                report['meta']
            )

            if result['success'] and not args.dry_run:
                saved = await shareholder_parser.save_to_db(conn, result)
                total_saved += saved
            elif result['success'] and args.dry_run:
                print(f"[DRY-RUN] Would save {len(result['shareholders'])} shareholders for {report['corp_code']}")

        print(f"\n=== 완료 ===")
        print(f"총 저장: {total_saved}")
        print(f"통계: {shareholder_parser.get_stats()}")

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
