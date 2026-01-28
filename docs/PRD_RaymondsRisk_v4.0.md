# RaymondsRisk Service PRD v4.0

## 통합 제품 요구사항 문서
**PostgreSQL + Neo4j 듀얼 DB 아키텍처 기반 설계**

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| 문서명 | RaymondsRisk Service PRD (통합본) |
| 버전 | 4.8 |
| 작성일 | 2025-12-15 |
| 최종 수정일 | 2026-01-23 |
| 이전 문서 | IMPLEMENTATION_PLAN.md, PHASE2_2_FRONTEND_IMPLEMENTATION.md, 화면기획서 v3.0, 관계형 리스크 기획서 v3.2.1 |
| 아키텍처 | PostgreSQL (정형 데이터) + Neo4j (관계 그래프) |
| 핵심 서비스 | 이해관계자 360° 통합 뷰 |
| Backend 상태 | 95% 완료 |
| Frontend 상태 | 90% 완료 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 4.8 | 2026-01-23 | DB 통계 현행화 - 유령기업/상장폐지 813개 삭제 반영, 신규 테이블 4개 추가 (financial_details, raymonds_index, stock_prices, largest_shareholder_info), 레코드 수 전면 업데이트 |
| 4.7 | 2026-01-23 | 관계도 기업 노드 네비게이션 기능 기획 - 그래프 내 DB 기업 노드 클릭 시 해당 기업 관계도로 이동, UX 개선 및 시각적 피드백 추가 |
| 4.6 | 2026-01-21 | 이용권 사전 체크 UX 개선 - 기업 클릭 시 페이지 이동 전 조회 가능 여부 확인, 조회 불가 시 검색 화면에서 모달 표시 |
| 4.5 | 2026-01-21 | 조회한 기업 목록 기능 추가, Trial 사용자 30일 만료/재조회 허용, 조회 제한 UX 개선, 공유 Header 전체 적용 |
| 4.4 | 2026-01-20 | Frontend 상태 85% 업데이트, 다크 테마 적용 완료, 미니 주가 차트 추가 |
| 4.3 | 2025-12-15 | 초기 작성 |

---

## 1. 프로젝트 개요

### 1.1 서비스 비전

**RaymondsRisk**는 한국 주식시장의 숨겨진 이해관계자 네트워크를 분석하여 개인 투자자를 보호하는 리스크 탐지 플랫폼입니다.

### 1.2 핵심 가치 제안

1. **이해관계자 360° 통합 뷰**: 임원, CB투자자, 대주주, 계열사를 한눈에
2. **타사 이력 추적**: 임원/투자자가 과거에 어떤 회사에 관여했는지 추적
3. **리스크 패턴 탐지**: 부실기업 전문 투자자, 반복 CB 발행, 순환출자 등 자동 감지
4. **재무건전성 분석**: 부채비율, 유동비율, 현금자산 등 핵심 지표 제공

### 1.3 타겟 사용자

- 개인 투자자 (주식, CB 투자자)
- 기관 투자자 리서치팀
- 금융 규제기관 분석가

---

## 2. 시스템 아키텍처

### 2.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React + TypeScript)                  │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│
│  │   검색/조회   │  │  리스크 대시  │  │ 이해관계자   │  │  관계망 그래프││
│  │     UI       │  │    보드      │  │   리스트     │  │   시각화     ││
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘│
└─────────┼─────────────────┼─────────────────┼─────────────────┼─────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Backend API (FastAPI)                             │
│                                                                          │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────┐│
│  │      PostgreSQL Service      │  │        Neo4j Service             ││
│  │  • 기업 기본정보             │  │  • 관계 그래프 쿼리              ││
│  │  • 재무제표 데이터           │  │  • 경로 탐색 (Shortest Path)     ││
│  │  • 리스크 점수 (연도별)      │  │  • 클러스터 분석                 ││
│  │  • 사용자/북마크/알림        │  │  • 중심성 계산 (Centrality)      ││
│  └──────────────┬───────────────┘  └──────────────┬───────────────────┘│
└─────────────────┼───────────────────────────────────┼────────────────────┘
                  │                                   │
                  ▼                                   ▼
┌─────────────────────────────┐    ┌─────────────────────────────────────┐
│        PostgreSQL           │    │              Neo4j                   │
│                             │    │                                      │
│  • companies (3,109)        │    │  Nodes:                              │
│  • officers (47,444)        │    │  • (:Company) 3,109                  │
│  • officer_positions (62K)  │    │  • (:Officer) 47,444                 │
│  • convertible_bonds (1,133)│    │  • (:ConvertibleBond) 1,133          │
│  • cb_subscribers (7,026)   │    │  • (:Subscriber) ~2,200              │
│  • financial_statements (9K)│    │                                      │
│  • risk_signals (1,412)     │    │  Relationships:                      │
│  • disclosures (279,258)    │    │  • [:WORKS_AT] 62,141                │
│  • affiliates (864)         │    │  • [:INVESTED_IN] ~3,100             │
│  • raymonds_index (5,257)   │    │  • [:SUBSCRIBED] ~4,000              │
│  • stock_prices (126,506)   │    │  • [:ISSUED] 1,133                   │
└─────────────────────────────┘    └─────────────────────────────────────┘
```

### 2.2 DB 역할 분담

| 데이터 유형 | PostgreSQL | Neo4j |
|-------------|------------|-------|
| 기업 기본정보 | ✅ Master | 🔗 Reference (corp_code) |
| 재무제표 | ✅ 전담 | ❌ |
| 리스크 점수 | ✅ 전담 | ❌ |
| 임원 정보 | ✅ 상세 데이터 | 🔗 관계 (Officer)-[:WORKS_AT]->(Company) |
| CB 투자 | ✅ 상세 데이터 | 🔗 관계 (Subscriber)-[:INVESTED_IN]->(Company) |
| 주주 정보 | ✅ 상세 데이터 | 🔗 관계 (Entity)-[:SHAREHOLDER_OF]->(Company) |
| 계열사 | ✅ 상세 데이터 | 🔗 관계 (Company)-[:AFFILIATE_OF]->(Company) |
| 관계망 쿼리 | ❌ | ✅ 전담 (Cypher) |
| 경로 탐색 | ❌ | ✅ 전담 |
| 클러스터 분석 | ❌ | ✅ 전담 |

---

## 3. 현재 구현 현황 (Backend 95%)

### 3.1 완료된 테이블 (PostgreSQL)

| 테이블명 | 레코드 수 | 상태 | 비고 |
|----------|----------|------|------|
| companies | 3,109 | ✅ | 상장사 3,021 + ETF 88 (유령/상장폐지 813개 삭제) |
| officers | 47,444 | ✅ | birth_date 99.9% |
| officer_positions | 62,141 | ✅ | 2022~2025 임원 재직 기록 |
| convertible_bonds | 1,133 | ✅ | 회차정보 포함 |
| cb_subscribers | 7,026 | ✅ | - |
| financial_statements | 9,820 | ✅ | - |
| financial_details | 10,288 | ✅ | XBRL v3.0 파서 적용 |
| risk_signals | 1,412 | ✅ | 5개 패턴 탐지 |
| disclosures | 279,258 | ✅ | 2022~2025 공시 |
| risk_scores | 3,138 | ✅ | 종합 리스크 점수 (상장폐지 774건 삭제) |
| major_shareholders | 44,574 | ✅ | 대주주 정보 |
| affiliates | 864 | ✅ | 계열사 정보 (109건 삭제) |
| raymonds_index | 5,257 | ✅ | RaymondsIndex 평가 결과 |
| stock_prices | 126,506 | ✅ | 주가 데이터 (818건 삭제) |
| largest_shareholder_info | 4,599 | ✅ | 최대주주 기본정보 |

### 3.2 완료된 Neo4j 그래프

| 항목 | 개수 | 상태 | 비고 |
|------|------|------|------|
| 전체 노드 | ~53,000 | ✅ | PostgreSQL 기준 재동기화 |
| Company 노드 | 3,109 | ✅ | corp_code 기반 |
| Officer 노드 | 47,444 | ✅ | PostgreSQL ID 동기화 |
| ConvertibleBond 노드 | 1,133 | ✅ | - |
| Subscriber 노드 | ~2,200 | ✅ | - |
| WORKS_AT 관계 | 62,141 | ✅ | corp_code 기반 매핑 |
| INVESTED_IN 관계 | ~3,100 | ✅ | - |
| SUBSCRIBED 관계 | ~4,000 | ✅ | - |
| ISSUED 관계 | 1,133 | ✅ | - |

> **2026-01-21 개선사항**: 유령기업 39개 + 상장폐지 기업 774개 삭제 (총 813개). 현재 3,109개 기업 관리 중.

### 3.3 완료된 API 엔드포인트

```
Graph API (/api/graph)
├── GET  /company/{id}              ✅ 회사 네트워크
├── GET  /officer/{id}/career       ✅ 임원 경력 이력
├── GET  /officer/{id}/career-network ✅ 경력 네트워크
├── GET  /subscriber/{id}/investments ✅ 투자 이력
├── GET  /subscriber/{id}/investment-network ✅ 투자 네트워크
└── POST /recenter                  ✅ 노드 중심 전환

Financial API (/api/financials)
├── GET  /company/{id}/metrics      ✅ 재무지표
└── GET  /company/{id}/health       ✅ 건전성 분석

Risk API (/api/risks)
├── GET  /company/{id}/analysis     ✅ 위험도 분석
└── GET  /company/{id}/patterns     ✅ 위험 패턴 탐지

Company API (/api/companies)
├── GET  /                          ✅ 회사 검색
└── GET  /{id}                      ✅ 회사 상세
```

---

## 4. 스키마 매핑 및 확장 계획

### 4.1 기존 스키마 ↔ 화면기획서 스키마 매핑

| 화면기획서 테이블 | 기존 테이블 | 매핑 상태 | 액션 |
|------------------|-------------|----------|------|
| companies | companies | ✅ 호환 | 컬럼 확장 필요 |
| executives | officers + officer_positions | ✅ 대체 가능 | - |
| executive_other_positions | Neo4j WORKS_AT 쿼리 | ✅ 대체 가능 | - |
| cb_issuances | convertible_bonds | ✅ 호환 | 컬럼명 차이만 |
| cb_participants | cb_subscribers | ✅ 호환 | - |
| cb_participant_other_investments | Neo4j INVESTED_IN | ✅ 대체 가능 | - |
| major_shareholders | major_shareholders (44,574) | ✅ 완료 | - |
| affiliates | affiliates (864) | ✅ 완료 | - |
| risk_scores | risk_scores (3,138) | ✅ 완료 | 종합 리스크 점수 |
| alerts | risk_signals (일부 역할) | ✅ 대체 가능 | - |

### 4.2 신규 생성 필요 테이블

#### 4.2.1 major_shareholders (대주주)

```sql
CREATE TABLE major_shareholders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    shareholder_name VARCHAR(100) NOT NULL,
    shareholder_name_normalized VARCHAR(100),
    shareholder_type VARCHAR(20),       -- INDIVIDUAL, INSTITUTION, TREASURY
    share_count BIGINT,
    share_ratio DECIMAL(7,4),           -- 지분율 (소수점 4자리)
    is_largest_shareholder BOOLEAN DEFAULT FALSE,
    is_related_party BOOLEAN DEFAULT FALSE,
    report_date DATE,
    report_year INTEGER,
    report_quarter INTEGER,
    change_reason VARCHAR(200),
    previous_share_ratio DECIMAL(7,4),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_shareholder_company ON major_shareholders(company_id);
