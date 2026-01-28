# 데이터베이스 스키마 레지스트리

> **중요**: 모든 테이블 접근 시 이 문서 참조 필수. 테이블명 추측 금지.
>
> **마지막 업데이트**: 2026-01-21
>
> **현재 데이터 상태** (2026-01-21):
> - companies: 3,109건 (813개 삭제 후)
> - officers: 47,444건
> - officer_positions: 62,141건
> - disclosures: 279,258건
> - convertible_bonds: 1,133건
> - cb_subscribers: 7,026건
> - financial_statements: 9,820건
> - risk_signals: 1,412건
> - risk_scores: 3,138건
> - major_shareholders: 44,574건
> - affiliates: 864건
> - financial_details: 10,288건 (XBRL v3.0 파서 적용)
> - **raymonds_index: 5,257건** (5,257개 기업 평가 완료)
> - **stock_prices: 126,506건**
> - **largest_shareholder_info: 4,599건** (최대주주 기본정보)
> - users: 4건
> - user_query_usage: - (조회 제한 추적)
> - page_contents: - (페이지 콘텐츠 관리)
> - site_settings: - (사이트 설정)
> - **company_labels: -** (기업 라벨)
> - **news_articles: 468건** (뉴스 기사)
> - **news_entities: 2,703건** (뉴스 엔티티)
> - **news_relations: 791건** (뉴스 관계)
> - **news_risks: 1,470건** (뉴스 위험요소)
> - **news_company_complexity: -** (뉴스 기업 복잡도)
> - **toss_users: 4건** (토스 로그인 사용자)
> - **credit_transactions: 16건** (이용권 거래)
> - **credit_products: 3건** (이용권 상품)
> - **report_views: 6건** (리포트 조회)
> - **pipeline_runs: 0건** (파이프라인 실행 이력)
> - **service_applications: 1건** (서비스 이용신청)
> - **financial_ratios: -** (재무비율 분석 - 25개 재무비율)
> - **company_view_history: -** (사용자 기업 조회 기록)
> - **crawl_jobs: -** (크롤링 작업)
> - **disclosure_parsed_data: -** (공시 파싱 데이터)
> - **script_execution_log: -** (스크립트 실행 로그)
> - **ontology_objects: -** (온톨로지 객체)
> - **ontology_links: -** (온톨로지 관계)
> - **alembic_version: 1건** (마이그레이션 버전)

---

## 핵심 테이블 목록 (PostgreSQL) - 총 43개 테이블

### 1. companies (기업 정보) - 3,109건

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
| **company_type** | varchar(20) | YES | 기업 유형 (NORMAL/SPAC/REIT/ETF/HOLDING/FINANCIAL), 기본값: 'NORMAL' |
| **trading_status** | varchar(20) | YES | 거래 상태 (NORMAL/SUSPENDED/TRADING_HALT), 기본값: 'NORMAL' |
| **is_managed** | varchar(1) | YES | 관리종목 여부 (Y/N), 기본값: 'N' |

**주의사항**: corp_code는 DART API 키, ticker는 거래소 코드

#### 기업 유형별 현황 (2026-01-12 추가)

| company_type | 설명 | 기업 수 |
|--------------|------|--------|
| NORMAL | 일반 상장사 | ~2,600 |
| SPAC | 기업인수목적회사 | 80 |
| REIT | 부동산투자회사 | 42 |
| ETF | 상장지수펀드 | 1,149 |

**참고**: SPAC/ETF/REIT는 임원/대주주/재무 데이터 구조가 다르므로 파싱 시 필터링 필요

---

### 2. officers (임원 정보) - 49,446건

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
| career_history | jsonb | YES | 경력 이력 (구조화된 파싱 결과) |
| **career_raw_text** | **text** | **YES** | **사업보고서 '주요경력' 원문 (v2.4 추가)** |
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

**연관 스크립트**: `parse_officers_from_local.py`, `reparse_officer_careers.py`
**주의사항**: 동일인 판단 = name + birth_date 조합

