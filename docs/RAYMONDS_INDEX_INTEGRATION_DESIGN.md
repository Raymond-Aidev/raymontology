# RaymondsIndex 시스템 통합 설계서

> **버전**: 2.1
> **작성일**: 2025-12-29
> **목적**: RaymondsIndex를 기존 Raymontology 시스템에 안전하게 통합

## v2.1 업데이트 요약

- **Sub-Index 가중치 변경**: CEI 20%, RII 35%, CGI 25%, MAI 20%
- **9단계 등급 체계 (완화)**: A++, A+, A, A-, B+, B, B-, C+, C
- **핵심 신규 지표**: 투자괴리율 v2.1, 유형자산효율성, 현금수익률, 부채/EBITDA, 성장투자비율
- **특별 규칙**: 위반 시 등급 강제 하향 (최대 B- 또는 C+)
- **등급 기준 완화**: A+ 90→88, A 85→80, A- 80→72, B+ 70→64 등

---

## 1. 설계 개요

### 1.1 통합 원칙

```
┌─────────────────────────────────────────────────────────────┐
│                    기존 시스템 보호 원칙                       │
├─────────────────────────────────────────────────────────────┤
│ 1. 기존 테이블 스키마 변경 금지 (financial_statements 등)      │
│ 2. 기존 API 엔드포인트 응답 구조 유지                          │
│ 3. 신규 기능은 별도 모듈로 분리                               │
│ 4. 점진적 통합 (단계별 배포)                                  │
│ 5. 실패해도 기존 서비스에 영향 없음                           │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Raymontology Frontend                        │
├──────────────────────────────┬──────────────────────────────────────┤
│   기존 시스템 (유지)           │   RaymondsIndex (신규)               │
│   ├─ MainSearchPage          │   ├─ RaymondsIndexRankingPage        │
│   ├─ ReportPage              │   ├─ RaymondsIndexCard (위젯)         │
│   ├─ GraphPage               │   ├─ SubIndexChart                   │
│   └─ AdminPage               │   └─ InvestmentGapMeter              │
└──────────────────────────────┴──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Raymontology Backend                         │
├──────────────────────────────┬──────────────────────────────────────┤
│   기존 API (유지)              │   RaymondsIndex API (신규)           │
│   ├─ /api/companies          │   ├─ /api/raymonds-index/{id}        │
│   ├─ /api/report             │   ├─ /api/raymonds-index/ranking     │
│   ├─ /api/risks              │   ├─ /api/raymonds-index/search      │
│   └─ /api/graph              │   └─ /api/raymonds-index/calculate   │
└──────────────────────────────┴──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL Database                          │
├──────────────────────────────┬──────────────────────────────────────┤
│   기존 테이블 (변경 금지)       │   신규 테이블                         │
│   ├─ companies               │   ├─ financial_details (상세 재무)    │
│   ├─ financial_statements    │   └─ raymonds_index (지수 결과)       │
│   ├─ risk_scores             │                                      │
│   └─ convertible_bonds       │                                      │
└──────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. 데이터베이스 스키마

### 2.1 신규 테이블: financial_details

```sql
-- RaymondsIndex용 상세 재무 데이터
-- 기존 financial_statements 테이블과 별도로 관리
CREATE TABLE financial_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,  -- NULL=연간, 1-4=분기
    report_type VARCHAR(20) DEFAULT 'annual',

    -- ═══════════════════════════════════════════════════════════════
    -- 재무상태표 - 유동자산 (Current Assets)
    -- ═══════════════════════════════════════════════════════════════
    current_assets BIGINT,                    -- 유동자산 합계
    cash_and_equivalents BIGINT,              -- 현금및현금성자산
    short_term_investments BIGINT,            -- 단기금융상품
    trade_and_other_receivables BIGINT,       -- 매출채권및기타채권
    inventories BIGINT,                       -- 재고자산
    current_tax_assets BIGINT,                -- 당기법인세자산
    other_financial_assets_current BIGINT,    -- 기타금융자산
    other_assets_current BIGINT,              -- 기타자산

    -- ═══════════════════════════════════════════════════════════════
    -- 재무상태표 - 비유동자산 (Non-Current Assets)
    -- ═══════════════════════════════════════════════════════════════
    non_current_assets BIGINT,                -- 비유동자산 합계
    fvpl_financial_assets BIGINT,             -- 당기손익공정가치측정금융자산
    investments_in_associates BIGINT,         -- 관계기업투자
    tangible_assets BIGINT,                   -- 유형자산
    intangible_assets BIGINT,                 -- 무형자산
    right_of_use_assets BIGINT,               -- 사용권자산
    net_defined_benefit_assets BIGINT,        -- 순확정급여자산
    deferred_tax_assets BIGINT,               -- 이연법인세자산
    other_financial_assets_non_current BIGINT,-- 기타금융자산(비유동)
    other_assets_non_current BIGINT,          -- 기타자산(비유동)

    -- ═══════════════════════════════════════════════════════════════
    -- 재무상태표 - 자산 합계
    -- ═══════════════════════════════════════════════════════════════
    total_assets BIGINT,                -- 자산총계

    -- ═══════════════════════════════════════════════════════════════
    -- 재무상태표 - 유동부채 (Current Liabilities)
    -- ═══════════════════════════════════════════════════════════════
    current_liabilities BIGINT,         -- 유동부채 합계
    trade_payables BIGINT,              -- 매입채무
    short_term_borrowings BIGINT,       -- 단기차입금
    current_portion_long_term_debt BIGINT, -- 유동성장기부채
    other_current_liabilities BIGINT,   -- 기타유동부채
    current_tax_liabilities BIGINT,     -- 당기법인세부채
    provisions_current BIGINT,          -- 유동충당부채

    -- ═══════════════════════════════════════════════════════════════
    -- 재무상태표 - 비유동부채 (Non-Current Liabilities)
    -- ═══════════════════════════════════════════════════════════════
    non_current_liabilities BIGINT,     -- 비유동부채 합계
    long_term_borrowings BIGINT,        -- 장기차입금
    bonds_payable BIGINT,               -- 사채
    convertible_bonds BIGINT,           -- 전환사채
    lease_liabilities BIGINT,           -- 리스부채
    deferred_tax_liabilities BIGINT,    -- 이연법인세부채
    provisions_non_current BIGINT,      -- 비유동충당부채
    other_non_current_liabilities BIGINT, -- 기타비유동부채

    -- ═══════════════════════════════════════════════════════════════
    -- 재무상태표 - 부채/자본 합계
    -- ═══════════════════════════════════════════════════════════════
    total_liabilities BIGINT,           -- 부채총계
    total_equity BIGINT,                -- 자본총계
    capital_stock BIGINT,               -- 자본금
    capital_surplus BIGINT,             -- 자본잉여금
    retained_earnings BIGINT,           -- 이익잉여금
    treasury_stock BIGINT,              -- 자기주식 (음수)

    -- ═══════════════════════════════════════════════════════════════
    -- 손익계산서
    -- ═══════════════════════════════════════════════════════════════
    revenue BIGINT,
    cost_of_sales BIGINT,
    selling_admin_expenses BIGINT,      -- 판매비와관리비 (신규)
    operating_income BIGINT,
    net_income BIGINT,

    -- ═══════════════════════════════════════════════════════════════
    -- 현금흐름표 (RaymondsIndex 핵심)
    -- ═══════════════════════════════════════════════════════════════
    operating_cash_flow BIGINT,
    investing_cash_flow BIGINT,
    financing_cash_flow BIGINT,
    capex BIGINT,                       -- 유형자산의취득 (음수) ⭐ 핵심
    intangible_acquisition BIGINT,      -- 무형자산의취득
    dividend_paid BIGINT,               -- 배당금지급
    treasury_stock_acquisition BIGINT,  -- 자기주식취득
    stock_issuance BIGINT,              -- 주식발행(유상증자)
    bond_issuance BIGINT,               -- 사채발행

    -- ═══════════════════════════════════════════════════════════════
    -- 메타데이터
    -- ═══════════════════════════════════════════════════════════════
    fs_type VARCHAR(10) DEFAULT 'CFS',  -- CFS=연결, OFS=별도
    data_source VARCHAR(50) DEFAULT 'DART',
    source_rcept_no VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_financial_details UNIQUE(company_id, fiscal_year, fiscal_quarter, fs_type)
);

