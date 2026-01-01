# Raymontology Frontend Specification

## Project Overview

**Project**: Raymontology - 관계형 리스크 분석 서비스
**Version**: 1.1.0
**Date**: 2025-12-15

### 목적
기관투자자와 개인 투자자를 위한 RaymondPartners 관계형 리스크 서비스를 시장 최고 수준으로 개발하고 상용화

### 핵심 가치
- 회사 간 관계 네트워크 시각화
- 리스크 신호 실시간 탐지
- 임원/대주주/CB 인수인 연결 분석
- 투자등급 및 종합 리스크 점수 제공

---

## 1. 화면 구성

### 1.1 전체 화면 구조

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

### 1.2 노드 타입 및 색상 체계

| 노드 타입 | 기본 색상 | 위험 표시 색상 | 설명 |
|----------|----------|--------------|------|
| Company (중심) | `#3B82F6` (Blue) | - | 조회 대상 회사 |
| Company (연결) | `#64748B` (Gray) | `#EF4444` (Red) | 연결된 회사 |
| Officer (임원) | `#10B981` (Green) | `#EF4444` (Red) | 현재/과거 임원 |
| Shareholder (대주주) | `#F59E0B` (Amber) | `#EF4444` (Red) | 주요 주주 |
| CB Subscriber (인수인) | `#8B5CF6` (Purple) | `#EF4444` (Red) | CB 인수자 |
| Affiliate (계열사) | `#06B6D4` (Cyan) | - | 계열회사 |

### 1.3 위험 노드 표시 규칙

**붉은색 표시 조건**:
1. **임원**: 상장사 임원 경력이 3개 이상인 경우
2. **대주주**: 다른 회사 대주주로 등록된 경우
3. **CB 인수인**: 다른 회사 CB에 참여 이력이 있는 경우

**주황색 배지 "주의" 표시 조건**:
- 임원이 적자기업(최근 2년 당기순이익 < 0) 경력이 1개 이상인 경우

```typescript
interface NodeRiskStatus {
  hasOtherCompanyHistory: boolean;  // 타사 이력 여부
  otherCompanies: string[];         // 관련 회사 목록
  isListed: boolean[];              // 상장사 여부
  riskLevel: 'normal' | 'warning';  // 위험도
  listedCareerCount?: number;       // 상장사 임원 경력 수
  deficitCareerCount?: number;      // 적자기업 경력 수
}
```

### 1.4 임원 경력 표시 규칙

**데이터 소스 우선순위**:
1. **상장사 임원 DB** (officer_positions 테이블)
   - 동일인 판단: 이름(name) + 생년월일(birth_date) 조합
   - 상단에 표시, "상장" 배지 부착
   - 빨간색 링크로 해당 회사 관계도로 이동 가능

2. **사업보고서 주요경력** (officers.career_history JSON)
   - 사업보고서 "임원 및 직원 등의 현황" 파싱 데이터
   - 하단에 표시, "現/前" 상태 표시
   - 비상장사 포함 전체 경력 표시

**표시 UI**:
```
┌─ 상장사 임원 DB ──────────────────────────────────┐
│  ● (주)A회사 [상장] [재직중]                       │
│    대표이사                                        │
│    2020.03 ~ 현재                                  │
│  ○ (주)B회사 [상장]                               │
│    사외이사                                        │
│    2018.01 ~ 2020.02                              │
└───────────────────────────────────────────────────┘
┌─ 사업보고서 주요경력 ─────────────────────────────┐
│  ● (주)C회사 [現]                                 │
│    재무이사                                        │
│  ○ (주)D회사 [前]                                 │
│    영업부장                                        │
└───────────────────────────────────────────────────┘
```

---

## 2. 페이지별 기능 명세

### 2.1 로그인 페이지 (`/login`)

| 기능 | 설명 | API |
|-----|------|-----|
| 이메일/비밀번호 로그인 | 기본 인증 | `POST /auth/login` |
| 소셜 로그인 (선택) | Google/Kakao OAuth | `POST /auth/oauth/{provider}` |
| 회원가입 | 신규 사용자 등록 | `POST /auth/register` |

### 2.2 메인 검색 페이지 (`/`)

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

### 2.3 관계도 페이지 (`/company/{companyId}/graph`)

#### 2.3.1 메인 그래프 영역

| 기능 | 설명 | API |
|-----|------|-----|
| 회사 중심 관계도 | Force-directed graph | `GET /api/graph/company/{id}` |
| 노드 드래그 | 위치 조정 | - (클라이언트) |
| 줌/패닝 | 그래프 탐색 | - (클라이언트) |
| 노드 클릭 | 상세 패널 표시 | - |
| 노드 더블클릭 | 중심 전환 | `POST /api/graph/recenter` |