#### career_history 컬럼 상세

**데이터 출처**: 사업보고서 > "임원 및 직원 등의 현황" > "주요경력" 필드

**JSON 형식**:
```json
[
  {"text": "(주)OO회사 재무이사", "status": "former"},
  {"text": "(주)OO회사 대표이사", "status": "current"}
]
```

**status 값**:
- `current`: 현재 경력 (現/현 패턴)
- `former`: 과거 경력 (前/전 패턴)
- `unknown`: 상태 미확인

**현황**: 49,446명 중 구조화된 경력 데이터 보유 (career_history)

#### career_raw_text 컬럼 상세 (v2.5 업데이트, 2026-01-07)

**현황**: 원문 경력 데이터 보유 (career_raw_text)

**목적**: 경력 패턴 파싱 실패 시에도 원문 표시 가능하도록 원문 텍스트 저장

**데이터 출처**: DART XML > SH5_SKL (주요경력) 필드

**변환 규칙**:
- `□` 불릿 → `• ` (줄바꿈 + 불릿) 변환
- 연속 줄바꿈 정리

**표시 방식**:
- 상장사 임원 DB 정보 (career_history) 아래에 표시
- "사업보고서 주요경력 (원문)" 라벨로 구분

**연관 파일**:
- 파서: `scripts/parsers/officer.py`
- 재파싱: `scripts/maintenance/reparse_officer_careers.py`
- API: `app/api/endpoints/graph_fallback.py`
- 프론트엔드: `frontend/src/components/graph/NodeDetailPanel.tsx`

---

### 3. officer_positions (임원 직책 이력) - 75,059건

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
| position_history | jsonb | YES | 직책 이력 (2026-01-04 추가) |
| created_at | timestamp | NO | 생성일시 |
| updated_at | timestamp | NO | 수정일시 |

**연관 스크립트**: `parse_officers_from_local.py`
**중복 판단 기준**: officer_id + company_id + position + birth_date

#### position_history 컬럼 상세 (2026-01-04 추가)

**JSON 형식**:
```json
[
  {"position": "사외이사", "date": "2023-03-15", "source": "20230315000123"},
  {"position": "감사위원", "date": "2024-03-20", "source": "20240320000456"}
]
```

**용도**: 동일 회사 내 직책 변경 이력 추적

---

### 4. disclosures (DART 공시) - 279,258건

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

### 5. convertible_bonds (전환사채) - 1,133건

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

### 6. cb_subscribers (CB 인수자) - 7,026건

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

### 7. financial_statements (재무제표) - 9,820건

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

### 10. major_shareholders (대주주) - 60,214건

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

**연관 스크립트**: `parse_major_shareholders.py`, `parse_major_shareholders_v2.py`
**소스 테이블**: DART XML의 BSH_SPCL (주주에 관한 사항)

#### 데이터 품질 이슈 (2026-01-01 수정)

| 유형 | 건수 | 설명 | 처리 상태 |
|------|------|------|-----------|
| 주식수 오기입 | 2,368 | 주식수가 주주명에 잘못 입력 (예: "473,440") | ✅ 삭제 완료 |
| 날짜/기간 오기입 | 254 | 재직기간이 주주명에 입력 (예: "03 ~ 12") | ✅ 삭제 완료 |
| 순수 숫자 | 35 | 의미없는 숫자만 입력 | ✅ 삭제 완료 |
| 정상 펀드명 | 1 | 연도로 시작하는 펀드명 (예: "2018큐씨피13호") | 정상 데이터 유지 |
| 재무항목명 오기입 | 19 | 재무제표 항목명이 주주명에 입력 (예: "영업이익", "감가상각비") | ✅ 삭제 완료 |

**정제 결과** (2026-01-01):
- 삭제된 레코드: 2,685건 (숫자 오기입 2,666건 + 재무항목명 19건)
- 현재 레코드: 60,214건 (426개 기업 보완 파싱 적용)
- 숫자로 시작하는 정상 데이터: 1건 (펀드명)