-- 인덱스
CREATE INDEX idx_fd_company ON financial_details(company_id);
CREATE INDEX idx_fd_year ON financial_details(fiscal_year);
CREATE INDEX idx_fd_quarter ON financial_details(fiscal_quarter);
CREATE INDEX idx_fd_fs_type ON financial_details(fs_type);
```

### 2.2 신규 테이블: raymonds_index

```sql
-- RaymondsIndex 계산 결과 저장
CREATE TABLE raymonds_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    calculation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    fiscal_year INTEGER NOT NULL,

    -- ═══════════════════════════════════════════════════════════════
    -- 종합 점수
    -- ═══════════════════════════════════════════════════════════════
    total_score DECIMAL(5,2) NOT NULL,  -- 0-100
    grade VARCHAR(5) NOT NULL,          -- A+, A, B, C, D

    -- ═══════════════════════════════════════════════════════════════
    -- Sub-Index 점수 (각 0-100)
    -- ═══════════════════════════════════════════════════════════════
    cei_score DECIMAL(5,2),  -- Capital Efficiency Index (20%)
    rii_score DECIMAL(5,2),  -- Reinvestment Intensity Index (35%) ⭐ 핵심
    cgi_score DECIMAL(5,2),  -- Cash Governance Index (25%)
    mai_score DECIMAL(5,2),  -- Momentum Alignment Index (20%)

    -- ═══════════════════════════════════════════════════════════════
    -- 핵심 지표
    -- ═══════════════════════════════════════════════════════════════
    investment_gap DECIMAL(6,2),   -- 투자괴리율 (%) = Cash CAGR - CAPEX Growth
    cash_cagr DECIMAL(6,2),        -- 현금 증가율 CAGR (%)
    capex_growth DECIMAL(6,2),     -- CAPEX 증가율 (%)
    idle_cash_ratio DECIMAL(5,2),  -- 유휴현금비율 (%)
    asset_turnover DECIMAL(5,3),   -- 자산회전율 (회)
    reinvestment_rate DECIMAL(5,2),-- 재투자율 (%)
    shareholder_return DECIMAL(5,2),-- 주주환원율 (%)

    -- ═══════════════════════════════════════════════════════════════
    -- 위험 신호
    -- ═══════════════════════════════════════════════════════════════
    red_flags JSONB DEFAULT '[]',     -- 위험 신호 배열
    yellow_flags JSONB DEFAULT '[]',  -- 주의 신호 배열

    -- ═══════════════════════════════════════════════════════════════
    -- v2.0/v2.1 지표
    -- ═══════════════════════════════════════════════════════════════
    investment_gap_v2 DECIMAL(6,2),   -- 투자괴리율 v2 (레거시: 초기2년-최근2년 재투자율)
    investment_gap_v21 DECIMAL(6,2),  -- 투자괴리율 v2.1 ⭐핵심 (현금 CAGR - CAPEX 성장률)
    cash_utilization DECIMAL(5,2),    -- 현금 활용도 (%)
    industry_sector VARCHAR(50),      -- 업종 분류
    weight_adjustment JSONB,          -- 업종별 가중치 조정 내역

    -- ═══════════════════════════════════════════════════════════════
    -- v2.1 신규 지표
    -- ═══════════════════════════════════════════════════════════════
    tangible_efficiency DECIMAL(6,3), -- 유형자산 효율성 (매출/유형자산)
    cash_yield DECIMAL(6,2),          -- 현금 수익률 (영업이익/총현금 %)
    debt_to_ebitda DECIMAL(6,2),      -- 부채/EBITDA
    growth_investment_ratio DECIMAL(5,2), -- 성장 투자 비율 (성장CAPEX/총CAPEX %)

    -- ═══════════════════════════════════════════════════════════════
    -- 해석
    -- ═══════════════════════════════════════════════════════════════
    verdict VARCHAR(200),        -- 한 줄 요약
    key_risk TEXT,               -- 핵심 리스크 설명
    recommendation TEXT,         -- 투자자 권고
    watch_trigger TEXT,          -- 재검토 시점

    -- ═══════════════════════════════════════════════════════════════
    -- 메타데이터
    -- ═══════════════════════════════════════════════════════════════
    data_quality_score DECIMAL(3,2),  -- 데이터 품질 점수 (0-1)
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_raymonds_index UNIQUE(company_id, fiscal_year)
);

