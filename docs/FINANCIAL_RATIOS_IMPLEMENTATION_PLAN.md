# 재무건전성 평가 시스템 구축 개발 계획

## 1. 현재 상태 분석

### 1.1 기존 구현 현황

| 구성요소 | 상태 | 파일 위치 |
|----------|------|-----------|
| **financial_details 테이블** | ✅ 구현 완료 | `app/models/financial_details.py` |
| **financial_statements 테이블** | ✅ 구현 완료 | `app/models/financial_statements.py` |
| **raymonds_index 테이블** | ✅ 구현 완료 | `app/models/raymonds_index.py` |
| **FinancialParser (v3.0)** | ✅ 구현 완료 | `scripts/parsers/financial.py` |
| **XBRLEnhancer** | ✅ 구현 완료 | `scripts/parsers/xbrl_enhancer.py` |
| **RaymondsIndex Calculator** | ✅ 구현 완료 | `app/services/raymonds_index_calculator.py` |
| **RaymondsIndex API** | ✅ 구현 완료 | `app/api/endpoints/raymonds_index.py` |

### 1.2 기존 `financial_details` 테이블 컬럼 (42개)

**재무상태표 (BS):**
- 유동자산: `current_assets`, `cash_and_equivalents`, `short_term_investments`, `trade_and_other_receivables`, `inventories`, `current_tax_assets`, `other_financial_assets_current`, `other_assets_current`
- 비유동자산: `non_current_assets`, `fvpl_financial_assets`, `investments_in_associates`, `tangible_assets`, `intangible_assets`, `right_of_use_assets`, `net_defined_benefit_assets`, `deferred_tax_assets`, `other_financial_assets_non_current`, `other_assets_non_current`
- 부채: `current_liabilities`, `trade_payables`, `short_term_borrowings`, `current_portion_long_term_debt`, `other_current_liabilities`, `current_tax_liabilities`, `provisions_current`, `non_current_liabilities`, `long_term_borrowings`, `bonds_payable`, `convertible_bonds`, `lease_liabilities`, `deferred_tax_liabilities`, `provisions_non_current`, `other_non_current_liabilities`, `total_liabilities`
- 자본: `total_equity`, `capital_stock`, `capital_surplus`, `retained_earnings`, `treasury_stock`

**손익계산서 (IS):**
- `revenue`, `cost_of_sales`, `selling_admin_expenses`, `operating_income`, `net_income`
- `r_and_d_expense`, `depreciation_expense`, `interest_expense`, `tax_expense`

**현금흐름표 (CF):**
- `operating_cash_flow`, `investing_cash_flow`, `financing_cash_flow`
- `capex`, `intangible_acquisition`, `dividend_paid`, `treasury_stock_acquisition`, `stock_issuance`, `bond_issuance`

### 1.3 프롬프트 요구사항과의 비교

| 프롬프트 요구 항목 | 기존 구현 | 추가 필요 |
|-------------------|----------|----------|
| 자산총계 (`total_assets`) | ✅ | - |
| 유동자산 (`current_assets`) | ✅ | - |
| 현금및현금성자산 (`cash_and_equivalents`) | ✅ | - |
| 단기금융상품 (`short_term_investments`) | ✅ | - |
| 매출채권 (`trade_and_other_receivables`) | ✅ | - |
| 재고자산 (`inventories`) | ✅ | - |
| 유형자산 (`tangible_assets`) | ✅ | - |
| 무형자산 (`intangible_assets`) | ✅ | - |
| 부채총계 (`total_liabilities`) | ✅ | - |
| 유동부채 (`current_liabilities`) | ✅ | - |
| 단기차입금 (`short_term_borrowings`) | ✅ | - |
| 장기차입금 (`long_term_borrowings`) | ✅ | - |
| 사채 (`bonds_payable`) | ✅ | - |
| 자본총계 (`total_equity`) | ✅ | - |
| 자본금 (`capital_stock`) | ✅ | - |
| 이익잉여금 (`retained_earnings`) | ✅ | - |
| 매출액 (`revenue`) | ✅ | - |
| 매출원가 (`cost_of_sales`) | ✅ | - |
| **매출총이익** (`gross_profit`) | ❌ | ✅ 추가 필요 |
| 판관비 (`selling_admin_expenses`) | ✅ | - |
| 영업이익 (`operating_income`) | ✅ | - |
| **이자수익** (`interest_income`) | ❌ | ✅ 추가 필요 |
| 이자비용 (`interest_expense`) | ✅ | - |
| **법인세차감전이익** (`income_before_tax`) | ❌ | ✅ 추가 필요 |
| 법인세비용 (`tax_expense`) | ✅ | - |
| 당기순이익 (`net_income`) | ✅ | - |
| 영업활동현금흐름 (`operating_cash_flow`) | ✅ | - |
| 투자활동현금흐름 (`investing_cash_flow`) | ✅ | - |
| 재무활동현금흐름 (`financing_cash_flow`) | ✅ | - |
| CAPEX (`capex`) | ✅ | - |
| 감가상각비 (`depreciation_expense`) | ✅ | - |
| **무형자산상각비** (`amortization`) | ❌ | ✅ 추가 필요 (depreciation과 통합 가능) |