**파싱 로직 개선** (2026-01-01):
- `is_valid_shareholder_name()` 함수 추가
- 숫자로 시작하는 주주명 필터링 (펀드명 예외 처리)
- 날짜/기간 패턴 필터링
- 무효 키워드 필터링 (자산, 부채, 거래량 등)

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

### 12. financial_details (상세 재무 데이터) - 9,926건

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
| **gross_profit** | bigint | YES | 매출총이익 ⭐신규 |
| **interest_income** | bigint | YES | 이자수익 ⭐신규 |
| **income_before_tax** | bigint | YES | 법인세차감전이익 ⭐신규 |
| **amortization** | bigint | YES | 무형자산상각비 ⭐신규 |
| created_at | timestamp | YES | 생성일시 |
| updated_at | timestamp | YES | 수정일시 |

**연관 스크립트**: `parse_q3_reports_2025.py`, `parse_local_financial_details.py`
**UNIQUE 제약**: company_id + fiscal_year + fiscal_quarter + fs_type

---

### 12-1. financial_ratios (재무비율 분석) - 신규 예정 ⭐

25개 재무비율 계산 결과 저장 테이블. `financial_details` 원본 데이터 기반으로 계산.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| fiscal_year | integer | NO | 사업연도 |
| fiscal_quarter | integer | YES | 분기 (NULL=연간) |
| calculation_date | timestamp | YES | 계산일시 |
| financial_detail_id | uuid | YES | FK → financial_details |
| **안정성 지표 (Stability)** |
| current_ratio | decimal(10,2) | YES | 유동비율 (%) |
| quick_ratio | decimal(10,2) | YES | 당좌비율 (%) |
| debt_ratio | decimal(10,2) | YES | 부채비율 (%) |
| equity_ratio | decimal(10,2) | YES | 자기자본비율 (%) |
| debt_dependency | decimal(10,2) | YES | 차입금의존도 (%) |
| non_current_ratio | decimal(10,2) | YES | 비유동비율 (%) |
| **수익성 지표 (Profitability)** |
| operating_margin | decimal(10,2) | YES | 매출액영업이익률 (%) |
| net_profit_margin | decimal(10,2) | YES | 매출액순이익률 (%) |
| roa | decimal(10,2) | YES | 총자산순이익률 (%) |
| roe | decimal(10,2) | YES | 자기자본순이익률 (%) |
| gross_margin | decimal(10,2) | YES | 매출총이익률 (%) |
| ebitda_margin | decimal(10,2) | YES | EBITDA마진 (%) |
| ebitda | bigint | YES | EBITDA (절대값) |
| **성장성 지표 (Growth)** |
| revenue_growth | decimal(10,2) | YES | 매출액증가율 (%) ⭐전기 데이터 필요 |
| operating_income_growth | decimal(10,2) | YES | 영업이익증가율 (%) ⭐전기 데이터 필요 |
| net_income_growth | decimal(10,2) | YES | 순이익증가율 (%) ⭐전기 데이터 필요 |
| total_assets_growth | decimal(10,2) | YES | 총자산증가율 (%) ⭐전기 데이터 필요 |
| growth_data_available | boolean | YES | 전기 데이터 유무, 기본값: false |
| **활동성 지표 (Activity)** |
| asset_turnover | decimal(10,2) | YES | 총자산회전율 (회) |
| receivables_turnover | decimal(10,2) | YES | 매출채권회전율 (회) |
| inventory_turnover | decimal(10,2) | YES | 재고자산회전율 (회) |
| payables_turnover | decimal(10,2) | YES | 매입채무회전율 (회) |
| receivables_days | decimal(10,2) | YES | 매출채권회수기간 (일) |
| inventory_days | decimal(10,2) | YES | 재고자산보유기간 (일) |
| payables_days | decimal(10,2) | YES | 매입채무지급기간 (일) |
| cash_conversion_cycle | decimal(10,2) | YES | 현금전환주기 (일) |
| **현금흐름 지표 (Cash Flow)** |
| ocf_ratio | decimal(10,2) | YES | 영업현금흐름비율 (%) |
| ocf_interest_coverage | decimal(10,2) | YES | 현금흐름이자보상배율 (배) |
| free_cash_flow | bigint | YES | 잉여현금흐름 (원) |
| fcf_margin | decimal(10,2) | YES | FCF마진 (%) |
| **레버리지 지표 (Leverage)** |
| interest_coverage | decimal(10,2) | YES | 이자보상배율 (배) |
| ebitda_interest_coverage | decimal(10,2) | YES | EBITDA이자보상배율 (배) |
| net_debt_to_ebitda | decimal(10,2) | YES | 순차입금/EBITDA (배) |
| financial_expense_ratio | decimal(10,2) | YES | 금융비용부담률 (%) |
| total_borrowings | bigint | YES | 총차입금 (원) |
| net_debt | bigint | YES | 순차입금 (원) |
| **연속 적자/흑자 정보** |
| consecutive_loss_quarters | integer | YES | 연속 적자 분기 수, 기본값: 0 |
| consecutive_profit_quarters | integer | YES | 연속 흑자 분기 수, 기본값: 0 |
| is_loss_making | boolean | YES | 당기 적자 여부 |
| **종합 점수** |
| stability_score | decimal(5,2) | YES | 안정성 점수 (0-100) |
| profitability_score | decimal(5,2) | YES | 수익성 점수 (0-100) |
| growth_score | decimal(5,2) | YES | 성장성 점수 (0-100) |
| activity_score | decimal(5,2) | YES | 활동성 점수 (0-100) |
| cashflow_score | decimal(5,2) | YES | 현금흐름 점수 (0-100) |
| leverage_score | decimal(5,2) | YES | 레버리지 점수 (0-100) |
| financial_health_score | decimal(5,2) | YES | 종합 건전성 점수 (0-100) |
| financial_health_grade | varchar(5) | YES | 등급 (A++~C) |
| financial_risk_level | varchar(20) | YES | 위험 수준 (LOW/MEDIUM/HIGH/CRITICAL) |
| **메타데이터** |
| data_completeness | decimal(5,2) | YES | 데이터 완성도 (0-1) |
| calculation_notes | text | YES | 계산 비고 |
| created_at | timestamp | YES | 생성일시 |