-- 인덱스
CREATE INDEX idx_ri_company ON raymonds_index(company_id);
CREATE INDEX idx_ri_year ON raymonds_index(fiscal_year);
CREATE INDEX idx_ri_score ON raymonds_index(total_score);
CREATE INDEX idx_ri_grade ON raymonds_index(grade);
CREATE INDEX idx_ri_investment_gap ON raymonds_index(investment_gap);
```

---

## 3. 백엔드 API 설계

### 3.1 파일 구조

```
backend/app/
├── api/endpoints/
│   ├── raymonds_index.py          # 신규: RaymondsIndex API
│   └── company_report.py          # 수정: raymonds_index 필드 추가
├── models/
│   ├── financial_details.py       # 신규: 상세 재무 모델
│   └── raymonds_index.py          # 신규: RaymondsIndex 모델
├── services/
│   ├── dart_financial_parser.py   # 신규: DART 재무 파서
│   └── raymonds_index_calculator.py # 신규: 계산 엔진
└── main.py                        # 수정: 라우터 등록

backend/scripts/
├── collect_financial_details.py   # 신규: 재무 데이터 수집
└── calculate_raymonds_index.py    # 신규: 배치 계산
```

### 3.2 API 엔드포인트

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RaymondsIndex API Endpoints                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  GET /api/raymonds-index/{company_id}                               │
│  ├─ 응답: 단일 회사의 최신 RaymondsIndex                             │
│  └─ 쿼리: ?year=2024 (특정 연도 조회)                                │
│                                                                      │
│  GET /api/raymonds-index/{company_id}/history                       │
│  └─ 응답: 해당 회사의 연도별 RaymondsIndex 추이                       │
│                                                                      │
│  GET /api/raymonds-index/ranking                                    │
│  ├─ 응답: 전체 랭킹 목록                                             │
│  ├─ 쿼리: ?sort=score_desc|investment_gap_asc                       │
│  ├─ 쿼리: ?grade=A+,A,B                                             │
│  └─ 쿼리: ?limit=50&offset=0                                        │
│                                                                      │
│  GET /api/raymonds-index/search                                     │
│  ├─ 응답: 조건부 검색 결과                                           │
│  ├─ 쿼리: ?min_score=60&max_score=100                               │
│  ├─ 쿼리: ?investment_gap_min=-10&investment_gap_max=10             │
│  └─ 쿼리: ?has_red_flags=false                                      │
│                                                                      │
│  POST /api/raymonds-index/{company_id}/calculate (관리자 전용)       │
│  └─ 특정 회사의 RaymondsIndex 재계산                                 │
│                                                                      │
│  GET /api/raymonds-index/statistics                                 │
│  └─ 전체 통계 (평균, 분포, 등급별 비율)                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 기존 API 확장 (최소 변경)

```python
# company_report.py 수정 - 기존 응답 구조 유지하면서 필드 추가

