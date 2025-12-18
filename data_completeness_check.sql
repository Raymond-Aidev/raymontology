-- ============================================================================
-- Raymontology 데이터 완전성 검사 SQL
-- 대상 기간: 2022-01-01 ~ 2025-06-30 (2Q)
-- 작성일: 2025-11-21
-- ============================================================================

-- 1. 상장 회사 전체 리스트 확인
-- ============================================================================
SELECT
    '1. Companies (상장회사)' as check_category,
    COUNT(*) as total_count,
    COUNT(DISTINCT ticker) as ticker_count,
    COUNT(DISTINCT corp_code) as corp_code_count,
    COUNT(CASE WHEN market = 'KOSPI' THEN 1 END) as kospi_count,
    COUNT(CASE WHEN market = 'KOSDAQ' THEN 1 END) as kosdaq_count,
    COUNT(CASE WHEN market = 'KONEX' THEN 1 END) as konex_count,
    COUNT(CASE WHEN ticker IS NULL THEN 1 END) as missing_ticker,
    COUNT(CASE WHEN corp_code IS NULL THEN 1 END) as missing_corp_code,
    COUNT(CASE WHEN business_number IS NULL THEN 1 END) as missing_business_number,
    COUNT(CASE WHEN sector IS NULL THEN 1 END) as missing_sector,
    COUNT(CASE WHEN industry IS NULL THEN 1 END) as missing_industry
FROM companies
WHERE market IN ('KOSPI', 'KOSDAQ', 'KONEX');

-- 재무지표 누락 확인
SELECT
    '1-1. Companies - 재무지표' as check_category,
    COUNT(CASE WHEN market_cap IS NULL THEN 1 END) as missing_market_cap,
    COUNT(CASE WHEN revenue IS NULL THEN 1 END) as missing_revenue,
    COUNT(CASE WHEN net_income IS NULL THEN 1 END) as missing_net_income,
    COUNT(CASE WHEN total_assets IS NULL THEN 1 END) as missing_total_assets,
    COUNT(CASE WHEN ownership_concentration IS NULL THEN 1 END) as missing_ownership_concentration,
    COUNT(CASE WHEN cb_issuance_count IS NULL OR cb_issuance_count = 0 THEN 1 END) as no_cb_issuance
FROM companies
WHERE market IN ('KOSPI', 'KOSDAQ', 'KONEX');

-- 2. Officers (임원) 데이터 확인
-- ============================================================================
SELECT
    '2. Officers (임원)' as check_category,
    COUNT(*) as total_officers,
    COUNT(DISTINCT name) as unique_names,
    COUNT(DISTINCT current_company_id) as companies_with_officers,
    COUNT(CASE WHEN position IS NULL THEN 1 END) as missing_position,
    COUNT(CASE WHEN current_company_id IS NULL THEN 1 END) as missing_company,
    COUNT(CASE WHEN career_history IS NULL OR career_history::text = '[]' THEN 1 END) as missing_career_history,
    COUNT(CASE WHEN influence_score IS NULL THEN 1 END) as missing_influence_score,
    COUNT(CASE WHEN board_count IS NULL OR board_count = 0 THEN 1 END) as no_board_positions
FROM officers;

-- 임원-회사 연결 확인
SELECT
    '2-1. Officers - 회사 연결' as check_category,
    COUNT(DISTINCT o.current_company_id) as officer_company_count,
    (SELECT COUNT(*) FROM companies WHERE market IN ('KOSPI', 'KOSDAQ', 'KONEX')) as total_listed_companies,
    ((SELECT COUNT(*) FROM companies WHERE market IN ('KOSPI', 'KOSDAQ', 'KONEX')) -
     COUNT(DISTINCT o.current_company_id)) as companies_without_officers
FROM officers o
WHERE o.current_company_id IS NOT NULL;

