# Frontend Development Checkpoint

## Phase 7 완료: 백엔드 버그 수정 및 데이터 정합성 (2025-12-12)

### 완료 항목

#### 1. Graph API 연결 문제 해결 (`backend/app/api/endpoints/graph.py`)
- [x] `neo4j_driver` import 스코핑 이슈 수정
- [x] 정적 import → 동적 모듈 참조로 변경
- [x] `init_db()` 이후 업데이트된 driver 값 정상 사용

```python
# Before (문제)
from app.database import neo4j_driver as shared_neo4j_driver

# After (해결)
import app.database as db_module
driver = db_module.neo4j_driver  # 동적 참조
```

#### 2. Neo4j 레거시 데이터 정리
- [x] 직책명이 이름으로 저장된 레거시 임원 데이터 698건 삭제
- [x] 영향받은 노드: 상무이사, 사외이사, 전무이사, 대표이사, 감사 등
- [x] 노브랜드 등 회사 임원 노드 정상 표시 확인

#### 3. 임원 동일인 식별 로직 개선 (`backend/app/api/endpoints/graph.py`)
- [x] `get_officer_career`: 이름만 비교 → 이름 + 생년월일 비교
- [x] `get_officer_career_network`: 동일 로직 적용
- [x] 생년월일 형식 정규화 (1975.03, 1968년 10월 등 다양한 형식 처리)
- [x] 동명이인 구분 테스트 완료 (이재상 1957.01 vs 1956년 01월)

### 수정된 파일

```
backend/
└── app/
    └── api/
        └── endpoints/
            └── graph.py    # neo4j_driver 동적 참조, 임원 식별 로직 개선
```

### Cypher 쿼리 변경 (임원 경력 조회)

```cypher
// 생년월일 비교: 숫자만 추출하여 앞 6자리 비교 (YYYYMM)
MATCH (o:Officer)-[r:WORKS_AT|WORKED_AT]->(c:Company)
WHERE o.name = target.name
  AND (
    (o.birth_date IS NOT NULL AND target.birth_date IS NOT NULL
     AND substring(replace(replace(replace(o.birth_date, '년', ''), '월', ''), '.', ''), 0, 6)
        = substring(replace(replace(replace(target.birth_date, '년', ''), '월', ''), '.', ''), 0, 6))
    OR (o.birth_date IS NULL AND target.birth_date IS NULL)
  )
```

---

## Phase 6 완료: 그래프 인터랙션 강화 (2025-12-10)

### 완료 항목

#### 1. Re-center 기능 (`src/components/graph/ForceGraph.tsx`)
- [x] 노드 더블클릭 → 해당 노드 중심으로 그래프 이동
- [x] `centerOnNodeFn()` - D3 transition으로 1초 애니메이션 (easeCubicInOut)
- [x] `forwardRef` + `useImperativeHandle`로 외부에서 호출 가능
- [x] `ForceGraphRef` 타입 export
- [x] 현재 줌 레벨 유지 (최소 1.2배)

#### 2. NodeDetailPanel Re-center 버튼 (`src/components/graph/NodeDetailPanel.tsx`)
- [x] `onRecenter` prop 추가
- [x] "노드로 이동" 버튼 (모든 노드 타입)
- [x] GraphPage에서 `forceGraphRef` 연결

#### 3. 임원 타사 근무 이력 (`src/api/graph.ts`, `NodeDetailPanel.tsx`)
- [x] `OfficerCareer` 타입: company_name, position, start_date, end_date, is_current
- [x] `fetchOfficerCareer(officerId)` API 함수
- [x] 임원 노드 선택 시 경력 자동 로드
- [x] **타임라인 UI**: 세로선 + 원형 마커
- [x] 현재 재직 중: 녹색 배경 + "재직중" 배지
- [x] 로딩 스켈레톤, 에러 메시지, "경력 정보 없음"

