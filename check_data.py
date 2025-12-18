#!/usr/bin/env python3
"""
데이터 완전성 검사 스크립트
2022-01-01 ~ 2025-Q2 기간 데이터 확인
"""

import asyncio
import asyncpg
import os
from datetime import datetime
import json

# DATABASE_URL 설정
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password@localhost:5432/raymontology_dev')

async def check_all_data():
    """전체 데이터 완전성 검사"""

    # PostgreSQL 연결
    conn = await asyncpg.connect(DATABASE_URL)

    results = {}

    try:
        print("="*80)
        print("RAYMONTOLOGY 데이터 완전성 검사")
        print("대상 기간: 2022-01-01 ~ 2025-06-30 (2Q)")
        print("="*80)

        # 1. Companies (회사)
        print("\n[1] COMPANIES (회사) 데이터 확인")
        print("-"*80)

        query = """
        SELECT
            COUNT(*) as total_companies,
            COUNT(DISTINCT ticker) as unique_tickers,
            COUNT(DISTINCT corp_code) as unique_corp_codes,
            COUNT(CASE WHEN market = 'KOSPI' THEN 1 END) as kospi_count,
            COUNT(CASE WHEN market = 'KOSDAQ' THEN 1 END) as kosdaq_count,
            COUNT(CASE WHEN market = 'KONEX' THEN 1 END) as konex_count,
            COUNT(CASE WHEN ticker IS NULL THEN 1 END) as missing_ticker,
            COUNT(CASE WHEN corp_code IS NULL THEN 1 END) as missing_corp_code,
            COUNT(CASE WHEN sector IS NULL THEN 1 END) as missing_sector,
            COUNT(CASE WHEN market_cap IS NULL THEN 1 END) as missing_market_cap,
            COUNT(CASE WHEN revenue IS NULL THEN 1 END) as missing_revenue
        FROM companies
        WHERE market IN ('KOSPI', 'KOSDAQ', 'KONEX') OR market IS NULL
        """

        row = await conn.fetchrow(query)
        results['companies'] = dict(row)

        for key, value in row.items():
            print(f"  {key}: {value}")

        # 2. Officers (임원)
        print("\n[2] OFFICERS (임원) 데이터 확인")
        print("-"*80)

        query = """
        SELECT
            COUNT(*) as total_officers,
            COUNT(DISTINCT name) as unique_names,
            COUNT(DISTINCT current_company_id) as companies_with_officers,
            COUNT(CASE WHEN position IS NULL THEN 1 END) as missing_position,
            COUNT(CASE WHEN current_company_id IS NULL THEN 1 END) as missing_company,
            COUNT(CASE WHEN career_history IS NULL OR career_history::text = '[]' OR career_history::text = '{}' THEN 1 END) as missing_career,
            COUNT(CASE WHEN influence_score IS NULL THEN 1 END) as missing_influence_score
        FROM officers
        """

        row = await conn.fetchrow(query)
        results['officers'] = dict(row)

        for key, value in row.items():
            print(f"  {key}: {value}")

        # 3. Convertible Bonds (전환사채)
        print("\n[3] CONVERTIBLE BONDS (전환사채) 데이터 확인")
        print("-"*80)

        query = """
        SELECT
            COUNT(*) as total_cbs,
            COUNT(DISTINCT company_id) as companies_with_cbs,
            COUNT(CASE WHEN issue_date >= '2022-01-01' AND issue_date < '2023-01-01' THEN 1 END) as issued_2022,
            COUNT(CASE WHEN issue_date >= '2023-01-01' AND issue_date < '2024-01-01' THEN 1 END) as issued_2023,
            COUNT(CASE WHEN issue_date >= '2024-01-01' AND issue_date < '2025-01-01' THEN 1 END) as issued_2024,
            COUNT(CASE WHEN issue_date >= '2025-01-01' AND issue_date < '2025-07-01' THEN 1 END) as issued_2025_h1,
            COUNT(CASE WHEN issue_amount IS NULL THEN 1 END) as missing_issue_amount,
            COUNT(CASE WHEN conversion_price IS NULL THEN 1 END) as missing_conversion_price,
            SUM(issue_amount)::BIGINT as total_issue_amount
        FROM convertible_bonds
        """

        row = await conn.fetchrow(query)
        results['convertible_bonds'] = dict(row)

        for key, value in row.items():
            if key == 'total_issue_amount' and value:
                print(f"  {key}: {value:,}원")
            else:
                print(f"  {key}: {value}")

        # 4. CB Subscribers (인수자)
        print("\n[4] CB SUBSCRIBERS (인수자) 데이터 확인")
        print("-"*80)

        query = """
        SELECT
            COUNT(*) as total_subscribers,
            COUNT(DISTINCT cb_id) as cbs_with_subscribers,
            COUNT(DISTINCT subscriber_name) as unique_subscribers,
            COUNT(CASE WHEN is_related_party = true THEN 1 END) as related_party_count,
            COUNT(CASE WHEN subscription_amount IS NULL THEN 1 END) as missing_amount,
            SUM(subscription_amount)::BIGINT as total_subscription_amount
        FROM cb_subscribers
        """

        row = await conn.fetchrow(query)
        results['cb_subscribers'] = dict(row)

        for key, value in row.items():
            if key == 'total_subscription_amount' and value:
                print(f"  {key}: {value:,}원")
            else:
                print(f"  {key}: {value}")

        # 5. Affiliates (계열사)
        print("\n[5] AFFILIATES (계열사) 데이터 확인")
        print("-"*80)

        query = """
        SELECT
            COUNT(*) as total_affiliates,
            COUNT(DISTINCT parent_company_id) as parent_companies,
            COUNT(DISTINCT affiliate_company_id) as affiliate_companies,
            COUNT(CASE WHEN source_date >= '2022-01-01' AND source_date < '2025-07-01' THEN 1 END) as records_in_period,
            COUNT(CASE WHEN ownership_ratio IS NULL THEN 1 END) as missing_ownership_ratio
        FROM affiliates
        """

        row = await conn.fetchrow(query)
        results['affiliates'] = dict(row)

        for key, value in row.items():
            print(f"  {key}: {value}")

        # 6. Financial Statements (재무제표)
        print("\n[6] FINANCIAL STATEMENTS (재무제표) 데이터 확인")
        print("-"*80)

        query = """
        SELECT
            COUNT(*) as total_statements,
            COUNT(DISTINCT company_id) as companies_with_statements,
            COUNT(CASE WHEN fiscal_year = 2022 THEN 1 END) as fy_2022,
            COUNT(CASE WHEN fiscal_year = 2023 THEN 1 END) as fy_2023,
            COUNT(CASE WHEN fiscal_year = 2024 THEN 1 END) as fy_2024,
            COUNT(CASE WHEN fiscal_year = 2025 THEN 1 END) as fy_2025,
            COUNT(CASE WHEN quarter = 'Q1' THEN 1 END) as q1_statements,
            COUNT(CASE WHEN quarter = 'Q2' THEN 1 END) as q2_statements,
            COUNT(CASE WHEN revenue IS NULL THEN 1 END) as missing_revenue,
            COUNT(CASE WHEN net_income IS NULL THEN 1 END) as missing_net_income
        FROM financial_statements
        WHERE fiscal_year BETWEEN 2022 AND 2025
        """

        row = await conn.fetchrow(query)
        results['financial_statements'] = dict(row)

        for key, value in row.items():
            print(f"  {key}: {value}")

        # 7. Risk Signals (리스크 신호)
        print("\n[7] RISK SIGNALS (리스크 신호) 데이터 확인")
        print("-"*80)

        query = """
        SELECT
            COUNT(*) as total_signals,
            COUNT(DISTINCT target_company_id) as companies_with_signals,
            COUNT(CASE WHEN severity = 'LOW' THEN 1 END) as low_severity,
            COUNT(CASE WHEN severity = 'MEDIUM' THEN 1 END) as medium_severity,
            COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_severity,
            COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical_severity,
            COUNT(CASE WHEN detected_at >= '2022-01-01' AND detected_at < '2025-07-01' THEN 1 END) as signals_in_period
        FROM risk_signals
        """

        row = await conn.fetchrow(query)
        results['risk_signals'] = dict(row)

        for key, value in row.items():
            print(f"  {key}: {value}")

        # 8. Disclosures (공시)
        print("\n[8] DISCLOSURES (공시) 데이터 확인")
        print("-"*80)

        query = """
        SELECT
            COUNT(*) as total_disclosures,
            COUNT(DISTINCT corp_code) as companies_with_disclosures,
            COUNT(CASE WHEN rcept_dt >= '20220101' AND rcept_dt < '20230101' THEN 1 END) as disclosures_2022,
            COUNT(CASE WHEN rcept_dt >= '20230101' AND rcept_dt < '20240101' THEN 1 END) as disclosures_2023,
            COUNT(CASE WHEN rcept_dt >= '20240101' AND rcept_dt < '20250101' THEN 1 END) as disclosures_2024,
            COUNT(CASE WHEN rcept_dt >= '20250101' AND rcept_dt < '20250701' THEN 1 END) as disclosures_2025_h1
        FROM disclosures
        WHERE rcept_dt >= '20220101' AND rcept_dt < '20250701'
        """

        row = await conn.fetchrow(query)
        results['disclosures'] = dict(row)

        for key, value in row.items():
            print(f"  {key}: {value}")

        # 종합 분석
        print("\n" + "="*80)
        print("종합 분석")
        print("="*80)

        total_companies = results['companies']['total_companies']
        companies_with_officers = results['officers']['companies_with_officers']
        companies_with_statements = results['financial_statements']['companies_with_statements']
        companies_with_cbs = results['convertible_bonds']['companies_with_cbs']

        print(f"\n전체 상장 회사: {total_companies}개")
        print(f"  - 임원 데이터 보유: {companies_with_officers}개 ({companies_with_officers/total_companies*100:.1f}%)")
        print(f"  - 재무제표 보유: {companies_with_statements}개 ({companies_with_statements/total_companies*100:.1f}%)")
        print(f"  - CB 발행 회사: {companies_with_cbs}개 ({companies_with_cbs/total_companies*100:.1f}%)")

        print(f"\n데이터 기간 분석 (2022-2025 Q2):")
        print(f"  - 2022년 CB 발행: {results['convertible_bonds']['issued_2022']}건")
        print(f"  - 2023년 CB 발행: {results['convertible_bonds']['issued_2023']}건")
        print(f"  - 2024년 CB 발행: {results['convertible_bonds']['issued_2024']}건")
        print(f"  - 2025년 상반기 CB 발행: {results['convertible_bonds']['issued_2025_h1']}건")

        print(f"\n재무제표 연도별:")
        print(f"  - 2022년: {results['financial_statements']['fy_2022']}건")
        print(f"  - 2023년: {results['financial_statements']['fy_2023']}건")
        print(f"  - 2024년: {results['financial_statements']['fy_2024']}건")
        print(f"  - 2025년: {results['financial_statements']['fy_2025']}건")

    finally:
        await conn.close()

    return results

# 실행
if __name__ == "__main__":
    results = asyncio.run(check_all_data())

    # JSON 파일로 저장
    output_file = '/Users/jaejoonpark/raymontology/data_completeness_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n결과가 {output_file}에 저장되었습니다.")
