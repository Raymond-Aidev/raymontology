# Raymontology PRD (Product Requirements Document)

**버전**: 2.0
**최종 수정**: 2025-12-09
**작성자**: Development Team

---

## 1. 제품 개요

### 1.1 제품명
**Raymontology** (Raymond + Ontology)

### 1.2 한 줄 정의
한국 주식시장의 기업-임원-투자자 관계를 온톨로지 기반으로 분석하여 일반 투자자에게 정보 비대칭을 해소하는 금융 리스크 분석 플랫폼

### 1.3 핵심 가치 제안
- **정보 비대칭 해소**: 기관/내부자만 알던 관계망 정보를 일반 투자자에게 제공
- **회사 간 관계 네트워크 시각화**: 임원/대주주/CB 인수인 연결 분석
- **리스크 신호 실시간 탐지**: 전환사채(CB) 남발, 내부자 거래 패턴 등 위험 신호 자동 감지
- **투자등급 및 종합 리스크 점수 제공**: RaymondsRisk 기반 투자 의사결정 지원

---

## 2. 문제 정의

### 2.1 해결하려는 문제
1. **정보 비대칭**: 기업 내부자와 기관투자자는 임원 네트워크, CB 인수자 정보 등을 쉽게 파악하지만 개인 투자자는 접근 불가
2. **분산된 공시 정보**: DART 공시가 존재하지만 XML 형태로 흩어져 있어 연결 관계 파악 어려움
3. **수작업 분석 한계**: 수천 개 기업의 임원/CB/재무 데이터를 개인이 수동 분석 불가능

### 2.2 타겟 사용자
| 페르소나 | 니즈 | 주요 기능 |
|---------|------|----------|
| 개인 투자자 | 투자 전 기업 리스크 파악 | 리스크 시그널, 관계망 시각화 |
| 기관투자자 | 기업 관계도 분석 | 온톨로지 그래프, CB 분석 |
| 금융 감독 기관 | 시세조종 패턴 탐지 | 리스크 패턴, 내부자 거래 추적 |

---

## 3. 온톨로지 모델

### 3.1 핵심 엔티티 (Nodes)

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAYMONTOLOGY ONTOLOGY                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────┐         WORKS_AT          ┌─────────────┐         │
│   │ Officer │─────────────────────────▶│   Company   │         │
│   │         │                           │             │         │
│   │ • name  │◀───────────────────────── │ • name      │         │
│   │ • birth │     (임기, 직위)          │ • market    │         │
│   │ • gender│                           │ • corp_code │         │
│   └─────────┘                           └──────┬──────┘         │
│                                                │                 │
│                                          ISSUED│                 │
│                                                ▼                 │
│   ┌────────────┐      SUBSCRIBED      ┌──────────────────┐      │
│   │ Subscriber │─────────────────────▶│ ConvertibleBond  │      │
│   │            │                       │                  │      │
│   │ • name     │                       │ • issue_amount   │      │
│   │ • amount   │                       │ • issue_date     │      │
│   │ • is_related│                      │ • maturity_date  │      │
│   └────────────┘                       │ • conversion_price│     │
│                                        └──────────────────┘      │
│   ┌────────────┐                                                 │
│   │Shareholder │       SHAREHOLDER_OF                            │
│   │            │─────────────────────▶ Company                   │
│   │ • name     │                                                 │
│   │ • ratio    │                                                 │
│   └────────────┘                                                 │
│                                                                  │
│   Company ─────── AFFILIATE_OF ──────▶ Company                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 관계 (Relationships)

| 관계 | 설명 | 속성 |
|------|------|------|
| `WORKS_AT` | 임원 → 기업 | position, term_start, term_end, is_current |
| `ISSUED` | 기업 → CB | - |
| `SUBSCRIBED` | 인수자 → CB | subscription_amount, is_related_party |
| `SHAREHOLDER_OF` | 주주 → 기업 | share_ratio, is_largest |
| `AFFILIATE_OF` | 기업 → 기업 | relationship_type |

