# 데이터베이스 스키마 레지스트리

> **중요**: 모든 테이블 접근 시 이 문서 참조 필수. 테이블명 추측 금지.
>
> **마지막 업데이트**: 2025-12-30
>
> **현재 데이터 상태** (2025-12-30):
> - companies: 3,922건
> - officers: 44,679건
> - officer_positions: 64,265건
> - disclosures: 213,304건
> - convertible_bonds: 1,463건
> - cb_subscribers: 7,490건
> - financial_statements: 9,432건
> - risk_signals: 1,412건
> - risk_scores: 3,912건
> - major_shareholders: 47,453건
> - affiliates: 973건
> - **financial_details: 12,757건** (RaymondsIndex용 상세 재무)
> - **raymonds_index: 7,648건** (자본 배분 효율성 지수 v2.1)
> - users: 4건
> - user_query_usage: - (조회 제한 추적)
> - page_contents: 2건 (페이지 콘텐츠 관리)
> - site_settings: 2건 (사이트 설정)

---

## 핵심 테이블 목록 (PostgreSQL) - 총 25개 테이블

### 1. companies (기업 정보) - 3,922건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| corp_code | varchar | YES | DART 고유 코드 (8자리) |
| ticker | varchar | YES | 종목코드 (6자리) |
| name | varchar | NO | 기업명 (한글) |
| name_en | varchar | YES | 기업명 (영문) |
| business_number | varchar | YES | 사업자번호 |
| market | varchar | YES | 시장 (KOSPI/KOSDAQ/KONEX) |
| listing_status | varchar | YES | 상장상태 |
| sector | varchar | YES | 업종 |
| industry | varchar | YES | 산업분류 |
| market_cap | double | YES | 시가총액 |
| revenue | double | YES | 매출액 |
| net_income | double | YES | 당기순이익 |
| total_assets | double | YES | 총자산 |
| ownership_concentration | double | YES | 지분집중도 |
| affiliate_transaction_ratio | double | YES | 계열사 거래비율 |
| cb_issuance_count | double | YES | CB 발행 횟수 |
| ontology_object_id | varchar | YES | 온톨로지 객체 ID |
| properties | jsonb | YES | 추가 속성 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

**주의사항**: corp_code는 DART API 키, ticker는 거래소 코드

---

### 2. officers (임원 정보) - 44,679건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| name | varchar | NO | 임원명 |
| name_en | varchar | YES | 영문명 |
| birth_date | varchar | YES | 생년월일 (YYYYMMDD 또는 YYYY.MM.DD) |
| gender | varchar | YES | 성별 |
| resident_number_hash | varchar | YES | 주민번호 해시 |
| position | varchar | YES | 현재 직책 |
| current_company_id | uuid | YES | 현재 재직 회사 FK |
| career_history | jsonb | YES | 경력 이력 |
| education | array | YES | 학력 |
| board_count | integer | YES | 겸직 수 |
| network_centrality | double | YES | 네트워크 중심성 |
| influence_score | double | YES | 영향력 점수 |
| has_conflict_of_interest | boolean | YES | 이해충돌 여부 |
| insider_trading_count | integer | YES | 내부자 거래 횟수 |
| ontology_object_id | varchar | YES | 온톨로지 객체 ID |
| properties | jsonb | YES | 추가 속성 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

**연관 스크립트**: `parse_officers_from_local.py`
**주의사항**: 동일인 판단 = name + birth_date 조합

---

### 3. officer_positions (임원 직책 이력) - 64,265건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| officer_id | uuid | NO | FK → officers |
| company_id | uuid | NO | FK → companies |
| position | varchar | NO | 직책명 |
| birth_date | varchar | YES | 생년월일 |
| gender | varchar | YES | 성별 |
| term_start_date | date | YES | 취임일 |
| term_end_date | date | YES | 퇴임일 |
| is_current | boolean | NO | 현재 재직 여부 |
| source_disclosure_id | varchar | YES | 출처 공시번호 |
| source_report_date | date | YES | 공시일 |
| appointment_number | integer | YES | 선임 차수 |
| created_at | timestamp | NO | 생성일시 |
| updated_at | timestamp | NO | 수정일시 |