-- 3. Convertible Bonds (전환사채) 데이터 확인
-- ============================================================================
SELECT
    '3. Convertible Bonds (전환사채)' as check_category,
    COUNT(*) as total_cbs,
    COUNT(DISTINCT company_id) as companies_with_cbs,
    COUNT(CASE WHEN issue_date >= '2022-01-01' AND issue_date < '2023-01-01' THEN 1 END) as issued_2022,
    COUNT(CASE WHEN issue_date >= '2023-01-01' AND issue_date < '2024-01-01' THEN 1 END) as issued_2023,
    COUNT(CASE WHEN issue_date >= '2024-01-01' AND issue_date < '2025-01-01' THEN 1 END) as issued_2024,
    COUNT(CASE WHEN issue_date >= '2025-01-01' AND issue_date < '2025-07-01' THEN 1 END) as issued_2025_h1,
    COUNT(CASE WHEN bond_name IS NULL THEN 1 END) as missing_bond_name,
    COUNT(CASE WHEN issue_date IS NULL THEN 1 END) as missing_issue_date,
    COUNT(CASE WHEN maturity_date IS NULL THEN 1 END) as missing_maturity_date,
    COUNT(CASE WHEN issue_amount IS NULL THEN 1 END) as missing_issue_amount,
    COUNT(CASE WHEN conversion_price IS NULL THEN 1 END) as missing_conversion_price,
    COUNT(CASE WHEN interest_rate IS NULL THEN 1 END) as missing_interest_rate
FROM convertible_bonds;

-- 전환사채 금액 통계
SELECT
    '3-1. CB - 발행금액 통계' as check_category,
    MIN(issue_amount) as min_amount,
    MAX(issue_amount) as max_amount,
    AVG(issue_amount)::BIGINT as avg_amount,
    SUM(issue_amount)::BIGINT as total_amount,
    COUNT(CASE WHEN issue_amount > 0 THEN 1 END) as valid_amount_count
FROM convertible_bonds
WHERE issue_date >= '2022-01-01' AND issue_date < '2025-07-01';

-- 4. CB Subscribers (CB 인수자) 데이터 확인
-- ============================================================================
SELECT
    '4. CB Subscribers (인수자)' as check_category,
    COUNT(*) as total_subscribers,
    COUNT(DISTINCT cb_id) as cbs_with_subscribers,
    COUNT(DISTINCT subscriber_name) as unique_subscriber_names,
    COUNT(CASE WHEN subscriber_type IS NULL THEN 1 END) as missing_subscriber_type,
    COUNT(CASE WHEN subscription_amount IS NULL THEN 1 END) as missing_subscription_amount,
    COUNT(CASE WHEN subscription_ratio IS NULL THEN 1 END) as missing_subscription_ratio,
    COUNT(CASE WHEN is_related_party = true THEN 1 END) as related_party_count,
    COUNT(CASE WHEN is_related_party IS NULL THEN 1 END) as missing_related_party_flag
FROM cb_subscribers;

-- CB와 인수자 연결 확인
SELECT
    '4-1. CB-Subscribers 연결' as check_category,
    (SELECT COUNT(*) FROM convertible_bonds WHERE issue_date >= '2022-01-01') as cbs_in_period,
    COUNT(DISTINCT s.cb_id) as cbs_with_subscribers,
    ((SELECT COUNT(*) FROM convertible_bonds WHERE issue_date >= '2022-01-01') -
     COUNT(DISTINCT s.cb_id)) as cbs_without_subscribers
FROM cb_subscribers s
JOIN convertible_bonds cb ON s.cb_id = cb.id
WHERE cb.issue_date >= '2022-01-01';

-- 5. Affiliates (계열사) 데이터 확인
-- ============================================================================
SELECT
    '5. Affiliates (계열사)' as check_category,
    COUNT(*) as total_affiliate_records,
    COUNT(DISTINCT parent_company_id) as parent_companies,
    COUNT(DISTINCT affiliate_company_id) as affiliate_companies,
    COUNT(CASE WHEN relationship_type IS NULL THEN 1 END) as missing_relationship_type,
    COUNT(CASE WHEN ownership_ratio IS NULL THEN 1 END) as missing_ownership_ratio,
    COUNT(CASE WHEN is_listed = true THEN 1 END) as listed_affiliates,
    COUNT(CASE WHEN total_assets IS NULL THEN 1 END) as missing_total_assets,
    COUNT(CASE WHEN revenue IS NULL THEN 1 END) as missing_revenue,
    COUNT(CASE WHEN source_date >= '2022-01-01' AND source_date < '2025-07-01' THEN 1 END) as records_in_period
FROM affiliates;

