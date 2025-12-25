# 데이터베이스 스키마 레지스트리

> **중요**: 모든 테이블 접근 시 이 문서 참조 필수. 테이블명 추측 금지.
>
> **마지막 업데이트**: 2025-12-25
>
> **현재 데이터 상태** (2025-12-25):
> - companies: 3,922건
> - officers: 44,679건
> - officer_positions: 64,265건 (중복 제거 완료)
> - disclosures: 213,304건
> - convertible_bonds: 1,463건
> - cb_subscribers: 7,490건
> - financial_statements: 9,432건
> - risk_signals: 1,412건
> - risk_scores: 3,912건
> - major_shareholders: 95,191건
> - affiliates: 973건
> - user_query_usage: - (조회 제한 추적)
> - page_contents: - (페이지 콘텐츠 관리)

---

## 핵심 테이블 목록 (PostgreSQL)

### 1. companies (기업 정보)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| corp_code | varchar | YES | DART 고유 코드 (8자리) |
| ticker | varchar | YES | 종목코드 (6자리) |
| name | varchar | NO | 기업명 (한글) |
| name_en | varchar | YES | 기업명 (영문) |
| market | varchar | YES | 시장 (KOSPI/KOSDAQ/KONEX) |
| listing_status | varchar | YES | 상장상태 |
| sector | varchar | YES | 업종 |
| industry | varchar | YES | 산업분류 |

**연관 스크립트**: -
**주의사항**: corp_code는 DART API 키, ticker는 거래소 코드

---

### 2. officers (임원 정보)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| name | varchar | NO | 임원명 |
| birth_date | varchar | YES | 생년월일 (YYYYMMDD 또는 YYYY.MM.DD) |
| gender | varchar | YES | 성별 |
| current_company_id | uuid | YES | 현재 재직 회사 FK |
| position | varchar | YES | 현재 직책 |
| board_count | integer | YES | 겸직 수 |
| influence_score | double | YES | 영향력 점수 |

**연관 스크립트**: `parse_officers_from_local.py`
**주의사항**: 동일인 판단 = name + birth_date 조합

---

### 3. officer_positions (임원 직책 이력)

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

**연관 스크립트**: `parse_officers_from_local.py`
**중복 판단 기준**: officer_id + company_id + position + birth_date

---

### 4. disclosures (DART 공시)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| rcept_no | varchar | NO | 접수번호 (DART 고유) |
| corp_code | varchar | YES | 기업 코드 (8자리) |
| corp_name | varchar | YES | 기업명 |
| stock_code | varchar | YES | 종목코드 |
| report_nm | varchar | YES | 공시명 |
| rcept_dt | varchar | YES | 접수일 |
| flr_nm | varchar | YES | 공시자명 |
| rm | varchar | YES | 비고 |
| storage_url | varchar | YES | 저장 URL |
| storage_key | varchar | YES | 저장 키 |

**연관 스크립트**: `download_missing_companies.py`
**주의**: company_id 없음, corp_code로 companies와 연결

---

### 5. convertible_bonds (전환사채)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| bond_name | varchar | YES | 사채명 |
| bond_type | varchar | YES | 사채종류 |
| issue_date | date | YES | 발행일 |
| maturity_date | date | YES | 만기일 |
| issue_amount | double | YES | 발행금액 (원) |
| conversion_price | double | YES | 전환가액 (원) |
| conversion_start_date | date | YES | 전환시작일 |
| conversion_end_date | date | YES | 전환종료일 |
| source_disclosure_id | varchar | YES | 출처 공시번호 |
| source_date | varchar | YES | 출처 공시일 |
| use_of_proceeds | text | YES | 자금사용목적 |

**연관 스크립트**: `parse_cb_disclosures.py`
**주의사항**: issue_amount는 원 단위, conversion_price도 원 단위

---

### 6. cb_subscribers (CB 인수자)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| cb_id | uuid | NO | FK → convertible_bonds |
| subscriber_name | varchar | NO | 인수자명 |
| subscriber_type | varchar | YES | 인수자 유형 (법인/개인/펀드 등) |
| is_related_party | varchar | YES | 특수관계인 여부 |
| subscription_amount | double | YES | 인수금액 (원) |
| subscription_quantity | double | YES | 인수수량 |
| subscriber_officer_id | uuid | YES | 임원인 경우 FK |
| subscriber_company_id | uuid | YES | 법인인 경우 FK |

**연관 스크립트**: `parse_cb_disclosures.py`

---

### 7. financial_statements (재무제표)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| year | integer | YES | 사업연도 |
| revenue | double | YES | 매출액 |
| net_income | double | YES | 당기순이익 |

**연관 스크립트**: -

---