CREATE INDEX idx_shareholder_name ON major_shareholders(shareholder_name_normalized);
```

#### 4.2.2 risk_scores (종합 리스크 점수)

```sql
CREATE TABLE risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- 분석 기간
    analysis_year INTEGER NOT NULL,
    analysis_quarter INTEGER,

    -- 종합 리스크
    total_score DECIMAL(5,2) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,    -- VERY_LOW, LOW, MEDIUM, HIGH, CRITICAL
    investment_grade VARCHAR(5),        -- AAA, AA, A, BBB, BB, B, CCC
    confidence DECIMAL(5,4),

    -- RaymondsRisk (50%)
    raymondsrisk_score DECIMAL(5,2),
    human_risk_score DECIMAL(5,2),      -- 인적 리스크 (25%)
    cb_risk_score DECIMAL(5,2),         -- CB 리스크 (25%)

    -- 재무건전성 (50%)
    financial_health_score DECIMAL(5,2),

    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(company_id, analysis_year, analysis_quarter)
);

CREATE INDEX idx_risk_scores_company ON risk_scores(company_id);
CREATE INDEX idx_risk_scores_year ON risk_scores(analysis_year);
```

---

## 5. API 엔드포인트 설계 (신규/확장)

### 5.1 이해관계자 360° 통합 API (핵심)

```yaml
GET /api/v1/companies/{corp_code}/stakeholders
  Query:
    - start_year: 2022
    - end_year: 2025
    - end_quarter: 2
    - include_details: true/false

  Response:
    company:
      corp_code: "A900260"
      corp_name: "엑시온그룹"
      stock_code: "900260"

    analysis_period:
      start_year: 2022
      end_year: 2025
      end_quarter: 2

    summary:
      total_stakeholders: 48
      executive_count: 5
      executive_other_company_count: 18
      executive_high_risk_count: 2
      cb_participant_count: 23
      cb_total_amount: 23000000000
      cb_high_risk_count: 5
      shareholder_count: 12
      largest_shareholder_ratio: 45.2
      affiliate_count: 8

    executives: [...]
    cb_investors: [...]
    shareholders: [...]
    affiliates: [...]
```

### 5.2 동명이인 식별 로직 (2025-12-12 개선)

#### 5.2.1 문제점

| 문제 | 상세 |
|------|------|
| 이름만 비교 | "김동규"로 검색 시 다른 사람의 경력이 반환됨 |
| ID 불일치 | PostgreSQL Officer ID ≠ Neo4j Officer ID |
| birth_date 누락 | Neo4j에 birth_date NULL인 임원 다수 존재 |

#### 5.2.2 해결 방안

1. **이름 + 생년월일 6자리 비교**
   - PostgreSQL birth_date: `197410`, `1974.10`, `1974년 10월` 등 다양한 형식
   - 비교 시 앞 6자리 (YYYYMM)로 정규화하여 비교
   - 생년월일 없는 경우 이름만으로 fallback

2. **Neo4j Officer 재동기화**
   - PostgreSQL ID를 Neo4j Officer.id로 사용
   - birth_date 형식 정규화: `YYYYMM` → `YYYY.MM`

3. **WORKS_AT 관계 재생성**
   - Company ID 불일치 문제 → corp_code 기반 매핑

#### 5.2.3 구현 세부사항

**PostgreSQL 경력 조회 시 생년월일 비교**

```sql
-- 생년월일이 있는 경우
SELECT career_history FROM officers
WHERE name = :name
AND birth_date IS NOT NULL
AND REPLACE(REPLACE(REPLACE(birth_date, '년', ''), '월', ''), '.', '') LIKE :birth_prefix || '%'
AND career_history IS NOT NULL
AND jsonb_array_length(career_history) > 0
LIMIT 1

-- 생년월일이 없는 경우 (fallback)
SELECT career_history FROM officers
WHERE name = :name
AND career_history IS NOT NULL
LIMIT 1
```

**Neo4j 동명이인 비교**

```cypher
MATCH (o:Officer)
WHERE o.name = $name
AND o.birth_date IS NOT NULL
AND substring(replace(o.birth_date, '.', ''), 0, 6) = $normalized_birth
RETURN o
```

#### 5.2.4 결과

| 항목 | 개선 전 | 개선 후 (현재) |
|------|---------|---------|
| Officers (Neo4j) | 95,596 | 47,444 |
| birth_date 보유율 | 88% | 99.9% |
| WORKS_AT 관계 | 55,206 | 62,141 |
| 동명이인 구분 | 불가 | 가능 |

### 5.3 임원 타사 이력 API

```yaml
GET /api/v1/executives/{person_id}/other-positions
  Query:
    - exclude_corp_code: "A900260"

  Response:
    person:
      person_id: "P_김철수_1965"
      name: "김철수"
      birth_year: "1965"

    current_company:
      corp_code: "A900260"
      corp_name: "엑시온그룹"
      position: "대표이사"

    other_positions:
      - corp_code: "A123456"
        corp_name: "ABC테크"
        position: "대표이사"
        tenure_start: "2020-01"
        tenure_end: "2022-02"
        company_status: "DELISTED"
        is_loss_making: true
      - ...

    statistics:
      total_companies: 4
      delisted_count: 1
      managed_count: 1
      loss_making_count: 2
      concurrent_positions: 1
```

### 5.3 CB 투자자 타사 투자 API

```yaml
GET /api/v1/cb-participants/{participant_id}/other-investments
  Query:
    - exclude_corp_code: "A900260"

  Response:
    participant:
      participant_id: "이상민"
      name: "이상민"
      participant_type: "INDIVIDUAL"

    investments_summary:
      total_companies: 12
      total_amount: 18000000000
      loss_company_count: 6
      loss_company_ratio: 0.50
      delisted_count: 2

    investments:
      - corp_code: "A111111"
        corp_name: "JKL에너지"
        investment_date: "2023-05-20"
        amount: 1500000000
        company_status: "NORMAL"
        is_loss_making: true
        consecutive_loss_quarters: 6
      - ...

    risk_assessment:
      is_high_risk: true
      risk_factors:
        - "적자기업 투자 비율 50% 초과"
        - "상장폐지 기업 2개사 투자 이력"
      suspicious_pattern: "부실기업 전문 투자 의심"
```

### 5.4 인적 리스크 API (신규)

```yaml
GET /api/v1/companies/{corp_code}/human-risk

Response:
  corp_code: "00126380"
  human_risk:
    score: 6.5
    level: "LOW"
    raw_score: 4
    notation: "(5)(16)"
    exec_count: 5
    total_other_companies: 16
    analysis_period: "2024.Q2~2025.Q2"

    score_breakdown:
      exec_count_score: 1
      exec_count_range: "≤10명"
      other_position_multiplier: 4
      other_position_range: "≥16건"

    executives:
      - exec_name: "김철수"
        birth_date: "1970-01-15"
        current_position: "대표이사"
        other_company_count: 3
        is_high_risk: false

    high_risk_executives:
      - exec_name: "정우성"
        risk_factors: ["7개사 재직", "현재 타회사 대표이사 겸직"]
```

### 5.5 CB 리스크 API (신규 - v3.2.1 기준)

```yaml
GET /api/v1/companies/{corp_code}/cb-risk

Response:
  corp_code: "00126380"
  cb_risk:
    score: 50
    level: "MEDIUM"
    notation: "(3)(80)(8)"

    # 분석 기간 정책 (v3.2.1)
    analysis_period:
      base_period:
        type: "최근 1년"
        start: "2024-Q2"
        end: "2025-Q2"
        description: "CB 발행 횟수/금액 기준"
      history_period:
        type: "전체 3.5년"
        start: "2022-01"
        end: "2025-Q2"
        description: "참여자 타사 투자 이력 조회"

    score_breakdown:
      frequency_score: 20
      frequency_detail: "최근 1년 3회 발행"
      amount_score: 15
      amount_detail: "최근 1년 총 80억원"
      quality_score: 10
      quality_detail: "고위험 참여자 25% (2/8명)"
      loss_connection_score: 5
      loss_connection_detail: "적자기업 2개사 연결"

    summary:
      cb_count_1y: 3           # 최근 1년 발행 횟수
      total_amount_billion_1y: 80  # 최근 1년 총 발행액
      participant_count: 8
      high_risk_participant_count: 2
      loss_company_count: 2

    high_risk_participants:
      - name: "이상민"
        participant_type: "INDIVIDUAL"
        total_other_investments: 12
        loss_company_count: 6
        loss_ratio: 0.5
        risk_factors: ["적자기업 투자 비율 50%"]
```

### 5.6 RaymondsRisk 통합 API (신규 - v3.2.1 기준)

```yaml
GET /api/v1/companies/{corp_code}/raymondsrisk

Response:
  corp_code: "00126380"
  raymondsrisk:
    score: 28.3
    level: "LOW"
    investment_grade: "A"
    notation: "(5)(16)(3)(80)(2)"

    # 분석 기간 정책 (v3.2.1)
    analysis_period:
      base_period:
        type: "최근 1년"
        start: "2024-Q2"
        end: "2025-Q2"
        description: "임원 수, CB 발행 횟수/금액 기준"
      history_period:
        type: "전체 3.5년"
        start: "2022-01"
        end: "2025-Q2"
        description: "타사 재직/투자 이력 조회 기준"

    data_confidence:
      total_confidence: 0.85
      confidence_level: "MEDIUM"

    breakdown:
      human_risk:
        score: 6.5
        level: "LOW"
        notation: "(5)(16)"
        weight: 0.5
        weighted_score: 3.25
      cb_risk:
        score: 50
        level: "MEDIUM"
        notation: "(3)(80)(2)"
        weight: 0.5
        weighted_score: 25.0
```

### 5.7 네트워크 시각화 API

```yaml
GET /api/v1/companies/{corp_code}/network
  Query:
    - depth: 1 or 2
    - filter: all | executive | cb | shareholder | affiliate
    - search: "검색어"
    - limit: 100

  Response:
    center_node:
      id: "A900260"
      corp_code: "A900260"
      corp_name: "엑시온그룹"

    nodes:
      - id: "A900260"
        label: "엑시온그룹"
        type: "company"
        corp_code: "A900260"
        risk_score: 52.4
        risk_level: "MEDIUM"
        size: 40
        color: "#4A90E2"
      - id: "P_김철수_1965"
        label: "김철수"
        type: "person"
        person_type: "EXECUTIVE"
        other_company_count: 3
        high_risk: false
        size: 25
        color: "#5AAEFF"
      - ...

    edges:
      - id: "e1"
        source: "P_김철수_1965"
        target: "A900260"
        type: "executive"
        position: "대표이사"
        width: 2
        color: "#999"
      - ...

    statistics:
      total_nodes: 42
      total_edges: 58
      connected_companies: 12
      central_persons: ["이상민", "홍길동"]
