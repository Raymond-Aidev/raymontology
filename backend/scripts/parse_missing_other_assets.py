#!/usr/bin/env python3
"""
기타금융자산/기타자산 부족 데이터 파싱 스크립트

DB에서 other_financial_assets_current와 other_assets_current가 NULL인 레코드를 대상으로
로컬 DART 파일에서 데이터를 추출하여 업데이트합니다.

사용법:
    python scripts/parse_missing_other_assets.py --sample 10  # 10개 회사만 테스트
    python scripts/parse_missing_other_assets.py              # 전체 실행
    python scripts/parse_missing_other_assets.py --export-missing  # 파일 없는 기업 목록 추출
"""
import asyncio
import asyncpg
import argparse
import json
import logging
import os
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway'
)
DART_DATA_DIR = Path(__file__).parent.parent / 'data' / 'dart'

# 기타금융자산/기타자산 파싱용 매핑 (확장)
ACCOUNT_MAPPING = {
    'other_financial_assets_current': [
        '기타금융자산', '기타유동금융자산', '기타 금융자산',
        '기타유동금융자산(유동)', '금융자산(유동)',
        '기타포괄손익공정가치측정금융자산', '상각후원가측정금융자산',
        '기타의금융자산', '기타금융자산(유동)', '유동기타금융자산',
        '기타의 금융자산', '단기기타금융자산', '기타 유동금융자산',
        '파생상품자산', '매매목적파생상품자산'
    ],
    'other_assets_current': [
        '기타자산', '기타유동자산', '기타 유동자산',
        '선급금', '선급비용', '기타자산(유동)',
        '기타의자산', '기타 자산', '유동기타자산',
        '선급금및선급비용', '선급금 및 선급비용', '선급금등',
        '기타의 자산', '단기기타자산', '선납세금',
        '계약자산', '기타의유동자산'
    ],
}


