#!/usr/bin/env python3
"""
임원 임기 정보 파싱 스크립트
사업보고서에서 임원의 임기만료일(term_end_date) 추출
- XML 태그: AUNIT="SH5_FIH" AUNITVALUE="YYYYMMDD" (임기만료일)
- 재직기간(SH5_PER)에서 term_start_date 계산 가능
"""
import asyncio
import asyncpg
import logging
import os
import re
import zipfile
import glob
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any, Optional
import unicodedata

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
DART_DATA_DIR = '/Users/jaejoonpark/raymontology/backend/data/dart'


def normalize_name(name: str) -> str:
    """이름 정규화"""
    if not name:
        return ""
    name = unicodedata.normalize('NFC', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'[\(\)（）\[\]【】].*', '', name)
    return name.strip()


def parse_date_yyyymmdd(date_str: str) -> Optional[date]:
    """YYYYMMDD 형식 날짜 파싱"""
    if not date_str or len(date_str) != 8:
        return None
    try:
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        # 유효성 검사
        if year < 1900 or year > 2100:
            return None
        if month < 1 or month > 12:
            return None
        if day < 1 or day > 31:
            return None
        return date(year, month, day)
    except (ValueError, TypeError):
        return None


def parse_service_period(period_str: str) -> Optional[int]:
    """재직기간 문자열에서 년수 추출 (예: "3년" -> 3)"""
    if not period_str:
        return None
    match = re.search(r'(\d+)\s*년', period_str)
    if match:
        return int(match.group(1))
    return None