```

---

## 6. 리스크 점수 계산 로직 (v3.2)

### 6.1 종합 리스크 구성

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                    🎯 종합 투자 리스크 (100점)                       │
│                                                                      │
│   ┌─────────────────────────────┐  ┌─────────────────────────────┐  │
│   │                             │  │                             │  │
│   │   🎯 RaymondsRisk (50%)    │  │   💰 재무건전성 (50%)       │  │
│   │                             │  │                             │  │
│   │  ┌─────────┐ ┌─────────┐  │  │  ┌─────────┐ ┌─────────┐   │  │
│   │  │ 인적    │ │ CB      │  │  │  │ 부채    │ │ 이자    │   │  │
│   │  │ 리스크  │ │ 리스크  │  │  │  │ 비율    │ │ 보상    │   │  │
│   │  │ (25%)   │ │ (25%)   │  │  │  │(12.5%)  │ │(12.5%)  │   │  │
│   │  └─────────┘ └─────────┘  │  │  └─────────┘ └─────────┘   │  │
│   │                             │  │  ┌─────────┐ ┌─────────┐   │  │
│   │                             │  │  │ 유동    │ │ 현금    │   │  │
│   │                             │  │  │ 비율    │ │ 비율    │   │  │
│   │                             │  │  │ (10%)   │ │ (7.5%)  │   │  │
│   │                             │  │  └─────────┘ └─────────┘   │  │
│   │                             │  │  ┌─────────┐               │  │
│   │                             │  │  │ 연속    │               │  │
│   │                             │  │  │ 적자    │               │  │
│   │                             │  │  │ (7.5%)  │               │  │
│   │                             │  │  └─────────┘               │  │
│   └─────────────────────────────┘  └─────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 분석 기간 정책 (v3.2.1)

> **핵심 원칙**: 모수(현재 임원 수, CB 발행)는 **최근 1년**, 이력 조회(타사 재직, 타사 CB 투자)는 **전체 3.5년**

#### 6.2.1 분석 기간 구분

| 구분 | 기간 | 용도 | 예시 |
|------|------|------|------|
| **모수 기준** | 최근 1년 (2024.Q2 ~ 2025.Q2) | 현재 임원 수, CB 발행 횟수/금액 | "현재 임원 5명", "최근 1년 CB 3회 발행" |
| **이력 조회** | 전체 3.5년 (2022.01 ~ 2025.Q2) | 타사 재직 이력, 타사 CB 투자 이력 | "과거 3.5년간 7개사 재직 이력" |

#### 6.2.2 분석 기간 정책 적용 예시

```
┌─────────────────────────────────────────────────────────────────────┐
│                     분석 기간 정책 적용                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [인적 리스크]                                                        │
│  ├── 현재 임원 수 (모수): 최근 1년 내 재직 중인 임원                    │
│  │   → "2024.Q2~2025.Q2 기간 내 재직 임원 5명"                        │
│  └── 타사 재직 이력 (이력): 전체 3.5년                                 │
│      → "각 임원의 2022.01~2025.Q2 타사 재직 이력 조회"                 │
│                                                                      │
│  [CB 리스크]                                                          │
│  ├── CB 발행 횟수/금액 (모수): 최근 1년                                │
│  │   → "2024.Q2~2025.Q2 기간 내 CB 4회 발행, 총 80억원"               │
│  └── 참여자 타사 투자 이력 (이력): 전체 3.5년                          │
│      → "각 참여자의 2022.01~2025.Q2 타사 CB 투자 이력 조회"            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 6.2.3 API 응답 포맷

```json
{
  "analysis_period": {
    "base_period": {
      "type": "최근 1년",
      "start": "2024-Q2",
      "end": "2025-Q2",
      "description": "현재 임원 수, CB 발행 횟수/금액 기준"
    },
    "history_period": {
      "type": "전체 3.5년",
      "start": "2022-01",
      "end": "2025-Q2",
      "description": "타사 재직/투자 이력 조회 기준"
    }
  }
}
```

### 6.3 인적 리스크 계산 (Human Risk) - 25%

#### 6.3.1 개요

| 항목 | 내용 |
|------|------|
| **목적** | 임원의 타사 재직 네트워크를 통한 부실 연결 위험 평가 |
| **가중치** | 종합 리스크의 25% (RaymondsRisk 50% × 내부 50%) |
| **점수 범위** | 0 ~ 100점 |
| **분석 기간** | 2024년 2분기 ~ 2025년 2분기 (최근 1년) - 모수 기준 |

#### 6.3.2 계산 로직

```
┌─────────────────────────────────────────────────────────────────────┐
│                     인적 리스크 계산 흐름                            │
├─────────────────────────────────────────────────────────────────────┤
│  [Step 1] 임원 수 기반 점수 산출                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ≤10명 → 1점 | 11~20명 → 3점 | 21~25명 → 6점                 │   │
│  │ 26~29명 → 10점 | ≥30명 → 15점                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▼                                       │
│  [Step 2] 타사 재직 건수 기반 배수 산출                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ≤5건 → ×1 | 6~10건 → ×2 | 11~15건 → ×3 | ≥16건 → ×4        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▼                                       │
│  [Step 3] 원점수 계산                                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 원점수 = 임원 수 점수 × 타사 재직 배수                       │   │
│  │ 범위: 1점 (1×1) ~ 60점 (15×4)                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▼                                       │
│  [Step 4] 0-100점 정규화 및 등급 판정                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 원점수 <30  → 0~49점 (LOW)                                   │   │
│  │ 원점수 30~50 → 50~69점 (MEDIUM)                              │   │
│  │ 원점수 >50  → 70~100점 (HIGH)                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 6.3.3 Python 구현

```python
def calculate_human_risk(exec_count: int, total_other_companies: int) -> dict:
    """인적 리스크 점수 계산 (0-100점)"""

    # Step 1: 임원 수 점수
    if exec_count <= 10:
        exec_score = 1
    elif exec_count <= 20:
        exec_score = 3
    elif exec_count <= 25:
        exec_score = 6
    elif exec_count <= 29:
        exec_score = 10
    else:
        exec_score = 15

    # Step 2: 타사 재직 배수
    if total_other_companies <= 5:
        multiplier = 1
    elif total_other_companies <= 10:
        multiplier = 2
    elif total_other_companies <= 15:
        multiplier = 3
    else:
        multiplier = 4

    # Step 3: 원점수
    raw_score = exec_score * multiplier

    # Step 4: 정규화 (0-100)
    if raw_score < 30:
        normalized = (raw_score / 30) * 49
        level = 'LOW'
    elif raw_score <= 50:
        normalized = 50 + ((raw_score - 30) / 20) * 19
        level = 'MEDIUM'
    else:
        normalized = 70 + ((raw_score - 50) / 10) * 30
        level = 'HIGH'

    return {
        "score": round(min(normalized, 100), 1),
        "level": level,
        "raw_score": raw_score,
        "notation": f"({exec_count})({total_other_companies})"
    }
```

#### 6.3.4 고위험 임원 판정 기준

| 조건 | 판정 | 표시 |
|------|------|------|
| 타회사 재직 ≥5개사 | 고위험 | 🔴 "N개사 재직" |
| 현재 타회사 대표이사 겸직 | 고위험 | 🔴 "현재 타회사 대표이사 겸직" |
| 동일 회사 2회 이상 재직 | 참고 | ⚠️ "동일 회사 중복 재직" |

### 6.4 CB 리스크 계산 (CB Risk) - 25%

#### 6.4.1 개요

| 항목 | 내용 |
|------|------|
| **목적** | CB 발행 패턴 및 참여자 품질을 통한 자금조달 위험 평가 |
| **가중치** | 종합 리스크의 25% (RaymondsRisk 50% × 내부 50%) |
| **점수 범위** | 0 ~ 100점 |
| **모수 기간** | 최근 1년 (2024.Q2 ~ 2025.Q2) - 발행 횟수/금액 |
| **이력 기간** | 전체 3.5년 (2022.01 ~ 2025.Q2) - 참여자 타사 투자 이력 |

#### 6.4.2 4개 컴포넌트 점수 체계

| 컴포넌트 | 배점 | 측정 항목 | 기간 |
|----------|------|----------|------|
| **발행 빈도** | 25점 | 최근 1년 CB 발행 횟수 | 모수 (1년) |
| **발행 규모** | 25점 | 최근 1년 총 발행금액 (억원) | 모수 (1년) |
| **참여자 품질** | 30점 | 고위험 참여자 비율 | 이력 (3.5년) |
| **적자기업 연결** | 20점 | 참여자가 투자한 적자기업 수 | 이력 (3.5년) |

#### 6.4.3 각 컴포넌트 점수표 (v3.2.1 기준)

**Component 1: 발행 빈도 (25점 만점) - 최근 1년 기준**

| 최근 1년 발행 횟수 | 점수 | 비고 |
|-------------------|------|------|
| ≥4회 | 25점 | 연 4회 이상 |
| 3회 | 20점 | |
| 2회 | 15점 | |
| 1회 | 10점 | |
| 0회 | 0점 | CB 없음 = 리스크 없음 |

**Component 2: 발행 규모 (25점 만점) - 최근 1년 기준**

| 최근 1년 총 발행액 | 점수 | 비고 |
|-------------------|------|------|
| ≥200억 | 25점 | 대규모 자금조달 |
| 100~199억 | 20점 | |
| 50~99억 | 15점 | |
| 20~49억 | 10점 | |
| 1~19억 | 5점 | |
| 0원 | 0점 | CB 없음 = 리스크 없음 |

**Component 3: 참여자 품질 (30점 만점)**

| 고위험 참여자 비율 | 점수 |
|--------------------|------|
| 50% 이상 | 30점 |
| 30~49% | 18~29점 |
| 10~29% | 6~17점 |
| <10% | 0~5점 |

> **고위험 참여자 정의**: 적자기업 투자 비율 ≥50%

**Component 4: 적자기업 연결 (20점 만점)**

| 적자기업 연결 수 | 점수 |
|------------------|------|
| ≥10개 | 20점 |
| 5~9개 | 15점 |
| 3~4개 | 10점 |
| 1~2개 | 개수 × 2점 |
| 0개 | 0점 |

#### 6.4.4 Python 구현 (v3.2.1)

```python
def calculate_cb_risk(
    cb_count_1y: int,           # 최근 1년 CB 발행 횟수
    total_amount_billion_1y: int,  # 최근 1년 총 발행액 (억원)
    participants: list,          # 전체 3.5년 참여자 목록
) -> dict:
    """CB 리스크 점수 계산 (0-100점) - v3.2.1 기준

    모수 기간: 최근 1년 (발행 횟수/금액)
    이력 기간: 전체 3.5년 (참여자 타사 투자)
    """

    # CB 없음 = 리스크 없음
    if cb_count_1y == 0 and total_amount_billion_1y == 0:
        return {"score": 0, "level": "LOW", "notation": "(0)(0)(0)"}

    # Component 1: 발행 빈도 (최근 1년 기준)
    if cb_count_1y >= 4:
        frequency_score = 25
    elif cb_count_1y == 3:
        frequency_score = 20
    elif cb_count_1y == 2:
        frequency_score = 15
    elif cb_count_1y == 1:
        frequency_score = 10
    else:
        frequency_score = 0  # 0회 = 0점

    # Component 2: 발행 규모 (최근 1년 기준)
    if total_amount_billion_1y >= 200:
        amount_score = 25
    elif total_amount_billion_1y >= 100:
        amount_score = 20
    elif total_amount_billion_1y >= 50:
        amount_score = 15
    elif total_amount_billion_1y >= 20:
        amount_score = 10
    elif total_amount_billion_1y >= 1:
        amount_score = 5
    else:
        amount_score = 0  # 0원 = 0점

    # Component 3: 참여자 품질
    if participants:
        high_risk = [p for p in participants if p.get('loss_ratio', 0) >= 0.5]
        high_risk_ratio = len(high_risk) / len(participants)
        quality_score = min(int(high_risk_ratio * 60), 30)
    else:
        quality_score = 15  # 데이터 없으면 중립

    # Component 4: 적자기업 연결
    loss_companies = set()
    for p in participants:
        loss_companies.update(p.get('loss_company_codes', []))
    loss_count = len(loss_companies)

    if loss_count >= 10:
        loss_score = 20
    elif loss_count >= 5:
        loss_score = 15
    elif loss_count >= 3:
        loss_score = 10
    else:
        loss_score = loss_count * 2

    # 총점
    total = frequency_score + amount_score + quality_score + loss_score

    if total >= 70:
        level = 'HIGH'
    elif total >= 40:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {
        "score": total,
        "level": level,
        "notation": f"({cb_count_1y})({total_amount_billion_1y})({loss_count})",
        "analysis_period": {
            "base": "최근 1년 (2024.Q2~2025.Q2)",
            "history": "전체 3.5년 (2022.01~2025.Q2)"
        },
        "breakdown": {
            "frequency_score": frequency_score,
            "frequency_detail": f"최근 1년 {cb_count_1y}회",
            "amount_score": amount_score,
            "amount_detail": f"최근 1년 {total_amount_billion_1y}억원",
            "quality_score": quality_score,
            "loss_connection_score": loss_score
        }
    }
