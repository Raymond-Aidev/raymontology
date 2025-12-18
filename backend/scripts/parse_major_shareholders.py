#!/usr/bin/env python3
"""
대주주 정보 파싱 스크립트
사업보고서/분기보고서에서 최대주주 및 특수관계인 주식소유 현황 추출
- 2022-2024: 연간사업보고서 (ACODE=11011)
- 2025: 반기/분기보고서 (ACODE=11012, 11013)
"""
import asyncio
import asyncpg
import logging
import os
import re
import zipfile
import glob
from datetime import datetime
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET
import unicodedata

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = '/Users/jaejoonpark/raymontology/backend/data/dart'

# 보고서 타입
REPORT_TYPES = {
    '11011': ('ANNUAL', None),      # 사업보고서
    '11012': ('HALF', 2),           # 반기보고서
    '11013': ('QUARTERLY', None),   # 분기보고서
    '11014': ('QUARTERLY', None),   # 분기보고서(1분기)
}


def normalize_name(name: str) -> str:
    """이름 정규화"""
    if not name:
        return ""
    name = unicodedata.normalize('NFC', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'[\(\)（）\[\]【】].*', '', name)  # 괄호 내용 제거
    name = re.sub(r'㈜|주식회사|유한회사|합자회사', '', name)
    return name.strip()


def extract_number(text: str) -> Optional[int]:
    """텍스트에서 숫자 추출 (주식수)"""
    if not text:
        return None
    text = text.replace(',', '').replace(' ', '')
    match = re.search(r'[\d]+', text)
    if match:
        return int(match.group())
    return None


def extract_ratio(text: str) -> Optional[float]:
    """텍스트에서 지분율 추출"""
    if not text:
        return None
    text = text.replace(' ', '').replace('%', '')
    match = re.search(r'[\d.]+', text)
    if match:
        try:
            return float(match.group())
        except:
            pass
    return None