**UNIQUE 제약**: company_id + fiscal_year + fiscal_quarter
**연관 모델**: `app/models/financial_ratios.py` (신규)
**연관 서비스**: `app/services/financial_ratios_calculator.py` (신규)

**성장성 지표 주의사항**:
- 전기(fiscal_year - 1) 데이터가 없으면 성장률 계산 불가
- `growth_data_available = false`인 경우 성장성 지표 모두 NULL
- 2022년 데이터는 2021년 전기 데이터가 없어 성장률 계산 불가

**데이터 현황** (예정):
| 연도 | 계산 가능 | 성장률 계산 |
|------|----------|------------|
| 2022 | ✅ | ❌ (전기 없음) |
| 2023 | ✅ | ✅ |
| 2024 | ✅ | ✅ |
| 2025 | ✅ | ✅ |

---

### 13. raymonds_index (자본 배분 효율성 지수 v2.1) - 5,257건

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

### 20-1. company_view_history (기업 조회 기록) - 신규 (2026-01-21)

사용자가 조회한 기업 목록을 저장하여 나중에 다시 볼 수 있도록 함.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| user_id | uuid | NO | FK → users |
| company_id | uuid | NO | FK → companies |
| company_name | varchar(200) | YES | 기업명 스냅샷 |
| ticker | varchar(20) | YES | 종목코드 스냅샷 |
| market | varchar(20) | YES | 시장 스냅샷 |
| viewed_at | timestamp(tz) | NO | 조회 시간 |

**용도**: 유료 회원의 조회한 기업 목록 기능
**인덱스**: `ix_company_view_history_user_viewed` (user_id, viewed_at)
**연관 모델**: `app/models/subscriptions.py` (CompanyViewHistory 클래스)
**연관 API**: `app/routes/view_history.py`