---

## 2. 신규 구현 항목

### 2.1 신규 테이블: `financial_ratios`

프롬프트에서 요청한 **25개 재무비율**을 저장하는 테이블 신규 생성

```sql
CREATE TABLE financial_ratios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- 기간 정보
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,
    calculation_date TIMESTAMP DEFAULT NOW(),

    -- 원본 데이터 참조
    financial_detail_id UUID REFERENCES financial_details(id),

    -- === 안정성 지표 (Stability) - 6개 ===
    current_ratio DECIMAL(10,2),           -- 유동비율 (%)
    quick_ratio DECIMAL(10,2),             -- 당좌비율 (%)
    debt_ratio DECIMAL(10,2),              -- 부채비율 (%)
    equity_ratio DECIMAL(10,2),            -- 자기자본비율 (%)
    debt_dependency DECIMAL(10,2),         -- 차입금의존도 (%)
    non_current_ratio DECIMAL(10,2),       -- 비유동비율 (%)

    -- === 수익성 지표 (Profitability) - 6개 ===
    operating_margin DECIMAL(10,2),        -- 매출액영업이익률 (%)
    net_profit_margin DECIMAL(10,2),       -- 매출액순이익률 (%)
    roa DECIMAL(10,2),                     -- 총자산순이익률 (%)
    roe DECIMAL(10,2),                     -- 자기자본순이익률 (%)
    gross_margin DECIMAL(10,2),            -- 매출총이익률 (%)
    ebitda_margin DECIMAL(10,2),           -- EBITDA마진 (%)
    ebitda BIGINT,                         -- EBITDA (절대값)

    -- === 성장성 지표 (Growth) - 4개 ===
    revenue_growth DECIMAL(10,2),          -- 매출액증가율 (%)
    operating_income_growth DECIMAL(10,2), -- 영업이익증가율 (%)
    net_income_growth DECIMAL(10,2),       -- 순이익증가율 (%)
    total_assets_growth DECIMAL(10,2),     -- 총자산증가율 (%)

    -- === 활동성 지표 (Activity) - 4개 ===
    asset_turnover DECIMAL(10,2),          -- 총자산회전율 (회)
    receivables_turnover DECIMAL(10,2),    -- 매출채권회전율 (회)
    inventory_turnover DECIMAL(10,2),      -- 재고자산회전율 (회)
    payables_turnover DECIMAL(10,2),       -- 매입채무회전율 (회)
    receivables_days DECIMAL(10,2),        -- 매출채권회수기간 (일)
    inventory_days DECIMAL(10,2),          -- 재고자산보유기간 (일)
    payables_days DECIMAL(10,2),           -- 매입채무지급기간 (일)
    cash_conversion_cycle DECIMAL(10,2),   -- 현금전환주기 (일)

    -- === 현금흐름 지표 (Cash Flow) - 3개 ===
    ocf_ratio DECIMAL(10,2),               -- 영업현금흐름비율 (%)
    ocf_interest_coverage DECIMAL(10,2),   -- 현금흐름이자보상배율 (배)
    free_cash_flow BIGINT,                 -- 잉여현금흐름 (원)
    fcf_margin DECIMAL(10,2),              -- FCF마진 (%)

    -- === 레버리지 지표 (Leverage) - 4개 ===
    interest_coverage DECIMAL(10,2),       -- 이자보상배율 (배)
    ebitda_interest_coverage DECIMAL(10,2),-- EBITDA이자보상배율 (배)
    net_debt_to_ebitda DECIMAL(10,2),      -- 순차입금/EBITDA (배)
    financial_expense_ratio DECIMAL(10,2), -- 금융비용부담률 (%)
    total_borrowings BIGINT,               -- 총차입금 (원)
    net_debt BIGINT,                       -- 순차입금 (원)

    -- === 연속 적자/흑자 정보 ===
    consecutive_loss_quarters INTEGER DEFAULT 0,
    consecutive_profit_quarters INTEGER DEFAULT 0,
    is_loss_making BOOLEAN DEFAULT FALSE,

    -- === 종합 점수 ===
    stability_score DECIMAL(5,2),
    profitability_score DECIMAL(5,2),
    growth_score DECIMAL(5,2),
    activity_score DECIMAL(5,2),
    cashflow_score DECIMAL(5,2),
    leverage_score DECIMAL(5,2),
    financial_health_score DECIMAL(5,2),
    financial_health_grade VARCHAR(5),     -- A++, A+, A, B+, B, B-, C+, C, D
    financial_risk_level VARCHAR(20),      -- LOW, MEDIUM, HIGH, CRITICAL

    -- 메타데이터
    data_completeness DECIMAL(5,2),
    calculation_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(company_id, fiscal_year, fiscal_quarter)
);

CREATE INDEX idx_fr_company ON financial_ratios(company_id);
CREATE INDEX idx_fr_year ON financial_ratios(fiscal_year, fiscal_quarter);
CREATE INDEX idx_fr_health_score ON financial_ratios(financial_health_score);
CREATE INDEX idx_fr_grade ON financial_ratios(financial_health_grade);
```