```

#### 6.4.5 고위험 참여자 판정 기준

| 조건 | 판정 | 표시 |
|------|------|------|
| 적자기업 투자 비율 ≥50% | 고위험 | 🔴 "적자기업 투자 비율 N%" |
| 타사 CB 투자 ≥10건 | 참고 | ⚠️ "N개사 CB 투자" |
| 동일 기업 반복 투자 | 참고 | ⚠️ "특정 기업 집중 투자" |

### 6.5 RaymondsRisk 통합 계산

```python
def calculate_raymondsrisk(human_risk: dict, cb_risk: dict) -> dict:
    """RaymondsRisk 점수 = 인적(50%) + CB(50%)"""

    score = human_risk['score'] * 0.5 + cb_risk['score'] * 0.5

    if score >= 70:
        level = 'HIGH'
    elif score >= 40:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {
        "score": round(score, 1),
        "level": level,
        "notation": f"{human_risk['notation']}{cb_risk['notation']}",
        "breakdown": {
            "human_risk": human_risk,
            "cb_risk": cb_risk
        }
    }
```

### 6.6 투자등급 체계

| 점수 범위 | 등급 | 리스크 레벨 | 의미 |
|-----------|------|-------------|------|
| 0~9점 | AAA | VERY_LOW | 최우량 |
| 10~19점 | AA | VERY_LOW | 우량 |
| 20~29점 | A | LOW | 양호 |
| 30~39점 | BBB | LOW | 적정 |
| 40~49점 | BB | MEDIUM | 주의 |
| 50~59점 | B | MEDIUM | 경계 |
| 60~69점 | CCC | HIGH | 위험 |
| 70~79점 | CC | HIGH | 고위험 |
| 80~89점 | C | CRITICAL | 심각 |
| 90~100점 | D | CRITICAL | 부실 |

### 6.7 데이터 신뢰도 계산

```python
def calculate_data_confidence(human_data: dict, cb_data: dict) -> dict:
    """데이터 완전성에 따른 신뢰도 계산"""

    # 인적 리스크 신뢰도
    if not human_data.get('executives'):
        human_conf = 0.0
    elif not human_data.get('other_positions'):
        human_conf = 0.5
    else:
        human_conf = 1.0

    # CB 리스크 신뢰도
    if not cb_data.get('cb_issuances'):
        cb_conf = 1.0  # CB 없음 = 정상
    elif not cb_data.get('participants'):
        cb_conf = 0.6
    elif not cb_data.get('participant_investments'):
        cb_conf = 0.7
    else:
        cb_conf = 1.0

    total = human_conf * 0.5 + cb_conf * 0.5

    return {
        "human_risk_confidence": human_conf,
        "cb_risk_confidence": cb_conf,
        "total_confidence": round(total, 2),
        "confidence_level": "HIGH" if total >= 0.9 else "MEDIUM" if total >= 0.7 else "LOW"
    }
```

---

## 7. 화면 설계

### 7.1 메인 검색 페이지

- 중앙 검색창 (기업명/종목코드 검색)
- 최근 분석 기업 카드 (4~8개)
- 각 카드: 기업명, 종목코드, 리스크 점수, 임원 수, CB 발행 수

### 7.2 기업 분석 결과 페이지 구성

```
┌─────────────────────────────────────────────────────────────────┐
│ 헤더: 기업명, 종목코드, 업종, 시장, 상태                          │
├─────────────────────────────────────────────────────────────────┤
│ 분석 기간 선택: [2022] [2023] [2024] [2025 Q2]                  │
├─────────────────────────────────────────────────────────────────┤
│ 종합 리스크 대시보드                                             │
│ ┌─────────────┐ ┌─────────────┐                                 │
│ │RaymondsRisk │ │ 재무건전성  │                                 │
│ │   48.2점    │ │   62.5점    │                                 │
│ └─────────────┘ └─────────────┘                                 │
├─────────────────────────────────────────────────────────────────┤
│ 이해관계자 360° 통합 뷰                                          │
│ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                                │
│ │임원 │ │CB   │ │대주주│ │계열사│                                │
│ │5명  │ │23명 │ │12명 │ │8개사│                                │
│ └─────┘ └─────┘ └─────┘ └─────┘                                │
├─────────────────────────────────────────────────────────────────┤
│ 섹션 상세 (아코디언)                                             │
│ ▼ 임원 현황                                                     │
│   - 임원 리스트 (이름, 직책, 타사 재직 수)                        │
│   - 고위험 임원 경고                                             │
│ ▼ CB 투자자 현황                                                │
│   - CB 발행 내역                                                 │
│   - 참여자별 타사 투자 이력                                       │
│ ...                                                              │
├─────────────────────────────────────────────────────────────────┤
│ 관계망 시각화 (Neo4j 그래프)                                      │
│ - 필터: 전체/임원/CB/대주주/계열사                               │
│ - 깊이: 1단계/2단계                                              │
│ - 노드 클릭 → 상세 팝업                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 그래프 시각화 규칙