---

## 주가 및 대주주 테이블 (2026-01-14 추가)

### 21. stock_prices (주가 데이터) - 127,324건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| price_date | date | NO | 월말 기준일 (2022-01-31) |
| year_month | varchar(7) | NO | 연월 ("2022-01", 조회 편의) |
| close_price | float | NO | 종가 (원) |
| open_price | float | YES | 시가 (월 시작일) |
| high_price | float | YES | 월중 최고가 |
| low_price | float | YES | 월중 최저가 |
| volume | bigint | YES | 월간 거래량 |
| change_rate | float | YES | 전월 대비 변동률 (%) |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

**연관 모델**: `app/models/stock_prices.py`
**UNIQUE 제약**: company_id + year_month
**데이터 범위**: 2022년 1월 ~ 현재, 상장사만 대상

---

### 22. largest_shareholder_info (최대주주 기본정보) - 4,599건

최대주주가 법인인 경우, 그 법인의 기본정보와 재무현황 저장.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| fiscal_year | integer | NO | 사업연도 |
| report_date | date | YES | 보고일 |
| shareholder_name | varchar(200) | YES | 최대주주명 |
| investor_count | integer | YES | 투자자 수 |
| ceo_name | varchar(100) | YES | 대표자명 |
| ceo_share_ratio | numeric(10,2) | YES | 대표자 지분율 |
| executor_name | varchar(100) | YES | 업무집행자명 |
| executor_share_ratio | numeric(10,2) | YES | 업무집행자 지분율 |
| largest_investor_name | varchar(100) | YES | 최대 출자자명 |
| largest_investor_share_ratio | numeric(10,2) | YES | 최대 출자자 지분율 |
| fin_total_assets | bigint | YES | 총자산 (원) |
| fin_total_liabilities | bigint | YES | 총부채 (원) |
| fin_total_equity | bigint | YES | 총자본 (원) |
| fin_revenue | bigint | YES | 매출액 (원) |
| fin_operating_income | bigint | YES | 영업이익 (원) |
| fin_net_income | bigint | YES | 당기순이익 (원) |
| data_source | varchar(50) | YES | 데이터 출처, 기본값: 'LOCAL_DART' |
| created_at | timestamp | YES | 생성일시 |
| updated_at | timestamp | YES | 수정일시 |

**활용**: 실질 지배구조 파악, 연쇄 리스크 분석, 지배구조 복잡도 측정
**UNIQUE 제약**: company_id + fiscal_year

---

## 뉴스 관계 분석 테이블 (2026-01-14 추가)

⚠️ **안전 설계**: 기존 테이블(companies, officers)에 FK 없음 (소프트 참조). 완전 롤백 가능.

### 23. news_articles (뉴스 기사) - 468건

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| url | varchar(500) | NO | 기사 URL (UNIQUE) |
| title | varchar(500) | NO | 기사 제목 |
| publisher | varchar(100) | YES | 발행사 |
| publish_date | date | YES | 발행일 |
| author | varchar(100) | YES | 저자 |
| summary | text | YES | Claude 분석 요약 |
| raw_content | text | YES | 원문 내용 |
| status | varchar(20) | NO | 상태 (active/archived/deleted), 기본값: 'active' |
| parse_version | varchar(10) | YES | 파싱 버전, 기본값: 'v4' |
| created_at | timestamp(tz) | YES | 생성일시 |
| updated_at | timestamp(tz) | YES | 수정일시 |

**연관 모델**: `app/models/news.py`

---

### 24. news_entities (뉴스 엔티티) - 2,703건

기사에서 추출된 엔티티 (company, person, fund, spc).

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| article_id | uuid | NO | FK → news_articles |
| entity_type | varchar(30) | NO | 엔티티 유형 (company/person/fund/spc) |
| entity_name | varchar(200) | NO | 엔티티명 |
| entity_role | varchar(300) | YES | 기사에서의 역할/설명 |
| matched_company_id | uuid | YES | 매칭된 companies.id (소프트 참조) |
| matched_officer_id | uuid | YES | 매칭된 officers.id (소프트 참조) |
| matched_corp_code | varchar(20) | YES | 매칭된 corp_code |
| match_confidence | numeric(3,2) | YES | 매칭 신뢰도 (0.00~1.00) |
| created_at | timestamp(tz) | YES | 생성일시 |

