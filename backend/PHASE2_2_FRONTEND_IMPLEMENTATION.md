# Phase 2-2: Frontend 그래프 시각화 구현

**시작 날짜:** 2025-11-20
**최종 업데이트:** 2025-12-10
**상태:** ✅ 핵심 기능 완료 (85%)

---

## 배경

- **Phase 0-4, 7:** Backend 완료 (95% 완성도)
- **Neo4j:** 91,312 노드, 93,623 관계 (INVESTED_IN 3,130개 포함)
- **Graph API:** 6개 엔드포인트 구현 완료
- **Frontend 기반:** React 18 + Vite + Tailwind CSS 이미 구축됨

## 구현 목표

IMPLEMENTATION_PLAN.md의 Phase 2-2에 따라 **neovis.js 기반 인터랙티브 그래프 시각화**를 구현합니다.

### 핵심 요구사항

#### 1. 임원 클릭 → 경력 회사 표시
- 임원 노드 클릭 → 우측 패널에 경력 이력 표시
- "경력 회사 보기" 버튼 → WORKED_AT 관계 노드들 그래프에 추가
- 경력 회사 노드 클릭 → 해당 회사 중심으로 네트워크 재구성

#### 2. CB 클릭 → 인수자 투자 이력 표시
- CB 노드 클릭 → 인수자 리스트 표시
- 인수자 항목 클릭 → 투자 이력 확장
- 회사명 클릭 → 해당 회사 발행 CB 그래프에 추가

---

## 설치된 Dependencies

```json
{
  "neovis.js": "^2.1.0",
  "d3": "^7.9.0",
  "@types/d3": "^7.4.3"
}
```

### Neo4j 연결 정보
```
NEO4J_URI: neo4j://localhost:7687
NEO4J_USER: neo4j
NEO4J_PASSWORD: password
```

---

## 구현 계획

### 1. 디렉토리 구조

```
frontend/src/components/GraphVisualization/
├── GraphCanvas.tsx          # neovis.js 래핑, 메인 그래프 렌더링
├── NodeDetailPanel.tsx      # 노드 클릭 시 우측 패널
├── OfficerCareerPanel.tsx   # 임원 경력 이력 타임라인
├── SubscriberInvestmentPanel.tsx  # 인수자 투자 포트폴리오
├── GraphControls.tsx        # 확대/축소/필터 컨트롤
├── GraphLegend.tsx          # 노드/관계 범례
└── index.ts                 # 컴포넌트 export

frontend/src/pages/
└── GraphExplorer.tsx        # 그래프 탐색 메인 페이지

frontend/src/services/
└── graphApi.ts              # Graph API 호출 함수들
```

### 2. 구현 순서