**연관 스크립트**: `parse_officers_from_local.py`
**중복 판단 기준**: officer_id + company_id + position + birth_date

---

### 4. disclosures (DART 공시) - 213,304건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | varchar | NO | PK |
| rcept_no | varchar | NO | 접수번호 (DART 고유) |
| corp_code | varchar | NO | 기업 코드 (8자리) |
| corp_name | varchar | NO | 기업명 |
| stock_code | varchar | YES | 종목코드 |
| report_nm | varchar | NO | 공시명 |
| rcept_dt | varchar | NO | 접수일 |
| flr_nm | varchar | YES | 공시자명 |
| rm | text | YES | 비고 |
| storage_url | varchar | YES | 저장 URL |
| storage_key | varchar | YES | 저장 키 |
| crawled_at | timestamp | NO | 크롤링 일시 |
| updated_at | timestamp | YES | 수정일시 |
| extra_metadata | jsonb | YES | 추가 메타데이터 |

**연관 스크립트**: `download_missing_companies.py`
**주의**: company_id 없음, corp_code로 companies와 연결

---

### 5. convertible_bonds (전환사채) - 1,463건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| bond_name | varchar | YES | 사채명 |
| bond_type | varchar | YES | 사채종류 |
| issue_date | date | YES | 발행일 |
| maturity_date | date | YES | 만기일 |
| issue_amount | double | YES | 발행금액 (원) |
| interest_rate | double | YES | 이자율 |
| conversion_price | double | YES | 전환가액 (원) |
| conversion_ratio | double | YES | 전환비율 |
| conversion_start_date | date | YES | 전환시작일 |
| conversion_end_date | date | YES | 전환종료일 |
| redemption_price | double | YES | 상환가액 |
| early_redemption_date | date | YES | 조기상환일 |
| outstanding_amount | double | YES | 미상환잔액 |
| converted_amount | double | YES | 전환된금액 |
| redeemed_amount | double | YES | 상환된금액 |
| status | varchar | YES | 상태 |
| use_of_proceeds | text | YES | 자금사용목적 |
| source_disclosure_id | varchar | YES | 출처 공시번호 |
| source_date | varchar | YES | 출처 공시일 |
| ontology_object_id | varchar | YES | 온톨로지 객체 ID |
| properties | jsonb | YES | 추가 속성 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

**연관 스크립트**: `parse_cb_disclosures.py`
**주의사항**: issue_amount는 원 단위, conversion_price도 원 단위

---

### 6. cb_subscribers (CB 인수자) - 7,490건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| cb_id | uuid | NO | FK → convertible_bonds |
| subscriber_name | varchar | NO | 인수자명 |
| subscriber_type | varchar | YES | 인수자 유형 (법인/개인/펀드 등) |
| relationship_to_company | varchar | YES | 회사와의 관계 |
| is_related_party | varchar | YES | 특수관계인 여부 |
| selection_rationale | text | YES | 선정 사유 |
| transaction_history | text | YES | 거래 이력 |
| subscription_amount | double | YES | 인수금액 (원) |
| subscription_quantity | double | YES | 인수수량 |
| notes | text | YES | 비고 |
| subscriber_officer_id | uuid | YES | 임원인 경우 FK |
| subscriber_company_id | uuid | YES | 법인인 경우 FK |
| source_disclosure_id | varchar | YES | 출처 공시번호 |
| source_date | varchar | YES | 출처 공시일 |
| source_report_date | date | YES | 보고일 |
| representative_name | varchar | YES | 대표자명 |
| representative_share | numeric | YES | 대표자 지분 |
| gp_name | varchar | YES | GP명 |
| gp_share | numeric | YES | GP 지분 |
| largest_shareholder_name | varchar | YES | 최대주주명 |
| largest_shareholder_share | numeric | YES | 최대주주 지분 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

