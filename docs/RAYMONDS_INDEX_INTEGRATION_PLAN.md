# RaymondsIndex 통합 개발 계획서

## Claude Code / Superclaude 실행용 개발 명세

**버전**: 1.1  
**작성일**: 2025-12-25  
**변경**: 데이터 수집 기간 2022-2024 (3개년)  
**목적**: Raymontology 시스템에 RaymondsIndex(자본 배분 효율성 지수) 통합

---

## 1. 현재 시스템 분석

### 1.1 기존 데이터 구조 (활용 가능)

| 테이블 | 레코드 | RaymondsIndex 활용 |
|--------|--------|-------------------|
| companies | 3,922 | 기업 기본정보 ✅ |
| financial_statements | 9,432 | 재무데이터 일부 ✅ |
| risk_scores | 3,912 | 기존 리스크 점수 연동 ✅ |
| convertible_bonds | 1,435 | CB 발행 = 자금조달 ✅ (2022-2025) |

### 1.2 추가 필요 데이터 (DART 파싱 필요)

| 항목 | 현재 | 필요 | 출처 |
|------|------|------|------|
| 현금및현금성자산 | ❌ | ✅ | 재무상태표 |
| 단기금융상품 | ❌ | ✅ | 재무상태표 |
| 유형자산 | ❌ | ✅ | 재무상태표 |
| 유형자산의취득 (CAPEX) | ❌ | ✅ | 현금흐름표 |
| 영업활동현금흐름 | ❌ | ✅ | 현금흐름표 |

### 1.3 데이터 수집 기간

| 항목 | 값 |
|------|-----|
| **수집 기간** | 2022년 ~ 2024년 (3개년) |
| **기존 CB 데이터** | 2022-2025 (동일 기간) |
| **총 수집 건수** | 3,922사 × 3년 = **11,766건** |
| **예상 소요시간** | 약 4-5시간 |

---

## 2. 데이터베이스 스키마 확장

### Phase 1: 테이블 생성

```bash
# Claude Code 명령어
claude "PostgreSQL에 RaymondsIndex용 테이블 생성해줘. 
다음 스키마로 만들어:

-- 상세 재무 데이터 (현금흐름표 포함)
CREATE TABLE financial_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,  -- NULL이면 연간
    report_type VARCHAR(20),  -- 'annual', 'semi', 'quarter'
    
    -- 재무상태표
    cash_and_equivalents BIGINT,        -- 현금및현금성자산
    short_term_investments BIGINT,      -- 단기금융상품
    trade_receivables BIGINT,           -- 매출채권
    inventories BIGINT,                 -- 재고자산
    tangible_assets BIGINT,             -- 유형자산
    intangible_assets BIGINT,           -- 무형자산
    total_assets BIGINT,                -- 자산총계
    current_liabilities BIGINT,         -- 유동부채
    non_current_liabilities BIGINT,     -- 비유동부채
    total_liabilities BIGINT,           -- 부채총계
    total_equity BIGINT,                -- 자본총계
    
    -- 손익계산서
    revenue BIGINT,                     -- 매출액
    cost_of_sales BIGINT,               -- 매출원가
    selling_admin_expenses BIGINT,      -- 판매비와관리비
    operating_income BIGINT,            -- 영업이익
    net_income BIGINT,                  -- 당기순이익
    
    -- 현금흐름표
    operating_cash_flow BIGINT,         -- 영업활동현금흐름
    investing_cash_flow BIGINT,         -- 투자활동현금흐름
    financing_cash_flow BIGINT,         -- 재무활동현금흐름
    capex BIGINT,                       -- 유형자산의취득 (음수)
    intangible_acquisition BIGINT,      -- 무형자산의취득
    dividend_paid BIGINT,               -- 배당금지급
    treasury_stock_acquisition BIGINT,  -- 자기주식취득
    stock_issuance BIGINT,              -- 주식발행(유상증자)
    bond_issuance BIGINT,               -- 사채발행
    
    -- 메타데이터
    data_source VARCHAR(50) DEFAULT 'DART',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(company_id, fiscal_year, fiscal_quarter)
);

-- RaymondsIndex 결과 저장
CREATE TABLE raymonds_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    calculation_date DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,
    
    -- 종합 점수 (0-100)
    total_score DECIMAL(5,2) NOT NULL,
    grade VARCHAR(5) NOT NULL,          -- 'A+', 'A', 'B', 'C', 'D'
    
    -- Sub-Index 점수
    cei_score DECIMAL(5,2),             -- Capital Efficiency Index
    rii_score DECIMAL(5,2),             -- Reinvestment Intensity Index
    cgi_score DECIMAL(5,2),             -- Cash Governance Index
    mai_score DECIMAL(5,2),             -- Momentum Alignment Index
    
    -- 핵심 지표
    investment_gap DECIMAL(6,2),        -- 투자괴리율 (%)
    cash_cagr DECIMAL(6,2),             -- 현금 증가율 CAGR (%)
    capex_growth DECIMAL(6,2),          -- CAPEX 증가율 (%)
    idle_cash_ratio DECIMAL(5,2),       -- 유휴현금비율 (%)
    asset_turnover DECIMAL(5,3),        -- 자산회전율
    
    -- 플래그
    red_flags JSONB,                    -- 위험 신호 배열
    yellow_flags JSONB,                 -- 주의 신호 배열
    
    -- 판정
    verdict VARCHAR(100),               -- 한 줄 요약
    key_risk TEXT,                      -- 핵심 리스크
    watch_trigger TEXT,                 -- 재검토 시점
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(company_id, fiscal_year)
);

-- 인덱스 생성
CREATE INDEX idx_financial_details_company ON financial_details(company_id);
CREATE INDEX idx_financial_details_year ON financial_details(fiscal_year);
CREATE INDEX idx_raymonds_index_company ON raymonds_index(company_id);
CREATE INDEX idx_raymonds_index_score ON raymonds_index(total_score);
CREATE INDEX idx_raymonds_index_grade ON raymonds_index(grade);
"
```