#### 2.3.2 기간 선택기

```typescript
interface DateRangeSelector {
  defaultStart: '2024-01-01';
  defaultEnd: '2025-06-30';  // Q2
  minDate: '2022-01-01';
  maxDate: '2025-12-31';
  presets: ['최근1년', '최근2년', '전체기간'];
}
```

| 기능 | 설명 |
|-----|------|
| 시작일 선택 | DatePicker |
| 종료일 선택 | DatePicker |
| 프리셋 버튼 | 빠른 기간 선택 |
| 적용 | 그래프 재로드 |

#### 2.3.3 노드 상세 사이드 패널

**임원 노드 클릭 시**:
```typescript
interface OfficerDetailPanel {
  name: string;
  position: string;
  birthDate?: string;       // 생년월일 (YYYY.MM 형식)
  termPeriod: string;

  // 타사 근무 이력
  careerHistory: {
    companyId: string;
    companyName: string;
    position: string;
    period: string;
    isListed: boolean;      // 상장사 여부
    hasData: boolean;       // DB 데이터 존재 여부
    isHighlighted: boolean; // 붉은색 표시 (상장+데이터 있음)
  }[];
}
```

> **동명이인 식별**: API는 이름 + 생년월일 앞 6자리(YYYYMM)로 임원을 식별합니다.
> birth_date가 없는 경우 이름만으로 조회합니다 (fallback).

**API**: `GET /api/graph/officer/{id}/career`

**대주주 노드 클릭 시**:
```typescript
interface ShareholderDetailPanel {
  name: string;
  shareRatio: number;
  isLargest: boolean;

  // 다른 회사 주주 이력
  otherCompanies: {
    companyId: string;
    companyName: string;
    shareRatio: number;
    isListed: boolean;
    hasData: boolean;
  }[];
}
```

**CB 인수인 노드 클릭 시**:
```typescript
interface SubscriberDetailPanel {
  name: string;
  totalInvestment: number;  // 총 투자액

  // 다른 회사 CB 참여 이력
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

**API**: `GET /api/graph/subscriber/{id}/investments`

#### 2.3.4 노드 중심 전환 (Re-center)

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

### 2.4 분석 보고서 페이지 (`/company/{companyId}/report`)

#### 2.4.1 리스크 대시보드

| 섹션 | 내용 | API |
|-----|------|-----|
| 종합 리스크 점수 | 0-100점, 게이지 차트 | `GET /api/report/name/{name}` |
| 투자등급 | AAA ~ D | - |
| 리스크 레벨 | VERY_LOW ~ CRITICAL | - |

#### 2.4.2 점수 구성 분석

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

#### 2.4.3 리스크 신호 목록

| 컬럼 | 설명 |
|-----|------|
| 패턴 타입 | CB_NETWORK_CLUSTER, SERIAL_CB_ISSUER 등 |
| 심각도 | HIGH / MEDIUM / LOW |
| 점수 | 0-100 |
| 제목 | 신호 요약 |
| 설명 | 상세 내용 |

#### 2.4.4 세부 데이터 탭

| 탭 | 내용 |
|---|------|
| CB 발행 | 발행일, 금액, 전환가, 만기 |
| CB 인수인 | 인수인별 금액, 횟수 |
| 임원 현황 | 이름, 직위, 임기 |
| 재무제표 | 자산, 부채, 매출, 순이익 |
| 주주 구성 | 주주명, 지분율 |
| 계열회사 | 계열사 목록 |

---

## 3. 사용자 플로우

### 3.1 주요 플로우 다이어그램

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

### 3.2 상세 플로우

#### 3.2.1 첫 진입 플로우

1. 사용자 로그인 (또는 게스트 모드)
2. 메인 검색 페이지 표시
   - 중앙에 큰 검색창
   - 하단에 고위험 회사 목록 (선택)
3. 회사명 입력 시 자동완성 동작
4. 회사 선택 → 관계도 페이지 이동

#### 3.2.2 관계도 탐색 플로우

1. 선택 회사 중심 관계도 렌더링
2. 위험 노드 붉은색 표시
3. 노드 클릭 → 사이드 패널 열림
4. 패널 내 타사 정보 확인
   - 상장사 + 데이터 있음 → 붉은색 표시
   - 클릭 가능
5. 붉은색 회사 클릭 → Re-center
6. 새 회사 중심 관계도 표시

#### 3.2.3 분석 보고서 플로우

1. [RaymondsRisk] 버튼 클릭
2. 분석보고서 페이지 이동
3. 리스크 대시보드 확인
4. 탭 전환하며 세부 데이터 확인
5. [관계도 보기] → 다시 관계도 페이지

---

## 4. 컴포넌트 구조

### 4.1 컴포넌트 트리

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

### 4.2 핵심 컴포넌트 명세

#### 4.2.1 NetworkGraph.tsx

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

#### 4.2.2 SearchBar.tsx (자동완성)

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

## 5. 상태 관리 전략

### 5.1 Zustand 스토어 구조

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

// authStore.ts
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}
```