**연관 스크립트**: `parse_cb_disclosures.py`

---

### 7. financial_statements (재무제표) - 9,432건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| fiscal_year | integer | NO | 사업연도 |
| quarter | varchar | YES | 분기 |
| statement_date | date | NO | 보고기준일 |
| report_type | varchar | NO | 보고서 유형 |
| cash_and_equivalents | bigint | YES | 현금및현금성자산 |
| short_term_investments | bigint | YES | 단기금융상품 |
| accounts_receivable | bigint | YES | 매출채권 |
| inventory | bigint | YES | 재고자산 |
| current_assets | bigint | YES | 유동자산 |
| non_current_assets | bigint | YES | 비유동자산 |
| total_assets | bigint | YES | 자산총계 |
| accounts_payable | bigint | YES | 매입채무 |
| short_term_debt | bigint | YES | 단기차입금 |
| current_liabilities | bigint | YES | 유동부채 |
| long_term_debt | bigint | YES | 장기차입금 |
| non_current_liabilities | bigint | YES | 비유동부채 |
| total_liabilities | bigint | YES | 부채총계 |
| capital_stock | bigint | YES | 자본금 |
| retained_earnings | bigint | YES | 이익잉여금 |
| total_equity | bigint | YES | 자본총계 |
| revenue | bigint | YES | 매출액 |
| cost_of_sales | bigint | YES | 매출원가 |
| gross_profit | bigint | YES | 매출총이익 |
| operating_expenses | bigint | YES | 판관비 |
| operating_profit | bigint | YES | 영업이익 |
| net_income | bigint | YES | 당기순이익 |
| operating_cash_flow | bigint | YES | 영업활동현금흐름 |
| investing_cash_flow | bigint | YES | 투자활동현금흐름 |
| financing_cash_flow | bigint | YES | 재무활동현금흐름 |
| source_rcept_no | varchar | YES | 출처 공시번호 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

---

### 8. risk_signals (위험 신호) - 1,412건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| signal_id | uuid | NO | PK |
| target_company_id | uuid | NO | FK → companies |
| pattern_type | varchar | NO | 위험 패턴 유형 |
| severity | enum | NO | 심각도 |
| status | enum | NO | 상태 |
| risk_score | double | NO | 위험 점수 |
| exploitation_probability | double | YES | 악용 확률 |
| expected_retail_loss | double | YES | 예상 개인투자자 손실 |
| title | varchar | NO | 제목 |
| description | varchar | NO | 설명 |
| evidence | jsonb | YES | 증거 데이터 |
| involved_object_ids | array | YES | 관련 객체 ID |
| involved_link_ids | array | YES | 관련 링크 ID |
| ontology_object_id | varchar | YES | 온톨로지 객체 ID |
| properties | jsonb | YES | 추가 속성 |
| detected_at | timestamp(tz) | NO | 탐지일시 |
| confirmed_at | timestamp(tz) | YES | 확정일시 |
| resolved_at | timestamp(tz) | YES | 해결일시 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

---

### 9. risk_scores (위험 점수) - 3,912건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| analysis_year | integer | NO | 분석 연도 |
| analysis_quarter | integer | YES | 분석 분기 |
| total_score | numeric | NO | 총점 |
| risk_level | varchar | NO | 위험 등급 |
| investment_grade | varchar | YES | 투자 등급 |
| confidence | numeric | YES | 신뢰도 |
| raymondsrisk_score | numeric | YES | RaymondsRisk 점수 |
| human_risk_score | numeric | YES | 인적 위험 점수 |
| cb_risk_score | numeric | YES | CB 위험 점수 |
| financial_health_score | numeric | YES | 재무건전성 점수 |
| score_breakdown | jsonb | YES | 점수 내역 |
| calculated_at | timestamp(tz) | YES | 계산일시 |
| created_at | timestamp(tz) | YES | 생성일시 |
| updated_at | timestamp(tz) | YES | 수정일시 |