### 3.3 데이터 소스
- **DART OpenAPI**: 공시 목록, 사업보고서, CB 공시 원문
- **사업보고서 XML**: 임원 현황 (임기, 생년월일, 성별)
- **CB 발행결정 공시**: 인수자, 발행금액, 전환가액

---

## 4. 시스템 아키텍처

### 4.1 기술 스택

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  React 18 + TypeScript + D3.js (그래프 시각화)             │  │
│  │  Zustand (상태관리) + TanStack Query (서버상태)            │  │
│  │  Tailwind CSS + shadcn/ui (스타일링)                       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API LAYER                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  FastAPI (Python 3.11) - REST API                         │  │
│  │  • /api/companies - 기업 검색/상세                         │  │
│  │  • /api/report - 종합 보고서                               │  │
│  │  • /api/graph - Neo4j 그래프 조회                          │  │
│  │  • /api/risks - 리스크 시그널                              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ PostgreSQL  │  │   Neo4j     │  │        Redis            │  │
│  │ (정형 데이터)│  │ (그래프 DB) │  │       (캐시)            │  │
│  │             │  │             │  │                         │  │
│  │ • companies │  │ • Company   │  │ • API 응답 캐시          │  │
│  │ • officers  │  │ • Officer   │  │ • 세션 관리             │  │
│  │ • cbs       │  │ • CB        │  │                         │  │
│  │ • positions │  │ • Subscriber│  │                         │  │
│  │ • risks     │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 데이터 플로우

```
DART API ──▶ XML 파싱 ──▶ PostgreSQL ──▶ Neo4j ──▶ Frontend
   │              │             │            │          │
   │              │             │            │          │
 공시목록      CB/임원       정형 저장    그래프 저장   시각화
 다운로드      추출                        동기화
```

---

## 5. 데이터 현황 (2025-12-09 기준)

### 5.1 PostgreSQL

| 테이블 | 레코드 수 | 상태 | 비고 |
|--------|----------|------|------|
| companies | 3,922 | ✅ | 상장사 전체 |
| officers | 38,125 | ✅ | - |
| officer_positions | 240,320 | ✅ | - |
| convertible_bonds | 1,435 | ✅ | 2022-2025 |
| cb_subscribers | 8,656 | ✅ | - |
| major_shareholders | 1,130 | ✅ | - |
| affiliates | 1,245 | ✅ | - |
| financial_statements | 9,432 | ✅ | - |
| risk_signals | 1,412 | ✅ | 5개 패턴 |
| risk_scores | 3,912 | ✅ | 99.7% 커버 |
| disclosures | 206,767 | ✅ | - |

### 5.2 데이터 커버리지

- **회사**: 상장사 3,922개 전체 커버
- **리스크 점수**: 99.7% 회사 계산 완료
- **CB 데이터**: 1,435건 (2022-2025)
- **임원 데이터**: 38,125명 (현재+과거)

---

## 6. 리스크 점수 계산 로직

### 6.1 종합 리스크 구성

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                    종합 투자 리스크 (100점)                          │
│                                                                      │
│   ┌─────────────────────────────┐  ┌─────────────────────────────┐  │
│   │                             │  │                             │  │
│   │   RaymondsRisk (50%)       │  │   재무건전성 (50%)          │  │
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

### 6.2 투자등급 매핑

| 종합 점수 | 투자등급 | 리스크 레벨 |
|----------|---------|------------|
| 0-15 | AAA | VERY_LOW |
| 16-25 | AA | LOW |
| 26-35 | A | LOW |
| 36-45 | BBB | MEDIUM |
| 46-55 | BB | MEDIUM |
| 56-65 | B | HIGH |
| 66-80 | CCC | HIGH |
| 81-100 | D | CRITICAL |

### 6.3 리스크 시그널 패턴

| 패턴 | 설명 | 심각도 |
|------|------|--------|
| CB_NETWORK_CLUSTER | CB 투자자 네트워크 클러스터 | HIGH |
| SERIAL_CB_ISSUER | 연속 CB 발행 | HIGH |
| FINANCIAL_DISTRESS | 재무 위기 신호 | CRITICAL |
| OFFICER_OVERLAP | 임원 중복 네트워크 | MEDIUM |
| HIGH_RISK_INVESTOR | 고위험 투자자 연결 | HIGH |