class CompanyFullReport(BaseModel):
    """회사 종합 보고서 - 기존 필드 유지"""
    basic_info: CompanyBasicInfo
    disclosure_count: int
    risk_score: Optional[RiskScoreInfo]
    risk_signals: List[RiskSignalInfo]
    convertible_bonds: List[CBInfo]
    cb_subscribers: List[CBSubscriberInfo]
    officers: List[OfficerInfo]
    financials: List[FinancialInfo]
    shareholders: List[ShareholderInfo]
    affiliates: List[AffiliateInfo]
    summary: Dict[str, Any]

    # ═══════════════════════════════════════════════════════════════
    # 신규 필드 (Optional - 기존 클라이언트 호환성 유지)
    # ═══════════════════════════════════════════════════════════════
    raymonds_index: Optional[RaymondsIndexInfo] = None  # 신규
```

---

## 4. RaymondsIndex 계산 로직

### 4.1 Sub-Index 구성 (v2.1)

```
┌─────────────────────────────────────────────────────────────────────┐
│                   RaymondsIndex v2.1 구성 (100점 만점)               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ CEI: Capital Efficiency Index (20%)                            │ │
│  │ ├─ 자산회전율 (Revenue / Total Assets) [25%]                   │ │
│  │ ├─ 유형자산 효율성 (Revenue / Tangible Assets) [20%]           │ │
│  │ ├─ 현금 수익률 (Operating Income / Cash) [20%]                 │ │
│  │ ├─ ROIC (투하자본수익률) [25%]                                 │ │
│  │ └─ 효율성 추세 (자산회전율 추세 분석) [10%]                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ RII: Reinvestment Intensity Index (35%) ⭐ 핵심                 │ │
│  │ ├─ CAPEX 강도 (CAPEX / Revenue) [30%]                          │ │
│  │ ├─ 투자괴리율 v2.1 (현금 CAGR - CAPEX 성장률) [30%] ⭐ 핵심    │ │
│  │ ├─ 재투자율 (CAPEX / OCF) [25%]                                │ │
│  │ └─ 투자 지속성 (CAPEX 변동계수) [15%]                          │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ CGI: Cash Governance Index (25%)                                │ │
│  │ ├─ 현금 활용도 (CAPEX+배당+자사주매입)/(현금+OCF) [20%]        │ │
│  │ ├─ 조달자금 투자전환율 (%) [25%]                               │ │
│  │ ├─ 주주환원 균형 (20-50% 적정) [20%]                           │ │
│  │ ├─ 현금 적정성 (유휴현금 10-20% 적정) [15%]                    │ │
│  │ └─ 부채 건전성 (Debt/EBITDA) [20%] ⭐ 신규                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ MAI: Momentum Alignment Index (20%)                            │ │
│  │ ├─ 매출-투자 동조성 (Revenue Growth ↔ CAPEX Growth) [30%]      │ │
│  │ ├─ 이익 품질 (Operating CF / Net Income) [25%]                 │ │
│  │ ├─ 투자 지속성 (CAPEX 추세 분석) [20%]                         │ │
│  │ ├─ 성장 투자 비율 (성장CAPEX / 총CAPEX) [15%] ⭐ 신규          │ │
│  │ └─ FCF 추세 (Free Cash Flow 추세) [10%]                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 등급 체계 (v2.1 - 9단계, 완화)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         v2.1 등급 기준 (완화됨)                       │
├─────────┬───────────┬───────────────────────────────────────────────┤
│ 등급    │ 점수 범위  │ 해석                                          │
├─────────┼───────────┼───────────────────────────────────────────────┤
│ A++     │ 95-100    │ 투자금을 성실히 사업에 활용하는 모범 기업       │
│ A+      │ 88-94     │ 투자금 활용이 우수한 기업                       │
│ A       │ 80-87     │ 투자금 활용이 양호한 기업                       │
│ A-      │ 72-79     │ 대체로 양호하나 일부 점검 필요                  │
│ B+      │ 64-71     │ 투자금 활용 현황 지속 관찰 필요                 │
│ B       │ 55-63     │ 투자금 활용에 의문점 발생                       │
│ B-      │ 45-54     │ 투자금 유용 가능성 경고                         │
│ C+      │ 30-44     │ 투자금 배임 가능성 높음                         │
│ C       │ 0-29      │ 투자금 배임 의심 - 투자 부적격                  │
└─────────┴───────────┴───────────────────────────────────────────────┘
```

**v2.1 등급 기준 변경 사항** (v4.0 설계 대비):
- A+ 기준: 90점 → 88점
- A 기준: 85점 → 80점
- A- 기준: 80점 → 72점
- B+ 기준: 70점 → 64점
- B 기준: 60점 → 55점
- B- 기준: 50점 → 45점
- C+ 기준: 40점 → 30점

### 4.3 특별 규칙 (v2.1)

```
┌─────────────────────────────────────────────────────────────────────┐
│                       특별 규칙 (등급 강제 하향)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  규칙 1: 현금-유형자산 비율 > 30:1                                  │
│  └─ 현금만 쌓고 투자를 안 함 → 최대 B-                              │
│                                                                      │
│  규칙 2: 조달자금 전환율 < 30%                                      │
│  └─ 유상증자/CB 발행 후 투자 미사용 → 최대 B-                       │
│                                                                      │
│  규칙 3: 단기금융상품비율 > 65% + CAPEX 감소                        │
│  └─ 이자놀이 + 투자 축소 콤보 → 최대 B                              │
│                                                                      │
│  복합 위반: 위 조건 2개 이상 해당 → 최대 C+                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Red/Yellow Flags

