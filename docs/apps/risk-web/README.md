# RISK-WEB (RaymondsRisk 웹 프론트엔드)

> 경로: `frontend/` | 배포: https://www.konnect-ai.net | 완성도: 85-90%

---

## 개요

한국 상장기업의 임원 관계망과 리스크 신호를 시각화하는 웹 애플리케이션입니다.

---

## 기술 스택

| 카테고리 | 기술 | 버전 |
|----------|------|------|
| 빌드 도구 | Vite | 5.0 |
| UI 프레임워크 | React | 18.2.0 |
| 그래프 시각화 | D3.js | 7.9.0 |
| 서버 상태 | TanStack Query | 5.8.4 |
| 클라이언트 상태 | Zustand | 4.4.6 |
| 라우팅 | React Router | 6.20.0 |
| 스타일링 | Tailwind CSS | 3.3.5 |
| HTTP 클라이언트 | Axios | 1.6.2 |

---

## 페이지 구조 (21개)

### 핵심 페이지
| 페이지 | 파일 | 설명 |
|--------|------|------|
| 메인 검색 | `MainSearchPage.tsx` | 기업 검색 랜딩 페이지 |
| 관계 그래프 | `GraphPage.tsx` | D3.js 포스 그래프 시각화 |
| 기업 리포트 | `ReportPage.tsx` | 기업 상세 리스크 분석 |
| RaymondsIndex 랭킹 | `RaymondsIndexRankingPage.tsx` | 인덱스 순위표 |

### 인증/결제
| 페이지 | 파일 | 설명 |
|--------|------|------|
| 로그인 | `LoginPage.tsx` | 이메일/소셜 로그인 |
| 회원가입 | `RegisterPage.tsx` | 회원가입 |
| 비밀번호 찾기 | `ForgotPasswordPage.tsx` | 비밀번호 재설정 요청 |
| 비밀번호 재설정 | `ResetPasswordPage.tsx` | 비밀번호 변경 |
| 이메일 인증 | `VerifyEmailPage.tsx` | 이메일 인증 처리 |
| OAuth 콜백 | `OAuthCallbackPage.tsx` | 소셜 로그인 콜백 |
| 요금제 | `PricingPage.tsx` | 구독 플랜 안내 |
| 결제 성공 | `PaymentSuccessPage.tsx` | 결제 완료 |
| 결제 실패 | `PaymentFailPage.tsx` | 결제 실패 |

### 부가 페이지
| 페이지 | 파일 | 설명 |
|--------|------|------|
| 조회 기록 | `ViewedCompaniesPage.tsx` | 조회한 기업 목록 |
| 서비스 신청 | `ServiceApplicationPage.tsx` | 기업 서비스 신청 |
| 관리자 | `AdminPage.tsx` | 관리자 대시보드 |
| 서비스 소개 | `AboutPage.tsx` | 서비스 소개 |
| 문의하기 | `ContactPage.tsx` | 문의 폼 |
| 이용약관 | `TermsPage.tsx` | 이용약관 |
| 개인정보처리방침 | `PrivacyPage.tsx` | 개인정보처리방침 |
| 404 | `NotFoundPage.tsx` | 페이지 없음 |

---

## 컴포넌트 구조 (34개)

### `/components/graph/` (6개)
| 컴포넌트 | 설명 |
|----------|------|
| `ForceGraph.tsx` | D3.js 포스 다이렉티드 그래프 |
| `NodeDetailPanel.tsx` | 노드 상세 정보 패널 |
| `GraphControls.tsx` | 그래프 조작 컨트롤 |
| `NavigationButtons.tsx` | 그래프 네비게이션 |
| `Breadcrumb.tsx` | 탐색 경로 표시 |
| `MiniStockChart.tsx` | 미니 주가 차트 |

### `/components/report/` (7개)
| 컴포넌트 | 설명 |
|----------|------|
| `RiskGauge.tsx` | 리스크 게이지 시각화 |
| `RiskSignalList.tsx` | 리스크 신호 목록 |
| `DataTabs.tsx` | 데이터 탭 네비게이션 |
| `ScoreBreakdown.tsx` | 점수 분석 상세 |
| `StockPriceCard.tsx` | 주가 정보 카드 |
| `GradeCard.tsx` | 등급 표시 카드 |
| `RaymondsIndexMiniCard.tsx` | 인덱스 미니 카드 |

### `/components/RaymondsIndex/` (4개)
| 컴포넌트 | 설명 |
|----------|------|
| `SubIndexRadar.tsx` | 4대 Sub-Index 레이더 차트 |
| `RiskFlagsPanel.tsx` | 위험 신호 패널 |
| `RaymondsIndexCard.tsx` | 인덱스 상세 카드 |
| `InvestmentGapMeter.tsx` | 투자괴리율 미터 |