class ShareholderParser:
    """대주주 정보 파싱"""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.stats = {'parsed': 0, 'saved': 0, 'errors': 0, 'skipped': 0}
        self.company_cache = {}

    async def load_company_cache(self):
        """회사 정보 캐시 로드"""
        rows = await self.conn.fetch("SELECT id, corp_code FROM companies WHERE corp_code IS NOT NULL")
        self.company_cache = {r['corp_code']: r['id'] for r in rows}
        logger.info(f"회사 캐시 로드: {len(self.company_cache)}개")

    def parse_xml_content(self, xml_content: bytes) -> Dict[str, Any]:
        """XML에서 메타정보 및 주주 정보 추출"""
        result = {
            'corp_code': None,
            'report_type': None,
            'report_quarter': None,
            'fiscal_year': None,
            'shareholders': []
        }

        try:
            # UTF-8 또는 EUC-KR 시도
            try:
                content = xml_content.decode('utf-8')
            except:
                content = xml_content.decode('euc-kr', errors='ignore')

            # 메타정보 추출
            corp_match = re.search(r'AREGCIK="(\d+)"', content)
            if corp_match:
                result['corp_code'] = corp_match.group(1)

            acode_match = re.search(r'<DOCUMENT-NAME[^>]*ACODE="(\d+)"', content)
            if acode_match:
                acode = acode_match.group(1)
                if acode in REPORT_TYPES:
                    result['report_type'], result['report_quarter'] = REPORT_TYPES[acode]

            # 회계연도 추출 (여러 패턴 시도)
            # 패턴 1: PERIODTO (보고서 종료일)
            period_match = re.search(r'AUNIT="PERIODTO"[^>]*AUNITVALUE="(\d{4})', content)
            if period_match:
                result['fiscal_year'] = int(period_match.group(1))
            else:
                # 패턴 2: PERIODFROM (보고서 시작일)
                period_match = re.search(r'AUNIT="PERIODFROM"[^>]*AUNITVALUE="(\d{4})', content)
                if period_match:
                    result['fiscal_year'] = int(period_match.group(1))
                else:
                    # 패턴 3: 제XX기 연도 추출
                    year_match = re.search(r'(\d{4})년\s*\d{1,2}월\s*\d{1,2}일.*?까지', content)
                    if year_match:
                        result['fiscal_year'] = int(year_match.group(1))

            # 주주에 관한 사항 섹션 찾기
            shareholder_section = self._find_shareholder_section(content)
            if shareholder_section:
                result['shareholders'] = self._parse_shareholder_table(shareholder_section)

        except Exception as e:
            logger.debug(f"XML 파싱 오류: {e}")

        return result

    def _find_shareholder_section(self, content: str) -> Optional[str]:
        """주주 관한 사항 섹션 찾기"""
        patterns = [
            r'<TITLE[^>]*>VII\.\s*주주에 관한 사항</TITLE>(.*?)<TITLE',
            r'주주에 관한 사항</TITLE>(.*?)(?:<TITLE|</BODY)',
            r'1\.\s*최대주주\s*및\s*특수관계인의\s*주식소유\s*현황(.*?)(?:2\.|</SECTION)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _parse_shareholder_table(self, section: str) -> List[Dict]:
        """주주 테이블 파싱"""
        shareholders = []

        # TABLE 태그 찾기
        table_matches = re.findall(r'<TABLE[^>]*>(.*?)</TABLE>', section, re.DOTALL | re.IGNORECASE)

        for table_content in table_matches:
            # TR (행) 추출
            rows = re.findall(r'<TR[^>]*>(.*?)</TR>', table_content, re.DOTALL | re.IGNORECASE)

            # 헤더 분석
            header_indices = {}
            if rows:
                header_cells = re.findall(r'<T[HD][^>]*>(.*?)</T[HD]>', rows[0], re.DOTALL | re.IGNORECASE)
                for i, cell in enumerate(header_cells):
                    cell_text = re.sub(r'<[^>]+>', '', cell)
                    cell_text = re.sub(r'\s+', '', cell_text)  # 모든 공백 제거 (성 명 → 성명)
                    if '성명' in cell_text or '주주명' in cell_text:
                        header_indices['name'] = i
                    elif '관계' in cell_text:
                        header_indices['relationship'] = i
                    elif '주식수' in cell_text and '소유' not in cell_text:
                        header_indices['share_count'] = i
                    elif '지분율' in cell_text or '소유지분' in cell_text:
                        if 'ratio' not in header_indices:
                            header_indices['ratio'] = i

            # 데이터 행 파싱
            for row in rows[1:]:
                # TD 및 TE (Table Element) 태그 모두 지원
                cells = re.findall(r'<T[DE][^>]*>(.*?)</T[DE]>', row, re.DOTALL | re.IGNORECASE)
                if len(cells) < 3:
                    continue

                # 셀 텍스트 정리
                cell_texts = []
                for cell in cells:
                    text = re.sub(r'<[^>]+>', '', cell)
                    text = re.sub(r'&[^;]+;', '', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    cell_texts.append(text)

                # 데이터 추출
                shareholder = {}

                name_idx = header_indices.get('name', 0)
                if name_idx < len(cell_texts):
                    name = cell_texts[name_idx]
                    if name and len(name) > 1 and not name.startswith('-'):
                        shareholder['name'] = name

                rel_idx = header_indices.get('relationship')
                if rel_idx and rel_idx < len(cell_texts):
                    shareholder['relationship'] = cell_texts[rel_idx]

                # 주식수, 지분율 찾기 (숫자가 있는 셀)
                for i, text in enumerate(cell_texts):
                    if extract_number(text) and 'share_count' not in shareholder:
                        if '주' in text or text.replace(',', '').isdigit():
                            shareholder['share_count'] = extract_number(text)

                    ratio = extract_ratio(text)
                    if ratio and ratio < 100 and 'ratio' not in shareholder:
                        shareholder['ratio'] = ratio

                if shareholder.get('name'):
                    shareholders.append(shareholder)

        return shareholders

    async def process_zip_file(self, zip_path: str, target_years: List[int]) -> int:
        """ZIP 파일 처리"""
        saved = 0
        rcept_no = os.path.basename(zip_path).replace('.zip', '')

        # 파일 경로에서 연도 추출 (예: /2023/)
        path_year = None
        year_match = re.search(r'/(\d{4})/', zip_path)
        if year_match:
            path_year = int(year_match.group(1))

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.xml'):
                        content = zf.read(name)
                        result = self.parse_xml_content(content)

                        if not result['corp_code'] or not result['shareholders']:
                            continue

                        # 연도 설정 (XML에서 추출 또는 경로에서 추출)
                        fiscal_year = result['fiscal_year'] or path_year

                        # 연도 필터
                        if fiscal_year and fiscal_year not in target_years:
                            continue

                        company_id = self.company_cache.get(result['corp_code'])
                        if not company_id:
                            self.stats['skipped'] += 1
                            continue

                        # 주주 정보 저장
                        for sh in result['shareholders']:
                            try:
                                relationship = sh.get('relationship', '')
                                is_largest = relationship == '본인' or '최대주주' in relationship

                                # shareholder_type 결정
                                if relationship == '본인':
                                    shareholder_type = 'LARGEST'
                                elif relationship in ['임원', '특수관계인']:
                                    shareholder_type = 'RELATED'
                                else:
                                    shareholder_type = 'OTHER'

                                # 중복 확인 후 삽입
                                existing = await self.conn.fetchval("""
                                    SELECT id FROM major_shareholders
                                    WHERE company_id = $1
                                      AND shareholder_name = $2
                                      AND report_year = $3
                                      AND COALESCE(report_quarter, 0) = COALESCE($4, 0)
                                """, company_id, sh.get('name'), result['fiscal_year'], result.get('report_quarter'))

                                if existing:
                                    # 업데이트
                                    await self.conn.execute("""
                                        UPDATE major_shareholders SET
                                            share_count = $1,
                                            share_ratio = $2,
                                            shareholder_type = $3,
                                            updated_at = NOW()
                                        WHERE id = $4
                                    """, sh.get('share_count'), sh.get('ratio'), shareholder_type, existing)
                                else:
                                    # 신규 삽입
                                    await self.conn.execute("""
                                        INSERT INTO major_shareholders (
                                            company_id, shareholder_name, shareholder_name_normalized,
                                            shareholder_type, share_count, share_ratio,
                                            is_largest_shareholder, is_related_party,
                                            report_year, report_quarter, source_rcept_no
                                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                                    """,
                                    company_id,
                                    sh.get('name'),
                                    normalize_name(sh.get('name', '')),
                                    shareholder_type,
                                    sh.get('share_count'),
                                    sh.get('ratio'),
                                    is_largest,
                                    relationship not in ['본인', ''],
                                    result['fiscal_year'],
                                    result.get('report_quarter'),
                                    rcept_no
                                )
                                saved += 1
                                self.stats['saved'] += 1
                            except Exception as e:
                                logger.debug(f"저장 오류: {e}")
                                self.stats['errors'] += 1

                        self.stats['parsed'] += 1

        except Exception as e:
            logger.debug(f"ZIP 처리 오류 {zip_path}: {e}")
            self.stats['errors'] += 1

        return saved

    async def parse_all(self, target_years: List[int], report_types: List[str] = None, limit: int = None):
        """전체 파싱 실행"""
        await self.load_company_cache()

        # ZIP 파일 목록
        all_zips = glob.glob(f"{DART_DATA_DIR}/**/*.zip", recursive=True)
        logger.info(f"총 ZIP 파일: {len(all_zips)}개")

        # 필터링 (연도 기준)
        filtered_zips = []
        for zp in all_zips:
            # 경로에서 연도 추출 (예: /2023/ 또는 /2024/)
            for year in target_years:
                if f'/{year}/' in zp:
                    filtered_zips.append(zp)
                    break

        if limit:
            filtered_zips = filtered_zips[:limit]

        logger.info(f"처리 대상 ZIP: {len(filtered_zips)}개")

        # 처리
        for i, zp in enumerate(filtered_zips):
            await self.process_zip_file(zp, target_years)

            if (i + 1) % 500 == 0:
                logger.info(f"진행: {i+1}/{len(filtered_zips)} - 파싱: {self.stats['parsed']}, 저장: {self.stats['saved']}")

        return self.stats


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='대주주 정보 파싱')
    parser.add_argument('--years', type=str, default='2022,2023,2024',
                       help='파싱할 연도 (쉼표 구분)')
    parser.add_argument('--limit', type=int, default=None,
                       help='처리할 최대 파일 수')
    parser.add_argument('--include-2025-quarterly', action='store_true',
                       help='2025년 분기보고서 포함')
    args = parser.parse_args()

    target_years = [int(y.strip()) for y in args.years.split(',')]
    if args.include_2025_quarterly:
        target_years.append(2025)

    logger.info("=" * 80)
    logger.info("대주주 정보 파싱 시작")
    logger.info(f"대상 연도: {target_years}")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)

    try:
        parser = ShareholderParser(conn)
        stats = await parser.parse_all(target_years, limit=args.limit)

        logger.info("\n" + "=" * 80)
        logger.info("대주주 파싱 완료")
        logger.info(f"파싱: {stats['parsed']}개")
        logger.info(f"저장: {stats['saved']}개")
        logger.info(f"스킵: {stats['skipped']}개")
        logger.info(f"오류: {stats['errors']}개")

        # 현재 상태
        count = await conn.fetchval("SELECT COUNT(*) FROM major_shareholders")
        logger.info(f"\n현재 major_shareholders 테이블: {count:,}개")

        # 연도별 통계
        year_stats = await conn.fetch("""
            SELECT report_year, COUNT(*) as cnt
            FROM major_shareholders
            GROUP BY report_year
            ORDER BY report_year
        """)
        for row in year_stats:
            logger.info(f"  - {row['report_year']}년: {row['cnt']}개")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
