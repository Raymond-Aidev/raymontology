# Raymontology 데이터베이스 스키마

> System Requirements Document (SRD) - 버전 1.1 | 최종 수정: 2026-01-24

---

## 1. 데이터베이스 개요

### 1.1 데이터베이스 구성

| 데이터베이스 | 용도 | 엔진 |
|-------------|------|------|
| PostgreSQL | 주 데이터 저장소 | PostgreSQL 15 |
| Neo4j | 그래프 쿼리 (선택) | Neo4j 5.x |

### 1.2 테이블 현황 요약 (43개 테이블)

| 분류 | 테이블 수 | 비고 |
|------|----------|------|
| 기업/임원 | 7 | companies, officers 등 |
| 재무 | 3 | financial_* |
| 리스크 | 4 | risk_*, convertible_bonds 등 |
| RaymondsIndex | 2 | raymonds_index, raymonds_index_v3 |
| 사용자/인증 | 4 | users, tokens 등 |
| 구독/결제 | 3 | subscription_*, user_query_usage |
| 크레딧 (토스) | 3 | credit_*, report_views |
| 뉴스 | 5 | news_* |
| 운영/기타 | 12 | disclosures, stock_prices 등 |

---

## 2. 핵심 테이블

### 2.1 companies (기업)

```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    corp_code VARCHAR(8) UNIQUE NOT NULL,      -- DART 고유번호
    ticker VARCHAR(10),                         -- 종목코드
    name VARCHAR(200) NOT NULL,                 -- 기업명
    english_name VARCHAR(200),                  -- 영문명
    market VARCHAR(20),                         -- KOSPI, KOSDAQ, KONEX
    listing_status VARCHAR(20) DEFAULT 'LISTED', -- LISTED, DELISTED
    company_type VARCHAR(20) DEFAULT 'NORMAL',  -- NORMAL, SPAC, REIT, ETF
    trading_status VARCHAR(20) DEFAULT 'NORMAL', -- NORMAL, SUSPENDED
    is_managed VARCHAR(1) DEFAULT 'N',          -- 관리종목 여부
    sector VARCHAR(100),                        -- 업종
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 3,109건

---

### 2.2 officers (임원)

```sql
CREATE TABLE officers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    birth_year_month VARCHAR(10),
    gender VARCHAR(10),
    career_history JSONB,
    career_raw_text TEXT,
    current_company_id INTEGER REFERENCES companies(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 47,444건

---

### 2.3 officer_positions (임원 직위)

```sql
CREATE TABLE officer_positions (
    id SERIAL PRIMARY KEY,
    officer_id INTEGER REFERENCES officers(id),
    company_id INTEGER REFERENCES companies(id),
    position VARCHAR(100),
    term_start DATE,
    term_end DATE,
    is_current BOOLEAN DEFAULT TRUE,
    source_disclosure_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 62,141건

---

### 2.4 major_shareholders (대주주)

```sql
CREATE TABLE major_shareholders (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    shareholder_name VARCHAR(200) NOT NULL,
    shareholder_type VARCHAR(50),
    share_ratio DECIMAL(10, 4),
    share_count BIGINT,
    is_largest BOOLEAN DEFAULT FALSE,
    report_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 44,574건

---

### 2.5 largest_shareholder_info (최대주주 법인 정보)

```sql
CREATE TABLE largest_shareholder_info (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    shareholder_name VARCHAR(200),
    investor_count INTEGER,
    largest_investor_name VARCHAR(200),
    largest_investor_ratio DECIMAL(10, 4),
    fin_total_assets BIGINT,
    fin_net_income BIGINT,
    report_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 4,599건

---

### 2.6 affiliates (계열사)

```sql
CREATE TABLE affiliates (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    affiliate_name VARCHAR(200) NOT NULL,
    relationship_type VARCHAR(100),
    ownership_ratio DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 864건

---

### 2.7 company_labels (기업 라벨)

```sql
CREATE TABLE company_labels (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    label VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 3. 재무 테이블

### 3.1 financial_statements (재무제표 요약)

```sql
CREATE TABLE financial_statements (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,
    quarter VARCHAR(10),
    revenue BIGINT,
    operating_income BIGINT,
    net_income BIGINT,
    total_assets BIGINT,
    total_equity BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 9,820건

---

### 3.2 financial_details (재무제표 상세 - XBRL)

```sql
CREATE TABLE financial_details (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,
    quarter VARCHAR(10),

    -- 재무상태표
    total_assets BIGINT,
    current_assets BIGINT,
    non_current_assets BIGINT,
    total_liabilities BIGINT,
    total_equity BIGINT,
    retained_earnings BIGINT,

    -- 손익계산서
    revenue BIGINT,
    operating_income BIGINT,
    net_income BIGINT,

    -- 현금흐름표
    cf_operating BIGINT,
    cf_investing BIGINT,
    cf_financing BIGINT,
    capex BIGINT,

    -- 기타
    shares_outstanding BIGINT,
    market_cap BIGINT,

    created_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 10,288건

---

### 3.3 financial_ratios (재무비율)

```sql
CREATE TABLE financial_ratios (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,

    -- 수익성
    roe DECIMAL(10, 4),
    roa DECIMAL(10, 4),
    operating_margin DECIMAL(10, 4),
    net_margin DECIMAL(10, 4),

    -- 안정성
    debt_ratio DECIMAL(10, 4),
    current_ratio DECIMAL(10, 4),

    -- 성장성
    revenue_growth DECIMAL(10, 4),
    net_income_growth DECIMAL(10, 4),

    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. 리스크 테이블

### 4.1 convertible_bonds (전환사채)

```sql
CREATE TABLE convertible_bonds (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    disclosure_id INTEGER,
    issue_date DATE,
    maturity_date DATE,
    issue_amount BIGINT,
    conversion_price INTEGER,
    conversion_ratio DECIMAL(10, 4),
    coupon_rate DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 1,133건

---

### 4.2 cb_subscribers (CB 인수인)

```sql
CREATE TABLE cb_subscribers (
    id SERIAL PRIMARY KEY,
    cb_id INTEGER REFERENCES convertible_bonds(id),
    subscriber_name VARCHAR(200) NOT NULL,
    subscription_amount BIGINT,
    is_related_party BOOLEAN DEFAULT FALSE,
    relationship_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 7,026건

---

### 4.3 risk_signals (리스크 신호)

```sql
CREATE TABLE risk_signals (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    signal_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20),
    description TEXT,
    detected_at TIMESTAMP DEFAULT NOW(),
    data JSONB
);
```

**신호 유형**: CB_EXCESSIVE, CB_RELATED_PARTY, DEFICIT_CONTINUOUS, OFFICER_FREQUENCY, FINANCIAL_DISTRESS

**레코드 수**: 1,412건

---

### 4.4 risk_scores (리스크 점수)

```sql
CREATE TABLE risk_scores (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) UNIQUE,
    total_score INTEGER,
    investment_grade VARCHAR(10),
    cb_score INTEGER,
    financial_score INTEGER,
    governance_score INTEGER,
    calculated_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 3,138건

---

## 5. RaymondsIndex 테이블

### 5.1 raymonds_index (v2)

```sql
CREATE TABLE raymonds_index (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,

    -- 종합 점수
    total_score DECIMAL(10, 4),
    grade VARCHAR(5),

    -- Sub-Index 점수
    cei_score DECIMAL(10, 4),   -- 자본효율성 (20%)
    rii_score DECIMAL(10, 4),   -- 재투자강도 (35%)
    cgi_score DECIMAL(10, 4),   -- 성장건전성 (25%)
    mai_score DECIMAL(10, 4),   -- 시장정렬도 (20%)

    -- 핵심 지표
    roe DECIMAL(10, 4),
    roa DECIMAL(10, 4),
    investment_gap DECIMAL(10, 4),
    retained_earnings_growth DECIMAL(10, 4),
    pbr DECIMAL(10, 4),

    -- 위험 플래그
    has_deficit BOOLEAN DEFAULT FALSE,
    has_negative_equity BOOLEAN DEFAULT FALSE,

    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(company_id, fiscal_year)
);
```

**레코드 수**: 5,257건

---

### 5.2 raymonds_index_v3 (v3)

```sql
CREATE TABLE raymonds_index_v3 (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,

    -- v3 확장 필드
    total_score DECIMAL(10, 4),
    grade VARCHAR(5),

    -- 추가 지표 (v3)
    -- ...

    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(company_id, fiscal_year)
);
```

---

## 6. 사용자/인증 테이블

### 6.1 users (사용자)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(100),
    provider VARCHAR(50),           -- local, google, kakao, naver
    provider_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 6.2 password_reset_tokens (비밀번호 재설정)

```sql
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 6.3 email_verification_tokens (이메일 인증)

```sql
CREATE TABLE email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 6.4 toss_users (토스 사용자)

```sql
CREATE TABLE toss_users (
    id SERIAL PRIMARY KEY,
    toss_user_id VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    access_token TEXT,
    refresh_token TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 7. 구독/결제 테이블

### 7.1 user_query_usage (조회 사용량)

```sql
CREATE TABLE user_query_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    company_id INTEGER REFERENCES companies(id),
    query_type VARCHAR(50),
    queried_at TIMESTAMP DEFAULT NOW()
);
```

---

### 7.2 subscription_payments (결제 내역)

```sql
CREATE TABLE subscription_payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    payment_key VARCHAR(255),
    order_id VARCHAR(255),
    amount INTEGER,
    status VARCHAR(50),
    plan VARCHAR(50),
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 7.3 company_view_history (기업 조회 이력)

```sql
CREATE TABLE company_view_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    company_id INTEGER REFERENCES companies(id),
    viewed_at TIMESTAMP DEFAULT NOW()
);
```

---

## 8. 크레딧 시스템 테이블 (토스)

### 8.1 credit_transactions (크레딧 거래)

```sql
CREATE TABLE credit_transactions (
    id SERIAL PRIMARY KEY,
    toss_user_id INTEGER REFERENCES toss_users(id),
    transaction_type VARCHAR(50),   -- CHARGE, USE, REFUND
    amount INTEGER,
    balance_after INTEGER,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 8.2 report_views (리포트 조회)

```sql
CREATE TABLE report_views (
    id SERIAL PRIMARY KEY,
    toss_user_id INTEGER REFERENCES toss_users(id),
    company_id INTEGER REFERENCES companies(id),
    credit_used INTEGER,
    viewed_at TIMESTAMP DEFAULT NOW()
);
```

---

### 8.3 credit_products (크레딧 상품)

```sql
CREATE TABLE credit_products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price INTEGER NOT NULL,
    credits INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 9. 뉴스 테이블

### 9.1 news_articles (뉴스 기사)

```sql
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    source VARCHAR(100),
    url VARCHAR(500),
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 9.2 news_entities (뉴스 엔티티)

```sql
CREATE TABLE news_entities (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES news_articles(id),
    entity_type VARCHAR(50),    -- COMPANY, PERSON, ORG
    entity_name VARCHAR(200),
    company_id INTEGER REFERENCES companies(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 9.3 news_relations (뉴스 관계)

```sql
CREATE TABLE news_relations (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES news_articles(id),
    source_entity_id INTEGER REFERENCES news_entities(id),
    target_entity_id INTEGER REFERENCES news_entities(id),
    relation_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 9.4 news_risks (뉴스 리스크)

```sql
CREATE TABLE news_risks (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES news_articles(id),
    company_id INTEGER REFERENCES companies(id),
    risk_type VARCHAR(50),
    severity VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 9.5 news_company_complexity (뉴스 기업 복잡도)

```sql
CREATE TABLE news_company_complexity (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    complexity_score DECIMAL(10, 4),
    article_count INTEGER,
    calculated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 10. 운영/기타 테이블

### 10.1 disclosures (공시)

```sql
CREATE TABLE disclosures (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    rcept_no VARCHAR(20) UNIQUE NOT NULL,
    report_nm VARCHAR(500),
    report_type VARCHAR(100),
    rcept_dt DATE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**레코드 수**: 279,258건

---

### 10.2 disclosure_parsed_data (공시 파싱 데이터)

```sql
CREATE TABLE disclosure_parsed_data (
    id SERIAL PRIMARY KEY,
    disclosure_id INTEGER REFERENCES disclosures(id),
    data_type VARCHAR(50),
    parsed_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 10.3 crawl_jobs (크롤링 작업)

```sql
CREATE TABLE crawl_jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50),
    status VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 10.4 stock_prices (주가)

```sql
CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    date DATE NOT NULL,
    open_price INTEGER,
    high_price INTEGER,
    low_price INTEGER,
    close_price INTEGER,
    volume BIGINT,
    market_cap BIGINT,

    UNIQUE(company_id, date)
);
```

**레코드 수**: 126,506건

---

### 10.5 service_applications (서비스 신청)

```sql
CREATE TABLE service_applications (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(200),
    contact_name VARCHAR(100),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    message TEXT,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 10.6 page_contents (페이지 콘텐츠)

```sql
CREATE TABLE page_contents (
    id SERIAL PRIMARY KEY,
    page_key VARCHAR(100) UNIQUE NOT NULL,
    content TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### 10.7 site_settings (사이트 설정)

```sql
CREATE TABLE site_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### 10.8 pipeline_runs (파이프라인 실행)

```sql
CREATE TABLE pipeline_runs (
    id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100),
    status VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    parameters JSONB,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 10.9 script_execution_log (스크립트 실행 로그)

```sql
CREATE TABLE script_execution_log (
    id SERIAL PRIMARY KEY,
    script_name VARCHAR(200),
    status VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    log_output TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 10.10 ontology_objects (온톨로지 객체)

```sql
CREATE TABLE ontology_objects (
    id SERIAL PRIMARY KEY,
    object_type VARCHAR(50) NOT NULL,
    object_id INTEGER NOT NULL,
    properties JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 10.11 ontology_links (온톨로지 관계)

```sql
CREATE TABLE ontology_links (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50),
    source_id INTEGER,
    target_type VARCHAR(50),
    target_id INTEGER,
    link_type VARCHAR(50),
    properties JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 10.12 alembic_version (마이그레이션)

```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(32) PRIMARY KEY
);
```

*시스템 테이블 - 마이그레이션 이력 추적용*

---

## 11. Neo4j 그래프 스키마

### 11.1 노드 유형

| 노드 | 속성 | 레코드 수 |
|------|------|----------|
| Company | id, name, ticker, market | 3,109 |
| Officer | id, name, birth_year_month | 47,444 |
| CB | id, issue_amount, issue_date | 1,133 |
| Subscriber | id, name | 7,026 |

### 11.2 관계 유형

| 관계 | 시작 → 끝 | 속성 |
|------|----------|------|
| WORKS_AT | Officer → Company | position, is_current |
| ISSUED | Company → CB | - |
| SUBSCRIBED | Subscriber → CB | amount, is_related |
| OWNS_SHARES | Shareholder → Company | ratio |

---

## 12. 인덱스 전략

### 12.1 주요 인덱스

```sql
-- 기업 검색
CREATE INDEX idx_companies_name_trgm ON companies USING gin (name gin_trgm_ops);
CREATE INDEX idx_companies_ticker ON companies (ticker);
CREATE INDEX idx_companies_listing_status ON companies (listing_status);

-- 임원 조회
CREATE INDEX idx_officer_positions_company_current
ON officer_positions (company_id, is_current) WHERE is_current = TRUE;

-- 재무 데이터
CREATE INDEX idx_financial_details_company_year ON financial_details (company_id, fiscal_year);

-- RaymondsIndex
CREATE INDEX idx_raymonds_index_grade ON raymonds_index (grade);
CREATE INDEX idx_raymonds_index_score ON raymonds_index (total_score DESC);

-- 공시
CREATE INDEX idx_disclosures_company_id ON disclosures (company_id);
CREATE INDEX idx_disclosures_rcept_dt ON disclosures (rcept_dt);
```

---

## 13. 데이터 무결성 규칙

### 13.1 외래 키 제약

- 모든 `company_id`는 `companies.id` 참조
- `officer_positions.officer_id`는 `officers.id` 참조
- `cb_subscribers.cb_id`는 `convertible_bonds.id` 참조
- `toss_users.user_id`는 `users.id` 참조

### 13.2 유니크 제약

- `companies.corp_code` - DART 고유번호 유일
- `disclosures.rcept_no` - 공시 접수번호 유일
- `raymonds_index(company_id, fiscal_year)` - 기업별 연도별 유일
- `stock_prices(company_id, date)` - 기업별 날짜별 유일

---

## 14. 관련 문서

- [시스템 아키텍처](SRD_Architecture.md)
- [데이터 현황](../data/DATA_STATUS.md)
- [BACKEND README](../apps/backend/README.md)
- [스키마 레지스트리](/backend/scripts/SCHEMA_REGISTRY.md) - **상세 컬럼 정보, 비즈니스 로직, 검증 쿼리 포함**

---

*마지막 업데이트: 2026-01-24*