class OfficerTenureParser:
    """임원 임기 정보 파싱"""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.stats = {'parsed': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        self.company_cache = {}
        self.officer_cache = {}

    async def load_caches(self):
        """회사 및 임원 캐시 로드"""
        # 회사 캐시
        rows = await self.conn.fetch("""
            SELECT id, corp_code FROM companies
            WHERE corp_code IS NOT NULL AND market IN ('KOSPI', 'KOSDAQ')
        """)
        self.company_cache = {r['corp_code']: r['id'] for r in rows}
        logger.info(f"상장사 캐시 로드: {len(self.company_cache)}개")

        # 임원 캐시 (이름 기준)
        rows = await self.conn.fetch("""
            SELECT op.id as position_id, o.name, op.company_id
            FROM officer_positions op
            JOIN officers o ON o.id = op.officer_id
            WHERE op.term_end_date IS NULL
        """)
        for r in rows:
            key = (str(r['company_id']), normalize_name(r['name']))
            self.officer_cache[key] = r['position_id']
        logger.info(f"임원 캐시 로드: {len(self.officer_cache)}개")

    def parse_xml_content(self, xml_content: bytes, corp_code: str) -> List[Dict[str, Any]]:
        """XML에서 임원 임기 정보 추출"""
        results = []

        try:
            # UTF-8 또는 EUC-KR 시도
            try:
                content = xml_content.decode('utf-8')
            except:
                content = xml_content.decode('euc-kr', errors='ignore')

            # 임원 섹션 찾기 (SH5_DRCT_STT)
            section_match = re.search(r'<TABLE-GROUP ACLASS="SH5_DRCT_STT"[^>]*>(.*?)</TABLE-GROUP>',
                                      content, re.DOTALL | re.IGNORECASE)
            if not section_match:
                return results

            section = section_match.group(1)

            # 각 임원 행(TR) 파싱
            rows = re.findall(r'<TR[^>]*>(.*?)</TR>', section, re.DOTALL | re.IGNORECASE)

            for row in rows:
                officer = {}

                # 성명 추출 (SH5_NM_T)
                name_match = re.search(r'ACODE="SH5_NM_T"[^>]*>([^<]+)', row)
                if name_match:
                    officer['name'] = name_match.group(1).strip()
                    officer['name'] = re.sub(r'&cr;', ' ', officer['name'])
                    officer['name'] = officer['name'].strip()

                # 임기만료일 추출 (SH5_FIH)
                tenure_match = re.search(r'AUNIT="SH5_FIH"\s+AUNITVALUE="(\d{8})"', row)
                if tenure_match:
                    officer['term_end_date'] = parse_date_yyyymmdd(tenure_match.group(1))

                # 재직기간 추출 (SH5_PER) - 선택적으로 term_start_date 계산에 사용
                period_match = re.search(r'ACODE="SH5_PER"[^>]*>([^<]+)', row)
                if period_match:
                    period_text = period_match.group(1).strip()
                    period_text = re.sub(r'&cr;', '', period_text)
                    officer['service_years'] = parse_service_period(period_text)

                # 직위 추출 (SH5_LEV)
                position_match = re.search(r'ACODE="SH5_LEV"[^>]*>([^<]+)', row)
                if position_match:
                    position = position_match.group(1).strip()
                    position = re.sub(r'&cr;', ' ', position)
                    officer['position'] = position.strip()

                # 유효한 데이터만 추가
                if officer.get('name') and officer.get('term_end_date'):
                    officer['corp_code'] = corp_code

                    # term_start_date 계산 (term_end_date - service_years)
                    if officer.get('service_years') and officer.get('term_end_date'):
                        try:
                            officer['term_start_date'] = officer['term_end_date'] - relativedelta(years=officer['service_years'])
                        except:
                            officer['term_start_date'] = None

                    results.append(officer)

        except Exception as e:
            logger.debug(f"XML 파싱 오류: {e}")

        return results

    async def process_zip_file(self, zip_path: str) -> int:
        """ZIP 파일에서 임기 정보 추출 및 업데이트"""
        updated = 0

        # 경로에서 corp_code 추출
        path_parts = zip_path.split('/')
        corp_code = None
        for i, part in enumerate(path_parts):
            if part.startswith('batch_') and i + 1 < len(path_parts):
                corp_code = path_parts[i + 1]
                break

        if not corp_code or corp_code not in self.company_cache:
            self.stats['skipped'] += 1
            return 0

        company_id = self.company_cache[corp_code]

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    # 메인 XML 파일만 처리 (00760은 감사보고서)
                    if name.endswith('.xml') and '_00760' not in name:
                        content = zf.read(name)
                        officers = self.parse_xml_content(content, corp_code)

                        for officer in officers:
                            try:
                                # 캐시에서 매칭되는 임원 찾기
                                key = (str(company_id), normalize_name(officer.get('name', '')))
                                position_id = self.officer_cache.get(key)

                                if position_id:
                                    # 임기 정보 업데이트
                                    await self.conn.execute("""
                                        UPDATE officer_positions
                                        SET term_end_date = $1,
                                            term_start_date = $2,
                                            updated_at = NOW()
                                        WHERE id = $3
                                        AND (term_end_date IS NULL OR term_end_date != $1)
                                    """,
                                        officer.get('term_end_date'),
                                        officer.get('term_start_date'),
                                        position_id
                                    )
                                    updated += 1
                                    self.stats['updated'] += 1
                                else:
                                    # 이름으로 직접 매칭 시도
                                    result = await self.conn.fetchval("""
                                        UPDATE officer_positions op
                                        SET term_end_date = $1,
                                            term_start_date = $2,
                                            updated_at = NOW()
                                        FROM officers o
                                        WHERE op.officer_id = o.id
                                        AND op.company_id = $3
                                        AND o.name = $4
                                        AND op.term_end_date IS NULL
                                        RETURNING op.id
                                    """,
                                        officer.get('term_end_date'),
                                        officer.get('term_start_date'),
                                        company_id,
                                        officer.get('name')
                                    )
                                    if result:
                                        updated += 1
                                        self.stats['updated'] += 1

                            except Exception as e:
                                logger.debug(f"업데이트 오류: {e}")
                                self.stats['errors'] += 1

                        self.stats['parsed'] += len(officers)

        except Exception as e:
            logger.debug(f"ZIP 처리 오류 {zip_path}: {e}")
            self.stats['errors'] += 1

        return updated

    async def process_all(self, target_years: List[int] = None, limit: int = None):
        """전체 ZIP 파일 처리 - 상장사 중심 최적화"""
        await self.load_caches()

        if target_years is None:
            target_years = [2022, 2023, 2024]

        # 상장사 corp_code 목록
        listed_corp_codes = set(self.company_cache.keys())
        logger.info(f"상장사 corp_code: {len(listed_corp_codes)}개")

        # 상장사 디렉토리만 탐색
        filtered_zips = []
        for batch_dir in glob.glob(f"{DART_DATA_DIR}/batch_*"):
            for corp_dir in glob.glob(f"{batch_dir}/*"):
                corp_code = os.path.basename(corp_dir)
                if corp_code in listed_corp_codes:
                    # 연도별 ZIP 파일 찾기
                    for year in target_years:
                        year_dir = os.path.join(corp_dir, str(year))
                        if os.path.exists(year_dir):
                            # 사업보고서 우선 (meta.json으로 필터링)
                            for zp in glob.glob(f"{year_dir}/*.zip"):
                                # meta.json 확인
                                meta_path = zp.replace('.zip', '_meta.json')
                                if os.path.exists(meta_path):
                                    try:
                                        import json
                                        with open(meta_path, 'r') as f:
                                            meta = json.load(f)
                                        # 사업보고서만 (report_nm에 "사업보고서" 포함)
                                        if '사업보고서' in meta.get('report_nm', ''):
                                            filtered_zips.append(zp)
                                    except:
                                        pass
                                else:
                                    # meta.json 없으면 일단 포함
                                    filtered_zips.append(zp)

        logger.info(f"총 ZIP 파일: {len(filtered_zips)}개 (상장사 사업보고서)")

        if limit:
            filtered_zips = filtered_zips[:limit]

        logger.info(f"처리 대상 ZIP: {len(filtered_zips)}개")

        # 처리
        for i, zp in enumerate(filtered_zips):
            await self.process_zip_file(zp)

            if (i + 1) % 500 == 0:
                logger.info(f"진행: {i+1}/{len(filtered_zips)} - 파싱: {self.stats['parsed']}, 업데이트: {self.stats['updated']}")

        return self.stats


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='임원 임기 정보 파싱')
    parser.add_argument('--years', type=str, default='2022,2023,2024',
                       help='파싱할 연도 (쉼표 구분)')
    parser.add_argument('--limit', type=int, default=None,
                       help='처리할 최대 파일 수')
    args = parser.parse_args()

    target_years = [int(y.strip()) for y in args.years.split(',')]

    logger.info("=" * 80)
    logger.info("임원 임기 정보 파싱 시작")
    logger.info(f"대상 연도: {target_years}")
    logger.info("=" * 80)

    conn = await asyncpg.connect(DB_URL)

    try:
        parser = OfficerTenureParser(conn)
        stats = await parser.process_all(target_years, limit=args.limit)

        logger.info("\n" + "=" * 80)
        logger.info("임기 파싱 완료")
        logger.info(f"파싱: {stats['parsed']}개")
        logger.info(f"업데이트: {stats['updated']}개")
        logger.info(f"스킵: {stats['skipped']}개")
        logger.info(f"오류: {stats['errors']}개")

        # 현재 상태
        tenure_count = await conn.fetchval("""
            SELECT COUNT(*) FROM officer_positions
            WHERE term_end_date IS NOT NULL
        """)
        total_count = await conn.fetchval("SELECT COUNT(*) FROM officer_positions")
        logger.info(f"\n현재 임기 정보 보유: {tenure_count:,}개 / 전체 {total_count:,}개 ({tenure_count*100/total_count:.1f}%)")

        # 연도별 통계
        year_stats = await conn.fetch("""
            SELECT
                EXTRACT(YEAR FROM term_end_date)::int as year,
                COUNT(*) as cnt
            FROM officer_positions
            WHERE term_end_date IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM term_end_date)
            ORDER BY year
        """)
        for row in year_stats:
            if row['year']:
                logger.info(f"  - 임기만료 {row['year']}년: {row['cnt']}개")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
