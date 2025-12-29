# RaymondsIndex™ 독립 사이트 개발 계획서

> **작성일**: 2025-12-29
> **버전**: 2.1 (운영 중)
> **프로덕션 URL**: https://raymondsindex.konnect-ai.net
> **백엔드 연동**: https://raymontology-production.up.railway.app/api
> **상태**: ✅ 운영 중 (2025-12-29)
> **데이터**: 2,695개 기업, 7,646건 레코드 (2024년 포함 3개년)

---

## 1. 프로젝트 개요

### 1.1 목적
기존 Raymontology 프로젝트의 RaymondsIndex 기능을 **독립적인 웹사이트**로 분리하여 운영

### 1.2 핵심 요구사항
- Raymontology 사이트와 **별개의 독립 사이트**로 구현
- 기존 백엔드 API (`raymontology-production.up.railway.app`) 활용
- 신규 프론트엔드 프로젝트 생성 (Next.js 14+)
- 도메인: `konnect-ai.net/raymondsindex`

### 1.3 기술 스택

| 영역 | 기술 |
|------|------|
| Framework | Next.js 14+ (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui |
| Charts | Recharts |
| State Management | React Query (TanStack Query) |
| Icons | Lucide React |
| Deployment | Vercel / Railway Static |

---

## 2. 프로젝트 구조

```
raymondsindex-web/                 # 새로운 독립 프로젝트
├── app/
│   ├── layout.tsx                 # 루트 레이아웃
│   ├── page.tsx                   # 홈페이지
│   ├── screener/
│   │   └── page.tsx               # 스크리너
│   ├── company/
│   │   └── [id]/
│   │       └── page.tsx           # 기업 상세
│   └── methodology/
│       └── page.tsx               # 방법론
├── components/
│   ├── ui/                        # shadcn/ui 기본 컴포넌트
│   ├── layout/
│   │   ├── header.tsx
│   │   └── footer.tsx
│   ├── grade-badge.tsx            # 등급 뱃지
│   ├── score-display.tsx          # 점수 표시
│   ├── metric-card.tsx            # 지표 카드
│   ├── company-search-bar.tsx     # 검색바
│   ├── sub-index-radar.tsx        # 레이더 차트
│   ├── trend-chart.tsx            # 추세 차트
│   ├── risk-flags-panel.tsx       # 위험 신호 패널
│   ├── top-companies-table.tsx    # TOP 기업 테이블
│   ├── grade-distribution.tsx     # 등급 분포 차트
│   └── alert-zone.tsx             # 경고 영역
├── lib/
│   ├── api.ts                     # API 클라이언트
│   ├── types.ts                   # 타입 정의
│   ├── constants.ts               # 상수 (등급 색상 등)
│   └── utils.ts                   # 유틸리티 함수
├── hooks/
│   ├── use-ranking.ts             # 랭킹 조회
│   ├── use-company.ts             # 기업 상세
│   ├── use-search.ts              # 검색
│   └── use-statistics.ts          # 통계
├── styles/
│   └── globals.css                # 글로벌 스타일
├── public/
│   ├── logo.svg
│   └── og-image.png
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 3. 개발 단계

### Phase 1: 프로젝트 초기화 (1일)

#### 3.1.1 프로젝트 생성
```bash
# 프로젝트 디렉토리 생성
cd /Users/jaejoonpark/raymontology
mkdir raymondsindex-web
cd raymondsindex-web

# Next.js 프로젝트 초기화
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*"

# 의존성 설치
npm install @tanstack/react-query recharts lucide-react
npm install -D @types/node
npx shadcn@latest init
```

#### 3.1.2 shadcn/ui 컴포넌트 설치
```bash
npx shadcn@latest add button card input table badge dialog
npx shadcn@latest add select slider checkbox tabs separator
```

#### 3.1.3 환경 변수 설정
```env
# .env.local
NEXT_PUBLIC_API_URL=https://raymontology-production.up.railway.app/api
```

---

### Phase 2: 기본 레이아웃 및 디자인 시스템 (1일)

#### 3.2.1 글로벌 스타일 설정
- Tailwind 테마 커스터마이징 (등급 색상)
- Pretendard 폰트 설정
- CSS 변수 정의

#### 3.2.2 레이아웃 컴포넌트
- Header (로고 + 네비게이션 + 검색)
- Footer (저작권 + 면책조항)

#### 3.2.3 기본 UI 컴포넌트
- GradeBadge
- ScoreDisplay
- MetricCard

---

### Phase 3: API 연동 레이어 (1일)

#### 3.3.1 API 클라이언트 구현
```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export const api = {
  ranking: {
    getAll: (params: RankingParams) => fetch(...),
    getByGrade: (grade: string) => fetch(...),
  },
  company: {
    getById: (id: string) => fetch(...),
    search: (query: string) => fetch(...),
  },
  statistics: {
    getDistribution: () => fetch(...),
    getDowngraded: (days: number) => fetch(...),
  },
};
```

#### 3.3.2 React Query 훅 구현
- `useRanking()` - 랭킹 목록 조회
- `useCompany(id)` - 기업 상세 조회
- `useSearch(query)` - 검색 (디바운스)
- `useStatistics()` - 통계 조회

#### 3.3.3 타입 정의
- RaymondsIndexResponse
- RankingParams
- StatisticsResponse

---

### Phase 4: 페이지 구현 (3일)

#### 3.4.1 홈페이지 (`/`) - 1일
- Hero Section (서비스 소개 + 검색바)
- TOP 10 기업 테이블
- 등급 분포 차트 (Horizontal Bar)
- Alert Zone (등급 하락 기업)

#### 3.4.2 Screener 페이지 (`/screener`) - 1일
- 필터 패널 (등급, 점수, 업종, 시가총액)
- 결과 테이블 (정렬, 페이지네이션)
- 상세 페이지 연결

#### 3.4.3 기업 상세 페이지 (`/company/[id]`) - 1일
- 헤더 (기업명, 등급, 점수)
- Sub-Index 레이더 차트
- 핵심 지표 카드 그리드
- 위험 신호 패널
- AI 해석 섹션
- 추세 차트 (5년)

---

### Phase 5: 추가 기능 및 최적화 (2일)

#### 3.5.1 방법론 페이지 (`/methodology`)
- 평가 체계 설명
- Sub-Index 상세 설명
- 특별 규칙 안내

#### 3.5.2 반응형 최적화
- 모바일 레이아웃 조정
- 터치 인터랙션 개선
- 차트 크기 조정

#### 3.5.3 SEO 및 메타데이터
- Open Graph 태그
- 페이지별 title/description
- sitemap.xml

---

## 4. 백엔드 API 현황

### 4.1 API 엔드포인트 현황

| 엔드포인트 | 설명 | 상태 |
|-----------|------|------|
| `GET /api/raymonds-index/ranking/list` | 랭킹 목록 | ✅ 사용 중 |
| `GET /api/raymonds-index/{company_id}` | 기업 상세 | ✅ 사용 중 |
| `GET /api/raymonds-index/statistics/summary` | 통계 (중복 제거됨) | ✅ 수정 완료 |
| `GET /api/raymonds-index/search/companies?q=` | 기업 검색 (자동완성) | ✅ 신규 추가 |
| `GET /api/raymonds-index/search/filter` | 조건 검색 | ✅ 사용 가능 |

### 4.2 신규 API 필요 여부

| 기능 | 엔드포인트 | 필요 여부 |
|------|-----------|----------|
| 등급 하락 기업 | `GET /api/raymonds-index/downgraded` | 신규 필요 |
| 연도별 추세 | `GET /api/raymonds-index/history/{id}` | 신규 필요 |
| 업종별 통계 | `GET /api/raymonds-index/statistics/sector` | 신규 필요 |

---

## 5. 일정 계획 (완료)

| Phase | 작업 내용 | 예상 기간 | 상태 |
|-------|----------|----------|------|
| 1 | 프로젝트 초기화 | 1일 | ✅ 완료 |
| 2 | 레이아웃 + 디자인 시스템 | 1일 | ✅ 완료 |
| 3 | API 연동 레이어 | 1일 | ✅ 완료 |
| 4 | 페이지 구현 (홈, 스크리너, 상세) | 3일 | ✅ 완료 |
| 5 | 방법론 + 반응형 + SEO | 2일 | ✅ 완료 |
| 6 | 인증 시스템 (로그인/회원가입/관리자) | 1일 | ✅ 완료 |
| 7 | 검색 API 및 통계 수정 | 1일 | ✅ 완료 |
| **합계** | | **10일** | ✅ |

---

## 6. 배포 전략

### 6.1 개발 환경
- 로컬: `npm run dev` → `localhost:3000`
- API: `https://raymontology-production.up.railway.app`

### 6.2 스테이징
- Vercel Preview 또는 Railway Preview

### 6.3 프로덕션
- 도메인: `konnect-ai.net/raymondsindex`
- 호스팅: Vercel 또는 Railway Static

### 6.4 CORS 설정 필요
기존 백엔드에 새 도메인 CORS 허용 추가:
```python
# backend/app/main.py
origins = [
    "https://raymontology.com",
    "https://konnect-ai.net",  # 추가 필요
]
```

---

## 7. 체크리스트

### 개발 착수 전 ✅

- [x] 프로젝트 디렉토리 생성 (`raymondsindex-web/`)
- [x] Next.js 프로젝트 초기화
- [x] shadcn/ui 설정
- [x] 환경 변수 설정
- [x] 백엔드 CORS 설정 확인

### 개발 완료 후 ✅

- [x] 모든 페이지 반응형 테스트
- [x] API 에러 핸들링 확인
- [x] 로딩 상태 UI 확인
- [x] SEO 메타태그 설정
- [x] 성능 최적화 (이미지, 번들)
- [x] 접근성 (a11y) 검토

### 추가 구현 (2025-12-27) ✅

- [x] 회원가입 페이지 (`/signup`) - 이용약관 모달 포함
- [x] 로그인 페이지 (`/login`)
- [x] 관리자 페이지 (`/admin`) - superuser 전용
- [x] HTTPS/SSL 인증서 적용 (Let's Encrypt)
- [x] 기업 검색 API 수정 (`/search/companies` 엔드포인트 추가)
- [x] 통계 API 수정 (중복 기업 제거)

### 지표 계산 및 UI 개선 (2025-12-28) ✅

#### Phase 1: 백엔드 - 투자괴리율 v2 계산 로직

수정 파일: `backend/app/services/raymonds_index_calculator.py`

**새로운 정의:**
- **현금성자산** = 현금 + 단기금융상품 + 장기금융상품 + 기타금융자산(비유동)
- **CAPEX (재무상태표)** = 유형자산 + 무형자산 + 사용권자산 + 관계기업투자
- **투자괴리율** = 현금성자산 증가비율 - CAPEX 증가비율 (2023~2025Q3 기간)

관련 함수: `_calculate_investment_gap_v2()` (라인 215-282)

#### Phase 2: 위험신호 분석 박스 개선

수정 파일: `raymondsindex-web/components/risk-flags-panel.tsx`

- [x] Red/Yellow Flags 없을 때 "정상 상태" UI 표시
- [x] 정상 상태 설명: "현재 위험 신호가 감지되지 않았습니다. 자본 배분 효율성이 양호한 상태입니다."
- [x] Red Flags 설명: "투자금 배분에 심각한 문제가 발견되었습니다. 투자 전 반드시 추가 조사가 필요합니다."
- [x] Yellow Flags 설명: "투자금 배분에 주의가 필요한 신호입니다. 향후 추이를 관찰하시기 바랍니다."

#### Phase 3: 지표 설명 Tooltip 추가

수정 파일:
- `raymondsindex-web/components/ui/tooltip.tsx` (shadcn/ui 컴포넌트)
- `raymondsindex-web/lib/constants.ts` (SUB_INDEX_INFO, METRIC_DESCRIPTIONS 추가)
- `raymondsindex-web/components/metric-card.tsx` (tooltip prop 추가)
- `raymondsindex-web/components/sub-index-radar.tsx` (SubIndexItem에 '?' 버튼 추가)
- `raymondsindex-web/app/company/[id]/page.tsx` (MetricCard에 tooltip 연결)

**Sub-Index 설명 (위험요소 관점):**

| 지표 | 설명 |
|------|------|
| CEI (자본 효율성) | 투입한 자본 대비 수익 창출 능력을 평가합니다. 자본 효율성이 낮으면 투자금이 성장에 기여하지 못하고 있을 수 있습니다. |
| RII (재투자 강도) | 벌어들인 이익을 성장에 재투자하는지 평가합니다. 재투자가 부족하면 현금만 쌓아두며 성장 기회를 놓치고 있을 수 있습니다. |
| CGI (현금 거버넌스) | 보유 현금을 생산적 자산으로 전환하는지 평가합니다. 단기금융상품에만 묻어두면 투자금이 유용될 위험이 있습니다. |
| MAI (모멘텀 정합성) | 매출 성장과 투자 방향이 일치하는지 평가합니다. 불일치하면 경영진의 자본 배분 판단에 의문이 생깁니다. |

**핵심 지표 설명:**

| 지표 | 설명 |
|------|------|
| 투자괴리율 | 현금 증가 대비 투자 증가 차이입니다. 괴리율이 높으면 현금만 쌓고 투자는 안 하고 있을 가능성이 있습니다. |
| 재투자율 | 영업이익 대비 설비투자 비율입니다. 재투자율이 낮으면 성장에 대한 의지가 부족할 수 있습니다. |
| ROIC | 투하자본수익률로, 투자금이 얼마나 효율적으로 수익을 창출하는지 보여줍니다. |
| 현금/유형자산 비율 | 현금 증가 대비 유형자산 증가 비율입니다. 30:1 이상이면 투자 없이 현금만 쌓고 있는 위험 신호입니다. |
| 단기금융비율 | 현금 중 단기금융상품 비율입니다. 65% 이상이면 이자놀이에 투자금을 묶어두고 있을 가능성이 있습니다. |
| 조달자금 전환율 | 조달한 자금 대비 투자 전환 비율입니다. 30% 미만이면 조달금을 목적대로 사용하지 않는 위험 신호입니다. |
| CAPEX 변동계수 | 투자의 일관성을 측정합니다. 변동이 크면 투자 계획이 불안정하고 예측 가능성이 낮습니다. |

#### Phase 4: 배치 스크립트 SQL 쿼리 버그 수정

수정 파일: `backend/scripts/calculate_raymonds_index.py`

**문제**: `get_financial_data()` 함수의 SQL 쿼리에서 투자괴리율 v2 계산에 필요한 4개 컬럼이 누락되어 있었음

**추가된 컬럼:**
- `right_of_use_assets` (사용권자산)
- `investments_in_associates` (관계기업투자)
- `fvpl_financial_assets` (장기금융상품)
- `other_financial_assets_non_current` (기타금융자산-비유동)

**영향**: 이 컬럼들이 없어서 `_calculate_investment_gap_v2()` 함수가 모든 값을 0으로 처리하던 버그 수정

#### Phase 5: HTTPS 보안 헤더 추가

수정 파일: `raymondsindex-web/next.config.ts`

**추가된 보안 헤더:**
- `Strict-Transport-Security`: 1년간 HTTPS 강제
- `Content-Security-Policy`: upgrade-insecure-requests
- `X-Frame-Options`: DENY (클릭재킹 방지)
- `X-Content-Type-Options`: nosniff
- `X-XSS-Protection`: 1; mode=block

#### 빌드 및 배치 상태

- [x] 프론트엔드 빌드 성공 (`npm run build`)
- [x] 배치 재계산 완료 (2025-12-28 11:27, 2,695개 기업)

---

### v2.1 계산 엔진 업그레이드 (2025-12-29)

#### Sub-Index 가중치 변경
| Sub-Index | v4.0 설계 | v2.1 구현 |
|-----------|----------|----------|
| CEI (자본 효율성) | 15% | **20%** |
| RII (재투자 강도) | 40% | **35%** |
| CGI (현금 거버넌스) | 30% | **25%** |
| MAI (모멘텀 정합성) | 15% | **20%** |

#### 등급 기준 완화
| 등급 | v4.0 설계 | v2.1 구현 |
|------|----------|----------|
| A++ | 95+ | 95+ |
| A+ | 90-94 | **88-94** |
| A | 85-89 | **80-87** |
| A- | 80-84 | **72-79** |
| B+ | 70-79 | **64-71** |
| B | 60-69 | **55-63** |
| B- | 50-59 | **45-54** |
| C+ | 40-49 | **30-44** |
| C | <40 | **0-29** |

#### v2.1 신규 지표
| 지표 | 설명 | 위치 |
|------|------|------|
| `investment_gap_v21` | 투자괴리율 v2.1 (현금 CAGR - CAPEX 성장률) | RII 핵심 |
| `tangible_efficiency` | 유형자산 효율성 (매출/유형자산) | CEI 구성 |
| `cash_yield` | 현금 수익률 (영업이익/총현금 %) | CEI 구성 |
| `debt_to_ebitda` | 부채/EBITDA | CGI 구성 |
| `growth_investment_ratio` | 성장 투자 비율 (성장CAPEX/총CAPEX %) | MAI 구성 |

#### Sub-Index 상세 구성 (v2.1)
**CEI (자본 효율성 20%)**:
- 자산회전율 25% + 유형자산효율성 20% + 현금수익률 20% + ROIC 25% + 추세 10%

**RII (재투자 강도 35%)** ⭐핵심:
- CAPEX강도 30% + 투자괴리율 v2.1 30% + 재투자율 25% + 지속성 15%

**CGI (현금 거버넌스 25%)**:
- 현금활용도 20% + 자금조달효율성 25% + 주주환원균형 20% + 현금적정성 15% + 부채건전성 20%

**MAI (모멘텀 정합성 20%)**:
- 매출-투자동조성 30% + 이익품질 25% + 투자지속성 20% + 성장투자비율 15% + FCF추세 10%

---

## 8. 참조 문서

| 문서 | 경로 |
|------|------|
| 화면기획서 | `docs/RAYMONDSINDEX_UI_SPEC_v2.md` |
| RaymondsIndex 설계 | `docs/RAYMONDS_INDEX_INTEGRATION_DESIGN.md` |
| 백엔드 모델 | `backend/app/models/raymonds_index.py` |
| API 라우터 | `backend/app/api/endpoints/raymonds_index.py` |

---

## 9. 시작 명령어

```bash
# 1. 프로젝트 디렉토리 생성
cd /Users/jaejoonpark/raymontology
mkdir raymondsindex-web && cd raymondsindex-web

# 2. Next.js 프로젝트 초기화
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*"

# 3. 의존성 설치
npm install @tanstack/react-query recharts lucide-react

# 4. shadcn/ui 초기화
npx shadcn@latest init

# 5. 개발 서버 시작
npm run dev
```
