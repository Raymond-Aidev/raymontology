# RaymondsRisk 앱인토스 프로젝트 진행 현황

> **최종 업데이트**: 2025-12-31
> **프로젝트 경로**: `raymondsrisk-app/`

---

## 프로젝트 개요

### 서비스 설명
- **서비스명**: RaymondsRisk (레이먼즈리스크)
- **서비스 유형**: 기업 리스크 분석 리포트 서비스
- **플랫폼**: 앱인토스 (Apps in Toss) - 토스 앱 내 서비스

### 비즈니스 모델
- **무료 영역**: 홈페이지, 기업 검색, 기능 설명
- **유료 영역**: 기업 리포트 상세 조회 (이용권 차감)
- **결제 방식**: 이용권(크레딧) 일회성 구매 (**구독 불가** - 앱인토스 정책)

### 상품 구성
| 상품 ID | 상품명 | 이용권 | 가격 | 건당 가격 | 뱃지 |
|---------|--------|--------|------|-----------|------|
| report_1 | 리포트 1건 | 1건 | 500원 | 500원 | - |
| report_10 | 리포트 10건 | 10건 | 3,000원 | 300원 | 추천 |
| report_30 | 리포트 30건 | 30건 | 7,000원 | 233원 | 최저가 |

---

## 개발 진행 현황

### Phase 1: 토스 로그인 연동 ✅ 완료

#### 작업 내용
1. **React 버전 다운그레이드**
   - React 19 → React 18.2.0 (앱인토스 SDK 호환성)
   - `package.json` 수정 후 `rm -rf node_modules && npm install`

2. **앱인토스 SDK 설치**
   ```bash
   npm install @apps-in-toss/web-framework
   ```

3. **인증 시스템 구현**

| 파일 | 설명 |
|------|------|
| `src/types/auth.ts` | 인증 관련 타입 정의 (TossUser, AuthState, AppLoginResponse 등) |
| `src/contexts/AuthContext.tsx` | React Context 기반 인증 상태 관리 |
| `src/services/authService.ts` | 백엔드 API 호출 서비스 |

4. **페이지 구현**

| 파일 | 설명 |
|------|------|
| `src/pages/PaywallPage.tsx` | 유료 서비스 안내 및 로그인/구매 유도 |
| `src/pages/PurchasePage.tsx` | 이용권 구매 페이지 |

5. **개발 환경 모의 로그인**
   - `import.meta.env.DEV` 환경에서 SDK 없이 테스트 가능
   - 모의 사용자: `userKey: 'dev_user_123'`

---

### Phase 2: 백엔드 결제 시스템 ✅ 완료

#### 데이터베이스 테이블

```sql
-- 마이그레이션 파일: backend/scripts/migrations/add_toss_users_tables.sql
-- Railway PostgreSQL에 적용 완료

-- 1. toss_users: 토스 로그인 사용자
-- 2. credit_transactions: 이용권 거래 내역
-- 3. report_views: 리포트 조회 기록 (중복 차감 방지)
-- 4. credit_products: 이용권 상품
```

#### SQLAlchemy 모델

| 파일 | 모델 |
|------|------|
| `backend/app/models/toss_users.py` | TossUser, CreditTransaction, ReportView, CreditProduct |

#### API 엔드포인트

**토스 인증 API** (`backend/app/routes/toss_auth.py`)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/auth/toss/token` | 인가 코드로 토큰 발급 |
| GET | `/api/auth/toss/me` | 현재 사용자 정보 조회 |
| POST | `/api/auth/toss/refresh` | 토큰 갱신 |
| POST | `/api/auth/toss/logout` | 로그아웃 |

**이용권 API** (`backend/app/routes/credits.py`)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/credits/balance` | 이용권 잔액 조회 |
| GET | `/api/credits/products` | 상품 목록 조회 |
| POST | `/api/credits/purchase` | 이용권 구매 |
| GET | `/api/credits/history` | 거래 내역 조회 |
| POST | `/api/credits/use` | 리포트 조회용 이용권 차감 |
| GET | `/api/credits/viewed-companies` | 조회한 기업 목록 |

---

### Phase 3: 프론트엔드-백엔드 연동 ✅ 완료

#### 작업 내용

1. **creditService 구현** (`src/services/creditService.ts`)
   - `getBalance()`: 이용권 잔액 조회
   - `getProducts()`: 상품 목록 조회
   - `purchaseCredits()`: 이용권 구매
   - `useCreditsForReport()`: 리포트 조회용 이용권 차감
   - `getTransactionHistory()`: 거래 내역
   - `getViewedCompanies()`: 조회한 기업 목록
   - `hasViewedCompany()`, `cacheViewedCompany()`: 로컬 캐시

2. **PurchasePage 인앱결제 SDK 연동**
   - 상품 목록 API 연동
   - 개발 환경: 모의 결제 + 백엔드 API 호출
   - 프로덕션: `window.AppsInToss.purchase()` SDK 호출

3. **ReportPage 접근 제어 API 연동**
   - `/api/credits/use` 호출로 서버측 이용권 차감
   - 이미 조회한 기업은 재차감 없음
   - 401/402 에러 시 Paywall 리다이렉트

4. **전역 타입 통합** (`src/types/auth.ts`)
   ```typescript
   declare global {
     interface Window {
       AppsInToss?: {
         appLogin: () => Promise<AppLoginResponse>
         purchase: (productId: string) => Promise<PurchaseResponse>
       }
     }
   }
   ```

5. **빌드 성공**
   ```
   ✓ 139 modules transformed
   ✓ built in 727ms
   ```