#### 4. 인수인 타사 CB 참여 이력 (`src/api/graph.ts`, `NodeDetailPanel.tsx`)
- [x] `SubscriberInvestment` 타입: company_name, cb_issue_date, amount
- [x] `fetchSubscriberInvestments(subscriberId)` API 함수
- [x] 인수인 노드 선택 시 투자 이력 자동 로드
- [x] **카드 형식 UI**: 회사명 + 금액(억원) + 투자일
- [x] 하단 총 투자금액 합계 표시
- [x] 최근 투자가 위로 정렬
- [x] 로딩 스켈레톤, 에러 메시지, "투자 이력 없음"

#### 5. 더미 데이터 개선
- [x] 임원 이름: 김영철, 이준호, 박민정, 최승환 (graph.ts, report.ts)

### API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/graph/officer/{id}/career` | GET | 임원 경력 이력 |
| `/api/graph/subscriber/{id}/investments` | GET | 인수인 투자 이력 |

### 테스트 결과

```bash
# 빌드
npm run build
# ✓ 676 modules transformed
# dist/assets/*.js    339.56 kB (gzip: 110.85 kB)
# ✓ built in 1.17s
```

---

## Phase 5 완료: CB/임원/재무 API 연동 (2025-12-10)

### 완료 항목

#### 1. CB 발행 API 연동 (`src/api/report.ts`)
- [x] `ApiConvertibleBond` 백엔드 응답 타입 정의
- [x] `getCompanyConvertibleBonds(companyId)` - 회사 CB 발행 목록 조회
- [x] `mapConvertibleBondToFrontend()` - API 응답 → CBIssuance 변환
- [x] 상태 매핑 (active/converted/redeemed)

#### 2. CB 인수자 API 연동
- [x] `ApiCBSubscriber` 백엔드 응답 타입 정의
- [x] `getCompanyCBSubscribers(companyId)` - 회사 CB 인수자 목록 조회
- [x] `mapCBSubscriberToFrontend()` - API 응답 → CBSubscriber 변환
- [x] 인수자 유형 매핑 (institution/individual/related)

#### 3. 임원 API 연동
- [x] `ApiOfficer` 백엔드 응답 타입 정의
- [x] `getCompanyOfficers(companyId)` - 회사 임원 목록 조회
- [x] `mapOfficerToFrontend()` - API 응답 → Officer 변환

#### 4. 재무제표 API 연동
- [x] `ApiFinancialStatement` 백엔드 응답 타입 정의
- [x] `getCompanyFinancials(companyId)` - 회사 재무제표 조회
- [x] `mapFinancialToFrontend()` - API 응답 → FinancialStatement 변환
- [x] 연도별 그룹화 (최신 데이터 우선)

#### 5. 통합 보고서 API 업데이트
- [x] `getCompanyReport()` 6개 API 병렬 호출
- [x] 빈 데이터 시 더미 데이터 fallback

### 백엔드 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/convertible-bonds/company/{company_id}` | GET | 회사 CB 발행 목록 |
| `/api/cb-subscribers/bond/{cb_id}` | GET | CB별 인수자 목록 |
| `/api/officers/company/{company_id}` | GET | 회사 임원 목록 |
| `/api/financials/companies/{company_id}/statements` | GET | 회사 재무제표 |

### 테스트 결과

```bash
# TypeScript
npx tsc --noEmit  # 에러 없음

# 빌드
npm run build
# ✓ 676 modules transformed
# dist/assets/*.css    23.68 kB (gzip: 4.99 kB)
# dist/assets/*.js    333.26 kB (gzip: 109.23 kB)
# ✓ built in 2.16s
```

### Fallback 동작
- [x] API 호출 실패 시 개별 더미 데이터 반환
- [x] 전체 API 실패 시 통합 더미 데이터 반환

---

## Phase 5-1 부분 완료: 추가 기능 (2025-12-10)

### 완료 항목

#### 1. 검색 자동완성 개선 (`src/components/common/SearchInput.tsx`)
- [x] 재사용 가능한 SearchInput 컴포넌트 분리
- [x] **검색어 하이라이팅** - 검색어와 일치하는 부분 노란색 표시
- [x] **최근 검색어 저장** - localStorage에 최대 5개 저장
- [x] **최근 검색어 표시** - 검색창 포커스 시 표시
- [x] **최근 검색어 삭제** - 개별 삭제 및 전체 삭제
- [x] 사이즈 옵션 (sm, md, lg)
- [x] MainSearchPage에 적용