-- 6. Financial Statements (재무제표) 데이터 확인
-- ============================================================================
SELECT
    '6. Financial Statements (재무제표)' as check_category,
    COUNT(*) as total_statements,
    COUNT(DISTINCT company_id) as companies_with_statements,
    COUNT(CASE WHEN fiscal_year = 2022 THEN 1 END) as fy_2022,
    COUNT(CASE WHEN fiscal_year = 2023 THEN 1 END) as fy_2023,
    COUNT(CASE WHEN fiscal_year = 2024 THEN 1 END) as fy_2024,
    COUNT(CASE WHEN fiscal_year = 2025 THEN 1 END) as fy_2025,
    COUNT(CASE WHEN quarter = 'Q1' THEN 1 END) as q1_statements,
    COUNT(CASE WHEN quarter = 'Q2' THEN 1 END) as q2_statements,
    COUNT(CASE WHEN quarter = 'Q3' THEN 1 END) as q3_statements,
    COUNT(CASE WHEN quarter = 'Q4' THEN 1 END) as q4_statements,
    COUNT(CASE WHEN quarter IS NULL THEN 1 END) as annual_statements
FROM financial_statements
WHERE fiscal_year BETWEEN 2022 AND 2025;

-- 재무제표 항목 누락 확인
SELECT
    '6-1. Financial Statements - 누락 항목' as check_category,
    COUNT(CASE WHEN total_assets IS NULL THEN 1 END) as missing_total_assets,
    COUNT(CASE WHEN total_liabilities IS NULL THEN 1 END) as missing_total_liabilities,
    COUNT(CASE WHEN total_equity IS NULL THEN 1 END) as missing_total_equity,
    COUNT(CASE WHEN revenue IS NULL THEN 1 END) as missing_revenue,
    COUNT(CASE WHEN operating_profit IS NULL THEN 1 END) as missing_operating_profit,
    COUNT(CASE WHEN net_income IS NULL THEN 1 END) as missing_net_income,
    COUNT(CASE WHEN operating_cash_flow IS NULL THEN 1 END) as missing_operating_cf,
    COUNT(CASE WHEN investing_cash_flow IS NULL THEN 1 END) as missing_investing_cf,
    COUNT(CASE WHEN financing_cash_flow IS NULL THEN 1 END) as missing_financing_cf
FROM financial_statements
WHERE fiscal_year BETWEEN 2022 AND 2025;

-- 회사별 재무제표 커버리지 확인 (2022-2025)
SELECT
    '6-2. Financial Statements - 회사별 커버리지' as check_category,
    (SELECT COUNT(*) FROM companies WHERE market IN ('KOSPI', 'KOSDAQ', 'KONEX')) as total_companies,
    COUNT(DISTINCT company_id) as companies_with_statements,
    ((SELECT COUNT(*) FROM companies WHERE market IN ('KOSPI', 'KOSDAQ', 'KONEX')) -
     COUNT(DISTINCT company_id)) as companies_without_statements
FROM financial_statements
WHERE fiscal_year BETWEEN 2022 AND 2025;

-- 7. Risk Signals (리스크 신호) 데이터 확인
-- ============================================================================
SELECT
    '7. Risk Signals (리스크 신호)' as check_category,
    COUNT(*) as total_signals,
    COUNT(DISTINCT target_company_id) as companies_with_signals,
    COUNT(CASE WHEN severity = 'LOW' THEN 1 END) as low_severity,
    COUNT(CASE WHEN severity = 'MEDIUM' THEN 1 END) as medium_severity,
    COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_severity,
    COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical_severity,
    COUNT(CASE WHEN status = 'DETECTED' THEN 1 END) as detected_status,
    COUNT(CASE WHEN status = 'CONFIRMED' THEN 1 END) as confirmed_status,
    COUNT(CASE WHEN status = 'RESOLVED' THEN 1 END) as resolved_status,
    COUNT(CASE WHEN detected_at >= '2022-01-01' AND detected_at < '2025-07-01' THEN 1 END) as signals_in_period
FROM risk_signals;

-- 리스크 패턴별 분포
SELECT
    '7-1. Risk Signals - 패턴별 분포' as check_category,
    pattern_type,
    COUNT(*) as signal_count,
    AVG(risk_score) as avg_risk_score