---

### 10. major_shareholders (대주주) - 47,453건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| shareholder_name | varchar | NO | 주주명 |
| shareholder_name_normalized | varchar | YES | 정규화된 주주명 |
| shareholder_type | varchar | YES | 주주유형 (INSTITUTION/OFFICER/INDIVIDUAL/OTHER) |
| share_count | bigint | YES | 주식수 |
| share_ratio | numeric | YES | 지분율 (%) |
| is_largest_shareholder | boolean | YES | 최대주주 여부 |
| is_related_party | boolean | YES | 특수관계인 여부 |
| report_date | date | YES | 보고일 |
| report_year | integer | YES | 보고연도 |
| report_quarter | integer | YES | 보고분기 |
| change_reason | varchar | YES | 변동사유 |
| previous_share_ratio | numeric | YES | 이전 지분율 |
| source_rcept_no | varchar | YES | 출처 공시번호 |
| created_at | timestamp(tz) | YES | 생성일시 |
| updated_at | timestamp(tz) | YES | 수정일시 |

**연관 스크립트**: `/tmp/parse_shareholders_investments_v2.py`
**소스 테이블**: DART XML의 BSH_SPCL (주주에 관한 사항)

---

### 11. affiliates (계열사) - 973건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| parent_company_id | uuid | NO | FK → companies (모회사) |
| affiliate_company_id | uuid | NO | FK → companies (계열사, 등록된 경우) |
| affiliate_name | varchar | NO | 계열사명 |
| business_number | varchar | YES | 사업자번호 |
| relationship_type | varchar | YES | 관계유형 |
| is_listed | boolean | YES | 상장여부 |
| ownership_ratio | double | YES | 지분율 (%) |
| voting_rights_ratio | double | YES | 의결권 비율 |
| total_assets | double | YES | 총자산 |
| revenue | double | YES | 매출액 |
| net_income | double | YES | 당기순이익 |
| source_disclosure_id | varchar | YES | 출처 공시번호 |
| source_date | varchar | YES | 출처 공시일 |
| ontology_object_id | varchar | YES | 온톨로지 객체 ID |
| properties | jsonb | YES | 추가 속성 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

**연관 스크립트**: `/tmp/parse_shareholders_investments_v2.py`
**소스 테이블**: DART XML의 INV_PRT (타법인출자 현황)

---