```python
# 자동 생성되는 위험 신호

RED_FLAGS = {
    "CASH_HOARDING": {
        "condition": "investment_gap > 15",
        "message": "현금 과다 축적: 3년간 현금증가율이 CAPEX 증가율 대비 15%p 이상"
    },
    "ZERO_CAPEX": {
        "condition": "capex_growth < -50",
        "message": "투자 급감: CAPEX가 전년 대비 50% 이상 감소"
    },
    "NEGATIVE_OPERATING_CF": {
        "condition": "operating_cash_flow < 0 for 2+ years",
        "message": "영업현금흐름 적자 지속"
    }
}

YELLOW_FLAGS = {
    "HIGH_IDLE_CASH": {
        "condition": "idle_cash_ratio > 30",
        "message": "유휴현금 30% 이상: 자금 활용 효율성 점검 필요"
    },
    "LOW_REINVESTMENT": {
        "condition": "reinvestment_rate < 20",
        "message": "재투자율 20% 미만: 성장 투자 부족 가능성"
    },
    "DECLINING_TURNOVER": {
        "condition": "asset_turnover declining 2+ years",
        "message": "자산회전율 2년 연속 하락"
    }
}
```

---

## 5. 프론트엔드 설계

### 5.1 파일 구조

```
frontend/src/
├── components/RaymondsIndex/
│   ├── RaymondsIndexCard.tsx      # 점수 카드 위젯
│   ├── SubIndexRadar.tsx          # 레이더 차트 (4개 Sub-Index)
│   ├── InvestmentGapMeter.tsx     # 투자괴리율 게이지
│   ├── RiskFlagsPanel.tsx         # Red/Yellow Flag 표시
│   ├── RaymondsIndexHistory.tsx   # 연도별 추이 차트
│   └── index.ts                   # 배럴 export
├── pages/
│   └── RaymondsIndexRankingPage.tsx # 랭킹 페이지
├── api/
│   └── raymondsIndex.ts           # API 호출 함수
├── hooks/
│   └── useRaymondsIndex.ts        # 커스텀 훅
└── types/
    └── raymondsIndex.ts           # 타입 정의
```