**노드 색상:**
- Company: 파란색 (#4A90E2)
- Officer: 경력 회사 수에 따라 진하기 조절
  - 0-2개: #A8D8FF
  - 3-5개: #5AAEFF
  - 6-10개: #2E7DD4
  - 11+: #1A4D8F
- ConvertibleBond: 녹색 (#50C878)
- Subscriber: 투자 건수에 따라 진하기 조절
  - 1-2건: #C7F5C7
  - 3-5건: #6FD66F
  - 6-10건: #3BA13B
  - 11+: #1E5F1E

**관계 스타일:**
- WORKS_AT: 실선, 회색 (#999)
- WORKED_AT: 점선, 연한 회색 (#CCC)
- ISSUED: 보라색 (#9B59B6)
- SUBSCRIBED: 녹색 (#27AE60)
- INVESTED_IN: 청록색 (#16A085)
- AFFILIATE_OF: 주황색 (#E67E22)

### 7.4 관계도 기업 노드 네비게이션 (v4.7)

> **기획 배경**: 관계도 그래프에서 연결된 기업 노드를 클릭하여 해당 기업의 관계도로 이동할 수 있는 기능 필요

#### 7.4.1 기능 개요

| 항목 | 내용 |
|------|------|
| **목적** | 그래프 내 연결된 기업들을 탐색하여 연쇄 리스크 분석 지원 |
| **대상** | DB에 등록된 기업 노드 (corp_code 존재) |
| **트리거** | 기업 노드 더블클릭 (싱글클릭은 상세패널 유지) |
| **히스토리** | 브라우저 히스토리 및 브레드크럼으로 탐색 경로 추적 |

#### 7.4.2 DB 기업 식별 기준

```typescript
// 이동 가능한 기업 판별
const isNavigable = (node: GraphNode): boolean => {
  return node.type === 'company'
    && node.corp_code !== undefined  // DB에 등록된 기업
    && node.corp_code !== currentCompanyId  // 현재 회사 제외
}
```

| 조건 | 네비게이션 | 설명 |
|------|----------|------|
| `corp_code` 존재 | ✅ 가능 | DB 등록 기업 (상장사) |
| `corp_code` 없음 | ❌ 불가 | 비상장사, 외부 기업 등 |
| 현재 회사와 동일 | ❌ 불가 | 순환 방지 |

#### 7.4.3 인터랙션 설계

**클릭 동작 구분:**

| 동작 | 현재 기능 | 개선 후 |
|------|----------|---------|
| **싱글클릭** | 상세패널 열기 | 유지 (상세패널) |
| **더블클릭** | 노드 재중심 (centerOnNode) | **해당 기업 관계도 이동** |
| **우클릭** | 없음 | 컨텍스트 메뉴 (옵션) |

**NodeDetailPanel 버튼:**

```
┌─────────────────────────────────────┐
│ [회사명] 삼성전자                     │
│ 코드: 00126380                       │
│                                      │
│ 관계형리스크: B+                      │
│ RaymondsIndex: 75.2 (B+)            │
│                                      │
│ ┌─────────────────────────────────┐ │
│ │  👆 노드로 이동                   │ │  ← 기존 버튼
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │  🔗 이 회사 관계도 보기           │ │  ← 신규 버튼 (corp_code 있을 때만)
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │  📊 분석 보고서 보기              │ │  ← 기존 버튼
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

#### 7.4.4 시각적 피드백

**DB 기업 vs 비DB 기업 구분:**

| 요소 | DB 기업 (이동 가능) | 비DB 기업 (이동 불가) |
|------|-------------------|---------------------|
| 커서 | `pointer` | `default` |
| 호버 효과 | 밝은 글로우 + 테두리 강조 | 기본 호버 |
| 툴팁 | "더블클릭: 관계도 이동" | 없음 |
| 노드 테두리 | 실선 (3px) | 점선 (2px) |

**ForceGraph 노드 스타일:**

```typescript
// DB 기업 노드 (corp_code 존재)
const dbCompanyStyle = {
  cursor: 'pointer',
  stroke: COMPANY_STROKE_COLOR,  // amber-500
  strokeWidth: 3,
  strokeDasharray: 'none',
}

// 비DB 기업 노드 (corp_code 없음)
const nonDbCompanyStyle = {
  cursor: 'default',
  stroke: '#6B7280',  // gray-500
  strokeWidth: 2,
  strokeDasharray: '4,2',  // 점선
}
```

#### 7.4.5 네비게이션 히스토리

**기존 구현 활용 (graphStore.ts):**

| 기능 | 구현 상태 | 설명 |
|------|----------|------|
| `pushNavigation()` | ✅ 완료 | 새 기업 방문 시 히스토리 추가 |
| `goBack()` / `goForward()` | ✅ 완료 | 뒤로/앞으로 이동 |
| `Breadcrumb` 컴포넌트 | ✅ 완료 | 탐색 경로 시각화 |
| 키보드 단축키 | ✅ 완료 | Alt+←/→ 지원 |

**탐색 경로 예시:**

```
삼성전자 → 삼성SDI → SK하이닉스 → LG에너지솔루션
    ↑                              ↑
  시작점                         현재 위치
```

#### 7.4.6 이용권 체크 연동

**이동 전 사전 체크:**

```typescript
const handleNavigateToCompany = async (node: GraphNode) => {
  if (!node.corp_code) return

  // 이용권 사전 체크 API 호출
  const canQuery = await checkCanQuery(node.corp_code)

  if (!canQuery.can_query) {
    // 모달 표시: "이용권이 필요합니다"
    showSubscriptionModal(canQuery.message)
    return
  }

  // 네비게이션 실행
  pushNavigation(node.corp_code, node.name)
  navigate(`/company/${node.corp_code}/graph`)
}
```

#### 7.4.7 구현 파일 목록

| 파일 | 수정 내용 | 우선순위 |
|------|----------|---------|
| `ForceGraph.tsx` | 더블클릭 핸들러 변경, 시각적 구분 추가 | HIGH |
| `NodeDetailPanel.tsx` | "관계도 보기" 버튼 활성화 | HIGH |
| `GraphPage.tsx` | 이용권 체크 연동 | MEDIUM |
| `graph.ts` (types) | `isNavigable` 필드 추가 (옵션) | LOW |

#### 7.4.8 예외 처리

| 시나리오 | 처리 방법 |
|---------|----------|
| 이용권 부족 | 모달 표시, 현재 화면 유지 |
| 네트워크 오류 | 토스트 메시지, 재시도 버튼 |
| 기업 데이터 없음 | "데이터 준비 중" 메시지 |
| 현재 회사 클릭 | 무시 (순환 방지) |

---

## 8. 구현 로드맵

### Phase A: 스키마 확장 (1주)

| 작업 | 우선순위 | 소요 |
|------|---------|------|
| companies 테이블 컬럼 추가 | HIGH | 0.5일 |
| officers 테이블 컬럼 추가 | HIGH | 0.5일 |
| major_shareholders 테이블 생성 | MEDIUM | 0.5일 |
| risk_scores 테이블 생성 | HIGH | 0.5일 |
| affiliates 테이블 활성화 | MEDIUM | 0.5일 |
| Alembic 마이그레이션 생성 | HIGH | 0.5일 |

### Phase B: 데이터 수집 스크립트 (1주)

| 작업 | 우선순위 | 소요 |
|------|---------|------|
| 대주주 현황 수집 스크립트 | MEDIUM | 1일 |
| 계열사 현황 수집 스크립트 | MEDIUM | 1일 |
| 종합 리스크 점수 계산 스크립트 | HIGH | 1일 |
| 기존 데이터 마이그레이션 | HIGH | 1일 |

### Phase C: API 확장 (1주)

| 작업 | 우선순위 | 소요 |
|------|---------|------|
| /stakeholders 통합 API 구현 | HIGH | 2일 |
| /executives/{id}/other-positions API | HIGH | 1일 |
| /cb-participants/{id}/other-investments API | HIGH | 1일 |
| /network 시각화 API 확장 | HIGH | 1일 |

### Phase D: Frontend 구현 (2주)

| 작업 | 우선순위 | 소요 |
|------|---------|------|
| 메인 검색 페이지 | HIGH | 1일 |
| 기업 분석 결과 페이지 레이아웃 | HIGH | 1일 |
| 이해관계자 360° 통합 뷰 | HIGH | 2일 |
| 각 섹션 아코디언 컴포넌트 | HIGH | 2일 |
| 관계망 시각화 (neovis.js) | HIGH | 3일 |
| 노드 팝업/상세 패널 | MEDIUM | 1일 |
| 반응형 디자인 | MEDIUM | 1일 |

### Phase E: 통합 및 최적화 (1주)

| 작업 | 우선순위 | 소요 |
|------|---------|------|
| API-Frontend 통합 테스트 | HIGH | 1일 |
| Neo4j 쿼리 최적화 | HIGH | 1일 |
| Redis 캐싱 적용 | MEDIUM | 1일 |
| 성능 테스트 | HIGH | 1일 |
| 버그 수정 | HIGH | 1일 |

---

## 9. 기술 스택

### Backend (기존 유지)
- FastAPI 0.104+
- SQLAlchemy 2.0
- Alembic
- PostgreSQL 15
- Neo4j 5.15
- Redis 7

### Frontend (신규)
- React 18 + TypeScript
- Vite
- Tailwind CSS
- neovis.js 2.1.0
- D3.js 7.9.0
- React Query (TanStack Query)
- Recharts (차트)

### 인프라
- Docker + Docker Compose
- Railway (배포)

---

## 10. 체크리스트

### Backend 완료 ✅
- [x] PostgreSQL 스키마 생성
- [x] Neo4j 그래프 구축
- [x] 기업 검색 API
- [x] 기업 기본정보 API
- [x] 임원 경력 API
- [x] CB 투자자 API
- [x] 재무지표 API
- [x] 리스크 신호 API

### Backend 추가 작업 ⏳
- [ ] major_shareholders 테이블 및 API
- [ ] affiliates 데이터 수집
- [ ] risk_scores 종합 계산 테이블
- [ ] /stakeholders 통합 API
- [ ] /other-positions API 확장
- [ ] /other-investments API 확장

### Frontend 85% 완료 ✅
- [x] React 프로젝트 초기화
- [x] D3.js 기반 관계도 시각화 (neovis.js 대체)
- [x] 메인 검색 페이지
- [x] 기업 분석 페이지 (관계도/리포트 탭)
- [x] 이해관계자 360° 뷰
- [x] 그래프 시각화 (Force-Directed Graph)
- [x] 노드 상세 패널
- [x] 반응형 디자인
- [x] 다크 테마 적용 (2026-01-20)
- [x] 미니 주가 차트 (MiniStockChart) 추가 (2026-01-20)
- [ ] iPad 반응형 최적화 (진행 중)

---

## 11. 문서 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2024-11 | IMPLEMENTATION_PLAN.md 초기 작성 |
| 2.0 | 2025-11-20 | Backend 구현 완료, FINAL_STATUS.md |
| 3.0 | 2025-11-02 | 화면기획서 v3.0 작성 |
| 4.0 | 2025-12-03 | 기존 구현 + 화면기획서 통합본 작성 |
| 4.1 | 2025-12-05 | 관계형 리스크 기획서 v3.2 반영 (인적/CB 리스크 상세 계산식, 투자등급 체계, 데이터 신뢰도, API 응답 형식 추가) |
| 4.2 | 2025-12-05 | 관계형 리스크 기획서 v3.2.1 반영: **분석 기간 정책** 추가 (모수=최근 1년, 이력=전체 3.5년), **CB 발행 빈도** 기준 변경 (연평균→최근 1년, 0회=0점 추가), **CB 발행 규모** 임계값 하향 (≥500억→≥200억), API 응답에 analysis_period 필드 추가 |
| 4.3 | 2025-12-15 | 문서 정보 갱신 |
| 4.4 | 2026-01-20 | **Frontend 85% 완료** 반영: 다크 테마 전면 적용 (RaymondsIndex 4개 컴포넌트, severityConfig), MiniStockChart 컴포넌트 추가 (주의 필요 기업 카드에 1년 주가 차트), Redis 캐시 연결 완료 |

---

## 12. 비즈니스 모델 및 수익화 전략

### 12.1 서비스 티어 구조

| 티어 | 월 요금 | 대상 | 주요 기능 |
|------|--------|------|----------|
| **Free** | 무료 | 개인 투자자 | 기업 검색 (일 10회), 기본 리스크 점수, 임원 현황 조회 |
| **Basic** | ₩29,000 | 활성 개인 투자자 | 무제한 검색, 전체 이해관계자 뷰, CB 투자자 타사 이력 |
| **Pro** | ₩99,000 | 전문 투자자 | 네트워크 시각화, 리스크 알림, API 접근 (일 100회), 엑셀 다운로드 |
| **Enterprise** | 협의 | 기관/연구기관 | 화이트라벨, 전용 API, 맞춤 보고서, SLA 보장, 온프레미스 옵션 |

### 12.2 수익 모델 상세

```
┌─────────────────────────────────────────────────────────────────┐
│                      수익 구조 (목표)                            │
├─────────────────────────────────────────────────────────────────┤
│  구독 수익 (B2C)                                    60%         │
│  ├── Free → Basic 전환율 목표: 5%                              │
│  ├── Basic → Pro 전환율 목표: 20%                              │
│  └── 연간 결제 할인: 20%                                        │
├─────────────────────────────────────────────────────────────────┤
│  기관 라이선스 (B2B)                                30%         │
│  ├── 증권사 리서치센터                                          │
│  ├── 자산운용사                                                 │
│  └── 금융 규제기관                                              │
├─────────────────────────────────────────────────────────────────┤
│  데이터 API (B2B2C)                                10%         │
│  └── 핀테크 앱, 증권 플랫폼 연동                                │
└─────────────────────────────────────────────────────────────────┘
```

### 12.3 핵심 성과 지표 (KPI)

| 지표 | 목표 (론칭 후 6개월) | 목표 (12개월) |
|------|---------------------|---------------|
| MAU (월간 활성 사용자) | 10,000 | 50,000 |
| 유료 전환율 | 3% | 5% |
| MRR (월간 반복 수익) | ₩15M | ₩100M |
| 기업 고객 수 | 3개사 | 10개사 |
| 이탈률 (월간) | <10% | <5% |
| NPS (순추천지수) | 40+ | 50+ |

### 12.4 가격 전략 근거

- **경쟁사 벤치마크**: 유사 금융정보 서비스 (에프앤가이드, 와이즈에프앤 등) 월 5~30만원
- **차별화 포인트**: 이해관계자 네트워크 분석은 타사 미제공 기능
- **가치 기반**: 1건의 투자 손실 방지 가치 >> 월 구독료

---

## 13. 사용자 시나리오 및 User Journey

### 13.1 핵심 사용자 페르소나

#### 페르소나 1: 김투자 (개인 투자자)
```yaml
프로필:
  나이: 35세
  직업: IT 회사 개발자
  투자 경력: 5년
  투자 규모: 5,000만원
  고민: "좋아 보이는 기업인데, 뭔가 찜찜해서 확인하고 싶다"

주요 시나리오:
  1. 투자 전 검증: 관심 기업의 리스크 점수 확인
  2. CB 발행 공시 확인 시: CB 투자자들의 타사 투자 이력 검토
  3. 임원 변경 발생 시: 새 임원의 과거 경력 추적

기대 가치:
  - 투자 전 5분 내 기업 리스크 파악
  - "부실기업 전문 투자자" 패턴 조기 발견
```

#### 페르소나 2: 박애널 (증권사 리서치)
```yaml
프로필:
  나이: 32세
  직업: 증권사 리서치센터 연구원
  담당: 중소형주 20개사
  고민: "담당 기업의 숨겨진 리스크를 놓치면 안 된다"

주요 시나리오:
  1. 커버리지 기업 정기 모니터링
  2. 신규 커버리지 기업 실사
  3. 기업 간 인적 네트워크 분석

기대 가치:
  - 기업 간 연결고리 자동 탐지
  - 주간/월간 리스크 변동 알림
```

### 13.2 User Journey Map

```
[신규 사용자 Journey]

검색 시작 ─────────────────────────────────────────────────────▶ 이탈/전환

│
├─ Step 1: 검색 (Acquisition)
│    └─ 기업명/종목코드 입력
│    └─ 자동완성으로 빠른 선택
│    └─ 💡 Free: 일 10회 제한 → "더 보려면 가입하세요" CTA
│
├─ Step 2: 기본 정보 확인 (Activation)
│    └─ 리스크 점수 게이지 확인
│    └─ 이해관계자 요약 카드 확인
│    └─ 💡 Free: 임원 3명까지만 표시 → "전체 보기" 유도
│
├─ Step 3: 상세 탐색 (Engagement)
│    └─ 이해관계자 상세 정보 확인
│    └─ 타사 이력 조회 클릭
│    └─ 💡 Free: 타사 이력 블러 처리 → Basic 유도
│
├─ Step 4: 네트워크 시각화 (Aha Moment)
│    └─ 그래프 뷰 전환
│    └─ 연결된 기업/인물 발견
│    └─ 💡 Basic: 1단계만 → Pro에서 2단계 확장
│
├─ Step 5: 알림 설정 (Retention)
│    └─ 관심 기업 북마크
│    └─ 리스크 변동 알림 설정
│    └─ 💡 Pro 전용 기능
│
└─ Step 6: 공유/내보내기 (Revenue)
     └─ 분석 결과 PDF 다운로드
     └─ 동료에게 공유
     └─ 💡 Pro 전용 기능
```

### 13.3 핵심 사용자 흐름 (Happy Path)

```
[시나리오: "엑시온그룹 투자 전 검증"]

1. 검색창에 "엑시온" 입력
   → 자동완성: "엑시온그룹 (900260, KOSDAQ)"

2. 기업 선택 → 분석 결과 페이지 로딩 (< 2초)

3. 종합 리스크 대시보드 확인
   → RaymondsRisk: 68점 (HIGH) ⚠️
   → 재무건전성: 45점 (MEDIUM)

4. 이해관계자 360° 요약 확인
   → 임원 5명 (타사 재직 18건, 고위험 2명)
   → CB 투자자 23명 (고위험 5명) ← 클릭

5. CB 투자자 "이상민" 타사 투자 이력 확인
   → 총 12개사 투자
   → 적자기업 비율 50%
   → 상장폐지 기업 2개사 ← 경고!

6. 네트워크 그래프로 시각화
   → "이상민"이 연결된 다른 기업들 확인
   → 패턴: 비슷한 업종의 소형주에만 투자

7. 결론: 투자 보류 결정
   → 북마크하고 모니터링 알림 설정
```

---

## 14. 오류 처리 및 예외 상황

### 14.1 시스템 오류 처리

| 오류 유형 | HTTP 코드 | 사용자 메시지 | 복구 전략 |
|----------|----------|--------------|----------|
| DB 연결 실패 | 503 | "일시적인 서버 오류입니다. 잠시 후 다시 시도해주세요." | 자동 재시도 (3회), 장애 알림 |
| Neo4j 쿼리 타임아웃 | 504 | "그래프 로딩에 시간이 걸리고 있습니다. 새로고침해주세요." | 쿼리 취소, 간소화된 결과 반환 |
| DART API 실패 | 502 | "공시 데이터를 불러오는 중 오류가 발생했습니다." | 캐시 데이터 사용, 배치 재시도 |
| 인증 만료 | 401 | "로그인이 만료되었습니다. 다시 로그인해주세요." | 리프레시 토큰 시도, 로그인 리다이렉트 |
| 권한 없음 | 403 | "이 기능은 Pro 플랜에서 사용 가능합니다." | 업그레이드 CTA 표시 |
| 요청 한도 초과 | 429 | "일일 조회 한도를 초과했습니다. 내일 다시 시도하거나 업그레이드하세요." | 남은 시간 표시, 업그레이드 CTA |

### 14.2 데이터 예외 상황

| 상황 | 처리 방법 | UI 표시 |
|-----|----------|---------|
| 기업 정보 없음 | 404 + 유사 기업 추천 | "해당 기업을 찾을 수 없습니다. 혹시 이 기업을 찾으셨나요?" |
| 임원 정보 부재 | 빈 배열 반환 | "등록된 임원 정보가 없습니다." |
| 재무제표 미제출 | null 필드 처리 | "2024년 재무제표가 아직 공시되지 않았습니다." (회색 표시) |
| 동명이인 임원 | 생년월일 기반 구분 | 이름 옆 "(1965년생)" 표시, 불확실 시 "동명이인 가능" 경고 |
| 그래프 노드 과다 | 상위 100개 제한 | "연결된 관계가 많습니다. 상위 100개만 표시합니다." + 필터 안내 |

### 14.3 비정상 데이터 처리

```python
# 데이터 유효성 검사 예시
class DataValidator:
    @staticmethod
    def validate_risk_score(score: float) -> float:
        """리스크 점수 범위 검증"""
        if score is None:
            return None  # 계산 불가 표시
        if score < 0:
            logger.warning(f"음수 리스크 점수 발견: {score}")
            return 0
        if score > 100:
            logger.warning(f"100 초과 리스크 점수: {score}")
            return 100
        return round(score, 1)

    @staticmethod
    def validate_birth_date(birth_date: str) -> Optional[str]:
        """생년월일 형식 검증"""
        if not birth_date:
            return None
        # YYYY.MM 또는 YYYY-MM 형식만 허용
        pattern = r'^(19|20)\d{2}[.\-](0[1-9]|1[0-2])$'
        if re.match(pattern, birth_date):
            return birth_date.replace('-', '.')
        logger.warning(f"비정상 생년월일 형식: {birth_date}")
        return None
```

### 14.4 네트워크 오류 처리 (Frontend)

```typescript
// API 호출 에러 핸들링
const useCompanyData = (corpCode: string) => {
  return useQuery({
    queryKey: ['company', corpCode],
    queryFn: () => fetchCompany(corpCode),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    onError: (error) => {
      if (error.response?.status === 429) {
        toast.error('일일 조회 한도를 초과했습니다.');
      } else if (error.response?.status === 503) {
        toast.error('서버 점검 중입니다. 잠시 후 다시 시도해주세요.');
      } else {
        toast.error('오류가 발생했습니다. 새로고침해주세요.');
      }
    },
    staleTime: 5 * 60 * 1000, // 5분 캐시
  });
};
```

---

## 15. 알림 시스템

### 15.1 알림 유형 및 우선순위

| 알림 유형 | 트리거 조건 | 우선순위 | 채널 |
|----------|------------|---------|------|
| **리스크 급등** | 리스크 점수 20점 이상 상승 | CRITICAL | 푸시, 이메일, 인앱 |
| **CB 발행 공시** | 북마크 기업 CB 결정 공시 | HIGH | 푸시, 인앱 |
| **임원 변경** | 대표이사/감사 변경 | HIGH | 푸시, 인앱 |
| **상장폐지 경고** | 관리종목 지정/상폐 예고 | CRITICAL | 푸시, 이메일, 인앱 |
| **재무제표 공시** | 분기/사업보고서 제출 | MEDIUM | 인앱 |
| **고위험 투자자 참여** | 블랙리스트 투자자 CB 인수 | HIGH | 푸시, 인앱 |
| **주간 리포트** | 매주 월요일 오전 8시 | LOW | 이메일 |

### 15.2 알림 설정 UI

```
┌─────────────────────────────────────────────────────────┐
│  알림 설정                                              │
├─────────────────────────────────────────────────────────┤
│  📊 리스크 변동 알림                                    │
│     ├─ [✓] 리스크 점수 급등 (20점 이상)                │
│     ├─ [✓] 리스크 등급 변경 (예: MEDIUM → HIGH)        │
│     └─ [ ] 소폭 변동도 알림 (5점 이상)                  │
│                                                         │
│  📰 공시 알림                                           │
│     ├─ [✓] CB/BW 발행 결정                             │
│     ├─ [✓] 임원 변경                                   │
│     └─ [ ] 모든 공시                                    │
│                                                         │
│  ⚠️ 긴급 알림                                          │
│     ├─ [✓] 관리종목 지정                               │
│     ├─ [✓] 상장폐지 관련                               │
│     └─ [✓] 감사의견 거절/한정                          │
│                                                         │
│  📧 알림 채널                                           │
│     ├─ [✓] 푸시 알림                                   │
│     ├─ [✓] 이메일 (daily digest)                       │
│     └─ [ ] SMS (Pro 전용)                              │
│                                                         │
│  🕐 조용한 시간                                         │
│     └─ 22:00 ~ 08:00 푸시 알림 끄기                     │
└─────────────────────────────────────────────────────────┘
```

### 15.3 알림 아키텍처

```
[공시 수집 배치] ──▶ [이벤트 큐 (Redis)] ──▶ [알림 워커]
       │                                          │
       │                                          ├──▶ [FCM 푸시]
       │                                          ├──▶ [이메일 (SES)]
       └──▶ [리스크 재계산] ──▶ [점수 비교] ──────┴──▶ [인앱 알림 저장]

알림 워커 로직:
1. 이벤트 수신 (예: CB_ISSUED)
2. 해당 기업 북마크한 사용자 조회
3. 각 사용자의 알림 설정 확인
4. 설정에 따라 채널별 알림 발송
5. 알림 이력 저장 (notifications 테이블)
```

### 15.4 알림 테이블 스키마

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id),

    notification_type VARCHAR(50) NOT NULL,  -- RISK_SPIKE, CB_ISSUED, OFFICER_CHANGE 등
    priority VARCHAR(20) NOT NULL,           -- CRITICAL, HIGH, MEDIUM, LOW
    title VARCHAR(200) NOT NULL,
    body TEXT,
    data JSONB,                              -- 추가 메타데이터

    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    sent_channels VARCHAR(50)[],             -- ['push', 'email', 'inapp']

    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_notifications_user_unread (user_id, is_read, created_at DESC)
);
```

---

## 16. 데이터 신선도 및 업데이트 정책

### 16.1 데이터 소스별 업데이트 주기

| 데이터 소스 | 업데이트 주기 | 방법 | 지연 허용치 |
|------------|--------------|------|------------|
| DART 공시 목록 | 실시간 (5분) | API 폴링 | 10분 |
| CB 공시 상세 | 1시간 | 신규 공시 감지 시 파싱 | 2시간 |
| 사업보고서 임원 정보 | 분기 (보고서 제출 후) | 배치 파싱 | 1일 |
| 재무제표 | 분기 | DART API + 파싱 | 1일 |
| 리스크 점수 | 일 1회 (새벽 3시) | 배치 계산 | 24시간 |
| 그래프 동기화 (Neo4j) | 6시간 | PostgreSQL → Neo4j | 12시간 |
| 시가총액/주가 | 일 1회 (장 마감 후) | 외부 API | 다음 영업일 |

### 16.2 데이터 신선도 표시

```
┌─────────────────────────────────────────────────────────┐
│  엑시온그룹 (900260)                                    │
│                                                         │
│  리스크 점수: 68.2점                                    │
│  ⏱️ 업데이트: 2025-12-03 03:00 (7시간 전)              │
│                                                         │
│  재무제표: 2024년 3분기                                 │
│  ⏱️ 공시일: 2024-11-14                                 │
│                                                         │
│  임원 현황                                              │
│  ⏱️ 기준: 2024년 반기보고서 (2024-08-14)               │
│  ⚠️ 최신 보고서 반영 대기 중                           │
└─────────────────────────────────────────────────────────┘
```

### 16.3 캐시 정책

```yaml
캐시 계층:
  L1 (Redis):
    - 회사 기본정보: TTL 1시간
    - 리스크 점수: TTL 24시간
    - 검색 결과: TTL 30분
    - 그래프 데이터: TTL 6시간

  L2 (CDN/Browser):
    - 정적 자산: max-age=1년 (versioned)
    - API 응답: max-age=5분, stale-while-revalidate=1시간

캐시 무효화 트리거:
  - 신규 공시 감지 → 해당 회사 캐시 무효화
  - 리스크 점수 재계산 → 전체 리스크 캐시 무효화
  - 수동 데이터 수정 → 해당 엔티티 캐시 무효화
```

### 16.4 데이터 갱신 모니터링

```python
# 데이터 신선도 체크 API
GET /api/v1/health/data-freshness

Response:
{
  "status": "HEALTHY",
  "last_checked": "2025-12-03T10:00:00Z",
  "sources": {
    "dart_disclosures": {
      "last_fetch": "2025-12-03T09:55:00Z",
      "records_today": 1234,
      "status": "OK"
    },
    "risk_scores": {
      "last_calculation": "2025-12-03T03:00:00Z",
      "companies_calculated": 2648,
      "status": "OK"
    },
    "neo4j_sync": {
      "last_sync": "2025-12-03T06:00:00Z",
      "nodes_synced": 112161,
      "status": "OK"
    }
  },
  "alerts": []
}
```

---

## 17. 성능 지표 및 SLA

### 17.1 응답 시간 목표 (SLO)

| 엔드포인트 | P50 | P95 | P99 | 타임아웃 |
|-----------|-----|-----|-----|---------|
| GET /companies (검색) | 100ms | 300ms | 500ms | 2s |
| GET /companies/{id} (상세) | 150ms | 400ms | 800ms | 3s |
| GET /stakeholders (이해관계자) | 300ms | 800ms | 1.5s | 5s |
| GET /network (그래프) | 500ms | 1.5s | 3s | 10s |
| GET /risk/analysis | 200ms | 500ms | 1s | 3s |
| Neo4j Cypher (간단) | 50ms | 150ms | 300ms | 2s |
| Neo4j Cypher (복잡 경로) | 200ms | 800ms | 2s | 10s |

### 17.2 가용성 목표

| 서비스 티어 | 월간 가용성 | 허용 다운타임 | 지원 시간 |
|------------|------------|--------------|----------|
| Free/Basic | 99.0% | 7.3시간/월 | 이메일 (48시간 응답) |
| Pro | 99.5% | 3.6시간/월 | 이메일 (24시간 응답) |
| Enterprise | 99.9% | 43분/월 | 24/7 전화/채팅 (1시간 응답) |

### 17.3 동시 접속 처리

```yaml
트래픽 예상:
  동시 사용자: 500명 (피크 1,000명)
  일일 요청: 100,000건
  피크 시간: 오전 9시~10시, 오후 2시~3시

인프라 스케일:
  API 서버: 2~4 인스턴스 (Auto Scaling)
  PostgreSQL: 1 Primary + 1 Read Replica
  Neo4j: 1 인스턴스 (8GB RAM, 4 vCPU)
  Redis: 1 인스턴스 (2GB)
```

### 17.4 모니터링 및 알림

```yaml
메트릭 수집:
  - API 응답 시간 (histogram)
  - DB 쿼리 시간 (slow query > 1s)
  - 에러율 (5xx, 4xx)
  - 활성 연결 수
  - 캐시 히트율

알림 규칙:
  - P95 응답시간 > 2s: WARNING
  - P95 응답시간 > 5s: CRITICAL
  - 에러율 > 1%: WARNING
  - 에러율 > 5%: CRITICAL (PagerDuty 호출)
  - DB 연결 풀 > 80%: WARNING

도구:
  - Prometheus + Grafana (메트릭)
  - Sentry (에러 추적)
  - AWS CloudWatch (인프라)
```

---

## 18. 테스트 전략

### 18.1 테스트 계층

```
┌─────────────────────────────────────────────────────┐
│                    E2E 테스트                       │
│            (Playwright, 주요 User Journey)          │
│                    커버리지: 30%                    │
├─────────────────────────────────────────────────────┤
│                 통합 테스트 (API)                   │
│            (pytest + httpx, 실제 DB)                │
│                    커버리지: 60%                    │
├─────────────────────────────────────────────────────┤
│                    단위 테스트                      │
│    (pytest, 리스크 계산 로직, 데이터 유효성)        │
│                    커버리지: 80%                    │
└─────────────────────────────────────────────────────┘
```

### 18.2 테스트 케이스 분류

| 카테고리 | 우선순위 | 예시 |
|---------|---------|------|
| 리스크 계산 정확성 | P0 | 인적 리스크 점수 산출 공식 검증 |
| 데이터 무결성 | P0 | 임원-회사 매핑 정확성 |
| API 응답 형식 | P1 | 스키마 일치, 필수 필드 존재 |
| 그래프 쿼리 정확성 | P1 | WORKS_AT 관계 연결 검증 |
| 에러 핸들링 | P1 | 존재하지 않는 기업 조회 시 404 |
| 인증/권한 | P1 | 무료 사용자 → 유료 기능 차단 |
| 성능 | P2 | 대량 노드 그래프 렌더링 시간 |

### 18.3 테스트 데이터 전략

```python
# 테스트 데이터 시나리오
class TestDataScenarios:
    """테스트용 시나리오별 데이터셋"""

    NORMAL_COMPANY = {
        "corp_code": "TEST001",
        "name": "정상기업",
        "risk_score": 25.0,
        "officers": 5,
        "cb_count": 0
    }

    HIGH_RISK_COMPANY = {
        "corp_code": "TEST002",
        "name": "고위험기업",
        "risk_score": 85.0,
        "officers": 30,
        "cb_count": 8,
        "loss_making": True
    }

    OFFICER_WITH_MULTIPLE_POSITIONS = {
        "name": "김다직",
        "birth_date": "1970.01",
        "companies": ["TEST001", "TEST002", "TEST003", "TEST004"]
    }

    SUSPICIOUS_CB_INVESTOR = {
        "name": "이투자",
        "investments": 12,
        "loss_company_ratio": 0.6,
        "delisted_count": 3
    }
```

### 18.4 CI/CD 파이프라인

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: pytest tests/unit -v --cov=app --cov-report=xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
      neo4j:
        image: neo4j:5.15-community
    steps:
      - name: Run integration tests
        run: pytest tests/integration -v

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Run E2E tests
        run: npx playwright test
```

---

## 19. 운영 및 유지보수

### 19.1 배포 전략

```yaml
배포 방식: Blue-Green Deployment

단계:
  1. 새 버전을 Green 환경에 배포
  2. 헬스체크 통과 확인
  3. 로드밸런서 트래픽 전환 (5% → 50% → 100%)
  4. 10분간 모니터링
  5. 이상 시 즉시 Blue로 롤백

롤백 트리거:
  - 에러율 > 2%
  - P95 응답시간 > 3s
  - 수동 롤백 명령
```

### 19.2 데이터 백업 정책

| 데이터 | 백업 주기 | 보관 기간 | 복원 시간 |
|-------|----------|----------|----------|
| PostgreSQL 전체 | 일 1회 (새벽 4시) | 30일 | < 1시간 |
| PostgreSQL 증분 | 1시간 | 7일 | < 15분 |
| Neo4j 스냅샷 | 일 1회 | 14일 | < 30분 |
| Redis | 필요 없음 (캐시) | - | - |
| 로그 (CloudWatch) | 실시간 | 90일 | 즉시 |

### 19.3 장애 대응 프로세스

```
┌─────────────────────────────────────────────────────────┐
│  장애 등급별 대응 절차                                  │
├─────────────────────────────────────────────────────────┤
│  SEV-1 (서비스 전체 장애)                               │
│  ├─ 탐지: 자동 (모니터링 알림)                         │
│  ├─ 대응: 5분 내 당직자 확인                           │
│  ├─ 에스컬레이션: 15분 내 리드 참여                    │
│  ├─ 목표 복구 시간: 30분                               │
│  └─ 사후 조치: 48시간 내 RCA 문서 작성                 │
├─────────────────────────────────────────────────────────┤
│  SEV-2 (핵심 기능 장애)                                 │
│  ├─ 탐지: 자동/수동                                    │
│  ├─ 대응: 30분 내 확인                                 │
│  ├─ 목표 복구 시간: 2시간                              │
│  └─ 사후 조치: 1주 내 개선 조치                        │
├─────────────────────────────────────────────────────────┤
│  SEV-3 (부분 기능 저하)                                 │
│  ├─ 탐지: 모니터링/사용자 리포트                       │
│  ├─ 대응: 다음 업무일 처리                             │
│  └─ 목표 복구 시간: 1주                                │
└─────────────────────────────────────────────────────────┘
```

### 19.4 정기 유지보수 작업

| 작업 | 주기 | 예상 소요 | 서비스 영향 |
|-----|------|----------|------------|
| DB 인덱스 최적화 | 월 1회 | 30분 | 없음 |
| Neo4j 메모리 튜닝 | 분기 1회 | 1시간 | 재시작 필요 |
| 보안 패치 적용 | 수시 | 1시간 | 롤링 재시작 |
| 로그 정리 | 주 1회 | 자동 | 없음 |
| 데이터 정합성 검사 | 주 1회 | 10분 | 없음 |

---

## 19.5 구독 및 조회 시스템 (2026-01-21 업데이트)

### 19.5.1 이용권 체계

| 이용권 | 가격 | 월 조회 제한 | 특징 |
|--------|------|-------------|------|
| Free | 무료 | 0건 | 검색만 가능 (상세 조회 불가) |
| **Trial** | 무료 | 1건 | 회원가입 시 자동 부여, **30일 후 만료** |
| Light | 3,000원/월 | 30건 | 기본 분석 기능 |
| Max | 30,000원/월 | 무제한 | 전체 기능 + API |

### 19.5.2 Trial 이용권 정책 (2026-01-21)

**핵심 로직**:
- 회원가입 시 자동으로 `trial` 등급 부여
- **30일 후 자동 만료** → `free` 등급과 동일 취급
- Trial 기간 내 최대 1건 조회 가능
- **이전 조회 기업 재조회 허용** (30일 이내, 추가 이용권 미차감)

**만료 체크 로직** (`usage_service.py`):
```python
if tier == "trial":
    created_at = user.created_at
    trial_expires = created_at + timedelta(days=30)
    if now > trial_expires:
        # Trial 만료 → free와 동일 취급
```

### 19.5.3 조회한 기업 목록 기능 (2026-01-21 신규)

**목적**: 유료 회원이 과거에 조회한 기업을 다시 확인할 수 있도록 함

**테이블**: `company_view_history`
| 컬럼 | 설명 |
|------|------|
| user_id | 조회한 사용자 |
| company_id | 조회한 기업 |
| company_name | 기업명 스냅샷 |
| ticker | 종목코드 스냅샷 |
| market | 시장 스냅샷 |
| viewed_at | 조회 시간 |

**API 엔드포인트**:
```
GET /api/companies/view-history/list
  - page: 페이지 번호 (1부터)
  - page_size: 페이지당 항목 수 (최대 100)
```

**접근 권한**:
- Free: 접근 불가 (403)
- Trial (만료 전): 접근 가능
- Trial (만료 후): 접근 불가 (403)
- Light/Max: 접근 가능

**관련 파일**:
- Backend: `app/routes/view_history.py`, `app/models/subscriptions.py`
- Frontend: `pages/ViewedCompaniesPage.tsx`, `api/company.ts`

### 19.5.4 조회 제한 UX 개선 (2026-01-21)

**사전 체크 API** (`/api/subscription/can-query/{company_id}`):
```python
# Backend: subscription.py
@router.get("/can-query/{company_id}")
async def check_can_query(company_id: str, ...):
    """
    기업 클릭 시 페이지 이동 전에 호출하여 조회 가능 여부 확인

    Returns:
        {
            "allowed": bool,        # 조회 가능 여부
            "reason": str,          # 사유 메시지
            "used": int,            # 사용량
            "limit": int,           # 한도
            "is_requery": bool      # 이전 조회 기업 재조회 여부
        }
    """
```

**Frontend 구현** (`MainSearchPage.tsx`):
```typescript
// 기업 클릭 시 사전 체크
const handleSelectCompany = async (company) => {
  // 1. 로그인 체크
  // 2. 관리자 체크 (항상 통과)
  // 3. 이용권 유효성 체크
  // 4. 사전 조회 API 호출
  const response = await apiClient.get(`/api/subscription/can-query/${company.id}`)

  if (!response.data.allowed) {
    // 모달 표시, 페이지 이동 안 함
    setNoQuotaMessage(response.data.reason)
    setShowNoQuotaModal(true)
    return
  }

  // 조회 가능 - 관계도 페이지로 이동
  navigate(`/company/${company.id}/graph`)
}
```

**UX 개선 포인트**:
1. **페이지 이동 전 사전 체크**: 기업 클릭 시 API로 조회 가능 여부 먼저 확인
2. **에러 화면 방지**: 조회 불가 시 그래프 페이지로 이동하지 않고 검색 화면에서 모달 표시
3. **서버 메시지 표시**: 백엔드에서 상황에 맞는 메시지 반환 (Trial/Free/유료 등)
4. **재조회 허용**: Trial 사용자가 이전에 조회한 기업은 30일 이내 재조회 가능
5. **자연스러운 유도**: 모달에서 이용권 구매 페이지로 연결

### 19.5.5 공유 Header 컴포넌트 (2026-01-21)

모든 페이지에 일관된 Header 컴포넌트 적용 완료.

**적용 페이지**:
- MainSearchPage, GraphPage, PricingPage
- AboutPage, ContactPage, PrivacyPage, TermsPage
- PaymentSuccessPage, PaymentFailPage
- RaymondsIndexRankingPage, ViewedCompaniesPage

**Header 기능**:
- 로고 클릭 → 홈 이동
- 로그인/로그아웃 버튼
- 유료 회원: "조회한 기업" 메뉴 표시

---

## 20. 경쟁 분석

### 20.1 직접 경쟁사

| 서비스 | 강점 | 약점 | 가격 |
|-------|------|------|------|
| **에프앤가이드 DataGuide** | 풍부한 재무 데이터, 기관 신뢰도 | 이해관계자 분석 부재, 복잡한 UI | 월 30만원+ |
| **와이즈에프앤** | 실시간 공시, API 제공 | 네트워크 분석 없음 | 월 5~50만원 |
| **씽크풀** | 기업 평판/뉴스 분석 | 정량적 리스크 부족 | 무료~월 5만원 |

### 20.2 간접 경쟁사

| 서비스 | 영역 | 우리와의 차별점 |
|-------|------|----------------|
| **네이버 금융** | 기업 기본정보, 차트 | 무료지만 분석 기능 없음 |
| **전자공시 DART** | 원천 공시 데이터 | 가공/분석 없이 원본만 제공 |
| **알파스퀘어** | 퀀트 투자 도구 | 기업 네트워크 분석 없음 |

### 20.3 경쟁 우위 요소

```
┌─────────────────────────────────────────────────────────┐
│  RaymondsRisk 차별화 포인트                             │
├─────────────────────────────────────────────────────────┤
│  1. 이해관계자 360° 통합 뷰 (업계 유일)                 │
│     - 임원/CB투자자/대주주/계열사 한 화면              │
│                                                         │
│  2. 타사 이력 추적 (업계 유일)                          │
│     - "이 사람이 과거에 어떤 회사에서 일했나?"          │
│     - "이 투자자가 투자한 다른 회사는?"                 │
│                                                         │
│  3. 그래프 시각화 (차별화)                              │
│     - Neo4j 기반 실시간 네트워크 그래프                 │
│     - 클릭 한 번으로 관계 탐색                          │
│                                                         │
│  4. 개인 투자자 친화적 가격                             │
│     - 무료 티어 제공                                    │
│     - 월 3만원으로 핵심 기능 사용                       │
└─────────────────────────────────────────────────────────┘
```

### 20.4 시장 기회

- **TAM (전체 시장)**: 국내 주식 투자자 약 1,400만 명
- **SAM (유효 시장)**: 능동적 개인 투자자 약 300만 명
- **SOM (획득 목표 시장)**: 정보 서비스 유료 사용 의향자 약 30만 명 (1% 침투 시 3,000명)

---

## 21. 접근성 및 법적 준수

### 21.1 접근성 가이드라인

```yaml
WCAG 2.1 AA 준수 목표:

색상 대비:
  - 텍스트 대비율: 최소 4.5:1
  - 리스크 레벨 표시: 색상 + 텍스트 라벨 병행
  - 그래프 노드: 색상 + 아이콘 병행

키보드 접근성:
  - 모든 기능 Tab 키로 접근 가능
  - 그래프 노드: 방향키로 이동 가능
  - 포커스 표시 명확

스크린 리더:
  - ARIA 레이블 적용
  - 그래프: 텍스트 대체 설명 제공
  - 동적 콘텐츠: aria-live 적용
```

### 21.2 개인정보 보호

| 항목 | 수집 여부 | 보관 기간 | 근거 |
|-----|----------|----------|------|
| 이메일 | 수집 (회원가입) | 탈퇴 후 30일 | 서비스 제공 |
| 결제 정보 | 외부 PG 위탁 | 저장 안 함 | 전자상거래법 |
| 검색 이력 | 수집 | 1년 | 서비스 개선 (동의 기반) |
| 임원 정보 | 공개 정보 활용 | 무기한 | DART 공시 데이터 |

### 21.3 법적 고지

```
서비스 면책 조항 (필수 표시):

"본 서비스에서 제공하는 정보는 투자 참고용이며,
투자 권유 또는 종목 추천이 아닙니다.
투자 결정에 대한 최종 책임은 이용자 본인에게 있습니다.

본 서비스는 DART(전자공시시스템)의 공개 정보를 가공하여 제공합니다.
정보의 정확성을 위해 노력하나, 원천 데이터 오류 또는
가공 과정에서의 오차가 있을 수 있습니다.

리스크 점수는 당사 자체 알고리즘에 의해 산출되며,
절대적인 투자 지표가 아닙니다."
```

---

## 22. 국제화 (i18n) 전략

### 22.1 현재 지원 범위

- **1차 출시 (MVP)**: 한국어 전용
- **데이터 범위**: 한국 상장사 (KOSPI, KOSDAQ)
- **통화**: KRW

### 22.2 향후 확장 계획

| 단계 | 언어/시장 | 시기 | 필요 작업 |
|-----|----------|------|----------|
| Phase 1 | 영문 UI | 런칭 후 6개월 | UI 번역, 숫자 포맷 |
| Phase 2 | 일본 시장 | 런칭 후 12개월 | EDINET 연동, 일본어 |
| Phase 3 | 동남아 시장 | 런칭 후 18개월 | 현지 공시 시스템 연동 |

### 22.3 국제화 기술 스택

```typescript
// i18n 설정 (react-i18next)
const resources = {
  ko: {
    translation: {
      risk_level: {
        VERY_LOW: "매우 낮음",
        LOW: "낮음",
        MEDIUM: "보통",
        HIGH: "높음",
        CRITICAL: "매우 높음"
      },
      stakeholder: {
        executive: "임원",
        cb_investor: "CB 투자자",
        shareholder: "주주"
      }
    }
  },
  en: {
    translation: {
      risk_level: {
        VERY_LOW: "Very Low",
        LOW: "Low",
        MEDIUM: "Medium",
        HIGH: "High",
        CRITICAL: "Critical"
      }
    }
  }
};
```

---

## 23. 모바일 전략

### 23.1 모바일 접근 방식

```
┌─────────────────────────────────────────────────────────┐
│  모바일 전략: 반응형 웹 우선 (Mobile-First)             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Phase 1: 반응형 웹                                     │
│  - 모든 화면 768px 이하 대응                            │
│  - 그래프 → 간소화된 리스트 뷰 전환                     │
│  - 터치 친화적 버튼 크기 (44px 이상)                    │
│                                                         │
│  Phase 2: PWA (Progressive Web App)                     │
│  - 홈 화면 추가 지원                                    │
│  - 오프라인 검색 결과 캐시                              │
│  - 푸시 알림                                            │
│                                                         │
│  Phase 3: 네이티브 앱 (선택적)                          │
│  - 유료 사용자 증가 시 검토                             │
│  - React Native 기반                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 23.2 모바일 UI 적응

| 요소 | 데스크톱 | 모바일 |
|-----|---------|--------|
| 이해관계자 360° | 5개 탭 가로 배치 | 드롭다운 + 스와이프 |
| 그래프 시각화 | 전체 화면 그래프 | 간소화 그래프 또는 리스트 |
| 리스크 대시보드 | 3열 카드 | 세로 스택 |
| 검색 | 상단 고정 바 | 전체 화면 검색 모드 |
| 필터 | 사이드바 | 바텀 시트 |

### 23.3 모바일 성능 최적화

```yaml
목표:
  - 첫 화면 로딩: < 3초 (3G 기준)
  - 인터랙션 응답: < 100ms
  - 번들 크기: < 200KB (gzipped)

최적화 기법:
  - 이미지: WebP + lazy loading
  - 코드: 코드 스플리팅 (route 기반)
  - 그래프: 모바일에서 노드 수 제한 (최대 30개)
  - API: GraphQL persisted queries
```

---

**작성자:** Claude Code
**승인자:** -
**다음 리뷰:** -