### 2.2 `financial_details` 테이블 컬럼 추가

기존 테이블에 **4개 컬럼 추가**:

```sql
ALTER TABLE financial_details ADD COLUMN gross_profit BIGINT;           -- 매출총이익
ALTER TABLE financial_details ADD COLUMN interest_income BIGINT;        -- 이자수익
ALTER TABLE financial_details ADD COLUMN income_before_tax BIGINT;      -- 법인세차감전이익
ALTER TABLE financial_details ADD COLUMN amortization BIGINT;           -- 무형자산상각비
```

### 2.3 FinancialParser 키워드 추가

`scripts/parsers/financial.py`의 `ACCOUNT_MAPPING`에 추가:

```python
'gross_profit': [
    '매출총이익', '매출총손익', '매출 총이익',
    'Gross profit', 'Gross income'
],
'interest_income': [
    '이자수익', '이자이익', '금융수익',
    'Interest income', 'Finance income'
],
'income_before_tax': [
    '법인세비용차감전순이익', '법인세차감전순이익', '세전이익',
    '법인세비용차감전계속사업이익', '세전계속사업이익',
    'Income before tax', 'Profit before tax'
],
'amortization': [
    '무형자산상각비', '상각비', '무형자산 상각',
    'Amortization', '무형자산상각'
],
```

---

## 3. 개발 단계별 계획

### Phase 1: 데이터 모델 확장 (백엔드)

**작업 목록:**
1. `financial_details` 모델에 4개 컬럼 추가
2. `financial_ratios` 신규 모델 생성
3. DB 마이그레이션 실행

**파일:**
- `backend/app/models/financial_details.py` - 수정
- `backend/app/models/financial_ratios.py` - 신규
- `backend/app/models/__init__.py` - import 추가

### Phase 2: 파서 확장 (데이터 수집)

**작업 목록:**
1. FinancialParser에 4개 계정과목 키워드 추가
2. `save_to_db()` 쿼리 확장 (신규 컬럼 포함)
3. 재파싱 스크립트 작성

**파일:**
- `backend/scripts/parsers/financial.py` - 수정
- `backend/scripts/maintenance/reparse_financial_details.py` - 수정/신규

### Phase 3: 재무비율 계산기 (핵심)