### 12. financial_details (상세 재무 데이터) - 12,757건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| fiscal_year | integer | NO | 사업연도 |
| fiscal_quarter | integer | YES | 분기 (1-4) |
| report_type | varchar | YES | 보고서 유형 (annual, q1, q2, q3) |
| **자산 항목** |
| cash_and_equivalents | bigint | YES | 현금및현금성자산 |
| short_term_investments | bigint | YES | 단기금융상품 |
| trade_and_other_receivables | bigint | YES | 매출채권 |
| inventories | bigint | YES | 재고자산 |
| current_assets | bigint | YES | 유동자산 |
| current_tax_assets | bigint | YES | 당기법인세자산 |
| other_financial_assets_current | bigint | YES | 기타금융자산(유동) |
| other_assets_current | bigint | YES | 기타자산(유동) |
| non_current_assets | bigint | YES | 비유동자산 |
| tangible_assets | bigint | YES | 유형자산 |
| intangible_assets | bigint | YES | 무형자산 |
| fvpl_financial_assets | bigint | YES | 당기손익-공정가치금융자산 |
| investments_in_associates | bigint | YES | 관계기업투자 |
| right_of_use_assets | bigint | YES | 사용권자산 |
| net_defined_benefit_assets | bigint | YES | 순확정급여자산 |
| deferred_tax_assets | bigint | YES | 이연법인세자산 |
| other_financial_assets_non_current | bigint | YES | 기타금융자산(비유동) |
| other_assets_non_current | bigint | YES | 기타자산(비유동) |
| total_assets | bigint | YES | 자산총계 |
| **부채 항목** |
| trade_payables | bigint | YES | 매입채무 |
| short_term_borrowings | bigint | YES | 단기차입금 |
| current_portion_long_term_debt | bigint | YES | 유동성장기부채 |
| current_liabilities | bigint | YES | 유동부채 |
| current_tax_liabilities | bigint | YES | 당기법인세부채 |
| provisions_current | bigint | YES | 충당부채(유동) |
| other_current_liabilities | bigint | YES | 기타유동부채 |
| long_term_borrowings | bigint | YES | 장기차입금 |
| bonds_payable | bigint | YES | 사채 |
| convertible_bonds | bigint | YES | 전환사채 |
| lease_liabilities | bigint | YES | 리스부채 |
| non_current_liabilities | bigint | YES | 비유동부채 |
| deferred_tax_liabilities | bigint | YES | 이연법인세부채 |
| provisions_non_current | bigint | YES | 충당부채(비유동) |
| other_non_current_liabilities | bigint | YES | 기타비유동부채 |
| total_liabilities | bigint | YES | 부채총계 |
| **자본 항목** |
| capital_stock | bigint | YES | 자본금 |
| capital_surplus | bigint | YES | 자본잉여금 |
| retained_earnings | bigint | YES | 이익잉여금 |
| treasury_stock | bigint | YES | 자기주식 |
| total_equity | bigint | YES | 자본총계 |
| **손익 항목** |
| revenue | bigint | YES | 매출액 |
| cost_of_sales | bigint | YES | 매출원가 |
| selling_admin_expenses | bigint | YES | 판관비 |
| operating_income | bigint | YES | 영업이익 |
| net_income | bigint | YES | 당기순이익 |
| r_and_d_expense | bigint | YES | 연구개발비 |
| depreciation_expense | bigint | YES | 감가상각비 |
| interest_expense | bigint | YES | 이자비용 |
| tax_expense | bigint | YES | 법인세비용 |
| **현금흐름 항목** |
| operating_cash_flow | bigint | YES | 영업활동현금흐름 |
| investing_cash_flow | bigint | YES | 투자활동현금흐름 |
| financing_cash_flow | bigint | YES | 재무활동현금흐름 |
| capex | bigint | YES | 유형자산취득 (CAPEX) |
| intangible_acquisition | bigint | YES | 무형자산취득 |
| dividend_paid | bigint | YES | 배당금지급 |
| treasury_stock_acquisition | bigint | YES | 자기주식취득 |
| stock_issuance | bigint | YES | 주식발행 |
| bond_issuance | bigint | YES | 사채발행 |
| **메타데이터** |
| fs_type | varchar | YES | 재무제표 유형 (CFS/OFS) |
| data_source | varchar | YES | 데이터 출처 |
| source_rcept_no | varchar | YES | 출처 공시번호 |
| created_at | timestamp | YES | 생성일시 |
| updated_at | timestamp | YES | 수정일시 |

**연관 스크립트**: `parse_q3_reports_2025.py`, `parse_local_financial_details.py`
**UNIQUE 제약**: company_id + fiscal_year + fiscal_quarter + fs_type

---