FROM risk_signals
WHERE detected_at >= '2022-01-01' AND detected_at < '2025-07-01'
GROUP BY pattern_type
ORDER BY signal_count DESC;

-- 8. Disclosures (공시) 데이터 확인
-- ============================================================================
SELECT
    '8. Disclosures (공시)' as check_category,
    COUNT(*) as total_disclosures,
    COUNT(DISTINCT corp_code) as companies_with_disclosures,
    COUNT(CASE WHEN rcept_dt >= '20220101' AND rcept_dt < '20230101' THEN 1 END) as disclosures_2022,
    COUNT(CASE WHEN rcept_dt >= '20230101' AND rcept_dt < '20240101' THEN 1 END) as disclosures_2023,
    COUNT(CASE WHEN rcept_dt >= '20240101' AND rcept_dt < '20250101' THEN 1 END) as disclosures_2024,
    COUNT(CASE WHEN rcept_dt >= '20250101' AND rcept_dt < '20250701' THEN 1 END) as disclosures_2025_h1,
    COUNT(CASE WHEN report_nm IS NULL THEN 1 END) as missing_report_name
FROM disclosures
WHERE rcept_dt >= '20220101' AND rcept_dt < '20250701';

-- 공시 파싱 데이터 확인
SELECT
    '8-1. Disclosure Parsed Data' as check_category,
    COUNT(*) as total_parsed,
    COUNT(DISTINCT rcept_no) as unique_disclosures_parsed,
    COUNT(CASE WHEN parsed_data IS NULL OR parsed_data::text = '{}' THEN 1 END) as empty_parsed_data,
    COUNT(CASE WHEN parsed_at >= '2022-01-01' AND parsed_at < '2025-07-01' THEN 1 END) as parsed_in_period
FROM disclosure_parsed_data;

-- 크롤링 작업 상태 확인
SELECT
    '8-2. Crawl Jobs 상태' as check_category,
    job_type,
    status,
    COUNT(*) as job_count,
    MAX(created_at) as last_job_created
FROM crawl_jobs
WHERE created_at >= '2022-01-01'
GROUP BY job_type, status
ORDER BY job_type, status;

-- ============================================================================
-- 종합 데이터 완전성 점검
-- ============================================================================

-- 회사당 평균 데이터 보유량
SELECT
    '종합 - 회사당 데이터 보유' as check_category,
    c.id as company_id,
    c.name as company_name,
    c.ticker,
    COUNT(DISTINCT o.id) as officer_count,
    COUNT(DISTINCT cb.id) as cb_count,
    COUNT(DISTINCT a.id) as affiliate_count,
    COUNT(DISTINCT fs.id) as financial_statement_count,
    COUNT(DISTINCT rs.signal_id) as risk_signal_count
FROM companies c
LEFT JOIN officers o ON o.current_company_id = c.id
LEFT JOIN convertible_bonds cb ON cb.company_id = c.id AND cb.issue_date >= '2022-01-01'
LEFT JOIN affiliates a ON a.parent_company_id = c.id AND a.source_date >= '2022-01-01'
LEFT JOIN financial_statements fs ON fs.company_id = c.id AND fs.fiscal_year BETWEEN 2022 AND 2025
LEFT JOIN risk_signals rs ON rs.target_company_id = c.id AND rs.detected_at >= '2022-01-01'
WHERE c.market IN ('KOSPI', 'KOSDAQ', 'KONEX')
GROUP BY c.id, c.name, c.ticker
ORDER BY officer_count DESC, cb_count DESC
LIMIT 100;

-- 시계열 데이터 커버리지 (연도별, 분기별)
SELECT
    '종합 - 시계열 커버리지' as check_category,
    fiscal_year,
    quarter,
    COUNT(DISTINCT company_id) as companies_covered,
    COUNT(*) as total_records
FROM financial_statements
WHERE fiscal_year BETWEEN 2022 AND 2025
GROUP BY fiscal_year, quarter
ORDER BY fiscal_year,
         CASE
             WHEN quarter IS NULL THEN 0
             WHEN quarter = 'Q1' THEN 1
             WHEN quarter = 'Q2' THEN 2
             WHEN quarter = 'Q3' THEN 3
             WHEN quarter = 'Q4' THEN 4
         END;