**작업 목록:**
1. `FinancialRatiosCalculator` 클래스 신규 작성
2. 25개 재무비율 계산 로직 구현
3. 6개 카테고리별 점수 계산
4. 종합 건전성 점수 및 등급 산정

**파일:**
- `backend/app/services/financial_ratios_calculator.py` - 신규
- `backend/scripts/pipeline/calculate_ratios.py` - 신규

### Phase 4: API 엔드포인트 (백엔드)

**작업 목록:**
1. `/api/financial-ratios/{company_id}` - 단일 회사 조회
2. `/api/financial-ratios/{company_id}/history` - 연도별 추이
3. `/api/financial-ratios/ranking` - 건전성 랭킹
4. `/api/financial-ratios/statistics` - 통계

**파일:**
- `backend/app/api/endpoints/financial_ratios.py` - 신규
- `backend/app/main.py` - 라우터 등록

### Phase 5: 프론트엔드 표시

**5.1 RaymondsRisk 웹 (`frontend/`)**
- 기업 상세 페이지에 "재무건전성" 탭 추가
- 재무비율 카드 컴포넌트
- 레이더 차트 (6개 카테고리)

**5.2 RaymondsIndex 웹 (`raymondsindex-web/`)**
- 기업 상세 페이지에 재무비율 섹션 통합
- 스크리너에 재무비율 필터 추가

**5.3 앱인토스 앱 (`raymondsrisk-app/`)**
- ReportPage에 재무건전성 패널 추가
- 모바일 최적화 카드 UI

---

## 4. 재무비율 계산 공식 (프롬프트 기반)

### 4.1 안정성 지표

| 지표 | 계산식 | 양호 | 위험 |
|------|--------|------|------|
| 유동비율 | 유동자산 / 유동부채 × 100 | ≥150% | <100% |
| 당좌비율 | (유동자산 - 재고) / 유동부채 × 100 | ≥100% | <50% |
| 부채비율 | 부채총계 / 자본총계 × 100 | <100% | ≥300% |
| 자기자본비율 | 자본총계 / 자산총계 × 100 | ≥50% | <20% |
| 차입금의존도 | 총차입금 / 자산총계 × 100 | <30% | ≥50% |
| 비유동비율 | 비유동자산 / 자본총계 × 100 | <100% | ≥150% |

### 4.2 수익성 지표

| 지표 | 계산식 | 양호 | 위험 |
|------|--------|------|------|
| 영업이익률 | 영업이익 / 매출액 × 100 | ≥10% | <0% |
| 순이익률 | 당기순이익 / 매출액 × 100 | ≥5% | <0% |
| ROA | 당기순이익 / 자산총계 × 100 | ≥5% | <0% |
| ROE | 당기순이익 / 자본총계 × 100 | ≥10% | <0% |
| 매출총이익률 | 매출총이익 / 매출액 × 100 | ≥20% | <10% |
| EBITDA마진 | EBITDA / 매출액 × 100 | ≥15% | <5% |

### 4.3 성장성 지표

| 지표 | 계산식 | 양호 | 위험 |
|------|--------|------|------|
| 매출성장률 | (당기매출 - 전기매출) / 전기매출 × 100 | ≥10% | <-10% |
| 영업이익성장률 | (당기영업이익 - 전기) / |전기| × 100 | ≥10% | <-20% |
| 순이익성장률 | (당기순이익 - 전기) / |전기| × 100 | ≥10% | <-30% |
| 총자산성장률 | (당기자산 - 전기) / 전기 × 100 | ≥5% | <-5% |

### 4.4 활동성 지표

| 지표 | 계산식 | 양호 | 위험 |
|------|--------|------|------|
| 총자산회전율 | 매출액 / 자산총계 | ≥1.0회 | <0.5회 |
| 매출채권회전율 | 매출액 / 매출채권 | ≥6.0회 | <3.0회 |
| 재고자산회전율 | 매출원가 / 재고자산 | ≥6.0회 | <3.0회 |
| 매입채무회전율 | 매출원가 / 매입채무 | ≥6.0회 | <3.0회 |

### 4.5 현금흐름 지표