### `/components/common/` (13개)
| 컴포넌트 | 설명 |
|----------|------|
| `Header.tsx` | 공통 헤더 |
| `Footer.tsx` | 공통 푸터 |
| `SearchInput.tsx` | 검색 입력 |
| `Loading.tsx` | 로딩 스피너 |
| `ErrorBoundary.tsx` | 에러 경계 |
| `EmptyState.tsx` | 빈 상태 표시 |
| `Skeleton.tsx` | 스켈레톤 로딩 |
| `MarketBadge.tsx` | 시장 배지 (KOSPI/KOSDAQ) |
| `UsageIndicator.tsx` | 조회 잔여량 표시 |
| `BottomSheet.tsx` | 바텀 시트 |
| `DateRangePicker.tsx` | 날짜 범위 선택 |
| `ApiStatusIndicator.tsx` | API 상태 표시 |
| `RaymondsRiskLogo.tsx` | 로고 컴포넌트 |

### `/components/auth/` (3개)
| 컴포넌트 | 설명 |
|----------|------|
| `LoginForm.tsx` | 로그인 폼 |
| `RegisterForm.tsx` | 회원가입 폼 |
| `ProtectedRoute.tsx` | 인증 라우트 가드 |

---

## 주요 기능

### 구현 완료
- [x] 기업 검색 (자동완성)
- [x] 임원 관계망 그래프 시각화
- [x] 기업 상세 리포트
- [x] RaymondsIndex 표시
- [x] 리스크 신호 표시
- [x] 회원가입/로그인 (이메일, Google, Kakao, Naver)
- [x] 구독 결제 (토스페이먼츠)
- [x] 조회 기록 관리
- [x] 다크 모드 지원
- [x] 반응형 디자인
- [x] **관계형리스크 4등급 체계** (2026-01-28 개편)

### 구현 예정
- [ ] 관계망 확장 노드 점선 테두리 (비DB 기업)
- [ ] 호버 툴팁 개선
- [ ] 뉴스 탭 추가

---

## 개발 명령어

```bash
cd frontend

# 개발 서버
npm run dev

# 프로덕션 빌드
npm run build

# 미리보기
npm run preview

# 린트
npm run lint
```

---

## 환경 변수

```env
VITE_API_URL=https://raymontology-production.up.railway.app/api
VITE_GOOGLE_CLIENT_ID=...
VITE_KAKAO_CLIENT_ID=...
VITE_NAVER_CLIENT_ID=...
```

---

## API 연동

| 엔드포인트 | 용도 |
|-----------|------|
| `/api/companies` | 기업 검색/목록 |
| `/api/companies/high-risk` | 주의필요기업 (HIGH_RISK 등급) |
| `/api/graph` | 관계망 데이터 |
| `/api/risks` | 리스크 신호 |
| `/api/raymonds-index` | 인덱스 데이터 |
| `/api/stock-prices` | 주가 데이터 |
| `/api/auth` | 인증 |
| `/api/subscriptions` | 구독 관리 |

---

## 관계형리스크 등급 체계 (v2.1)

### 4등급 체계 (2026-01-28 개편)

| 등급 | 점수 범위 | 색상 | 의미 |
|------|----------|------|------|
| LOW_RISK | 0-19점 | 🟢 초록 | 저위험 - 안정적, 투자 적격 |
| RISK | 20-34점 | 🟡 노랑 | 위험 - 모니터링 필요 |
| MEDIUM_RISK | 35-49점 | 🟠 주황 | 중위험 - 주의, 투자 신중 |
| HIGH_RISK | 50점+ | 🔴 빨강 | 고위험 - 경고, 투자 회피 |

### 점수 계산 공식

```
총점 = RaymondsRisk × 0.4 + 재무건전성 × 0.6

RaymondsRisk = 인적리스크 × 0.5 + CB리스크 × 0.5
```

### 등급 분포 (2026-01-28 기준)

| 등급 | 기업 수 | 비율 |
|------|--------|------|
| LOW_RISK | 1,515 | 48.9% |
| RISK | 780 | 25.2% |
| MEDIUM_RISK | 653 | 21.1% |
| HIGH_RISK | 152 | 4.9% |

### 관련 파일

| 파일 | 역할 |
|------|------|
| `types/report.ts` | 등급 타입, 색상, 변환 유틸리티 |
| `types/company.ts` | 등급 라벨 매핑 |
| `components/report/GradeCard.tsx` | 등급 표시 컴포넌트 |
| `api/company.ts` | 주의필요기업 API 호출 |

---

*마지막 업데이트: 2026-01-28*