### 5.2 컴포넌트 설계

```tsx
// RaymondsIndexCard.tsx - 핵심 위젯
interface RaymondsIndexCardProps {
  score: number           // 0-100
  grade: string           // A+, A, B, C, D
  investmentGap: number   // 투자괴리율 (%)
  redFlags: string[]      // 위험 신호
  yellowFlags: string[]   // 주의 신호
  compact?: boolean       // ReportPage 내 삽입용 컴팩트 모드
}

// SubIndexRadar.tsx - 레이더 차트
interface SubIndexRadarProps {
  cei: number   // Capital Efficiency
  rii: number   // Reinvestment Intensity
  cgi: number   // Cash Governance
  mai: number   // Momentum Alignment
}

// InvestmentGapMeter.tsx - 핵심 지표 게이지
interface InvestmentGapMeterProps {
  gap: number           // -50 ~ +50 범위
  cashGrowth: number    // 현금 CAGR
  capexGrowth: number   // CAPEX 증가율
}
```

### 5.3 ReportPage 통합

```tsx
// ReportPage.tsx 수정 - 기존 구조 유지하면서 섹션 추가

return (
  <div className="max-w-6xl mx-auto">
    {/* 기존 섹션들 유지 */}
    <RiskDashboard ... />
    <DataTabs ... />

    {/* ═══════════════════════════════════════════════════════════ */}
    {/* 신규: RaymondsIndex 섹션 (Optional - 데이터 있을 때만 표시) */}
    {/* ═══════════════════════════════════════════════════════════ */}
    {reportData.raymonds_index && (
      <div className="mt-6">
        <h2 className="text-lg font-bold mb-4">자본 배분 효율성 (RaymondsIndex)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <RaymondsIndexCard
            score={reportData.raymonds_index.total_score}
            grade={reportData.raymonds_index.grade}
            investmentGap={reportData.raymonds_index.investment_gap}
            redFlags={reportData.raymonds_index.red_flags}
            yellowFlags={reportData.raymonds_index.yellow_flags}
          />
          <SubIndexRadar
            cei={reportData.raymonds_index.cei_score}
            rii={reportData.raymonds_index.rii_score}
            cgi={reportData.raymonds_index.cgi_score}
            mai={reportData.raymonds_index.mai_score}
          />
        </div>
        <InvestmentGapMeter
          gap={reportData.raymonds_index.investment_gap}
          cashGrowth={reportData.raymonds_index.cash_cagr}
          capexGrowth={reportData.raymonds_index.capex_growth}
        />
      </div>
    )}
  </div>
)
```

---

## 6. 데이터 수집 전략