---

### 25. news_relations (뉴스 관계) - 791건

엔티티 간 관계 정보와 위험 가중치.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| article_id | uuid | NO | FK → news_articles |
| source_entity_id | uuid | NO | FK → news_entities (출발) |
| target_entity_id | uuid | NO | FK → news_entities (도착) |
| relation_type | varchar(50) | NO | 관계 유형 (cb_subscriber, major_shareholder 등) |
| relation_detail | varchar(500) | YES | 상세 설명 |
| relation_period | varchar(100) | YES | 기간 정보 |
| risk_weight | numeric(3,2) | NO | 위험 가중치, 기본값: 1.0 |
| created_at | timestamp(tz) | YES | 생성일시 |

**관계 유형별 위험 가중치**:
| relation_type | risk_weight | 설명 |
|---------------|-------------|------|
| cb_subscriber | 3.0 | CB 인수자 |
| major_shareholder | 2.5 | 대주주 |
| spc_related | 2.5 | SPC 관련 |
| cross_officer | 2.0 | 겸직 임원 |
| fund_related | 2.0 | 펀드 관련 |
| affiliate | 1.5 | 계열사 |
| investor | 1.5 | 투자자 |
| business_partner | 1.0 | 거래처 |

---

### 26. news_risks (뉴스 위험요소) - 1,470건

기사에서 감지된 위험 요소.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| article_id | uuid | NO | FK → news_articles |
| risk_type | varchar(50) | NO | 위험 유형 (governance/financial/operational/legal) |
| description | text | NO | 위험 설명 |
| severity | varchar(20) | NO | 심각도 (low/medium/high/critical), 기본값: 'medium' |
| created_at | timestamp(tz) | YES | 생성일시 |

---

### 27. news_company_complexity (기업 복잡도 스코어) - 0건

뉴스 기반 관계 분석 결과를 집계한 기업별 복잡도 등급.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | 소프트 참조 (companies.id) |
| corp_code | varchar(20) | NO | corp_code |
| complexity_score | numeric(5,2) | NO | 복잡도 점수 (0~100), 기본값: 0 |
| complexity_grade | varchar(5) | NO | 복잡도 등급 (A~F), 기본값: 'A' |
| entity_count | integer | NO | 엔티티 수 |
| relation_count | integer | NO | 관계 수 |
| high_risk_count | integer | NO | 고위험 관계 수 |
| article_count | integer | NO | 관련 기사 수 |
| calculated_at | timestamp(tz) | YES | 계산일시 |

**복잡도 등급 기준**:
| 등급 | 점수 범위 | 설명 |
|------|----------|------|
| A | 0-20 | 단순 |
| B | 20-40 | 보통 |
| C | 40-60 | 복잡 |
| D | 60-80 | 매우 복잡 |
| E | 80-90 | 위험 |
| F | 90-100 | 고위험 |

---

## 앱인토스/토스 관련 테이블 (2026-01-14 추가)

### 28. toss_users (토스 로그인 사용자) - 4건

앱인토스에서 토스 로그인한 사용자 정보.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| toss_user_key | varchar(100) | NO | 토스 사용자 식별자 (UNIQUE) |
| name | varchar(100) | YES | 복호화된 이름 |
| phone | varchar(20) | YES | 복호화된 전화번호 |
| email | varchar(255) | YES | 복호화된 이메일 |
| credits | integer | NO | 이용권 수, 기본값: 0, -1은 무제한 |
| access_token | text | YES | 토스 액세스 토큰 |
| refresh_token | text | YES | 토스 리프레시 토큰 |
| token_expires_at | timestamp(tz) | YES | 토큰 만료일시 |
| is_active | boolean | NO | 활성 여부 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |
| last_login_at | timestamp(tz) | YES | 마지막 로그인 |

