#!/usr/bin/env python3
"""
financial_details 재파싱 스크립트 (v2.0 파서 적용)

문제:
- 기존 파서가 재무상태표 섹션만 추출하여 손익계산서/현금흐름표 데이터 누락
- 요약재무정보(백만원)와 본문 재무제표(원) 단위 혼동

해결:
- v2.0 파서: 각 재무제표 섹션별 독립 파싱 및 단위 감지

사용법:
    python scripts/reparse_financial_details_v2.py --sample 10  # 테스트
    python scripts/reparse_financial_details_v2.py --year 2024  # 2024년만
    python scripts/reparse_financial_details_v2.py              # 전체
"""
import asyncio
import asyncpg
import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.parse_local_financial_details import LocalDARTFinancialParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR@hopper.proxy.rlwy.net:41316/railway'
)


async def get_companies_to_reparse(conn, year: int = None, sample: int = None,
                                    suspicious_only: bool = False):
    """재파싱이 필요한 회사 목록 조회

    Args:
        suspicious_only: True면 revenue < 10000인 의심스러운 레코드만 (LOCAL_DART, LOCAL_DART_V2 포함)
    """
    if suspicious_only:
        # 의심스러운 매출액 레코드 재파싱 (모든 LOCAL 소스)
        query = """
            SELECT c.id, c.corp_code, c.name, fd.fiscal_year,
                   0 as priority
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE fd.data_source IN ('LOCAL_DART', 'LOCAL_DART_V2')
              AND fd.report_type = 'annual'
              AND fd.revenue IS NOT NULL
              AND fd.revenue > 0
              AND fd.revenue < 10000
        """
    else:
        # 기존: LOCAL_DART 소스만
        query = """
            SELECT c.id, c.corp_code, c.name, fd.fiscal_year,
                   CASE WHEN fd.revenue IS NULL OR fd.revenue < 100000 THEN 0 ELSE 1 END as priority
            FROM financial_details fd
            JOIN companies c ON fd.company_id = c.id
            WHERE fd.data_source = 'LOCAL_DART'
              AND fd.report_type = 'annual'
        """
    params = []

    if year:
        query += " AND fd.fiscal_year = $1"
        params.append(year)

    # revenue가 의심스러운 데이터 우선
    query += """
        ORDER BY priority, fd.fiscal_year DESC
    """

    if sample:
        query += f" LIMIT {sample}"

    return await conn.fetch(query, *params)


async def reparse_company(parser: LocalDARTFinancialParser, conn, company_id: str,
                          corp_code: str, name: str, year: int) -> bool:
    """단일 회사 재파싱"""
    # 해당 회사의 사업보고서 찾기
    reports = parser.find_business_reports(corp_code)

    if not reports:
        logger.debug(f"No reports found for {name} ({corp_code})")
        return False

    # 해당 연도 보고서 찾기
    target_report = None
    for r in reports:
        # 보고서의 연도 확인 (report_nm에서 추출 또는 year_dir)
        year_dir = r.get('year_dir', '')
        if str(year) in year_dir or str(year + 1) in year_dir:  # 2024년 데이터는 2025년에 제출
            target_report = r
            break

    if not target_report:
        logger.debug(f"No {year} report found for {name}")
        return False

    # XML 추출 (v2.0: 사업보고서 우선)
    xml_content = parser.extract_xml_content(target_report['zip_path'])
    if not xml_content:
        logger.warning(f"Failed to extract XML for {name}")
        return False

    # v2.0 파싱
    parsed_data = parser._extract_values_from_all_statements(xml_content, 'CFS')
    if not parsed_data:
        # CFS 실패시 OFS 시도
        parsed_data = parser._extract_values_from_all_statements(xml_content, 'OFS')

    if not parsed_data:
        logger.warning(f"Failed to parse {name}")
        return False

    # 핵심 필드 검증
    revenue = parsed_data.get('revenue')
    total_assets = parsed_data.get('total_assets')

    if not revenue and not total_assets:
        logger.debug(f"No key fields for {name}")
        return False

    # DB 업데이트
    update_fields = []
    update_values = []

    field_mapping = [
        'revenue', 'operating_income', 'net_income', 'cost_of_sales', 'selling_admin_expenses',
        'total_assets', 'total_equity', 'total_liabilities',
        'current_assets', 'non_current_assets', 'current_liabilities', 'non_current_liabilities',
        'cash_and_equivalents', 'tangible_assets', 'intangible_assets',
        'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow',
        'capex', 'dividend_paid',
    ]

    for field in field_mapping:
        if field in parsed_data and parsed_data[field] is not None:
            update_fields.append(f"{field} = ${len(update_values) + 3}")
            update_values.append(parsed_data[field])

    if not update_fields:
        return False

    # 데이터 소스 업데이트
    update_fields.append(f"data_source = ${len(update_values) + 3}")
    update_values.append('LOCAL_DART_V2')

    update_fields.append(f"updated_at = NOW()")

    query = f"""
        UPDATE financial_details
        SET {', '.join(update_fields)}
        WHERE company_id = $1 AND fiscal_year = $2 AND report_type = 'annual'
    """

    await conn.execute(query, company_id, year, *update_values)

    logger.info(f"✓ {name}: revenue={revenue:,}" if revenue else f"✓ {name}: updated")
    return True


async def main():
    parser_arg = argparse.ArgumentParser()
    parser_arg.add_argument('--year', type=int, help='특정 연도만 재파싱')
    parser_arg.add_argument('--sample', type=int, help='샘플 개수')
    parser_arg.add_argument('--dry-run', action='store_true', help='실제 업데이트 없이 테스트')
    parser_arg.add_argument('--suspicious', action='store_true',
                           help='의심스러운 매출액(< 10000) 레코드만 재파싱')
    args = parser_arg.parse_args()

    parser = LocalDARTFinancialParser()

    # asyncpg URL 변환 (postgresql:// -> postgresql://)
    db_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')

    conn = await asyncpg.connect(db_url)

    try:
        companies = await get_companies_to_reparse(conn, args.year, args.sample,
                                                    suspicious_only=args.suspicious)
        logger.info(f"재파싱 대상: {len(companies)}개 회사")

        success = 0
        failed = 0

        for row in companies:
            company_id = str(row['id'])
            corp_code = row['corp_code']
            name = row['name']
            year = row['fiscal_year']

            if args.dry_run:
                logger.info(f"[DRY-RUN] {name} ({corp_code}) - {year}")
                continue

            try:
                if await reparse_company(parser, conn, company_id, corp_code, name, year):
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Error reparsing {name}: {e}")
                failed += 1

        logger.info(f"\n=== 완료 ===")
        logger.info(f"성공: {success}, 실패: {failed}")

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