#### 2. 그래프 필터링 (`src/components/graph/GraphControls.tsx`)
- [x] **노드 타입별 필터링** - 회사, 임원, CB 투자자, 전환사채 토글
- [x] **노드 카운트 표시** - 각 타입별 노드 수 표시
- [x] **전체 선택/회사만** 버튼
- [x] **필터링된 통계 표시** - 하단 통계에 필터링 결과 반영 (현재/전체)
- [x] GraphPage에 필터링 로직 적용 (useMemo)

### 생성된 파일

```
src/
└── components/
    └── common/
        └── SearchInput.tsx  # 검색 자동완성 컴포넌트
```

### 수정된 파일

```
src/
├── components/
│   ├── common/
│   │   └── index.ts         # SearchInput export 추가
│   └── graph/
│       └── GraphControls.tsx # 필터링 기능 추가
└── pages/
    ├── MainSearchPage.tsx   # SearchInput 컴포넌트 사용
    └── GraphPage.tsx        # 필터링 로직 추가
```

### 테스트 결과

```bash
# TypeScript
npx tsc --noEmit  # 에러 없음

# 빌드
npm run build
# ✓ 676 modules transformed
# dist/assets/*.css    23.68 kB (gzip: 4.99 kB)
# dist/assets/*.js    331.15 kB (gzip: 108.61 kB)
# ✓ built in 1.24s
```

### 미완료 항목 (Phase 5 남은 작업)
- [ ] 보고서 PDF 다운로드 (추가 라이브러리 필요: jspdf, html2canvas)
- [ ] CB/임원/재무 실제 데이터 API 연동 (백엔드 API 추가 필요)

---

## Phase 4-3 완료: 분석보고서 페이지 API 연동 (2025-12-09)

### 완료 항목

#### 1. Report API 서비스 함수 (`src/api/report.ts`)
- [x] `ApiRiskFactor`, `ApiRiskComponent`, `ApiRiskScoreResponse` 백엔드 응답 타입
- [x] `ApiCompanyDetail` 회사 상세 정보 응답 타입
- [x] `CompanyReportData` 프론트엔드 통합 타입
- [x] `mapRiskScoreToFrontend()` - API 리스크 점수 → 프론트 RiskScore 변환
- [x] `mapRiskLevelToGrade()` - 리스크 레벨 → 투자등급 매핑
- [x] `getCompanyDetail(companyId)` - 회사 상세 정보 조회
- [x] `getCompanyRiskScore(companyId)` - 리스크 점수 조회
- [x] `getCompanyReport(companyId)` - 통합 보고서 데이터 조회
- [x] `generateDummyReportData()` - API 실패 시 더미 데이터 fallback

#### 2. ReportPage API 연동 업데이트
- [x] `getCompanyReport()` API 호출
- [x] 로딩 상태 (스피너 + "보고서 로딩 중...")
- [x] 에러 상태 (에러 아이콘 + 메시지 + "다시 시도" 버튼)
- [x] 빈 상태 ("보고서 데이터가 없습니다")
- [x] API 연결 실패 배너 ("API 연결 실패 - 더미 데이터를 표시합니다")
- [x] 경고 메시지 리스트 표시 (API warnings 배열)
- [x] 분석 시점 표시 (calculatedAt)
- [x] `handleRetry()` 재시도 함수

### 백엔드 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/companies/{company_id}` | GET | 회사 상세 정보 |
| `/api/companies/{company_id}/risk-score` | GET | 리스크 점수 (5가지 컴포넌트) |

### 생성된 파일

```
src/
└── api/
    └── report.ts    # Report API 함수 + 타입 매핑 + 더미 데이터
```

### 테스트 결과

```bash
# TypeScript
npx tsc --noEmit  # 에러 없음

# 빌드
npm run build
# ✓ 675 modules transformed
# dist/assets/*.css    22.50 kB (gzip: 4.87 kB)
# dist/assets/*.js    325.25 kB (gzip: 107.11 kB)
# ✓ built in 1.37s
```