### 8. risk_signals (위험 신호)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| signal_type | varchar | YES | 위험 유형 |

---

### 9. risk_scores (위험 점수)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| company_id | uuid | NO | FK → companies |
| score | double | YES | 위험 점수 |

---

### 10. major_shareholders (대주주)

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
| created_at | timestamp | YES | 생성일시 |
| updated_at | timestamp | YES | 수정일시 |

**연관 스크립트**: `/tmp/parse_shareholders_investments_v2.py`
**소스 테이블**: DART XML의 BSH_SPCL (주주에 관한 사항)
**파싱 필드**: SH5_NM_T (성명), SH5_RET (관계), SH5_END_CNT (주식수), SH5_END_RT (지분율)

---

### 11. affiliates (계열사)

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
| created_at | timestamp | NO | 생성일시 |
| updated_at | timestamp | NO | 수정일시 |

**연관 스크립트**: `/tmp/parse_shareholders_investments_v2.py` (ownership_ratio 업데이트)
**소스 테이블**: DART XML의 INV_PRT (타법인출자 현황)
**파싱 필드**: INV_PRM (법인명), INV_YN (상장여부), INV_LPR (기말잔액 기준 지분율)

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

---

## 시스템/유틸리티 테이블

### script_execution_log (스크립트 실행 기록)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | serial | NO | PK |
| script_name | varchar(255) | NO | 실행한 스크립트명 |
| executed_at | timestamp | NO | 실행 시각 |
| table_counts_before | jsonb | YES | 작업 전 테이블 COUNT |
| table_counts_after | jsonb | YES | 작업 후 테이블 COUNT |
| records_added | integer | YES | 추가된 레코드 수 |
| records_deleted | integer | YES | 삭제된 레코드 수 |
| status | varchar(50) | YES | 실행 결과 (success/failed) |
| error_message | text | YES | 에러 메시지 |
| execution_time_seconds | numeric | YES | 실행 시간 (초) |
| notes | text | YES | 비고 |

**용도**: 모든 파싱/데이터 작업 기록 추적

---

## 사용자/콘텐츠 관리 테이블 (2025-12-25 추가)

### user_query_usage (사용자 조회 사용량)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| user_id | uuid | NO | FK → users |
| year_month | varchar(7) | NO | 연월 (YYYY-MM) |
| query_count | integer | NO | 조회 횟수 |
| created_at | timestamp | NO | 생성일시 |
| updated_at | timestamp | NO | 수정일시 |

**용도**: 구독별 월간 조회 제한 추적
**관련 파일**: `backend/app/models/subscriptions.py`, `backend/app/services/usage_service.py`

---

### page_contents (페이지 콘텐츠)

| 컬럼명 | 데이터타입 | NULL | 설명 |
|--------|-----------|------|------|
| id | uuid | NO | PK |
| page | varchar(50) | NO | 페이지명 (about, features 등) |
| section | varchar(50) | NO | 섹션명 (hero, advantage1 등) |
| field | varchar(50) | NO | 필드명 (title, description, image) |
| value | text | YES | 콘텐츠 값 (텍스트 또는 이미지 URL) |
| created_at | timestamp | NO | 생성일시 |
| updated_at | timestamp | NO | 수정일시 |

**용도**: 어드민에서 페이지 콘텐츠 동적 편집
**관련 파일**: `backend/app/models/content.py`, `backend/app/routes/content.py`

---

## 기타 시스템 테이블 (직접 접근 금지)

| 테이블명 | 용도 | 주의사항 |
|----------|------|----------|
| alembic_version | DB 마이그레이션 버전 | 수정 금지 |
| users | 사용자 계정 | 직접 조작 금지 |
| crawl_jobs | 크롤링 작업 | - |
| disclosure_parsed_data | 파싱된 공시 데이터 | - |
| ontology_links | 온톨로지 링크 | - |
| ontology_objects | 온톨로지 객체 | - |

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
                   ├────── (N) risk_signals
                   │
                   ├────── (N) risk_scores
                   │
                   ├────── (N) major_shareholders
                   │
                   └────── (N) affiliates
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
UNION ALL SELECT 'risk_signals', COUNT(*) FROM risk_signals
UNION ALL SELECT 'risk_scores', COUNT(*) FROM risk_scores
UNION ALL SELECT 'major_shareholders', COUNT(*) FROM major_shareholders
UNION ALL SELECT 'affiliates', COUNT(*) FROM affiliates
ORDER BY 1;
```

### 기업별 데이터 커버리지 확인

```sql
-- 임원 데이터 있는 기업 수
SELECT COUNT(DISTINCT company_id) FROM officer_positions;

-- CB 데이터 있는 기업 수
SELECT COUNT(DISTINCT company_id) FROM convertible_bonds;
```