---

## 3. DART 데이터 파싱 모듈

### Phase 2: 파서 구현

```bash
claude "DART API에서 현금흐름표와 재무상태표 상세 데이터를 파싱하는 
Python 모듈을 만들어줘.

파일 위치: backend/app/services/dart_financial_parser.py

요구사항:
1. DART OpenAPI fnlttSinglAcnt (단일회사 전체 재무제표) 사용
2. 다음 계정과목 파싱:
   - 재무상태표: 현금및현금성자산, 단기금융상품, 유형자산, 자산총계, 부채총계, 자본총계
   - 손익계산서: 매출액, 영업이익, 당기순이익
   - 현금흐름표: 영업활동현금흐름, 유형자산의취득, 배당금지급, 사채발행
3. 계정과목명 변형 처리 (매핑 테이블 사용)
4. 연결/별도 재무제표 구분
5. 2022-2024년 (3개년) 데이터 수집
6. 비동기 처리 (asyncio + httpx)
7. 에러 핸들링 및 로깅

계정과목 매핑:
ACCOUNT_MAPPING = {
    '현금및현금성자산': ['현금및현금성자산', '현금및현금등가물'],
    '단기금융상품': ['단기금융상품', '단기금융자산'],
    '유형자산': ['유형자산'],
    '자산총계': ['자산총계'],
    '매출액': ['매출액', '영업수익', '수익(매출액)'],
    '영업이익': ['영업이익', '영업이익(손실)'],
    '당기순이익': ['당기순이익', '당기순이익(손실)'],
    '영업활동현금흐름': ['영업활동현금흐름', '영업활동으로인한현금흐름'],
    '유형자산의취득': ['유형자산의 취득', '유형자산의취득', '유형자산 취득'],
}

기존 코드 스타일 참고: backend/app/services/dart_service.py
"
```

### Phase 2-2: 배치 수집 스크립트

```bash
claude "전체 상장사 재무 상세 데이터를 배치로 수집하는 스크립트 만들어줘.

파일 위치: backend/scripts/collect_financial_details.py

요구사항:
1. companies 테이블에서 전체 상장사 목록 조회
2. 각 회사별로 2022-2024년 (3개년) 재무데이터 수집
3. financial_details 테이블에 upsert
4. Rate limiting (DART API 제한 준수: 분당 1000건)
5. 진행상황 로깅 (매 100개사마다)
6. 실패 건 별도 로깅 및 재시도 로직
7. 병렬 처리 (동시 5개 요청)

실행 예시:
python collect_financial_details.py --start-year 2022 --end-year 2024 --batch-size 100

예상:
- 대상: 3,922개 상장사 × 3년 = 11,766건
- 소요시간: 약 4-5시간
"
```

---

## 4. RaymondsIndex 계산 엔진

### Phase 3: 계산 로직 구현