### Fallback 동작 확인
- [x] 백엔드 미실행 → 더미 데이터 표시
- [x] 콘솔: "Report API 호출 실패, 더미 데이터 사용"
- [x] UI 정상 표시 (리스크 게이지, 등급 카드, 데이터 탭)

---

## Phase 4-2 완료: 관계도 페이지 API 연동 (2025-12-09)

### 완료 항목

#### 1. Graph API 서비스 함수 (`src/api/graph.ts`)
- [x] `ApiGraphNode`, `ApiGraphRelationship`, `ApiGraphResponse` 백엔드 응답 타입
- [x] `mapNodeType()` - API 노드 타입 → 프론트 노드 타입 매핑
- [x] `mapLinkType()` - API 관계 타입 → 프론트 링크 타입 매핑
- [x] `transformApiResponse()` - API 응답 → GraphData 변환
- [x] `getCompanyNetwork(companyId, depth, limit)` - 회사 중심 네트워크 조회
- [x] `getOfficerCareerNetwork(officerId)` - 임원 경력 네트워크 조회
- [x] `getSubscriberInvestmentNetwork(subscriberId)` - CB 인수자 투자 네트워크 조회
- [x] `generateDummyGraphData()` - API 실패 시 더미 데이터 fallback

#### 2. GraphPage API 연동 업데이트
- [x] `getCompanyNetwork()` API 호출
- [x] 로딩 상태 (스피너 + "그래프 로딩 중...")
- [x] 에러 상태 (에러 아이콘 + 메시지 + "다시 시도" 버튼)
- [x] 빈 상태 ("관계 데이터가 없습니다")
- [x] API 연결 실패 배너 ("API 연결 실패 - 더미 데이터를 표시합니다")
- [x] `handleRetry()` 재시도 함수

### 백엔드 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/graph/company/{company_id}?depth=1&limit=100` | GET | 회사 중심 네트워크 |
| `/api/graph/officer/{officer_id}/career-network` | GET | 임원 경력 네트워크 |
| `/api/graph/subscriber/{subscriber_id}/investment-network` | GET | CB 인수자 투자 네트워크 |

### 생성된 파일

```
src/
└── api/
    └── graph.ts    # Graph API 함수 + 타입 매핑 + 더미 데이터
```

### 테스트 결과

```bash
# TypeScript
npx tsc --noEmit  # 에러 없음

# 빌드
npm run build
# ✓ 674 modules transformed
# dist/assets/*.css    22.27 kB (gzip: 4.82 kB)
# dist/assets/*.js    321.12 kB (gzip: 106.67 kB)
# ✓ built in 1.13s
```

### Fallback 동작 확인
- [x] 백엔드 미실행 → 더미 데이터 표시
- [x] 콘솔: "Graph API 호출 실패, 더미 데이터 사용"
- [x] UI 정상 표시 (11 노드, 11 링크)

---

## Phase 3-3 완료: 분석보고서 페이지 (2025-12-09)

### 완료 항목

#### 1. 리포트 타입 정의 (`src/types/report.ts`)
- [x] `RiskScore` - 리스크 점수 (total, cbRisk, officerRisk, financialRisk, networkRisk)
- [x] `InvestmentGrade` - 투자등급 타입 (AAA ~ D)
- [x] `CBIssuance`, `CBSubscriber`, `Officer`, `FinancialStatement` 타입
- [x] `riskLevelConfig`, `gradeConfig` - 색상/라벨 매핑
- [x] `getRiskLevel()` - 점수 → 레벨 판정 함수

#### 2. 리포트 컴포넌트 (`src/components/report/`)
- [x] `RiskGauge.tsx` - D3.js 반원형 게이지 차트
  - 0-100 점수 시각화
  - 눈금 (0, 25, 50, 75, 100)
  - 색상별 리스크 레벨 표시