### 13. raymonds_index (자본 배분 효율성 지수 v2.1) - 7,648건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| calculation_date | date | NO | 계산일 |
| fiscal_year | integer | NO | 기준 사업연도 |
| **종합 점수** |
| total_score | numeric(5,2) | NO | 총점 (0-100) |
| grade | varchar(5) | NO | 등급 (A++/A+/A/A-/B+/B/B-/C+/C) |
| **Sub-Index 점수** |
| cei_score | numeric(5,2) | YES | Capital Efficiency Index (20%) |
| rii_score | numeric(5,2) | YES | Reinvestment Intensity Index (35%) ⭐ |
| cgi_score | numeric(5,2) | YES | Cash Governance Index (25%) |
| mai_score | numeric(5,2) | YES | Momentum Alignment Index (20%) |
| **핵심 지표 (기존)** |
| investment_gap | numeric(6,2) | YES | 투자괴리율 (%) |
| cash_cagr | numeric(6,2) | YES | 현금 CAGR (%) |
| capex_growth | numeric(6,2) | YES | CAPEX 성장률 (%) |
| idle_cash_ratio | numeric(5,2) | YES | 유휴현금비율 (%) |
| asset_turnover | numeric(5,3) | YES | 자산회전율 (회) |
| reinvestment_rate | numeric(5,2) | YES | 재투자율 (%) |
| shareholder_return | numeric(5,2) | YES | 주주환원율 (%) |
| **v4.0 위험 탐지 지표** |
| cash_tangible_ratio | numeric(10,2) | YES | 현금-유형자산 증가비율 (X:1) |
| fundraising_utilization | numeric(5,2) | YES | 조달자금 투자전환율 (%) |
| short_term_ratio | numeric(5,2) | YES | 단기금융상품 비율 (%) |
| capex_trend | varchar(20) | YES | CAPEX 추세 (increasing/stable/decreasing) |
| roic | numeric(6,2) | YES | 투하자본수익률 ROIC (%) |
| capex_cv | numeric(5,3) | YES | CAPEX 변동계수 (투자 지속성) |
| violation_count | integer | YES | 특별규칙 위반 개수 (0-3) |
| **v2.0/v2.1 신규 지표** |
| investment_gap_v2 | numeric(6,2) | YES | 투자괴리율 v2 (레거시: 초기2년 - 최근2년 재투자율) |
| investment_gap_v21 | numeric(6,2) | YES | 투자괴리율 v2.1 ⭐핵심 (현금 CAGR - CAPEX 성장률) |
| rd_intensity | numeric(5,2) | YES | R&D 강도 (미사용) |
| ebitda | bigint | YES | EBITDA |
| debt_to_ebitda | numeric(6,2) | YES | 부채/EBITDA (CGI용) |
| cash_utilization | numeric(5,2) | YES | 현금 활용도 (%) |
| industry_sector | varchar(50) | YES | 업종 분류 |
| weight_adjustment | jsonb | YES | 업종별 가중치 조정 내역 |
| **v2.1 신규 지표** |
| tangible_efficiency | numeric(6,3) | YES | 유형자산 효율성 (매출/유형자산) |
| cash_yield | numeric(6,2) | YES | 현금 수익률 (영업이익/총현금 %) |
| growth_investment_ratio | numeric(5,2) | YES | 성장 투자 비율 (성장CAPEX/총CAPEX %) |
| **위험 신호** |
| red_flags | jsonb | YES | 적색 경고 배열 |
| yellow_flags | jsonb | YES | 황색 경고 배열 |
| **해석** |
| verdict | varchar(200) | YES | 한 줄 요약 |
| key_risk | text | YES | 핵심 리스크 |
| recommendation | text | YES | 투자자 권고 |
| watch_trigger | text | YES | 재검토 시점 |
| **메타데이터** |
| data_quality_score | numeric(3,2) | YES | 데이터 품질 점수 (0-1) |
| created_at | timestamp | NO | 생성일시 |

**연관 스크립트**: `calculate_raymonds_index.py`
**UNIQUE 제약**: company_id + fiscal_year

**v2.1 등급 기준 (완화됨)**:
| 등급 | 점수 범위 | 설명 |
|------|----------|------|
| A++ | 95-100 | 최우수 |
| A+ | 88-94 | 우수 |
| A | 80-87 | 양호 |
| A- | 72-79 | 양호- |
| B+ | 64-71 | 보통+ |
| B | 55-63 | 보통 |
| B- | 45-54 | 보통- |
| C+ | 30-44 | 주의 |
| C | 0-29 | 위험 |