---

### Phase 4: 샌드박스 테스트 ⏳ 대기

#### 남은 작업
1. 앱인토스 개발자 콘솔에서 샌드박스 앱 등록
2. mTLS 인증서 발급 및 백엔드 적용
3. 실제 토스 앱 환경에서 로그인 플로우 테스트
4. 인앱결제 테스트 (샌드박스 모드)
5. 비게임 심사 체크리스트 확인

---

## 프로젝트 구조

```
raymondsrisk-app/
├── src/
│   ├── api/
│   │   ├── client.ts           # Axios API 클라이언트 (AUTH_TOKEN_KEY 통일)
│   │   └── company.ts          # 기업 관련 API (검색, 통계)
│   ├── components/
│   │   ├── index.ts            # 컴포넌트 내보내기
│   │   ├── DebugPanel.tsx      # 디버그 패널 (공통)
│   │   └── ListItem.tsx        # 리스트 아이템 (공통)
│   ├── constants/
│   │   └── colors.ts           # 토스 디자인 시스템 색상 (공통)
│   ├── contexts/
│   │   └── AuthContext.tsx     # 인증 상태 관리
│   ├── services/
│   │   ├── authService.ts      # 인증 API 서비스
│   │   └── creditService.ts    # 이용권 API 서비스
│   ├── types/
│   │   ├── auth.ts             # 인증/SDK 타입 정의
│   │   └── company.ts          # 기업 관련 타입
│   ├── pages/
│   │   ├── HomePage.tsx        # 홈페이지 (무료, API 통계 연동)
│   │   ├── SearchPage.tsx      # 기업 검색 (무료)
│   │   ├── PaywallPage.tsx     # 유료 서비스 안내
│   │   ├── PurchasePage.tsx    # 이용권 구매
│   │   └── ReportPage.tsx      # 기업 리포트 (유료)
│   └── App.tsx                 # 라우팅 설정
├── package.json
└── vite.config.ts
```

---

## 핵심 코드 참조

### 사용자 플로우
```
[홈페이지] → [검색] → [기업 클릭] → [PaywallPage]
                                         ↓
                         [로그인 안됨] → [토스 로그인]
                                         ↓
                         [이용권 없음] → [PurchasePage] → [인앱결제]
                                         ↓
                         [이용권 있음] → [ReportPage] (이용권 차감)
```

### 접근 제어 로직 (ReportPage)
```typescript
// 1. 로그인 확인
if (!isAuthenticated) {
  navigate('/paywall', { state: { returnTo: location.pathname } })
  return
}

// 2. 백엔드에서 이용권 확인 및 차감
const result = await creditService.useCreditsForReport(corpCode, companyName)

// 이미 본 기업이면 deducted: false (차감 안됨)
// 처음 보는 기업이면 deducted: true (1건 차감)
if (result.deducted) {
  await refreshCredits()
}
```

### 인앱결제 로직 (PurchasePage)
```typescript
// 개발 환경
if (import.meta.env.DEV) {
  await creditService.purchaseCredits(selectedProduct)
  await refreshCredits()
  return
}

// 프로덕션: 앱인토스 SDK 호출
const purchaseResult = await window.AppsInToss.purchase(selectedProduct)
if (purchaseResult.success) {
  await creditService.purchaseCredits(selectedProduct, purchaseResult.receiptData)
  await refreshCredits()
}
```

---

## 환경 설정

### 프론트엔드 환경변수
```env
# .env.development
VITE_API_URL=http://localhost:8000

# .env.production
VITE_API_URL=https://raymontology-production.up.railway.app
```

### 백엔드 라우터 등록 (`main.py`)
```python
from app.routes import toss_auth, credits

app.include_router(toss_auth.router)
app.include_router(credits.router)
```

---

## 주의사항

### 앱인토스 정책
- **구독 상품 불가**: 월정액 구독 모델 사용 불가, 일회성 구매만 가능
- **mTLS 필수**: 토스 API 서버 호출 시 클라이언트 인증서 필요
- **심사 필수**: 비게임 서비스 심사 체크리스트 통과 필요

### 개발 환경
- React 18 필수 (앱인토스 SDK 호환성)
- 개발 환경에서는 모의 로그인/결제 지원
- `import.meta.env.DEV`로 환경 분기

### 보안
- 액세스 토큰은 localStorage에 저장
- 백엔드에서 토큰 검증 후 사용자 식별
- 이용권 차감은 반드시 서버측에서 처리 (프론트엔드 우회 방지)

---

## 다음 세션 작업 가이드

### Phase 4 시작 시
1. 앱인토스 개발자 콘솔 접속
2. 샌드박스 앱 등록 및 설정
3. mTLS 인증서 발급
4. 백엔드 토스 API 연동 코드 작성
5. 실제 토스 앱에서 테스트

### 참조 문서
- 앱인토스 개발자 문서: https://developers-apps-in-toss.toss.im/
- 프로젝트 가이드: `docs/APPS_IN_TOSS_GUIDE.md`
- 스키마 레지스트리: `backend/scripts/SCHEMA_REGISTRY.md`

---

## 변경 이력

| 날짜 | 작업 내용 |
|------|-----------|
| 2025-12-31 | 코드 품질 개선: 토큰 키 통일, colors 상수 공통화, 공통 컴포넌트 분리 (DebugPanel, ListItem), HomePage 통계 API 연동 |
| 2025-12-30 | Phase 1-3 완료: 토스 로그인, 백엔드 결제 시스템, 프론트-백 연동 |