- [x] `GradeCard.tsx` - 투자등급 카드
- [x] `ScoreBreakdown.tsx` - 리스크 구성 요소 바 차트
- [x] `DataTabs.tsx` - 세부 데이터 탭
  - CB 발행 테이블
  - CB 인수인 테이블
  - 임원 현황 테이블
  - 재무제표 테이블

#### 3. ReportPage 업데이트
- [x] 리스크 대시보드 (게이지 + 등급 + 구성요소)
- [x] 주의 필요 요약 배너
- [x] 세부 데이터 탭 전환
- [x] 면책조항

### 생성된 파일

```
src/
├── types/
│   └── report.ts              # 리포트 타입 + 색상 매핑
└── components/
    └── report/
        ├── index.ts           # 배럴 export
        ├── RiskGauge.tsx      # D3 게이지 차트
        ├── GradeCard.tsx      # 투자등급 카드
        ├── ScoreBreakdown.tsx # 점수 구성 바차트
        └── DataTabs.tsx       # 세부 데이터 탭
```

### 테스트 결과

```bash
# TypeScript
npx tsc --noEmit  # 에러 없음

# 빌드
npm run build
# ✓ 673 modules transformed
# dist/assets/*.css    22.27 kB (gzip: 4.82 kB)
# dist/assets/*.js    317.56 kB (gzip: 105.47 kB)
# ✓ built in 1.11s
```

### 스크린샷
`.playwright-mcp/report-page-dashboard.png`

---

## Phase 3-2 완료: 관계도 페이지 (2025-12-09)

### 완료 항목

#### 1. 그래프 타입 정의 (`src/types/graph.ts`)
- [x] `GraphNode` - 노드 데이터 (회사, 임원, CB투자자, 전환사채)
- [x] `GraphLink` - 엣지 데이터 (임원, CB발행, 계열사 등)
- [x] `NodeType` / `nodeTypeColors` - 노드 타입별 색상
- [x] `linkTypeColors` - 엣지 타입별 색상

#### 2. 그래프 컴포넌트 (`src/components/graph/`)
- [x] `ForceGraph.tsx` - D3.js Force-directed 그래프
  - Force 시뮬레이션 (link, charge, center, collision)
  - 노드 드래그 상호작용
  - 줌/패닝 (d3.zoom)
  - 노드 클릭 이벤트
  - 선택 노드 하이라이트
- [x] `NodeDetailPanel.tsx` - 노드 상세 정보 사이드 패널
  - 회사: 리스크 레벨, 투자등급
  - 임원: 직책
  - CB: 투자금액, 발행일
- [x] `GraphControls.tsx` - 줌/패닝 컨트롤 + 범례

#### 3. GraphPage 업데이트
- [x] 더미 그래프 데이터 생성 (11 노드, 11 링크)
- [x] 컨테이너 크기 반응형 감지
- [x] 노드 클릭 → 사이드 패널 표시
- [x] 하단 통계 (관련 회사, 임원, CB 투자자, 전환사채, 관계 수)
- [x] 분석 보고서 링크

### 생성된 파일

```
src/
├── types/
│   └── graph.ts           # 그래프 타입 + 색상 매핑
└── components/
    └── graph/
        ├── index.ts       # 배럴 export
        ├── ForceGraph.tsx # D3 Force 그래프
        ├── NodeDetailPanel.tsx  # 노드 상세 패널
        └── GraphControls.tsx    # 줌/범례 컨트롤
```

### 테스트 결과

```bash
# TypeScript
npx tsc --noEmit  # 에러 없음

# 빌드
npm run build
# ✓ 667 modules transformed
# dist/assets/*.css    20.67 kB (gzip: 4.59 kB)
# dist/assets/*.js    298.51 kB (gzip: 100.06 kB)
# ✓ built in 1.11s
```

### 스크린샷
`.playwright-mcp/graph-page-node-selected.png`

---

## Phase 4-1 완료: 홈페이지 DB 연동 (2025-12-09)

### 완료 항목