class MissingDataParser:
    """부족 데이터 전용 파서"""

    def __init__(self, data_dir: Path = DART_DATA_DIR):
        self.data_dir = data_dir
        self.stats = {
            'total_checked': 0,
            'files_found': 0,
            'parsed': 0,
            'updated': 0,
            'no_file': 0,
            'errors': 0
        }

    def find_reports_for_company(self, corp_code: str, target_years: List[int] = None) -> Dict[int, Dict]:
        """특정 회사의 연도별 보고서 찾기"""
        reports = {}

        for batch_dir in self.data_dir.iterdir():
            if not batch_dir.is_dir() or batch_dir.name.startswith('.'):
                continue

            corp_dir = batch_dir / corp_code
            if not corp_dir.exists():
                continue

            for year_dir in corp_dir.iterdir():
                if not year_dir.is_dir():
                    continue

                try:
                    year = int(year_dir.name)
                except ValueError:
                    continue

                if target_years and year not in target_years:
                    continue

                for meta_file in year_dir.glob('*_meta.json'):
                    try:
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            meta = json.load(f)

                        # 사업보고서 우선
                        report_nm = meta.get('report_nm', '')
                        zip_file = meta_file.with_name(
                            meta_file.name.replace('_meta.json', '.zip')
                        )

                        if not zip_file.exists():
                            continue

                        # 사업보고서를 우선시하고, 없으면 반기/분기 보고서 사용
                        if '사업보고서' in report_nm:
                            reports[year] = {
                                'meta': meta,
                                'zip_path': zip_file,
                                'priority': 1
                            }
                        elif year not in reports or reports[year].get('priority', 99) > 2:
                            if '반기' in report_nm:
                                reports[year] = {
                                    'meta': meta,
                                    'zip_path': zip_file,
                                    'priority': 2
                                }
                            elif '분기' in report_nm:
                                reports[year] = {
                                    'meta': meta,
                                    'zip_path': zip_file,
                                    'priority': 3
                                }
                    except Exception as e:
                        logger.debug(f"Meta read error: {meta_file}: {e}")

        return reports

    def extract_xml_content(self, zip_path: Path) -> Optional[str]:
        """ZIP에서 XML 추출"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.xml'):
                        raw_bytes = zf.read(name)
                        for encoding in ['utf-8', 'euc-kr', 'cp949']:
                            try:
                                content = raw_bytes.decode(encoding)
                                if '재무' in content or '자산' in content:
                                    return content
                            except UnicodeDecodeError:
                                continue
                        return raw_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            logger.error(f"ZIP extraction error: {zip_path}: {e}")
        return None

    def _detect_unit(self, xml_content: str) -> int:
        """단위 감지"""
        # 백만원 먼저 체크
        if re.search(r'단위\s*[:\s:]\s*백만\s*원', xml_content):
            return 1_000_000
        elif re.search(r'단위\s*[:\s:]\s*천\s*원', xml_content):
            return 1_000
        elif re.search(r'단위\s*[:\s:]\s*원[^천백]', xml_content) or \
             re.search(r'단위\s*[:\s:]\s*원\)', xml_content):
            return 1
        return 1_000  # 기본값

    def _parse_amount(self, amount_str: str, multiplier: int = 1) -> Optional[int]:
        """금액 파싱"""
        if not amount_str:
            return None

        try:
            cleaned = amount_str.replace(',', '').replace(' ', '').strip()

            is_negative = False
            if cleaned.startswith('(') and cleaned.endswith(')'):
                is_negative = True
                cleaned = cleaned[1:-1]
            elif cleaned.startswith('-'):
                is_negative = True
                cleaned = cleaned[1:]

            cleaned = re.sub(r'[^\d\.]', '', cleaned)
            if not cleaned:
                return None

            if '.' in cleaned:
                value = int(float(cleaned))
            else:
                value = int(cleaned)

            value = value * multiplier

            # int64 범위 체크 (PostgreSQL BigInteger 한계)
            MAX_INT64 = 9223372036854775807
            if abs(value) > MAX_INT64:
                logger.warning(f"Value out of int64 range: {value}, skipping")
                return None

            return -value if is_negative else value
        except (ValueError, TypeError):
            return None

    def parse_other_assets(self, xml_content: str) -> Dict[str, int]:
        """기타금융자산/기타자산만 파싱"""
        values = {}

        unit_multiplier = self._detect_unit(xml_content)

        # 태그 제거한 텍스트
        clean_text = re.sub(r'<[^>]+>', ' ', xml_content)
        clean_text = re.sub(r'\s+', ' ', clean_text)

        for field, aliases in ACCOUNT_MAPPING.items():
            for alias in aliases:
                alias_pattern = r'\s*'.join(re.escape(c) for c in alias)
                pattern = rf'{alias_pattern}[^\d\-]*?([\-\(]?\d[\d,\.]*[\)]?)'

                matches = re.findall(pattern, clean_text, re.IGNORECASE)
                if matches:
                    amount = self._parse_amount(matches[0], unit_multiplier)
                    if amount is not None:
                        values[field] = amount
                        break

        return values


class MissingDataUpdater:
    """부족 데이터 업데이트 관리"""

    def __init__(self, db_url: str):
        self.db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        self.parser = MissingDataParser()
        self.missing_companies = []  # 파일 없는 기업 목록

    async def get_missing_records(self, conn, limit: Optional[int] = None) -> List[Dict]:
        """부족 데이터 레코드 조회"""
        query = """
            SELECT
                fd.id,
                fd.company_id,
                fd.fiscal_year,
                fd.fiscal_quarter,
                fd.other_financial_assets_current,
                fd.other_assets_current,
                c.corp_code,
                c.name
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE c.corp_code IS NOT NULL
              AND (fd.other_financial_assets_current IS NULL
                   OR fd.other_assets_current IS NULL)
            ORDER BY c.name, fd.fiscal_year
        """
        if limit:
            query += f" LIMIT {limit}"

        rows = await conn.fetch(query)
        return [dict(row) for row in rows]

    async def update_record(self, conn, record_id: str, data: Dict) -> bool:
        """레코드 업데이트"""
        try:
            updates = []
            params = [uuid.UUID(record_id)]
            param_idx = 2

            if 'other_financial_assets_current' in data:
                updates.append(f"other_financial_assets_current = ${param_idx}")
                params.append(data['other_financial_assets_current'])
                param_idx += 1

            if 'other_assets_current' in data:
                updates.append(f"other_assets_current = ${param_idx}")
                params.append(data['other_assets_current'])
                param_idx += 1

            if not updates:
                return False

            updates.append("updated_at = NOW()")

            query = f"""
                UPDATE financial_details
                SET {', '.join(updates)}
                WHERE id = $1
            """

            await conn.execute(query, *params)
            return True
        except Exception as e:
            logger.error(f"Update error: {e}")
            return False

    async def run(self, limit: Optional[int] = None):
        """부족 데이터 파싱 실행"""
        conn = await asyncpg.connect(self.db_url)

        try:
            records = await self.get_missing_records(conn, limit)

            logger.info("=" * 80)
            logger.info("기타금융자산/기타자산 부족 데이터 파싱 시작")
            logger.info("=" * 80)
            logger.info(f"대상 레코드: {len(records)}건")
            logger.info("=" * 80)

            # 기업별로 그룹핑
            by_company = defaultdict(list)
            for record in records:
                by_company[record['corp_code']].append(record)

            logger.info(f"대상 기업: {len(by_company)}개")

            processed_companies = set()

            for i, (corp_code, company_records) in enumerate(by_company.items(), 1):
                company_name = company_records[0]['name']
                target_years = list(set(r['fiscal_year'] for r in company_records))

                self.parser.stats['total_checked'] += 1

                # 해당 기업의 보고서 찾기
                reports = self.parser.find_reports_for_company(corp_code, target_years)

                if not reports:
                    self.parser.stats['no_file'] += 1
                    self.missing_companies.append({
                        'corp_code': corp_code,
                        'name': company_name,
                        'missing_years': target_years
                    })
                    continue

                self.parser.stats['files_found'] += 1

                # 연도별 파싱 및 업데이트
                for record in company_records:
                    year = record['fiscal_year']

                    if year not in reports:
                        continue

                    report = reports[year]
                    xml_content = self.parser.extract_xml_content(report['zip_path'])

                    if not xml_content:
                        continue

                    self.parser.stats['parsed'] += 1

                    # 파싱
                    parsed_data = self.parser.parse_other_assets(xml_content)

                    if parsed_data:
                        # 기존 NULL인 필드만 업데이트
                        update_data = {}
                        if record['other_financial_assets_current'] is None and \
                           'other_financial_assets_current' in parsed_data:
                            update_data['other_financial_assets_current'] = \
                                parsed_data['other_financial_assets_current']

                        if record['other_assets_current'] is None and \
                           'other_assets_current' in parsed_data:
                            update_data['other_assets_current'] = \
                                parsed_data['other_assets_current']

                        if update_data:
                            success = await self.update_record(conn, str(record['id']), update_data)
                            if success:
                                self.parser.stats['updated'] += 1

                # 진행 상황
                if i % 100 == 0:
                    logger.info(
                        f"Progress: {i}/{len(by_company)} - "
                        f"Files: {self.parser.stats['files_found']}, "
                        f"Updated: {self.parser.stats['updated']}, "
                        f"NoFile: {self.parser.stats['no_file']}"
                    )

            # 결과
            logger.info("=" * 80)
            logger.info("파싱 완료")
            logger.info("=" * 80)
            logger.info(f"확인 기업: {self.parser.stats['total_checked']}")
            logger.info(f"파일 발견: {self.parser.stats['files_found']}")
            logger.info(f"파싱 완료: {self.parser.stats['parsed']}")
            logger.info(f"업데이트: {self.parser.stats['updated']}건")
            logger.info(f"파일 없음: {self.parser.stats['no_file']}개 기업")
            logger.info("=" * 80)

        finally:
            await conn.close()

    async def export_missing_companies(self):
        """파일 없는 기업 목록 추출"""
        conn = await asyncpg.connect(self.db_url)

        try:
            # 데이터 부족 기업 조회
            records = await self.get_missing_records(conn)

            # 기업별로 그룹핑
            by_company = defaultdict(list)
            for record in records:
                by_company[record['corp_code']].append(record)

            logger.info(f"총 {len(by_company)}개 기업 확인 중...")

            missing = []
            with_file = []

            for corp_code, company_records in by_company.items():
                company_name = company_records[0]['name']
                target_years = list(set(r['fiscal_year'] for r in company_records))

                reports = self.parser.find_reports_for_company(corp_code, target_years)

                if not reports:
                    missing.append({
                        'corp_code': corp_code,
                        'name': company_name,
                        'missing_years': sorted(target_years)
                    })
                else:
                    found_years = list(reports.keys())
                    missing_years = [y for y in target_years if y not in reports]
                    with_file.append({
                        'corp_code': corp_code,
                        'name': company_name,
                        'found_years': sorted(found_years),
                        'missing_years': sorted(missing_years)
                    })

            # 결과 저장
            output_dir = Path(__file__).parent / 'output'
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 파일 없는 기업 목록
            missing_file = output_dir / f'missing_companies_{timestamp}.json'
            with open(missing_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'total': len(missing),
                    'companies': missing
                }, f, ensure_ascii=False, indent=2)

            # 파일 있는 기업 목록 (부분 누락 포함)
            with_file_output = output_dir / f'companies_with_files_{timestamp}.json'
            with open(with_file_output, 'w', encoding='utf-8') as f:
                json.dump({
                    'total': len(with_file),
                    'companies': with_file
                }, f, ensure_ascii=False, indent=2)

            logger.info("=" * 80)
            logger.info("파일 현황 분석 완료")
            logger.info("=" * 80)
            logger.info(f"파일 없는 기업: {len(missing)}개")
            logger.info(f"파일 있는 기업: {len(with_file)}개")
            logger.info(f"결과 파일: {missing_file}")
            logger.info(f"결과 파일: {with_file_output}")
            logger.info("=" * 80)

        finally:
            await conn.close()


async def verify_results():
    """결과 검증"""
    db_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    try:
        result = await conn.fetch("""
            SELECT
                fiscal_year,
                COUNT(*) as total,
                SUM(CASE WHEN other_financial_assets_current IS NOT NULL THEN 1 ELSE 0 END) as has_other_fin,
                SUM(CASE WHEN other_assets_current IS NOT NULL THEN 1 ELSE 0 END) as has_other_assets
            FROM financial_details
            GROUP BY fiscal_year
            ORDER BY fiscal_year
        """)

        logger.info("\n[데이터 현황]")
        for row in result:
            logger.info(
                f"  {row['fiscal_year']}년: 총 {row['total']}건 "
                f"(기타금융자산: {row['has_other_fin']}, 기타자산: {row['has_other_assets']})"
            )

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='기타금융자산/기타자산 부족 데이터 파싱')
    parser.add_argument('--sample', type=int, help='샘플 레코드 수')
    parser.add_argument('--export-missing', action='store_true', help='파일 없는 기업 목록 추출')
    parser.add_argument('--verify-only', action='store_true', help='결과 검증만')

    args = parser.parse_args()

    if args.verify_only:
        asyncio.run(verify_results())
        return

    if args.export_missing:
        updater = MissingDataUpdater(DATABASE_URL)
        asyncio.run(updater.export_missing_companies())
        return

    updater = MissingDataUpdater(DATABASE_URL)
    asyncio.run(updater.run(limit=args.sample))
    asyncio.run(verify_results())


if __name__ == "__main__":
    main()