### 6.1 DART API 활용

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DART API 데이터 수집 전략                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  API: fnlttSinglAcnt (단일회사 전체 재무제표)                        │
│                                                                      │
│  수집 대상:                                                          │
│  ├─ 대상 기업: 3,922개 상장사                                       │
│  ├─ 수집 기간: 2022-2024 (3개년)                                    │
│  ├─ 총 요청 건수: 약 11,766건                                       │
│  └─ 예상 소요시간: 4-5시간                                          │
│                                                                      │
│  Rate Limiting:                                                      │
│  ├─ DART 제한: 분당 1,000건                                         │
│  ├─ 안전 마진: 분당 500건으로 설정                                  │
│  └─ 동시 요청: 5개                                                  │
│                                                                      │
│  계정과목 매핑:                                                      │
│  ├─ 현금및현금성자산 → ['현금및현금성자산', '현금및현금등가물']      │
│  ├─ 유형자산의취득 → ['유형자산의 취득', '유형자산의취득']           │
│  └─ 영업활동현금흐름 → ['영업활동현금흐름', '영업활동으로인한현금흐름'] │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 수집 스크립트 설계

```python
# collect_financial_details.py 의사코드

async def main():
    # 1. 상장사 목록 조회
    companies = await get_all_companies()

    # 2. 연도별 수집
    for year in [2022, 2023, 2024]:
        for batch in chunked(companies, 100):
            tasks = [
                fetch_financial_details(company, year)
                for company in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 3. DB 저장 (upsert)
            await upsert_financial_details(results)

            # 4. Rate limiting
            await asyncio.sleep(12)  # 100건 / 500rpm ≈ 12초

            # 5. 진행상황 로깅
            logger.info(f"Processed {len(processed)}/{total_companies}")
```

---

## 7. 배포 전략

### 7.1 단계별 배포

```
┌─────────────────────────────────────────────────────────────────────┐
│                    단계별 배포 계획                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Phase 1: 인프라 (Day 1)                                            │
│  ├─ DB 테이블 생성 (financial_details, raymonds_index)              │
│  ├─ 기존 서비스 영향 없음 확인                                       │
│  └─ 롤백 계획 준비                                                  │
│                                                                      │
│  Phase 2: 데이터 수집 (Day 1-2)                                     │
│  ├─ DART 파서 배포                                                  │
│  ├─ 배치 수집 실행 (약 5시간)                                       │
│  └─ 데이터 품질 검증                                                │
│                                                                      │
│  Phase 3: 계산 엔진 (Day 2)                                         │
│  ├─ 계산 로직 배포                                                  │
│  ├─ 배치 계산 실행                                                  │
│  └─ 결과 검증 (샘플링)                                              │
│                                                                      │
│  Phase 4: API (Day 2-3)                                             │
│  ├─ RaymondsIndex API 배포                                          │
│  ├─ company_report API 확장                                         │
│  └─ API 테스트                                                      │
│                                                                      │
│  Phase 5: 프론트엔드 (Day 3)                                        │
│  ├─ 컴포넌트 배포                                                   │
│  ├─ ReportPage 통합                                                 │
│  ├─ RankingPage 배포                                                │
│  └─ E2E 테스트                                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 롤백 계획

```sql
-- 롤백 시 실행 (기존 시스템에 영향 없음)
DROP TABLE IF EXISTS raymonds_index;
DROP TABLE IF EXISTS financial_details;

-- 프론트엔드: raymonds_index 필드가 null이면 섹션 숨김 (이미 설계됨)
```

---

## 8. 테스트 전략

### 8.1 단위 테스트

```python
# tests/test_raymonds_index_calculator.py

def test_cei_calculation():
    """CEI 계산 테스트"""

def test_rii_calculation():
    """RII (핵심) 계산 테스트"""

def test_investment_gap():
    """투자괴리율 계산 테스트"""

def test_grade_assignment():
    """등급 부여 테스트"""

def test_red_flags_generation():
    """Red Flag 자동 생성 테스트"""
```

### 8.2 통합 테스트

```python
# tests/test_raymonds_index_api.py

async def test_get_raymonds_index():
    """단일 회사 조회 테스트"""

async def test_ranking_api():
    """랭킹 API 테스트"""

async def test_report_integration():
    """기존 Report API와 통합 테스트"""
```

### 8.3 E2E 테스트

```typescript
// cypress/e2e/raymonds-index.cy.ts