| 지표 | 계산식 | 양호 | 위험 |
|------|--------|------|------|
| 영업현금흐름비율 | OCF / 유동부채 × 100 | ≥40% | <10% |
| 현금흐름이자보상 | OCF / 이자비용 | ≥3.0배 | <1.0배 |
| FCF | OCF - CAPEX | >0 | <0 |

### 4.6 레버리지 지표

| 지표 | 계산식 | 양호 | 위험 |
|------|--------|------|------|
| 이자보상배율 | 영업이익 / 이자비용 | ≥3.0배 | <1.0배 |
| EBITDA이자보상 | EBITDA / 이자비용 | ≥5.0배 | <2.0배 |
| 순차입금/EBITDA | (총차입금 - 현금) / EBITDA | <3.0배 | ≥5.0배 |
| 금융비용부담률 | 이자비용 / 매출액 × 100 | <3% | ≥10% |

---

## 5. 기존 RaymondsIndex와의 관계

### 5.1 데이터 소스

| 시스템 | 데이터 소스 | 용도 |
|--------|------------|------|
| **RaymondsIndex** | `financial_details` | 자본 배분 효율성 지수 |
| **Financial Ratios** | `financial_details` | 재무건전성 평가 |

**공통점**: 둘 다 `financial_details` 테이블의 원본 재무 데이터 사용

### 5.2 보완 관계

- **RaymondsIndex**: 자본 배분의 **효율성** 평가 (현금 활용, CAPEX 강도, 투자괴리율)
- **Financial Ratios**: 기업의 **재무건전성** 평가 (유동성, 수익성, 안정성)

두 시스템을 함께 사용하면 기업의 **효율성**과 **건전성**을 종합적으로 평가 가능

### 5.3 API 통합 방안

기업 상세 조회 시 두 데이터를 함께 반환:

```json
{
  "company_id": "...",
  "raymonds_index": {
    "total_score": 75.5,
    "grade": "B+",
    "investment_gap": 15.2
  },
  "financial_ratios": {
    "financial_health_score": 68.3,
    "financial_health_grade": "B",
    "stability": { ... },
    "profitability": { ... }
  }
}
```

---

## 6. 다년간 데이터 처리 전략 (2022-2025)

### 6.1 현재 데이터 현황

| 연도 | financial_details 레코드 | 비고 |
|------|------------------------|------|
| 2022 | 2,413건 | 기준 연도 |
| 2023 | 2,569건 | YoY 계산 가능 |
| 2024 | 2,723건 | YoY 계산 가능 |
| 2025 | 2,221건 | 최신 데이터 |

**결론**: 2022년부터 데이터가 적재되어 있어 **최근 3년간 추이 표시 가능**

### 6.2 성장성 지표 계산 전략

성장성 지표(매출성장률, 영업이익성장률, 순이익성장률, 총자산성장률)는 **전기 데이터**가 필요합니다.

#### 계산 로직
```python
async def calculate_growth_ratios(
    self,
    company_id: UUID,
    current_year: int,
    db: AsyncSession
) -> dict:
    """성장성 지표 계산 - 전기 데이터 조인"""

    # 당기 데이터
    current = await self._get_financial_data(company_id, current_year)

    # 전기 데이터 (1년 전)
    previous = await self._get_financial_data(company_id, current_year - 1)

    if not previous:
        # 전기 데이터 없으면 성장률 계산 불가
        return {
            'revenue_growth': None,
            'operating_income_growth': None,
            'net_income_growth': None,
            'total_assets_growth': None,
            'growth_data_available': False
        }

    # 매출성장률
    revenue_growth = None
    if previous.revenue and previous.revenue != 0:
        revenue_growth = ((current.revenue - previous.revenue) / previous.revenue) * 100

    # 영업이익성장률 (절대값 사용)
    operating_income_growth = None
    if previous.operating_income and previous.operating_income != 0:
        operating_income_growth = (
            (current.operating_income - previous.operating_income)
            / abs(previous.operating_income)
        ) * 100

    # 순이익성장률 (절대값 사용)
    net_income_growth = None
    if previous.net_income and previous.net_income != 0:
        net_income_growth = (
            (current.net_income - previous.net_income)
            / abs(previous.net_income)
        ) * 100

    # 총자산성장률
    total_assets_growth = None
    if previous.total_assets and previous.total_assets != 0:
        total_assets_growth = (
            (current.total_assets - previous.total_assets)
            / previous.total_assets
        ) * 100

    return {
        'revenue_growth': revenue_growth,
        'operating_income_growth': operating_income_growth,
        'net_income_growth': net_income_growth,
        'total_assets_growth': total_assets_growth,
        'growth_data_available': True
    }
```