```bash
claude "RaymondsIndex 계산 엔진을 Python으로 구현해줘.

파일 위치: backend/app/services/raymonds_index_calculator.py

요구사항:
1. 4개 Sub-Index 계산:
   - CEI (20%): 자산회전율, 유형자산효율성, 현금수익률
   - RII (35%): 투자괴리율, CAPEX강도, 재투자율 (핵심)
   - CGI (25%): 유휴현금비율, 자금활용률, 주주환원율
   - MAI (20%): 매출-투자 동조성, 이익의 질

2. 등급 체계:
   - A+ (80-100), A (60-79), B (40-59), C (20-39), D (0-19)

3. 핵심 공식:
   Investment Gap = Cash CAGR - CAPEX Growth Rate
   (양수면 현금만 쌓는 중, 음수면 적극 투자 중)

4. Red/Yellow Flag 자동 생성

5. 최소 3개년 데이터 필요 (2022-2024 충족)

기존 risk_calculator.py 스타일 참고
"
```

### Phase 3-2: 배치 계산 스크립트

```bash
claude "전체 상장사 RaymondsIndex를 배치로 계산하는 스크립트 만들어줘.

파일 위치: backend/scripts/calculate_raymonds_index.py

실행 예시:
python calculate_raymonds_index.py --year 2024
"
```

---

## 5. API 엔드포인트

### Phase 4: FastAPI 라우터

```bash
claude "RaymondsIndex용 FastAPI 라우터를 추가해줘.

파일 위치: backend/app/api/raymonds_index.py

엔드포인트:
1. GET /api/raymonds-index/{company_id}
2. GET /api/raymonds-index/search?grade=&min_score=
3. GET /api/raymonds-index/ranking?top=&bottom=
4. GET /api/raymonds-index/{company_id}/detail
5. POST /api/raymonds-index/{company_id}/calculate (관리자용)

main.py에 라우터 등록 추가
"
```

### Phase 4-2: Report API 확장

```bash
claude "기존 /api/report/name/{company_name} 응답에 raymonds_index 추가"
```

---

## 6. 프론트엔드

### Phase 5: UI 컴포넌트

```bash
claude "RaymondsIndex 표시용 React 컴포넌트를 만들어줘.

파일 위치: frontend/src/components/RaymondsIndex/
- RaymondsIndexCard.tsx (점수 게이지 + 등급)
- SubIndexChart.tsx (레이더 차트)
- InvestmentGapMeter.tsx (스펙트럼 바)
- RiskFlagsPanel.tsx (플래그 목록)
- RaymondsIndexHistory.tsx (추이 차트)

Tailwind CSS + shadcn/ui 스타일
"
```

### Phase 5-2~4: 페이지 및 통합

```bash
claude "사이드바에 RaymondsIndex 메뉴 추가, 랭킹 페이지 생성, ReportPage에 섹션 추가"
```

---

## 7. 실행 순서

```bash
# 1. DB 스키마
claude "Phase 1 실행"

# 2. 파서 구현
claude "Phase 2 실행"

# 3. 데이터 수집 (2022-2024, 약 4-5시간)
python backend/scripts/collect_financial_details.py --start-year 2022 --end-year 2024

# 4. 계산 엔진
claude "Phase 3 실행"

# 5. 배치 계산
python backend/scripts/calculate_raymonds_index.py --year 2024

# 6. API
claude "Phase 4 실행"

# 7. 프론트엔드
claude "Phase 5 실행"

# 8. 통합
claude "Phase 6 실행"
```

---

## 8. 예상 일정

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| 1 | DB 스키마 | 1시간 |
| 2 | DART 파서 | 4시간 |
| 2-2 | 데이터 수집 (2022-2024) | **5시간** |
| 3 | 계산 엔진 | 4시간 |
| 4 | API | 2시간 |
| 5 | 프론트엔드 | 6시간 |
| 6 | 통합/테스트 | 3시간 |
| **합계** | | **25시간** |

---

## 9. 파일 구조

```
backend/
├── app/
│   ├── api/
│   │   ├── raymonds_index.py          # 신규
│   │   └── report.py                  # 수정
│   ├── services/
│   │   ├── dart_financial_parser.py   # 신규
│   │   └── raymonds_index_calculator.py # 신규
│   └── main.py                        # 수정
├── scripts/
│   ├── collect_financial_details.py   # 신규
│   └── calculate_raymonds_index.py    # 신규

frontend/src/
├── components/RaymondsIndex/
│   ├── RaymondsIndexCard.tsx
│   ├── SubIndexChart.tsx
│   ├── InvestmentGapMeter.tsx
│   └── RiskFlagsPanel.tsx
├── pages/
│   └── RaymondsIndexRankingPage.tsx
├── api/raymondsIndex.ts
├── hooks/useRaymondsIndex.ts
└── types/raymondsIndex.ts
```

---

## 끝