**v2.1 Sub-Index 가중치**:
- CEI (20%): 자산회전율(25%) + 유형자산효율성(20%) + 현금수익률(20%) + ROIC(25%) + 추세(10%)
- RII (35%): CAPEX강도(30%) + 투자괴리율(30%) + 재투자율(25%) + 지속성(15%)
- CGI (25%): 현금활용도(20%) + 자금조달효율성(25%) + 주주환원균형(20%) + 현금적정성(15%) + 부채건전성(20%)
- MAI (20%): 매출-투자동조성(30%) + 이익품질(25%) + 투자지속성(20%) + 성장투자비율(15%) + FCF추세(10%)

**특별 규칙**:
- 현금-유형자산 비율 > 30:1 → 최대 B-
- 조달자금 전환율 < 30% → 최대 B-
- 단기금융상품비율 > 65% + CAPEX 감소 → 최대 B
- 위 조건 2개 이상 해당 → 최대 C+

---

## 사용자/인증 관련 테이블

### 14. users (사용자) - 4건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| email | varchar | NO | 이메일 |
| username | varchar | NO | 사용자명 |
| hashed_password | varchar | YES | 해시된 비밀번호 |
| full_name | varchar | YES | 전체 이름 |
| is_active | boolean | NO | 활성 여부 |
| is_superuser | boolean | NO | 관리자 여부 |
| profile_image | varchar | YES | 프로필 이미지 URL |
| oauth_provider | varchar | YES | OAuth 제공자 |
| oauth_provider_id | varchar | YES | OAuth 제공자 ID |
| subscription_tier | varchar | NO | 구독 등급 (free/light/max) |
| subscription_expires_at | timestamp(tz) | YES | 구독 만료일 |
| last_login | timestamp(tz) | YES | 마지막 로그인 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

### 15. email_verification_tokens (이메일 인증 토큰) - 4건

### 16. password_reset_tokens (비밀번호 재설정 토큰) - 0건

### 17. subscription_payments (구독 결제) - 0건

---

## 콘텐츠/설정 관련 테이블

### 18. user_query_usage (사용자 조회 사용량) - 0건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| user_id | uuid | NO | FK → users |
| year_month | varchar(7) | NO | 연월 (YYYY-MM) |
| query_count | integer | NO | 조회 횟수 |
| created_at | timestamp | NO | 생성일시 |
| updated_at | timestamp | NO | 수정일시 |

**용도**: 구독별 월간 조회 제한 추적

### 19. page_contents (페이지 콘텐츠) - 2건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| page | varchar(50) | NO | 페이지명 |
| section | varchar(50) | NO | 섹션명 |
| field | varchar(50) | NO | 필드명 |
| value | text | YES | 콘텐츠 값 |
| created_at | timestamp | NO | 생성일시 |
| updated_at | timestamp | NO | 수정일시 |

**용도**: 어드민에서 페이지 콘텐츠 동적 편집

### 20. site_settings (사이트 설정) - 2건

---

## 시스템/기타 테이블

| 테이블명 | 레코드 수 | 용도 | 주의사항 |
|----------|----------|------|----------|
| alembic_version | 1 | DB 마이그레이션 버전 | 수정 금지 |
| crawl_jobs | 0 | 크롤링 작업 | - |
| disclosure_parsed_data | 0 | 파싱된 공시 데이터 | - |
| ontology_links | 0 | 온톨로지 링크 | - |
| ontology_objects | 0 | 온톨로지 객체 | - |

---

## 자주 혼동되는 테이블명