### 6.3 다년간 추이 API 응답 구조

#### `/api/financial-ratios/{company_id}/history` 응답 예시
```json
{
  "company_id": "uuid",
  "company_name": "삼성전자",
  "history": [
    {
      "fiscal_year": 2022,
      "financial_health_score": 72.5,
      "financial_health_grade": "B+",
      "stability": {
        "current_ratio": 245.3,
        "debt_ratio": 65.2,
        "equity_ratio": 60.5
      },
      "profitability": {
        "operating_margin": 15.2,
        "net_profit_margin": 10.8,
        "roe": 12.5
      },
      "growth": {
        "revenue_growth": null,  // 2021년 데이터 없음
        "data_available": false
      },
      "activity": { ... },
      "cashflow": { ... },
      "leverage": { ... }
    },
    {
      "fiscal_year": 2023,
      "financial_health_score": 68.3,
      "financial_health_grade": "B",
      "growth": {
        "revenue_growth": -8.5,  // 2022년 대비
        "operating_income_growth": -15.2,
        "net_income_growth": -20.1,
        "total_assets_growth": 3.2,
        "data_available": true
      },
      ...
    },
    {
      "fiscal_year": 2024,
      "financial_health_score": 75.1,
      "financial_health_grade": "B+",
      "growth": {
        "revenue_growth": 12.3,  // 2023년 대비
        "operating_income_growth": 25.6,
        "net_income_growth": 30.2,
        "total_assets_growth": 5.1,
        "data_available": true
      },
      ...
    }
  ],
  "trend_summary": {
    "score_trend": "improving",  // improving, stable, declining
    "avg_3y_growth": {
      "revenue": 1.9,
      "operating_income": 5.2
    }
  }
}
```

### 6.4 연속 적자/흑자 계산

```python
async def calculate_consecutive_status(
    self,
    company_id: UUID,
    db: AsyncSession
) -> dict:
    """연속 적자/흑자 분기 수 계산"""

    # 최근 12분기 데이터 조회 (3년)
    query = select(FinancialDetails).where(
        FinancialDetails.company_id == company_id
    ).order_by(
        FinancialDetails.fiscal_year.desc(),
        FinancialDetails.fiscal_quarter.desc().nullsfirst()
    ).limit(12)

    results = await db.execute(query)
    records = results.scalars().all()

    consecutive_loss = 0
    consecutive_profit = 0

    for record in records:
        if record.net_income is not None:
            if record.net_income < 0:
                if consecutive_profit == 0:
                    consecutive_loss += 1
                else:
                    break
            else:
                if consecutive_loss == 0:
                    consecutive_profit += 1
                else:
                    break

    return {
        'consecutive_loss_quarters': consecutive_loss,
        'consecutive_profit_quarters': consecutive_profit,
        'is_loss_making': records[0].net_income < 0 if records else None
    }
```

### 6.5 프론트엔드 추이 차트 명세

#### 3년 추이 차트 컴포넌트
```typescript
// components/FinancialTrendChart.tsx
interface FinancialTrendProps {
  data: {
    fiscal_year: number;
    financial_health_score: number;
    stability_score: number;
    profitability_score: number;
    growth_score: number;
  }[];
}

// 표시 항목
// 1. 종합 건전성 점수 추이 (Line Chart)
// 2. 6개 카테고리 점수 비교 (Grouped Bar Chart)
// 3. 주요 비율 추이 (Multi-line Chart)
//    - 부채비율, 영업이익률, ROE, 매출성장률
```

#### RaymondsIndex 웹 (`raymondsindex-web/`)
- `app/company/[id]/page.tsx`에 3년 추이 섹션 추가
- Recharts `LineChart` + `BarChart` 활용

#### RaymondsRisk 웹 (`frontend/`)
- 기업 상세 페이지에 "재무건전성 추이" 탭 추가
- 연도별 점수 변화 시각화

