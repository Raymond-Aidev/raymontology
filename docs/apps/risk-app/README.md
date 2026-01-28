# RISK-APP (RaymondsRisk 토스 앱인앱)

> 경로: `raymondsrisk-app/` | 배포: 토스 앱인앱 (intoss://raymondsrisk) | 완성도: 80%

---

## 개요

토스 앱 내에서 실행되는 RaymondsRisk 서비스입니다. 앱인토스(Apps in Toss) SDK를 사용합니다.

---

## 기술 스택

| 카테고리 | 기술 | 버전 |
|----------|------|------|
| 빌드 도구 | Vite | 7.2.4 |
| UI 프레임워크 | React | 18.2.0 |
| 토스 SDK | @apps-in-toss/web-framework | 1.8.0 |
| 토스 디자인 | @toss/tds-mobile | 2.2.0 |
| 스타일링 | Emotion | 11.14.0 |
| 그래프 시각화 | D3.js | 7.9.0 |
| 서버 상태 | TanStack Query | 5.90.15 |
| 클라이언트 상태 | Zustand | 5.0.9 |
| 라우팅 | React Router | 6.28.0 |

---

## 페이지 구조 (9개)

| 페이지 | 파일 | 설명 |
|--------|------|------|
| 홈 | `HomePage.tsx` | 메인 랜딩 |
| 검색 | `SearchPage.tsx` | 기업 검색 |
| 관계 그래프 | `GraphPage.tsx` | 관계망 시각화 |
| 리포트 | `ReportPage.tsx` | 기업 리스크 분석 |
| 분석 | `AnalysisPage.tsx` | 상세 분석 |
| 내 기업 | `MyCompaniesPage.tsx` | 관심 기업 목록 |
| 로그인 | `LoginPage.tsx` | 토스 로그인 연동 |
| 페이월 | `PaywallPage.tsx` | 이용권 안내 |
| 구매 | `PurchasePage.tsx` | 이용권 구매 |

---

## 토스 연동 현황

### 완료된 연동
- [x] 토스 로그인 (`getTossLogin`)
- [x] 토스 결제 (`openCheckout`)
- [x] 앱 정보 조회 (`getAppInfo`)
- [x] 사용자 정보 조회 (`getUserInfo`)

### 이용권 시스템

| 이용권 | 가격 | 월 조회 제한 |
|--------|------|-------------|
| Free | 무료 | 5건 |
| Light | 3,000원/월 | 30건 |
| Max | 30,000원/월 | 무제한 |

---

## 앱인토스 설정

### 기본 정보

| 항목 | 값 |
|------|-----|
| 앱 이름 | `raymondsrisk` |
| 스킴 | `intoss://raymondsrisk` |
| 현재 상태 | 샌드박스 테스트 |

### granite.config.ts

```typescript
export default {
  appId: 'raymondsrisk',
  appName: 'RaymondsRisk',
  version: '1.0.0',
  // ...
}
```

---

## 주요 기능

### 구현 완료
- [x] 기업 검색
- [x] 관계망 그래프 시각화
- [x] 기업 리스크 리포트
- [x] 토스 로그인 연동
- [x] 이용권 시스템
- [x] 조회 이력 관리
- [x] 토스 결제 연동

### 구현 예정
- [ ] 토스 앱 심사 제출
- [ ] 프로덕션 배포
- [ ] 푸시 알림

---

## 개발 명령어

```bash
cd raymondsrisk-app

# 개발 서버
npm run dev

# Granite 개발 서버 (토스 환경 시뮬레이션)
npm run granite:dev

# 프로덕션 빌드
npm run build

# Granite 빌드 (.ait 패키지 생성)
npm run granite:build

# 린트
npm run lint
```

---

## 환경 변수

```env
VITE_API_URL=https://raymontology-production.up.railway.app/api
```

---

## 토스 SDK API

### 로그인
```typescript
import { getTossLogin } from '@apps-in-toss/web-framework';

const { accessToken, refreshToken } = await getTossLogin();
```

### 결제
```typescript
import { openCheckout } from '@apps-in-toss/web-framework';

await openCheckout({
  productName: 'RaymondsRisk Light',
  amount: 3000,
  // ...
});
```

---

## 디렉토리 구조

```
raymondsrisk-app/
├── granite.config.ts     # 앱인토스 설정
├── src/
│   ├── pages/           # 페이지 컴포넌트
│   ├── components/      # 공용 컴포넌트
│   ├── hooks/           # 커스텀 훅
│   ├── services/        # API 서비스
│   ├── stores/          # Zustand 스토어
│   ├── constants/       # 상수
│   └── types/           # TypeScript 타입
├── public/
└── package.json
```

---

## 테스트 환경

### 샌드박스 테스트
1. 토스 앱 개발자 모드 활성화
2. `npm run granite:dev` 실행
3. 토스 앱에서 개발 앱 접속

### 주의사항
- 프로덕션 API 키와 샌드박스 API 키 구분 필수
- 결제 테스트는 샌드박스 환경에서만 진행
- 토스 앱 심사 전 모든 기능 검증 필요

---

## 관련 문서

- [APPS_IN_TOSS_GUIDE.md](../../APPS_IN_TOSS_GUIDE.md) - 통합 가이드
- [APPS_IN_TOSS_LOGIN_GUIDE.md](../../APPS_IN_TOSS_LOGIN_GUIDE.md) - 로그인 연동
- [APPS_IN_TOSS_API_GUIDE.md](../../APPS_IN_TOSS_API_GUIDE.md) - SDK API

---

*마지막 업데이트: 2026-01-23*