**CHECK 제약**: credits >= -1
**연관 모델**: `app/models/toss_users.py`

---

### 29. credit_transactions (이용권 거래 내역) - 16건

이용권 구매, 사용, 환불 등 모든 거래 기록.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| user_id | uuid | NO | FK → toss_users |
| transaction_type | varchar(20) | NO | 거래 유형 (purchase/use/refund/bonus) |
| amount | integer | NO | 금액 (양수: 충전, 음수: 사용) |
| balance_after | integer | NO | 거래 후 잔액 |
| product_id | varchar(50) | YES | 상품 ID (report_1, report_10, report_30) |
| order_id | varchar(100) | YES | 토스 인앱결제 주문 ID |
| payment_amount | integer | YES | 결제 금액 (원) |
| payment_method | varchar(30) | YES | 결제 수단 |
| receipt_data | text | YES | 영수증 데이터 |
| company_id | varchar(20) | YES | 조회한 기업 코드 |
| company_name | varchar(200) | YES | 조회한 기업명 |
| description | varchar(500) | YES | 설명 |
| created_at | timestamp(tz) | NO | 생성일시 |

**UNIQUE 인덱스**: order_id (NULL 제외)

---

### 30. credit_products (이용권 상품) - 3건

이용권 상품 정보.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | varchar(50) | NO | PK (report_1, report_10, report_30) |
| name | varchar(100) | NO | 상품명 |
| credits | integer | NO | 충전되는 이용권 수 |
| price | integer | NO | 가격 (원) |
| badge | varchar(20) | YES | 배지 (추천, 최저가) |
| is_active | boolean | NO | 활성 여부 |
| sort_order | integer | NO | 정렬 순서 |
| toss_sku | varchar(100) | YES | 토스 인앱결제 SKU |
| apple_product_id | varchar(100) | YES | Apple 상품 ID |
| google_product_id | varchar(100) | YES | Google 상품 ID |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

---

### 31. report_views (리포트 조회 기록) - 6건

동일 기업 재조회 시 이용권 중복 차감 방지. 30일 보관 기간 적용.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| user_id | uuid | NO | FK → toss_users |
| company_id | varchar(20) | NO | 기업 코드 (corp_code) |
| company_name | varchar(200) | YES | 기업명 |
| first_viewed_at | timestamp(tz) | NO | 최초 조회일시 |
| last_viewed_at | timestamp(tz) | NO | 마지막 조회일시 |
| view_count | integer | NO | 조회 횟수 |
| expires_at | timestamp(tz) | YES | 만료일 (30일), NULL은 무제한 |

**UNIQUE 인덱스**: user_id + company_id

---

## 파이프라인/서비스 테이블 (2026-01-14 추가)

### 32. pipeline_runs (파이프라인 실행 이력) - 0건

분기 파이프라인 및 배치 작업 실행 이력.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| pipeline_type | varchar(50) | NO | 파이프라인 유형 (quarterly/daily/manual/backfill) |
| quarter | varchar(10) | YES | 분기 (Q1/Q2/Q3/Q4) |
| year | integer | YES | 연도 |
| status | varchar(20) | NO | 상태 (pending/running/completed/failed/cancelled) |
| started_at | timestamp(tz) | YES | 시작일시 |
| completed_at | timestamp(tz) | YES | 완료일시 |
| duration_seconds | integer | YES | 실행 시간 (초) |
| companies_processed | integer | YES | 처리된 기업 수 |
| files_processed | integer | YES | 처리된 파일 수 |
| officers_inserted | integer | YES | 추가된 임원 수 |
| positions_inserted | integer | YES | 추가된 직책 수 |
| errors_count | integer | YES | 오류 수 |
| error_message | text | YES | 오류 메시지 |
| log_file_path | varchar(500) | YES | 로그 파일 경로 |
| metadata | jsonb | YES | 추가 메타데이터 |
| created_at | timestamp(tz) | YES | 생성일시 |
| updated_at | timestamp(tz) | YES | 수정일시 |