---

## 7. API 명세

### 7.1 기업 검색 API

```
GET /api/report/search?q={query}&limit=20

Response:
[
  {
    "id": "uuid",
    "corp_code": "00126380",
    "name": "엑시온그룹",
    "cb_count": 10,
    "risk_level": "HIGH",
    "investment_grade": "BB"
  }
]
```

### 7.2 종합 보고서 API

```
GET /api/report/name/{company_name}

Response:
{
  "basic_info": { "id", "corp_code", "name" },
  "disclosure_count": 1234,
  "risk_score": {
    "total_score": 43.73,
    "risk_level": "MEDIUM",
    "investment_grade": "BB",
    "raymondsrisk_score": 28.5,
    "human_risk_score": 7.0,
    "cb_risk_score": 50.0,
    "financial_health_score": 59.0
  },
  "risk_signals": [...],
  "convertible_bonds": [...],
  "cb_subscribers": [...],
  "officers": [...],
  "financials": [...],
  "shareholders": [...],
  "affiliates": [...],
  "summary": {...}
}
```

### 7.3 그래프 API

```
GET /api/graph/company/{id}
GET /api/graph/officer/{id}/career
GET /api/graph/subscriber/{id}/investments
POST /api/graph/recenter
```

### 7.4 고위험 회사 API

```
GET /api/report/high-risk?min_score=50&limit=50

Response:
[
  {
    "id": "uuid",
    "name": "고위험회사",
    "cb_count": 15,
    "risk_level": "HIGH",
    "investment_grade": "CCC"
  }
]
```

---

## 8. 프론트엔드 명세

### 8.1 전체 화면 구조

```
┌─────────────────────────────────────────────────────────────┐
│  Header (로고, 검색창, 사용자 메뉴)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │              관계도 그래프 영역                      │   │
│  │          (D3.js Force-directed Graph)              │   │
│  │                                                     │   │
│  │     [회사] ── [임원] ── [타회사]                    │   │
│  │       │                                            │   │
│  │     [대주주]  [CB인수인]  [계열사]                   │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌────────────────────┐ ┌────────────────────────────┐    │
│  │ 기간 선택          │ │ [RaymondsRisk 분석보고서]  │    │
│  │ 2024.01 ~ 2025.Q2  │ └────────────────────────────┘    │
│  └────────────────────┘                                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  사이드 패널 (노드 상세 정보)                               │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 노드 타입 및 색상 체계

| 노드 타입 | 기본 색상 | 위험 표시 색상 | 설명 |
|----------|----------|--------------|------|
| Company (중심) | `#3B82F6` (Blue) | - | 조회 대상 회사 |
| Company (연결) | `#64748B` (Gray) | `#EF4444` (Red) | 연결된 회사 |
| Officer (임원) | `#10B981` (Green) | `#EF4444` (Red) | 현재/과거 임원 |
| Shareholder (대주주) | `#F59E0B` (Amber) | `#EF4444` (Red) | 주요 주주 |
| CB Subscriber (인수인) | `#8B5CF6` (Purple) | `#EF4444` (Red) | CB 인수자 |
| Affiliate (계열사) | `#06B6D4` (Cyan) | - | 계열회사 |

### 8.3 위험 노드 표시 규칙

**붉은색 표시 조건**:
1. **임원**: 다른 회사에 재직 이력이 있는 경우
2. **대주주**: 다른 회사 대주주로 등록된 경우
3. **CB 인수인**: 다른 회사 CB에 참여 이력이 있는 경우

```typescript
interface NodeRiskStatus {
  hasOtherCompanyHistory: boolean;  // 타사 이력 여부
  otherCompanies: string[];         // 관련 회사 목록
  isListed: boolean[];              // 상장사 여부
  riskLevel: 'normal' | 'warning';  // 위험도
}
```

---

## 9. 페이지별 기능 명세

### 9.1 로그인 페이지 (`/login`)