#### 앱인토스 앱 (`raymondsrisk-app/`)
- 간소화된 추이 카드 (최근 2년 비교)
- 점수 변화 방향 아이콘 (↑ ↓ →)

### 6.6 데이터 검증 쿼리

```sql
-- 3년 연속 데이터 보유 기업 수 확인
SELECT COUNT(DISTINCT company_id) as companies_with_3y_data
FROM (
    SELECT company_id, COUNT(DISTINCT fiscal_year) as year_count
    FROM financial_details
    WHERE fiscal_year BETWEEN 2022 AND 2024
    GROUP BY company_id
    HAVING COUNT(DISTINCT fiscal_year) >= 3
) subq;

-- 결과: 약 2,200+ 기업이 3년 연속 데이터 보유 예상
```

### 6.7 성장성 지표 데이터 가용성 처리

| 연도 | 전기 데이터 | 성장률 계산 | 비고 |
|------|------------|------------|------|
| 2022 | 2021년 없음 | ❌ 불가 | `growth_data_available: false` |
| 2023 | 2022년 있음 | ✅ 가능 | YoY 계산 |
| 2024 | 2023년 있음 | ✅ 가능 | YoY 계산 |
| 2025 | 2024년 있음 | ✅ 가능 | YoY 계산 |

**UI 표시 규칙**:
- 전기 데이터 없는 경우: "데이터 부족" 또는 "-" 표시
- API 응답에 `growth_data_available` 플래그 포함

---

## 7. 예상 소요 기간

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| Phase 1 | 데이터 모델 확장 | 2시간 |
| Phase 2 | 파서 확장 + 재파싱 | 4시간 |
| Phase 3 | 재무비율 계산기 | 6시간 |
| Phase 4 | API 엔드포인트 | 3시간 |
| Phase 5 | 프론트엔드 (3개) | 8시간 |
| **총계** | | **23시간** |

---

## 7. 체크리스트

### Phase 1 체크리스트
- [ ] `financial_details` 모델에 4개 컬럼 추가
- [ ] `financial_ratios` 모델 신규 생성
- [ ] DB 마이그레이션 실행
- [ ] SCHEMA_REGISTRY.md 업데이트

### Phase 2 체크리스트
- [ ] FinancialParser 키워드 추가 (4개)
- [ ] save_to_db 쿼리 수정
- [ ] 테스트 파싱 실행 (샘플 5개 기업)
- [ ] 전체 재파싱 실행

### Phase 3 체크리스트
- [ ] FinancialRatiosCalculator 클래스 구현
- [ ] 25개 비율 계산 로직 구현
- [ ] 6개 카테고리 점수 계산
- [ ] 종합 등급 산정 로직
- [ ] **성장성 지표 전기 데이터 조인 로직 구현**
- [ ] **연속 적자/흑자 계산 로직 구현**
- [ ] **`growth_data_available` 플래그 처리**
- [ ] 테스트 케이스 작성

### Phase 4 체크리스트
- [ ] GET `/api/financial-ratios/{company_id}`
- [ ] GET `/api/financial-ratios/{company_id}/history` **(3년 추이 포함)**
- [ ] GET `/api/financial-ratios/ranking`
- [ ] GET `/api/financial-ratios/statistics`
- [ ] **history API에 `trend_summary` 포함 (score_trend, avg_3y_growth)**
- [ ] **API 응답에 `growth_data_available` 플래그 포함**
- [ ] main.py 라우터 등록
- [ ] Swagger 문서 확인

### Phase 5 체크리스트
- [ ] RaymondsRisk 웹: 재무건전성 탭
- [ ] RaymondsIndex 웹: 기업 상세 섹션
- [ ] 앱인토스: 리포트 패널
- [ ] 레이더 차트 컴포넌트
- [ ] **3년 추이 Line Chart (종합 점수)**
- [ ] **6개 카테고리 Grouped Bar Chart**
- [ ] **주요 비율 Multi-line Chart (부채비율, ROE, 매출성장률)**
- [ ] **전기 데이터 없는 경우 "-" 표시 처리**
- [ ] 모바일 반응형 확인