#### Step 1: GraphCanvas.tsx (핵심)
- **역할:** neovis.js 초기화 및 그래프 렌더링
- **기능:**
  - Neo4j 직접 연결 (bolt://localhost:7687)
  - 노드 타입별 색상/크기 규칙 설정
  - 노드 클릭 이벤트 핸들러
  - 관계 타입별 스타일 설정

**노드 시각화 규칙 (IMPLEMENTATION_PLAN.md 기준):**
- **Company:** 파란색 (#4A90E2)
- **Officer:** 경력 회사 수에 따라 색상 진하기 조절
  - 0-2개: 옅은 파란색 (#A8D8FF)
  - 3-5개: 파란색 (#5AAEFF)
  - 6-10개: 진한 파란색 (#2E7DD4)
  - 11개 이상: 남색 (#1A4D8F)
- **ConvertibleBond:** 녹색 (#50C878)
- **Subscriber:** 투자 건수에 따라 색상 진하기 조절
  - 1-2건: 옅은 녹색 (#C7F5C7)
  - 3-5건: 녹색 (#6FD66F)
  - 6-10건: 진한 녹색 (#3BA13B)
  - 11건 이상: 짙은 녹색 (#1E5F1E)

**관계 시각화 규칙:**
- WORKS_AT: 실선, 굵기 2, 회색 (#999)
- WORKED_AT: 점선, 굵기 1, 연한 회색 (#CCC)
- HAS_AFFILIATE: 주황색 (#E67E22)
- ISSUED: 보라색 (#9B59B6)
- SUBSCRIBED: 녹색 (#27AE60)
- INVESTED_IN: 청록색 (#16A085)

#### Step 2: NodeDetailPanel.tsx
- **역할:** 노드 클릭 시 우측 패널 표시
- **기능:**
  - 노드 타입 감지 (Company/Officer/CB/Subscriber)
  - 타입별로 적절한 하위 패널 렌더링
  - 패널 닫기/토글 기능

#### Step 3: OfficerCareerPanel.tsx
- **역할:** 임원 경력 이력 표시
- **API:** `GET /api/graph/officer/{officer_id}/career`
- **기능:**
  - 경력 이력 타임라인 (시간순 정렬)
  - "그래프에 표시" 버튼 → `GET /api/graph/officer/{officer_id}/career-network`
  - 회사명 클릭 → `POST /api/graph/recenter` (Company 중심)

#### Step 4: SubscriberInvestmentPanel.tsx
- **역할:** 인수자 투자 이력 표시
- **API:** `GET /api/graph/subscriber/{subscriber_id}/investments`
- **기능:**
  - 투자한 회사 목록 (accordion 형식)
  - 회사별 CB 목록 표시
  - CB 클릭 → `POST /api/graph/recenter` (CB 중심)
  - "투자 네트워크 보기" → `GET /api/graph/subscriber/{subscriber_id}/investment-network`

#### Step 5: GraphControls.tsx
- **역할:** 그래프 조작 컨트롤
- **기능:**
  - 확대/축소 버튼
  - 레이아웃 재정렬 (force-directed)
  - 필터 (노드 타입별 show/hide)
  - 초기화 버튼

#### Step 6: GraphLegend.tsx
- **역할:** 노드/관계 범례
- **기능:**
  - 노드 타입별 색상/모양 설명
  - 관계 타입별 선 스타일 설명
  - 토글 가능

#### Step 7: GraphExplorer.tsx (페이지)
- **역할:** 전체 그래프 탐색 페이지
- **기능:**
  - 회사 검색 → 검색된 회사 중심 그래프 로드
  - `GET /api/graph/company/{company_id}`로 초기 그래프 로드
  - 좌측: GraphControls + GraphLegend
  - 중앙: GraphCanvas
  - 우측: NodeDetailPanel (노드 선택 시 표시)

---

## API 연동 (이미 구현된 Backend 엔드포인트)

### Graph API Endpoints (app/api/endpoints/graph.py)

```python
# 1. 회사 중심 네트워크
GET /api/graph/company/{company_id}?depth=1&limit=100

# 2. 임원 경력 이력
GET /api/graph/officer/{officer_id}/career

# 3. 임원 경력 네트워크 확장
GET /api/graph/officer/{officer_id}/career-network

# 4. Subscriber 투자 이력
GET /api/graph/subscriber/{subscriber_id}/investments

# 5. Subscriber 투자 네트워크 확장
GET /api/graph/subscriber/{subscriber_id}/investment-network

# 6. 노드 중심 전환
POST /api/graph/recenter
Body: { "node_type": "Company|Officer|CB|Subscriber", "node_id": "..." }
```

---

## neovis.js 구현 방식

### 직접 Cypher 쿼리 방식 (채택)

neovis.js는 Neo4j에 직접 연결하여 Cypher 쿼리를 실행합니다.

```typescript
const config = {
  containerId: "graph-canvas",
  neo4j: {
    serverUrl: "bolt://localhost:7687",
    serverUser: "neo4j",
    serverPassword: "password"
  },
  initialCypher: "MATCH (c:Company {id: $companyId})-[r]-(n) RETURN c, r, n LIMIT 100",
  labels: {
    Company: {
      label: "name",
      size: "total_connections",
      color: "#4A90E2"
    },
    Officer: {
      label: "name",
      color: (node) => {
        const careerCount = node.properties.career_count || 0;
        if (careerCount <= 2) return "#A8D8FF";
        if (careerCount <= 5) return "#5AAEFF";
        if (careerCount <= 10) return "#2E7DD4";
        return "#1A4D8F";
      }
    }
  },
  relationships: {
    WORKS_AT: { color: "#999", width: 2 },
    WORKED_AT: { color: "#CCC", width: 1, dashed: true }
  }
};

const viz = new NeoVis(config);
viz.render();
```

### REST API 방식 (보조)

경력/투자 이력 등 상세 데이터는 Backend REST API 사용:

```typescript
// 임원 경력 이력 조회
const careerData = await axios.get(`/api/graph/officer/${officerId}/career`);

// 그래프 확장
viz.updateWithCypher("MATCH (o:Officer {id: $id})-[:WORKED_AT]->(c) RETURN o, c");
```

---

## 현재 진행 상황

### ✅ 완료 (2025-12-10 기준)

#### 핵심 그래프 시각화
1. ✅ neovis.js 설치 (v2.1.0)
2. ✅ d3 설치 (v7.9.0)
3. ✅ GraphVisualization 디렉토리 생성
4. ✅ GraphCanvas.tsx - D3 기반 인터랙티브 그래프
5. ✅ NodeDetailPanel.tsx - 노드 상세 정보 패널
6. ✅ GraphControls.tsx - 확대/축소/필터 컨트롤
7. ✅ GraphLegend.tsx - 노드/관계 범례
8. ✅ GraphPage.tsx - 그래프 탐색 메인 페이지
9. ✅ 라우팅 연동

#### 상태 관리 (Phase 20)
10. ✅ Zustand 설치 및 설정
11. ✅ graphStore.ts - 그래프 상태 (centerCompany, selectedNode, visibleNodeTypes, dateRange)
12. ✅ reportStore.ts - 보고서 캐싱 (10분 TTL)
13. ✅ authStore.ts - 인증 상태 (mock login)

#### 네비게이션 (Phase 18)
14. ✅ useGraphNavigation.ts - 네비게이션 상태 훅
15. ✅ NavigationButtons.tsx - 뒤로가기/앞으로가기
16. ✅ Breadcrumb.tsx - 네비게이션 경로 표시
17. ✅ 키보드 단축키 (Alt+←, Alt+→)

#### Loading/Error 컴포넌트 (Phase 21)
18. ✅ Loading.tsx - 로딩 스피너 (PageLoading, InlineLoading, ButtonLoading)
19. ✅ Skeleton.tsx - 스켈레톤 UI (SkeletonCard, SkeletonTable, SkeletonGraph, SkeletonDashboard)
20. ✅ ErrorBoundary.tsx - 에러 처리 (ErrorFallback, ApiError)
21. ✅ EmptyState.tsx - 빈 상태 (NoSearchResults, NoData, NoGraphData, NoOfficers, NoReports)

### 🔄 진행중 / ⏳ 예정

#### Phase 19: 기간 필터 API 연동 (~1h)
- ⏳ DateRangePicker와 API 연동
- ⏳ 날짜 범위에 따른 그래프 필터링

#### Phase 22: 성능 최적화 (~2h)
- ⏳ React.memo / useMemo 적용
- ⏳ 번들 사이즈 최적화 (현재 552KB → 목표 400KB)
- ⏳ 코드 스플리팅 (dynamic import)
- ⏳ 이미지/아이콘 최적화

---

## 소요 시간 기록

### 완료된 작업
| 작업 | 예상 | 실제 |
|------|------|------|
| GraphCanvas.tsx | 2h | ✅ 완료 |
| NodeDetailPanel.tsx | 1h | ✅ 완료 |
| GraphControls.tsx | 0.5h | ✅ 완료 |
| GraphLegend.tsx | 0.5h | ✅ 완료 |
| GraphPage.tsx | 1h | ✅ 완료 |
| Zustand 상태관리 | 1.5h | ✅ 완료 |
| Navigation History | 1h | ✅ 완료 |
| Loading/Error 컴포넌트 | 1h | ✅ 완료 |

### 남은 작업
| 작업 | 예상 |
|------|------|
| 기간 필터 API 연동 | 1h |
| 성능 최적화 | 2h |
| **총 남은 시간** | **~3h** |

---

## 빌드 현황

```
✓ 1536 modules transformed
✓ built in 1.77s

dist/index.html                   0.47 kB │ gzip:   0.35 kB
dist/assets/index-C3h_SYM7.css   50.61 kB │ gzip:   8.46 kB
dist/assets/index-CV8WJdDk.js   552.38 kB │ gzip: 166.26 kB
```

---

## 다음 단계

1. ⏳ Phase 19: DateRangePicker API 연동
2. ⏳ Phase 22: 성능 최적화
   - React.memo / useMemo 적용
   - 코드 스플리팅 (lazy loading)
   - 번들 사이즈 최적화

---

## 구현된 파일 구조

```
frontend/src/
├── components/
│   ├── common/
│   │   ├── index.ts
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── SearchInput.tsx
│   │   ├── DateRangePicker.tsx
│   │   ├── Loading.tsx          # Phase 21
│   │   ├── Skeleton.tsx         # Phase 21
│   │   ├── ErrorBoundary.tsx    # Phase 21
│   │   └── EmptyState.tsx       # Phase 21
│   ├── graph/
│   │   ├── index.ts
│   │   ├── GraphCanvas.tsx
│   │   ├── GraphControls.tsx
│   │   ├── GraphLegend.tsx
│   │   ├── NodeDetailPanel.tsx
│   │   ├── NavigationButtons.tsx  # Phase 18
│   │   └── Breadcrumb.tsx         # Phase 18
│   └── panels/
│       ├── OfficerPanel.tsx
│       ├── CompanyPanel.tsx
│       └── CBPanel.tsx
├── hooks/
│   └── useGraphNavigation.ts    # Phase 18
├── store/
│   ├── index.ts                 # Phase 20
│   ├── graphStore.ts            # Phase 20
│   ├── reportStore.ts           # Phase 20
│   └── authStore.ts             # Phase 20
├── pages/
│   ├── HomePage.tsx
│   ├── GraphPage.tsx
│   └── ReportPage.tsx
├── services/
│   └── api.ts
└── types/
    └── graph.ts
```

---

**작성자:** Claude Code
**최초 작성:** 2025-11-20
**최종 수정:** 2025-12-10
**버전:** 2.0.0