### 5.2 React Query 활용

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

## 6. API 연동 방식

### 6.1 API 엔드포인트 매핑

| 기능 | 메서드 | 엔드포인트 | 응답 |
|-----|-------|-----------|------|
| 회사 검색 | GET | `/api/report/search?q={query}` | `CompanySearchResult[]` |
| 종합 보고서 | GET | `/api/report/name/{name}` | `CompanyFullReport` |
| 고위험 목록 | GET | `/api/report/high-risk` | `CompanySearchResult[]` |
| 회사 그래프 | GET | `/api/graph/company/{id}` | `GraphResponse` |
| 임원 경력 | GET | `/api/graph/officer/{id}/career` | `OfficerCareerResponse` |
| 인수인 투자 | GET | `/api/graph/subscriber/{id}/investments` | `SubscriberInvestmentResponse` |
| 그래프 재중심 | POST | `/api/graph/recenter` | `GraphResponse` |

### 6.2 API 클라이언트 설정

```typescript
// api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 인증 인터셉터
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 에러 인터셉터
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 로그아웃 처리
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### 6.3 데이터 타입 정의

```typescript
// types/api.ts

interface CompanySearchResult {
  id: string;
  corp_code: string;
  name: string;
  cb_count: number;
  risk_level: string | null;
  investment_grade: string | null;
}

interface GraphNode {
  id: string;
  type: 'Company' | 'Officer' | 'Shareholder' | 'Subscriber' | 'Affiliate';
  properties: Record<string, any>;
  riskStatus?: {
    hasOtherHistory: boolean;
    otherCompanies: string[];
  };
}

interface GraphEdge {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: Record<string, any>;
}

interface GraphResponse {
  nodes: GraphNode[];
  relationships: GraphEdge[];
  center: { type: string; id: string } | null;
}

interface CompanyFullReport {
  basic_info: CompanyBasicInfo;
  disclosure_count: number;
  risk_score: RiskScoreInfo | null;
  risk_signals: RiskSignalInfo[];
  convertible_bonds: CBInfo[];
  cb_subscribers: CBSubscriberInfo[];
  officers: OfficerInfo[];
  financials: FinancialInfo[];
  shareholders: ShareholderInfo[];
  affiliates: AffiliateInfo[];
  summary: ReportSummary;
}
```

---

## 7. 기술 스택 추천

### 7.1 Core Framework

| 기술 | 버전 | 용도 |
|-----|------|------|
| React | 18.x | UI 프레임워크 |
| TypeScript | 5.x | 타입 안정성 |
| Vite | 5.x | 빌드 도구 |

### 7.2 상태 관리 & 데이터 페칭

| 기술 | 용도 |
|-----|------|
| Zustand | 전역 상태 관리 (가벼움, 간결함) |
| TanStack Query (React Query) | 서버 상태 관리, 캐싱 |
| Axios | HTTP 클라이언트 |

### 7.3 UI & 스타일링

| 기술 | 용도 |
|-----|------|
| Tailwind CSS | 유틸리티 CSS |
| shadcn/ui | 컴포넌트 라이브러리 |
| Lucide Icons | 아이콘 |
| Framer Motion | 애니메이션 |

### 7.4 그래프 시각화

| 기술 | 용도 |
|-----|------|
| D3.js | Force-directed 그래프 |
| @visx/visx | 차트 (점수 게이지 등) |

### 7.5 하이브리드 앱 대응

| 기술 | 용도 |
|-----|------|
| Capacitor | 웹앱 → 네이티브 앱 변환 |
| PWA (Workbox) | 오프라인 지원, 설치 가능 |

### 7.6 Package.json 핵심 의존성

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "zustand": "^4.4.7",
    "@tanstack/react-query": "^5.12.0",
    "axios": "^1.6.2",
    "d3": "^7.8.5",
    "@visx/visx": "^3.5.0",
    "tailwindcss": "^3.3.6",
    "framer-motion": "^10.16.16",
    "lucide-react": "^0.294.0",
    "date-fns": "^2.30.0"
  },
  "devDependencies": {
    "typescript": "^5.3.2",
    "vite": "^5.0.8",
    "@vitejs/plugin-react": "^4.2.1",
    "@capacitor/core": "^5.6.0",
    "@capacitor/cli": "^5.6.0"
  }
}
```

---

## 8. 현재 DB 데이터 현황

### 8.1 데이터 축적 현황 (2025-12-09 기준)

