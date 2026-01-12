#!/usr/bin/env python3
"""
426개 대상 기업 재무제표 파싱
"""
import asyncio
import asyncpg
import json
import re
import zipfile
import logging
import os
import sys
from pathlib import Path
from datetime import date
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
sys.stdout.reconfigure(line_buffering=True)

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')
BASE_DATA_DIR = Path('/Users/jaejoonpark/raymontology/backend/data/dart')
CORP_MAP_FILE = Path(__file__).parent / 'corp_dir_map.json'
TARGET_CORPS_FILE = Path(__file__).parent / 'target_corps_426.txt'


def parse_number(text: str) -> int:
    """숫자 문자열 파싱"""
    if not text:
        return None
    text = text.strip().replace(',', '').replace(' ', '')
    is_negative = text.startswith('(') and text.endswith(')')
    if is_negative:
        text = text[1:-1]
    text = re.sub(r'[^\d.-]', '', text)
    if not text or text == '-':
        return None
    try:
        value = int(float(text))
        return -value if is_negative else value
    except:
        return None


def extract_financial_data(xml_content: str) -> dict:
    """XML에서 재무제표 데이터 추출"""
    data = {}

    patterns = {
        'total_assets': r'자산\s*총계</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'total_liabilities': r'부채\s*총계</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'total_equity': r'자본\s*총계</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'revenue': r'(?:매출액|수익\(매출액\))</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'operating_profit': r'영업이익(?:\(손실\))?</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
        'net_income': r'(?:당기순이익(?:\(손실\))?|당기순손익)</P>\s*</TE>\s*<TE[^>]*>\s*<P[^>]*>([^<]+)</P>',
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, xml_content, re.IGNORECASE | re.DOTALL)
        if match:
            value = parse_number(match.group(1))
            if value is not None:
                data[field] = value

    return data