describe('RaymondsIndex', () => {
  it('ReportPage에서 RaymondsIndex 표시', () => {
    cy.visit('/company/삼성전자/report')
    cy.get('[data-testid="raymonds-index-card"]').should('be.visible')
  })

  it('RankingPage 접근 및 정렬', () => {
    cy.visit('/raymonds-index/ranking')
    cy.get('[data-testid="ranking-table"]').should('be.visible')
  })
})
```

---

## 9. 모니터링

### 9.1 주요 지표

```
┌─────────────────────────────────────────────────────────────────────┐
│                    모니터링 지표                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  데이터 품질:                                                        │
│  ├─ financial_details 수집 완료율 (목표: 95%)                        │
│  ├─ raymonds_index 계산 완료율 (목표: 90%)                           │
│  └─ 데이터 품질 점수 분포                                            │
│                                                                      │
│  API 성능:                                                           │
│  ├─ /api/raymonds-index 응답시간 (목표: <500ms)                      │
│  ├─ /api/report 응답시간 증가량 (목표: <100ms 증가)                   │
│  └─ 에러율 (목표: <1%)                                               │
│                                                                      │
│  사용량:                                                             │
│  ├─ RaymondsIndex 조회 수                                            │
│  ├─ RankingPage 방문 수                                              │
│  └─ 검색 쿼리 패턴                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. 기존 시스템과의 관계

### 10.1 데이터 연동

```
┌─────────────────────────────────────────────────────────────────────┐
│                    데이터 연동 관계                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  기존 테이블 → RaymondsIndex (읽기 전용)                            │
│                                                                      │
│  companies                                                           │
│    └─→ company_id (FK)                                              │
│                                                                      │
│  convertible_bonds (참조만, 수정 안 함)                              │
│    └─→ CB 발행 = 자금조달 패턴 분석용                               │
│                                                                      │
│  risk_scores (참조만, 수정 안 함)                                    │
│    └─→ 기존 리스크 점수와 교차 분석용                                │
│                                                                      │
│  financial_statements (참조만, 수정 안 함)                           │
│    └─→ 일부 데이터 검증용 (중복 저장은 financial_details에)          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.2 기존 시스템 영향도

```
┌─────────────────────────────────────────────────────────────────────┐
│                    기존 시스템 영향 분석                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ✅ 영향 없음:                                                       │
│  ├─ companies 테이블                                                │
│  ├─ financial_statements 테이블                                     │
│  ├─ risk_scores 테이블                                              │
│  ├─ 기존 모든 API 엔드포인트                                        │
│  ├─ MainSearchPage                                                  │
│  └─ GraphPage                                                       │
│                                                                      │
│  🔄 수정 필요 (최소):                                                │
│  ├─ company_report.py: Optional 필드 추가                           │
│  ├─ main.py: 라우터 등록 1줄 추가                                   │
│  ├─ ReportPage.tsx: 조건부 섹션 추가                                │
│  └─ App.tsx: 라우트 1개 추가                                        │
│                                                                      │
│  ➕ 신규 추가:                                                       │
│  ├─ 2개 DB 테이블                                                   │
│  ├─ 2개 모델 파일                                                   │
│  ├─ 2개 서비스 파일                                                 │
│  ├─ 1개 API 라우터                                                  │
│  ├─ 5개 컴포넌트                                                    │
│  └─ 1개 페이지                                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 11. 체크리스트

### 11.1 구현 전 체크리스트

- [ ] DART API 키 확인 및 Rate Limit 테스트
- [ ] 로컬 개발 환경에서 테이블 생성 테스트
- [ ] 샘플 기업 10개로 데이터 수집 테스트
- [ ] 계산 로직 수동 검증 (엑셀 대조)

### 11.2 배포 전 체크리스트

- [ ] 프로덕션 DB 백업
- [ ] 기존 API 응답 스냅샷 저장
- [ ] 롤백 스크립트 준비
- [ ] 모니터링 대시보드 설정

### 11.3 배포 후 체크리스트

- [ ] 기존 /api/report 응답 시간 확인
- [ ] 기존 페이지 정상 동작 확인
- [ ] RaymondsIndex 데이터 샘플링 검증
- [ ] 에러 로그 모니터링

---

## 12. 결론

RaymondsIndex는 **기존 시스템에 영향 없이** 별도 모듈로 추가됩니다:

1. **신규 테이블 2개**: `financial_details`, `raymonds_index`
2. **신규 API 1개**: `/api/raymonds-index/*`
3. **기존 API 최소 수정**: Optional 필드 추가
4. **프론트엔드 조건부 표시**: 데이터 있을 때만 섹션 표시

이 설계를 기반으로 `/sc:implement`를 통해 단계별 구현을 진행할 수 있습니다.

---

**다음 단계**: `/sc:implement Phase 1 - DB 스키마 생성`