| 기능 | 설명 | API |
|-----|------|-----|
| 이메일/비밀번호 로그인 | 기본 인증 | `POST /auth/login` |
| 소셜 로그인 (선택) | Google/Kakao OAuth | `POST /auth/oauth/{provider}` |
| 회원가입 | 신규 사용자 등록 | `POST /auth/register` |

### 9.2 메인 검색 페이지 (`/`)

| 기능 | 설명 | API |
|-----|------|-----|
| 자동완성 검색 | 회사명 실시간 검색 | `GET /api/report/search?q={query}` |
| 검색 결과 표시 | CB건수, 리스크등급 포함 | - |
| 회사 선택 | 관계도 페이지로 이동 | - |
| 고위험 회사 목록 | 빠른 접근 | `GET /api/report/high-risk` |

**자동완성 컴포넌트 요구사항**:
- 2자 이상 입력 시 검색 시작
- Debounce: 300ms
- 최대 20개 결과 표시
- 키보드 네비게이션 지원 (↑↓ Enter)

### 9.3 관계도 페이지 (`/company/{companyId}/graph`)

#### 9.3.1 메인 그래프 영역

| 기능 | 설명 | API |
|-----|------|-----|
| 회사 중심 관계도 | Force-directed graph | `GET /api/graph/company/{id}` |
| 노드 드래그 | 위치 조정 | - (클라이언트) |
| 줌/패닝 | 그래프 탐색 | - (클라이언트) |
| 노드 클릭 | 상세 패널 표시 | - |
| 노드 더블클릭 | 중심 전환 | `POST /api/graph/recenter` |

#### 9.3.2 기간 선택기

```typescript
interface DateRangeSelector {
  defaultStart: '2024-01-01';
  defaultEnd: '2025-06-30';  // Q2
  minDate: '2022-01-01';
  maxDate: '2025-12-31';
  presets: ['최근1년', '최근2년', '전체기간'];
}
```

#### 9.3.3 노드 상세 사이드 패널

**임원 노드 클릭 시**:
```typescript
interface OfficerDetailPanel {
  name: string;
  position: string;
  termPeriod: string;

  careerHistory: {
    companyId: string;
    companyName: string;
    position: string;
    period: string;
    isListed: boolean;
    hasData: boolean;
    isHighlighted: boolean;  // 붉은색 표시
  }[];
}
```

**CB 인수인 노드 클릭 시**:
```typescript
interface SubscriberDetailPanel {
  name: string;
  totalInvestment: number;

  investmentHistory: {
    companyId: string;
    companyName: string;
    amount: number;
    issueDate: string;
    isListed: boolean;
    hasData: boolean;
  }[];
}
```

#### 9.3.4 노드 중심 전환 (Re-center)

**트리거 조건**:
1. 상세 패널에서 붉은색 회사 클릭
2. 노드 더블클릭

**동작**:
- 새로운 회사를 중심으로 관계도 재구성
- 이전 중심 회사는 연결 노드로 표시
- 네비게이션 히스토리 저장 (뒤로가기 지원)

```typescript
interface GraphNavigation {
  history: string[];  // company IDs
  currentIndex: number;

  goBack(): void;
  goForward(): void;
  recenter(companyId: string): void;
}
```

### 9.4 분석 보고서 페이지 (`/company/{companyId}/report`)

#### 9.4.1 리스크 대시보드

| 섹션 | 내용 | API |
|-----|------|-----|
| 종합 리스크 점수 | 0-100점, 게이지 차트 | `GET /api/report/name/{name}` |
| 투자등급 | AAA ~ D | - |
| 리스크 레벨 | VERY_LOW ~ CRITICAL | - |

#### 9.4.2 점수 구성 분석

```
RaymondsRisk Score Breakdown
├── 인적 리스크 (25%)
│   ├── 임원 수 점수
│   └── 타사 재직 배수
├── CB 리스크 (25%)
│   ├── 발행 빈도 (25점)
│   ├── 발행 규모 (25점)
│   ├── 참여자 품질 (30점)
│   └── 적자기업 연결 (20점)
└── 재무건전성 (50%)
    ├── 부채비율
    ├── 영업이익
    ├── 순이익
    └── 자산규모
```