| 테이블 | 레코드 수 | 활용 |
|--------|----------|------|
| companies | 3,922 | 회사 노드 |
| officers | 38,125 | 임원 노드 |
| officer_positions | 240,320 | 임원-회사 엣지 |
| convertible_bonds | 1,435 | CB 노드 |
| cb_subscribers | 8,656 | 인수인 노드 |
| major_shareholders | 1,130 | 주주 노드 |
| affiliates | 1,245 | 계열사 엣지 |
| risk_scores | 3,912 | 리스크 점수 |
| risk_signals | 1,412 | 리스크 신호 |
| financial_statements | 9,432 | 재무 데이터 |

### 8.2 데이터 커버리지

- **회사**: 상장사 3,922개 전체 커버
- **리스크 점수**: 99.7% 회사 계산 완료
- **CB 데이터**: 1,435건 (2022-2025)
- **임원 데이터**: 38,125명 (현재+과거)

---

## 9. 구현 우선순위

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

## 10. 성능 고려사항

### 10.1 그래프 렌더링 최적화

```typescript
// 대량 노드 처리
const MAX_NODES = 200;  // 최대 노드 수 제한

// Canvas 기반 렌더링 (대량 노드용)
const useCanvasRenderer = (nodeCount: number) => {
  return nodeCount > 100;  // 100개 초과 시 Canvas 사용
};

// 가상화 (패널 목록용)
import { useVirtualizer } from '@tanstack/react-virtual';
```

### 10.2 데이터 페칭 최적화

```typescript
// 프리페칭
const prefetchCompanyGraph = (companyId: string) => {
  queryClient.prefetchQuery({
    queryKey: ['graph', companyId],
    queryFn: () => fetchCompanyGraph(companyId),
  });
};

// 노드 호버 시 상세 데이터 프리페치
const handleNodeHover = (node: GraphNode) => {
  if (node.type === 'Officer') {
    prefetchOfficerCareer(node.id);
  }
};
```

---

## 11. 데이터 현황 (2025-12-15)

### 11.1 PostgreSQL 데이터

| 테이블 | 레코드 수 | 비고 |
|--------|----------|------|
| companies | 3,922 | 상장사 전체 |
| officers | 38,125 | birth_date 99.9% 보유 |
| officer_positions | 240,320 | 2022~2025 재직 기록 |
| convertible_bonds | 1,435 | 회차정보 포함 |
| cb_subscribers | 8,656 | CB 인수자 |
| financial_statements | 9,432 | 재무제표 |
| risk_signals | 1,412 | 리스크 신호 |
| risk_scores | 3,912 | 종합 리스크 점수 |
| major_shareholders | 1,130 | 대주주 정보 |
| affiliates | 1,245 | 계열사 정보 |
| disclosures | 206,767 | 2022~2025 공시 |

### 11.2 Neo4j 그래프

| 항목 | 개수 | 비고 |
|------|------|------|
| Company 노드 | 3,922 | corp_code 기반 |
| Officer 노드 | 38,125 | PostgreSQL ID 동기화 |
| ConvertibleBond 노드 | 1,435 | - |
| Subscriber 노드 | 2,227 | - |
| WORKS_AT 관계 | 240,320 | corp_code 기반 매핑 |
| INVESTED_IN 관계 | 3,130 | - |
| SUBSCRIBED 관계 | 4,014 | - |
| ISSUED 관계 | 1,435 | - |

### 11.3 동명이인 식별 로직 (2025-12-12 개선)

**문제점**:
- 이름만으로 임원 검색 시 동명이인 구분 불가
- PostgreSQL과 Neo4j 간 Officer ID 불일치

**해결 방안**:
1. **이름 + 생년월일 6자리 비교**
   - birth_date 형식: `YYYY.MM` (예: `1974.10`)
   - 비교 시 YYYYMM 6자리로 정규화

2. **API 동작 방식**
   - birth_date 있는 경우: 이름 + 생년월일로 검색
   - birth_date 없는 경우: 이름만으로 fallback

**프론트엔드 대응**:
- 임원 노드에 birth_date 표시 (선택적)
- 동명이인 존재 시 UI에서 구분 표시

---

## Appendix: 참고 자료

### A. 기존 API 엔드포인트

- `/api/report/*` - 회사 종합 보고서
- `/api/graph/*` - 그래프 네트워크
- `/api/companies/*` - 회사 CRUD
- `/api/risks/*` - 리스크 분석

### B. 디자인 참고

- 관계도: Neo4j Bloom, Linkurious 스타일
- 대시보드: Tremor, shadcn/ui 차트
- 테이블: TanStack Table

### C. 테스트 회사

- 엑시온그룹 (고위험, CB 10건)
- 삼성전자 (저위험, CB 없음)
- 현대ADM (고위험, 리스크 신호 2건)