#### 1. API 클라이언트 설정
- [x] Axios 인스턴스 생성 (`src/api/client.ts`)
- [x] 요청/응답 인터셉터 설정
- [x] 인증 토큰 자동 첨부
- [x] 401 에러 시 로그인 리다이렉트
- [x] 환경변수 API URL 지원 (`VITE_API_URL`)

#### 2. 타입 정의 (`src/types/company.ts`)
```typescript
interface CompanySearchResult {
  id: string
  corp_code: string
  name: string
  cb_count: number
  risk_level: string | null
  investment_grade: string | null
}
```

#### 3. API 서비스 함수 (`src/api/company.ts`)
- [x] `searchCompanies(query, limit)` - 회사 검색
- [x] `getHighRiskCompanies(minScore, limit)` - 고위험 회사 목록
- [x] `checkApiHealth()` - API 상태 확인
- [x] API 실패 시 더미 데이터 fallback

#### 4. 홈페이지 API 연동
- [x] 검색: `searchCompanies()` 호출
- [x] 고위험 목록: `getHighRiskCompanies()` 호출
- [x] 로딩 상태 표시 (스피너)
- [x] 에러 상태 표시 (재시도 버튼)
- [x] 빈 상태 표시 ("현재 고위험 기업이 없습니다")
- [x] API 연결 실패 배너 표시

### 백엔드 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/report/search?q={query}&limit=20` | GET | 회사 검색 |
| `/api/report/high-risk?min_score=50&limit=50` | GET | 고위험 회사 |

### 생성된 파일

```
src/
├── api/
│   ├── client.ts      # Axios 인스턴스
│   └── company.ts     # 회사 API 함수
└── types/
    └── company.ts     # 타입 + 색상 매핑
```

### 테스트 결과

```bash
# TypeScript
npx tsc --noEmit  # 에러 없음

# 빌드
npm run build
# ✓ 96 modules transformed
# dist/assets/*.css    19.70 kB (gzip: 4.45 kB)
# dist/assets/*.js    224.16 kB (gzip: 74.77 kB)
# ✓ built in 789ms
```

### Fallback 동작 확인
- [x] 백엔드 미실행 → 더미 데이터 표시
- [x] 콘솔: "API 호출 실패, 더미 데이터 사용"
- [x] UI 정상 표시

### 스크린샷
`.playwright-mcp/homepage-api-connected.png`

---

## Phase 3-1 완료: 홈페이지 UI 완성 (2025-12-09)

### 완료 항목
- [x] 검색창 자동완성 (debounce 300ms, 키보드 네비게이션)
- [x] 더미 데이터 12개 회사
- [x] 고위험 회사 카드 목록
- [x] 리스크 레벨/투자등급 색상
- [x] 애니메이션 (fade-in, slide-down)
- [x] 서비스 소개 섹션

---

## Phase 2 완료: 레이아웃 컴포넌트 (2025-12-09)

### 완료 항목
- [x] Header.tsx - 반응형 네비게이션
- [x] Footer.tsx - 4컬럼 그리드
- [x] MainLayout.tsx - Header + Outlet + Footer

---

## Phase 1 완료: 프로젝트 셋업 (2025-12-09)

### 완료 항목
- [x] Vite + React 18 + TypeScript 5
- [x] 패키지: react-router-dom, axios, @tanstack/react-query, zustand, d3, tailwindcss
- [x] 폴더 구조
- [x] 라우팅 설정

---

## 다음 단계

### Phase 5: 추가 기능 (완료)
- [x] 검색 자동완성 개선 (검색어 하이라이팅, 최근 검색어)
- [x] 그래프 필터링 (노드 타입별 토글, 카운트 표시)
- [x] CB/임원/재무 실제 데이터 API 연동
- [ ] 보고서 PDF 다운로드 (jspdf, html2canvas 설치 필요)

---

## 백엔드 서버 실행

```bash
cd /Users/jaejoonpark/raymontology/backend
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

## 프론트엔드 개발 서버

```bash
cd /Users/jaejoonpark/raymontology/frontend
npm run dev
# http://localhost:5173
```

---

**저장 시점**: 2025-12-12 Phase 7 완료 (백엔드 버그 수정 및 데이터 정합성)