#### 9.4.3 세부 데이터 탭

| 탭 | 내용 |
|---|------|
| CB 발행 | 발행일, 금액, 전환가, 만기 |
| CB 인수인 | 인수인별 금액, 횟수 |
| 임원 현황 | 이름, 직위, 임기 |
| 재무제표 | 자산, 부채, 매출, 순이익 |
| 주주 구성 | 주주명, 지분율 |
| 계열회사 | 계열사 목록 |

---

## 10. 사용자 플로우

### 10.1 주요 플로우 다이어그램

```
[로그인] → [메인 검색] → [관계도] → [분석보고서]
              │              │
              │              ├── [노드 클릭] → [상세 패널]
              │              │                    │
              │              │                    └── [붉은색 회사 클릭]
              │              │                              │
              │              │                              ↓
              │              └──────────────── [Re-center: 새 관계도]
              │
              └── [새 검색] → [새 관계도]
```

### 10.2 상세 플로우

#### 10.2.1 첫 진입 플로우

1. 사용자 로그인 (또는 게스트 모드)
2. 메인 검색 페이지 표시
   - 중앙에 큰 검색창
   - 하단에 고위험 회사 목록 (선택)
3. 회사명 입력 시 자동완성 동작
4. 회사 선택 → 관계도 페이지 이동

#### 10.2.2 관계도 탐색 플로우

1. 선택 회사 중심 관계도 렌더링
2. 위험 노드 붉은색 표시
3. 노드 클릭 → 사이드 패널 열림
4. 패널 내 타사 정보 확인
   - 상장사 + 데이터 있음 → 붉은색 표시
   - 클릭 가능
5. 붉은색 회사 클릭 → Re-center
6. 새 회사 중심 관계도 표시

#### 10.2.3 분석 보고서 플로우

1. [RaymondsRisk] 버튼 클릭
2. 분석보고서 페이지 이동
3. 리스크 대시보드 확인
4. 탭 전환하며 세부 데이터 확인
5. [관계도 보기] → 다시 관계도 페이지

---

## 11. 컴포넌트 구조

### 11.1 컴포넌트 트리

```
src/
├── components/
│   ├── common/
│   │   ├── Header.tsx
│   │   ├── SearchBar.tsx           # 자동완성 검색
│   │   ├── DateRangePicker.tsx     # 기간 선택
│   │   ├── Loading.tsx
│   │   └── ErrorBoundary.tsx
│   │
│   ├── graph/
│   │   ├── NetworkGraph.tsx        # D3 그래프 메인
│   │   ├── GraphNode.tsx           # 노드 컴포넌트
│   │   ├── GraphEdge.tsx           # 엣지 컴포넌트
│   │   ├── GraphControls.tsx       # 줌/패닝 컨트롤
│   │   ├── GraphLegend.tsx         # 범례
│   │   └── NodeTooltip.tsx         # 호버 툴팁
│   │
│   ├── panels/
│   │   ├── SidePanel.tsx           # 사이드 패널 컨테이너
│   │   ├── OfficerDetail.tsx       # 임원 상세
│   │   ├── ShareholderDetail.tsx   # 주주 상세
│   │   ├── SubscriberDetail.tsx    # 인수인 상세
│   │   └── CompanyCard.tsx         # 회사 카드 (클릭용)
│   │
│   ├── report/
│   │   ├── RiskDashboard.tsx       # 리스크 대시보드
│   │   ├── RiskGauge.tsx           # 점수 게이지
│   │   ├── RiskBreakdown.tsx       # 점수 구성
│   │   ├── RiskSignalList.tsx      # 리스크 신호 목록
│   │   ├── CBTable.tsx             # CB 테이블
│   │   ├── OfficerTable.tsx        # 임원 테이블
│   │   ├── FinancialTable.tsx      # 재무 테이블
│   │   └── ShareholderTable.tsx    # 주주 테이블
│   │
│   └── auth/
│       ├── LoginForm.tsx
│       └── RegisterForm.tsx
│
├── pages/
│   ├── LoginPage.tsx
│   ├── MainSearchPage.tsx
│   ├── GraphPage.tsx
│   └── ReportPage.tsx
│
├── hooks/
│   ├── useCompanySearch.ts         # 검색 자동완성
│   ├── useGraphData.ts             # 그래프 데이터
│   ├── useNodeDetail.ts            # 노드 상세
│   ├── useCompanyReport.ts         # 분석 보고서
│   └── useGraphNavigation.ts       # 그래프 네비게이션
│
├── store/
│   ├── authStore.ts                # 인증 상태
│   ├── graphStore.ts               # 그래프 상태
│   └── reportStore.ts              # 보고서 상태
│
├── api/
│   ├── client.ts                   # Axios 클라이언트
│   ├── auth.ts                     # 인증 API
│   ├── company.ts                  # 회사 API
│   ├── graph.ts                    # 그래프 API
│   └── report.ts                   # 보고서 API
│
└── types/
    ├── api.ts                      # API 응답 타입
    ├── graph.ts                    # 그래프 타입
    └── company.ts                  # 회사 타입
```