def extract_xml_from_zip(zip_path: Path) -> str:
    """ZIP에서 메인 XML 추출"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
            if not xml_files:
                return None

            main_xml = max(xml_files, key=lambda x: zf.getinfo(x).file_size)

            try:
                return zf.read(main_xml).decode('utf-8')
            except:
                return zf.read(main_xml).decode('euc-kr', errors='ignore')
    except:
        return None


async def main():
    conn = await asyncpg.connect(DB_URL, timeout=60, command_timeout=300)

    try:
        # 회사 정보 로드
        rows = await conn.fetch("SELECT id, corp_code, name FROM companies WHERE corp_code IS NOT NULL")
        company_cache = {r['corp_code']: {'id': str(r['id']), 'name': r['name']} for r in rows}
        logger.info(f"회사 캐시 로드: {len(company_cache)}개")

        # 기존 재무제표 로드 (중복 방지)
        existing = set()
        fin_rows = await conn.fetch("SELECT company_id, fiscal_year, quarter FROM financial_statements")
        for r in fin_rows:
            key = f"{r['company_id']}_{r['fiscal_year']}_{r['quarter'] or ''}"
            existing.add(key)
        logger.info(f"기존 재무제표 로드: {len(existing)}개")

        # 대상 기업 목록 로드
        target_corps = []
        with open(TARGET_CORPS_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if parts:
                    target_corps.append((parts[0], parts[1] if len(parts) > 1 else ''))
        logger.info(f"대상 기업: {len(target_corps)}개")

        # 기업 폴더 맵 로드
        with open(CORP_MAP_FILE, 'r') as f:
            corp_map = json.load(f)
        logger.info(f"폴더 맵 로드: {len(corp_map)}개")

        stats = {'parsed': 0, 'inserted': 0, 'companies': 0, 'skipped': 0}
        financials_to_insert = []

        for i, (corp_code, corp_name) in enumerate(target_corps):
            corp_dirs = corp_map.get(corp_code, [])
            if not corp_dirs:
                continue

            company_info = company_cache.get(corp_code)
            if not company_info:
                continue

            company_id = company_info['id']

            for corp_dir_str in corp_dirs:
                corp_dir = Path(corp_dir_str)
                if not corp_dir.exists():
                    continue

                # 연도별 폴더 순회 (2022, 2023, 2024)
                for year_dir in corp_dir.iterdir():
                    if not year_dir.is_dir() or year_dir.name not in {'2022', '2023', '2024'}:
                        continue

                    # meta 파일 찾기
                    for meta_file in year_dir.glob("*_meta.json"):
                        try:
                            with open(meta_file, 'r', encoding='utf-8') as f:
                                meta = json.load(f)

                            report_nm = meta.get('report_nm', '')
                            rcept_no = meta.get('rcept_no')

                            # 사업보고서만 처리
                            if '사업보고서' not in report_nm:
                                continue

                            # 연도 추출
                            year_match = re.search(r'\((\d{4})\.(\d{2})\)', report_nm)
                            if not year_match:
                                continue

                            fiscal_year = int(year_match.group(1))
                            fiscal_month = int(year_match.group(2))

                            if fiscal_month != 12:
                                continue

                            # 중복 체크
                            key = f"{company_id}_{fiscal_year}_"
                            if key in existing:
                                stats['skipped'] += 1
                                continue

                            # ZIP 파일 열기
                            zip_path = year_dir / f"{rcept_no}.zip"
                            if not zip_path.exists():
                                continue

                            xml_content = extract_xml_from_zip(zip_path)
                            if not xml_content:
                                continue

                            fin_data = extract_financial_data(xml_content)
                            if not fin_data:
                                continue

                            stats['parsed'] += 1
                            existing.add(key)

                            stmt_date = date(fiscal_year, 12, 31)

                            financials_to_insert.append((
                                str(uuid.uuid4()),
                                company_id,
                                fiscal_year,
                                None,  # quarter
                                stmt_date,
                                '사업보고서',
                                fin_data.get('total_assets'),
                                fin_data.get('total_liabilities'),
                                fin_data.get('total_equity'),
                                fin_data.get('revenue'),
                                fin_data.get('operating_profit'),
                                fin_data.get('net_income'),
                                rcept_no
                            ))

                        except Exception as e:
                            pass

            stats['companies'] += 1

            if (i + 1) % 50 == 0:
                logger.info(f"진행: {i+1}/{len(target_corps)} 기업, 파싱: {stats['parsed']}건")

        logger.info(f"\n파싱 완료: {stats['parsed']}건, 기업: {stats['companies']}개")

        # 배치 삽입
        if financials_to_insert:
            logger.info(f"재무제표 {len(financials_to_insert)}개 삽입 시작...")

            batch_size = 100
            total_batches = (len(financials_to_insert) + batch_size - 1) // batch_size

            for i in range(total_batches):
                start = i * batch_size
                end = min(start + batch_size, len(financials_to_insert))
                batch = financials_to_insert[start:end]

                try:
                    await conn.executemany("""
                        INSERT INTO financial_statements
                        (id, company_id, fiscal_year, quarter, statement_date, report_type,
                         total_assets, total_liabilities, total_equity, revenue,
                         operating_profit, net_income, source_rcept_no)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        ON CONFLICT (company_id, fiscal_year, quarter)
                        DO UPDATE SET
                            total_assets = EXCLUDED.total_assets,
                            total_liabilities = EXCLUDED.total_liabilities,
                            total_equity = EXCLUDED.total_equity,
                            revenue = EXCLUDED.revenue,
                            operating_profit = EXCLUDED.operating_profit,
                            net_income = EXCLUDED.net_income
                    """, batch)
                    stats['inserted'] += len(batch)
                except Exception as e:
                    logger.warning(f"배치 {i+1} 실패: {e}")
                    for fin in batch:
                        try:
                            await conn.execute("""
                                INSERT INTO financial_statements
                                (id, company_id, fiscal_year, quarter, statement_date, report_type,
                                 total_assets, total_liabilities, total_equity, revenue,
                                 operating_profit, net_income, source_rcept_no)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                                ON CONFLICT (company_id, fiscal_year, quarter)
                                DO UPDATE SET
                                    total_assets = EXCLUDED.total_assets,
                                    total_liabilities = EXCLUDED.total_liabilities,
                                    total_equity = EXCLUDED.total_equity,
                                    revenue = EXCLUDED.revenue,
                                    operating_profit = EXCLUDED.operating_profit,
                                    net_income = EXCLUDED.net_income
                            """, *fin)
                            stats['inserted'] += 1
                        except:
                            pass

                if (i + 1) % 5 == 0 or (i + 1) == total_batches:
                    logger.info(f"삽입 진행: {i+1}/{total_batches} ({stats['inserted']}/{len(financials_to_insert)})")

        # 최종 통계
        logger.info("\n" + "=" * 80)
        logger.info("재무제표 파싱 완료")
        logger.info("=" * 80)
        logger.info(f"파싱된 재무제표: {stats['parsed']}개")
        logger.info(f"삽입된 재무제표: {stats['inserted']}개")
        logger.info(f"스킵 (중복): {stats['skipped']}개")

        total_fin = await conn.fetchval("SELECT COUNT(*) FROM financial_statements")
        logger.info(f"\n현재 DB 재무제표: {total_fin:,}개")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