| 틀린 이름 | 올바른 이름 | 비고 |
|----------|------------|------|
| company | **companies** | 복수형 |
| officer | **officers** | 복수형 |
| position | **officer_positions** | officer_ 접두사 필요 |
| positions | **officer_positions** | officer_ 접두사 필요 |
| cb | **convertible_bonds** | 전체 이름 사용 |
| bond | **convertible_bonds** | 전체 이름 사용 |
| subscriber | **cb_subscribers** | cb_ 접두사 필요 |
| subscribers | **cb_subscribers** | cb_ 접두사 필요 |
| disclosure | **disclosures** | 복수형 |
| shareholder | **major_shareholders** | major_ 접두사 필요 |
| affiliate | **affiliates** | 복수형 |
| financial | **financial_details** | _details 접미사 필요 |
| raymond | **raymonds_index** | raymonds_index 사용 |

---

## 테이블 관계도

```
companies (1) ─────┬────── (N) officers
                   │
                   ├────── (N) officer_positions ──── (N) officers
                   │
                   ├────── (N) disclosures
                   │
                   ├────── (N) convertible_bonds ──── (N) cb_subscribers
                   │
                   ├────── (N) financial_statements
                   │
                   ├────── (N) financial_details
                   │
                   ├────── (N) raymonds_index
                   │
                   ├────── (N) risk_signals
                   │
                   ├────── (N) risk_scores
                   │
                   ├────── (N) major_shareholders
                   │
                   └────── (N) affiliates

users (1) ─────────┬────── (N) user_query_usage
                   │
                   ├────── (N) subscription_payments
                   │
                   ├────── (N) email_verification_tokens
                   │
                   └────── (N) password_reset_tokens
```

---

## 데이터 검증 쿼리

### 전체 테이블 COUNT (세션 시작 시 실행)

```sql
SELECT 'companies' as tbl, COUNT(*) FROM companies
UNION ALL SELECT 'officers', COUNT(*) FROM officers
UNION ALL SELECT 'officer_positions', COUNT(*) FROM officer_positions
UNION ALL SELECT 'disclosures', COUNT(*) FROM disclosures
UNION ALL SELECT 'convertible_bonds', COUNT(*) FROM convertible_bonds
UNION ALL SELECT 'cb_subscribers', COUNT(*) FROM cb_subscribers
UNION ALL SELECT 'financial_statements', COUNT(*) FROM financial_statements
UNION ALL SELECT 'financial_details', COUNT(*) FROM financial_details
UNION ALL SELECT 'raymonds_index', COUNT(*) FROM raymonds_index
UNION ALL SELECT 'risk_signals', COUNT(*) FROM risk_signals
UNION ALL SELECT 'risk_scores', COUNT(*) FROM risk_scores
UNION ALL SELECT 'major_shareholders', COUNT(*) FROM major_shareholders
UNION ALL SELECT 'affiliates', COUNT(*) FROM affiliates
UNION ALL SELECT 'users', COUNT(*) FROM users
ORDER BY 1;
```

### 기업별 데이터 커버리지 확인

```sql
-- 임원 데이터 있는 기업 수
SELECT COUNT(DISTINCT company_id) FROM officer_positions;

-- CB 데이터 있는 기업 수
SELECT COUNT(DISTINCT company_id) FROM convertible_bonds;

-- RaymondsIndex 평가 완료 기업 수
SELECT COUNT(DISTINCT company_id) FROM raymonds_index;
```

### RaymondsIndex 등급별 분포

```sql
SELECT grade, COUNT(*) as count
FROM raymonds_index
WHERE fiscal_year = 2024
GROUP BY grade
ORDER BY CASE grade
    WHEN 'A++' THEN 1 WHEN 'A+' THEN 2 WHEN 'A' THEN 3 WHEN 'A-' THEN 4
    WHEN 'B+' THEN 5 WHEN 'B' THEN 6 WHEN 'B-' THEN 7
    WHEN 'C+' THEN 8 WHEN 'C' THEN 9
END;
```