### 11.2 핵심 컴포넌트 명세

#### 11.2.1 NetworkGraph.tsx

```typescript
interface NetworkGraphProps {
  companyId: string;
  dateRange: DateRange;
  onNodeClick: (node: GraphNode) => void;
  onNodeDoubleClick: (node: GraphNode) => void;
  selectedNodeId?: string;
}

// D3.js Force Simulation 설정
const forceConfig = {
  charge: -300,           // 노드 간 반발력
  linkDistance: 100,      // 링크 거리
  centerForce: 0.05,      // 중심 인력
  collisionRadius: 30,    // 충돌 반경
};
```

#### 11.2.2 SearchBar.tsx (자동완성)

```typescript
interface SearchBarProps {
  onSelect: (company: CompanySearchResult) => void;
  placeholder?: string;
  autoFocus?: boolean;
}

// 자동완성 로직
const useAutoComplete = (query: string) => {
  const [results, setResults] = useState<CompanySearchResult[]>([]);

  useEffect(() => {
    if (query.length < 2) return;

    const handler = debounce(async () => {
      const data = await searchCompanies(query);
      setResults(data);
    }, 300);

    handler();
    return () => handler.cancel();
  }, [query]);

  return results;
};
```

---

## 12. 상태 관리 전략

### 12.1 Zustand 스토어 구조

```typescript
// graphStore.ts
interface GraphState {
  // 현재 그래프 상태
  centerCompanyId: string | null;
  nodes: GraphNode[];
  edges: GraphEdge[];

  // 선택 상태
  selectedNodeId: string | null;
  hoveredNodeId: string | null;

  // 기간 필터
  dateRange: DateRange;

  // 네비게이션 히스토리
  history: string[];
  historyIndex: number;

  // 액션
  setCenter: (companyId: string) => void;
  selectNode: (nodeId: string | null) => void;
  setDateRange: (range: DateRange) => void;
  goBack: () => void;
  goForward: () => void;
}

// reportStore.ts
interface ReportState {
  companyId: string | null;
  report: CompanyFullReport | null;
  loading: boolean;
  error: string | null;

  fetchReport: (companyId: string) => Promise<void>;
  clearReport: () => void;
}
```

### 12.2 React Query 활용

```typescript
// 그래프 데이터 캐싱
const useCompanyGraph = (companyId: string, dateRange: DateRange) => {
  return useQuery({
    queryKey: ['graph', companyId, dateRange],
    queryFn: () => fetchCompanyGraph(companyId, dateRange),
    staleTime: 5 * 60 * 1000,  // 5분
    cacheTime: 30 * 60 * 1000, // 30분
  });
};

// 검색 자동완성 (짧은 캐시)
const useCompanySearch = (query: string) => {
  return useQuery({
    queryKey: ['search', query],
    queryFn: () => searchCompanies(query),
    enabled: query.length >= 2,
    staleTime: 30 * 1000,  // 30초
  });
};

// 분석 보고서 (긴 캐시)
const useCompanyReport = (companyId: string) => {
  return useQuery({
    queryKey: ['report', companyId],
    queryFn: () => fetchCompanyReport(companyId),
    staleTime: 10 * 60 * 1000,  // 10분
  });
};
```