**연관 모델**: `app/models/pipeline_run.py`

---

### 33. service_applications (서비스 이용신청) - 1건

수동 입금확인 방식의 엔터프라이즈 서비스 이용신청 관리.

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| user_id | uuid | NO | FK → users |
| applicant_email | varchar(255) | NO | 신청자 이메일 |
| business_registration_file_content | text | YES | 사업자등록증 (Base64) |
| business_registration_file_name | varchar(255) | YES | 파일명 |
| business_registration_mime_type | varchar(50) | YES | MIME 타입 |
| plan_type | varchar(20) | NO | 플랜 (1_MONTH/6_MONTHS/1_YEAR) |
| plan_amount | integer | NO | 금액 (원) |
| status | varchar(20) | NO | 상태, 기본값: 'PENDING' |
| admin_memo | text | YES | 관리자 메모 |
| processed_by | uuid | YES | FK → users (처리자) |
| processed_at | timestamp(tz) | YES | 처리일시 |
| subscription_start_date | date | YES | 구독 시작일 |
| subscription_end_date | date | YES | 구독 종료일 |
| created_at | timestamp(tz) | NO | 생성일시 |
| updated_at | timestamp(tz) | NO | 수정일시 |

**상태 값**: PENDING → PAYMENT_CONFIRMED → APPROVED / REJECTED / CANCELLED
**플랜별 금액**: 1_MONTH=300,000원, 6_MONTHS=1,500,000원, 1_YEAR=3,000,000원

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
| ratios | **financial_ratios** | financial_ 접두사 필요 |
| raymond | **raymonds_index** | raymonds_index 사용 |
| news | **news_articles** | news_articles 사용 |
| toss_user | **toss_users** | 복수형 |
| credit | **credit_transactions** | 전체 이름 사용 |
| pipeline | **pipeline_runs** | _runs 접미사 필요 |

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
                   ├────── (N) financial_details ──── (N) financial_ratios
                   │
                   ├────── (N) financial_ratios
                   │
                   ├────── (N) raymonds_index
                   │
                   ├────── (N) risk_signals
                   │
                   ├────── (N) risk_scores
                   │
                   ├────── (N) major_shareholders
                   │
                   ├────── (N) affiliates
                   │
                   ├────── (N) stock_prices
                   │
                   └────── (N) largest_shareholder_info

users (1) ─────────┬────── (N) user_query_usage
                   │
                   ├────── (N) subscription_payments
                   │
                   ├────── (N) email_verification_tokens
                   │
                   ├────── (N) password_reset_tokens
                   │
                   ├────── (N) service_applications
                   │
                   └────── (N) company_view_history

toss_users (1) ────┬────── (N) credit_transactions
                   │
                   └────── (N) report_views

news_articles (1) ─┬────── (N) news_entities
                   │
                   ├────── (N) news_relations
                   │
                   └────── (N) news_risks

news_entities (1) ─┬────── (N) news_relations (source)
                   │
                   └────── (N) news_relations (target)
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
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'largest_shareholder_info', COUNT(*) FROM largest_shareholder_info
UNION ALL SELECT 'news_articles', COUNT(*) FROM news_articles
UNION ALL SELECT 'news_entities', COUNT(*) FROM news_entities
UNION ALL SELECT 'news_relations', COUNT(*) FROM news_relations
UNION ALL SELECT 'news_risks', COUNT(*) FROM news_risks
UNION ALL SELECT 'toss_users', COUNT(*) FROM toss_users
UNION ALL SELECT 'credit_transactions', COUNT(*) FROM credit_transactions
UNION ALL SELECT 'credit_products', COUNT(*) FROM credit_products
UNION ALL SELECT 'report_views', COUNT(*) FROM report_views
UNION ALL SELECT 'pipeline_runs', COUNT(*) FROM pipeline_runs
UNION ALL SELECT 'service_applications', COUNT(*) FROM service_applications
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