---

## 13. 기술 스택

### 13.1 Frontend

| 기술 | 버전 | 용도 |
|-----|------|------|
| React | 18.x | UI 프레임워크 |
| TypeScript | 5.x | 타입 안정성 |
| Vite | 5.x | 빌드 도구 |
| Zustand | 4.x | 전역 상태 관리 |
| TanStack Query | 5.x | 서버 상태 관리 |
| Axios | 1.x | HTTP 클라이언트 |
| D3.js | 7.x | 그래프 시각화 |
| Tailwind CSS | 3.x | 유틸리티 CSS |
| shadcn/ui | - | 컴포넌트 라이브러리 |

### 13.2 Backend

| 기술 | 버전 | 용도 |
|-----|------|------|
| Python | 3.11 | 런타임 |
| FastAPI | 0.104 | REST API |
| PostgreSQL | 15 | 정형 데이터 |
| Neo4j | 5.x | 그래프 DB |
| asyncpg | 0.29 | PostgreSQL 드라이버 |
| neo4j | 5.x | Neo4j 드라이버 |

### 13.3 하이브리드 앱 대응

| 기술 | 용도 |
|-----|------|
| Capacitor | 웹앱 → 네이티브 앱 변환 |
| PWA (Workbox) | 오프라인 지원, 설치 가능 |

---

## 14. 구현 우선순위

### Phase 1: MVP (2주)
1. 로그인/회원가입 페이지
2. 메인 검색 (자동완성)
3. 기본 관계도 (회사-임원-CB)
4. 기본 분석보고서

### Phase 2: Core Features (2주)
5. 노드 상세 패널
6. 위험 노드 표시
7. Re-center 기능
8. 기간 필터

### Phase 3: Enhancement (2주)
9. 네비게이션 히스토리
10. 하이브리드 앱 (Capacitor)
11. PWA 지원
12. 성능 최적화

---

## 15. 보안 및 규정 준수

### 15.1 데이터 출처 명시
- 모든 데이터는 DART OpenAPI (공개 API)에서 수집
- 개인정보 최소화 (공시된 정보만 사용)

### 15.2 접근 제어
- 관리자/일반 사용자 역할 분리
- API Rate Limiting
- JWT 기반 인증

---

## 부록 A: 데이터베이스 스키마

### risk_scores

```sql
CREATE TABLE risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    analysis_year INTEGER NOT NULL,
    analysis_quarter INTEGER,
    total_score DECIMAL(5,2) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    investment_grade VARCHAR(5),
    raymondsrisk_score DECIMAL(5,2),
    human_risk_score DECIMAL(5,2),
    cb_risk_score DECIMAL(5,2),
    financial_health_score DECIMAL(5,2),
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, analysis_year, analysis_quarter)
);
```

### risk_signals

```sql
CREATE TABLE risk_signals (
    signal_id UUID PRIMARY KEY,
    target_company_id UUID REFERENCES companies(id),
    pattern_type VARCHAR(50),
    severity riskseverity,
    status riskstatus,
    risk_score INTEGER,
    title VARCHAR(200),
    description TEXT,
    evidence JSONB,
    detected_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## 부록 B: 용어 정의

| 용어 | 정의 |
|------|------|
| CB (Convertible Bond) | 전환사채. 채권이지만 주식으로 전환 가능 |
| DART | 금융감독원 전자공시시스템 |
| RaymondsRisk | 인적 리스크 + CB 리스크 종합 점수 |
| 온톨로지 | 개념과 관계를 정의하는 지식 모델 |
| Re-center | 그래프 중심 회사 전환 기능 |

---

## 부록 C: 테스트 회사

- **엑시온그룹**: 고위험, CB 10건, 리스크 신호 2건
- **삼성전자**: 저위험, CB 없음
- **현대ADM**: 고위험, 리스크 신호 2건

---

**문서 끝**
