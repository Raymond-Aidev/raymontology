# RaymondsRisk 앱인토스 통합 개발 가이드

> **최종 업데이트**: 2025-12-31
> **서비스**: RaymondsRisk (기업 리스크 분석 리포트)
> **앱 이름**: `raymondsrisk` | **스킴**: `intoss://raymondsrisk`

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [개발 환경 설정](#2-개발-환경-설정)
3. [토스 로그인 구현](#3-토스-로그인-구현)
4. [인앱결제(IAP) 구현](#4-인앱결제iap-구현)
5. [mTLS 인증서 설정](#5-mtls-인증서-설정)
6. [테스트 및 출시](#6-테스트-및-출시)
7. [구현 완료 현황](#7-구현-완료-현황)
8. [트러블슈팅](#8-트러블슈팅)

---

## 1. 프로젝트 개요

### 서비스 범위

| 서비스 | 앱인토스 포함 |
|--------|-------------|
| **RaymondsRisk** | ✅ 포함 |
| Raymontology | ❌ 미포함 |
| RaymondsIndex | ❌ 미포함 |

### 비즈니스 모델

- **무료**: 홈페이지, 기업 검색, 기능 설명
- **유료**: 기업 리포트 상세 조회 (이용권 차감)
- **결제**: 일회성 이용권 구매 (구독 불가 - 앱인토스 정책)

### 상품 구성

| 상품 ID | 상품명 | 이용권 | 가격 | 건당 가격 |
|---------|--------|--------|------|-----------|
| report_1 | 리포트 1건 | 1건 | 500원 | 500원 |
| report_10 | 리포트 10건 | 10건 | 3,000원 | 300원 |
| report_30 | 리포트 30건 | 30건 | 7,000원 | 233원 |

### API 서버

| 환경 | URL |
|------|-----|
| 로컬 개발 | `http://localhost:8000/api` |
| 프로덕션 | `https://raymontology-production.up.railway.app/api` |

---

## 2. 개발 환경 설정

### 2.1 패키지 설치

```bash
npm install @apps-in-toss/web-framework
```

### 2.2 초기화

```bash
npx ait init
# 1. web-framework 선택
# 2. 앱 이름: raymondsrisk
# 3. dev 명령어: vite
# 4. build 명령어: vite build
# 5. 포트: 5173
```

### 2.3 설정 파일 (granite.config.ts)

```typescript
import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'raymondsrisk',
  brand: {
    displayName: '레이먼즈리스크',
    primaryColor: '#3182F6',
    icon: '',
  },
  web: {
    host: 'localhost', // 실기기 테스트 시 IP로 변경
    port: 5173,
    commands: {
      dev: 'vite',       // 실기기: 'vite --host'
      build: 'vite build',
    },
  },
  permissions: [],
});
```

### 2.4 TDS (Toss Design System) 필수

비게임 WebView 미니앱은 **TDS 사용 필수** (검수 기준).

| web-framework 버전 | 패키지 |
|-------------------|--------|
| < 1.0.0 | @toss-design-system/mobile |
| >= 1.0.0 | @toss/tds-mobile |

---

## 3. 토스 로그인 구현

### 3.1 개발 흐름

```
1. 인가 코드 받기 (SDK appLogin)
2. AccessToken 발급 (서버 API)
3. AccessToken 재발급 (서버 API)
4. 사용자 정보 조회 (서버 API)
5. 로그인 끊기 (서버 API)
```

### 3.2 토큰 유효시간

| 토큰 | 유효시간 |
|------|----------|
| authorizationCode | **10분** (중복 사용 불가) |
| accessToken | **1시간** |
| refreshToken | **14일** |

### 3.3 클라이언트 구현 (SDK)

```typescript
import { appLogin, getOperationalEnvironment } from '@apps-in-toss/web-framework'

// 환경 확인
const environment = getOperationalEnvironment() // 'toss' | 'sandbox'

// 인가 코드 요청
const { authorizationCode, referrer } = await appLogin()
// referrer: 'sandbox' (샌드박스앱) 또는 'DEFAULT' (토스앱)
```

**SDK 브릿지 초기화 확인 (중요)**:
```typescript
// SDK 브릿지 초기화 확인 함수
const checkBridge = () => {
  const hasConstantMap = typeof window !== 'undefined' &&
    window.__CONSTANT_HANDLER_MAP &&
    Object.keys(window.__CONSTANT_HANDLER_MAP).length > 0
  const hasWebView = typeof window !== 'undefined' &&
    window.ReactNativeWebView?.postMessage
  return { hasConstantMap, hasWebView }
}

// 초기화 대기 (최대 3초)
for (let i = 0; i < 30; i++) {
  const bridge = checkBridge()
  if (bridge.hasConstantMap && bridge.hasWebView) break
  await new Promise(r => setTimeout(r, 100))
}
```

### 3.4 서버 API 구현

**토스 API Base URL**: `https://apps-in-toss-api.toss.im`

#### 토큰 발급

```
POST /api-partner/v1/apps-in-toss/user/oauth2/generate-token
Content-Type: application/json
```

요청:
```json
{
  "authorizationCode": "인가코드",
  "referrer": "sandbox" // 또는 "DEFAULT"
}
```

성공 응답:
```json
{
  "resultType": "SUCCESS",
  "success": {
    "accessToken": "eyJ...",
    "refreshToken": "xNEY...",
    "expiresIn": 3599,
    "tokenType": "Bearer"
  }
}
```

#### 토큰 갱신

```
POST /api-partner/v1/apps-in-toss/user/oauth2/refresh-token
```

요청:
```json
{
  "refreshToken": "리프레시토큰"
}
```

#### 사용자 정보 조회

```
GET /api-partner/v1/apps-in-toss/user/oauth2/login-me
Authorization: Bearer {accessToken}
```

응답:
```json
{
  "resultType": "SUCCESS",
  "success": {
    "userKey": 443731104,
    "name": "ENCRYPTED_VALUE",
    "phone": "ENCRYPTED_VALUE"
  }
}
```

> **주의**: 개인정보는 **AES-256-GCM 암호화**됨. 복호화 키는 이메일로 별도 제공.

#### 로그아웃

```
POST /api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-access-token
Authorization: Bearer {accessToken}
```

### 3.5 RaymondsRisk 백엔드 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/auth/toss/token` | 인가 코드 → 토큰 발급 |
| GET | `/api/auth/toss/me` | 현재 사용자 정보 |
| POST | `/api/auth/toss/refresh` | 토큰 갱신 |
| POST | `/api/auth/toss/logout` | 로그아웃 |
| GET | `/api/auth/toss/status` | mTLS 상태 확인 |

---

## 4. 인앱결제(IAP) 구현

### 4.1 SDK 버전 요구사항

| 버전 | 기능 |
|------|------|
| **1.1.3+** | `processProductGrant` (상품 지급 완료 처리) |
| **1.2.2+** | `getPendingOrders` (구매 복원) |

### 4.2 구매 흐름

```typescript
import { IAP } from '@apps-in-toss/web-framework'

// 1. 상품 목록 조회
const products = await IAP.getProducts()

// 2. 구매 요청
IAP.createOneTimePurchaseOrder({
  options: {
    sku: 'report_10',
    processProductGrant: async ({ orderId }) => {
      // 서버에서 상품 지급 처리 (필수!)
      const result = await serverGrantProduct(orderId)
      return result.success  // true: 성공, false: 에러
    },
  },
  onEvent: () => {
    // 결제 + 상품 지급 모두 성공
  },
  onError: (error) => {
    // 에러 처리
  },
})

// 3. 미지급 주문 복원 (앱 시작 시 필수!)
const pendingOrders = await IAP.getPendingOrders()
for (const order of pendingOrders) {
  const granted = await serverGrantProduct(order.orderId)
  if (granted) {
    await IAP.completeProductGrant({ orderId: order.orderId })
  }
}
```

### 4.3 주문 상태 코드

| 상태 | 설명 |
|------|------|
| PURCHASED | 구매 완료 |
| PAYMENT_COMPLETED | 결제 완료 (지급 전) |
| FAILED | 실패 |
| REFUNDED | 환불됨 |
| PRODUCT_NOT_GRANTED_BY_PARTNER | 파트너 상품 지급 실패 |

### 4.4 RaymondsRisk 백엔드 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/credits/balance` | 이용권 잔액 |
| GET | `/api/credits/products` | 상품 목록 |
| POST | `/api/credits/purchase` | 구매 (IAP 검증) |
| POST | `/api/credits/use` | 리포트 조회 (차감) |
| GET | `/api/credits/viewed-companies` | 조회한 기업 목록 |

---

## 5. mTLS 인증서 설정

### 5.1 필수 대상

토스 로그인, 인앱결제 등 **모든 서버 API**에 mTLS 필수.

### 5.2 발급 방법

1. 앱인토스 콘솔 접속
2. 앱 선택 → **mTLS 인증서** 탭
3. **+ 발급받기** 클릭
4. 인증서(.pem) + 키(.pem) 다운로드

### 5.3 서버 적용 (Python)

```python
import httpx

class TossAPIClient:
    BASE_URL = "https://apps-in-toss-api.toss.im"

    def __init__(self, cert_path: str, key_path: str):
        self.cert = (cert_path, key_path)

    async def generate_token(self, authorization_code: str, referrer: str):
        async with httpx.AsyncClient(cert=self.cert) as client:
            response = await client.post(
                f"{self.BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/generate-token",
                json={"authorizationCode": authorization_code, "referrer": referrer}
            )
            return response.json()
```

### 5.4 환경변수

```bash
TOSS_MTLS_CERT_PATH=/path/to/cert.pem
TOSS_MTLS_KEY_PATH=/path/to/key.pem
```

### 5.5 주의사항

- 인증서/키 **유출 금지**
- **만료 전 재발급** 필수
- **무중단 교체**를 위해 2개 이상 등록 가능

---

## 6. 테스트 및 출시

### 6.1 샌드박스 테스트

#### 스킴 실행
```
intoss://raymondsrisk
```

#### iOS
1. 샌드박스 앱 실행
2. 스킴 입력: `intoss://raymondsrisk`
3. "스키마 열기" 버튼

#### Android
```bash
adb reverse tcp:8081 tcp:8081
adb reverse tcp:5173 tcp:5173
```

### 6.2 테스트 시나리오

#### 로그인
| 시나리오 | 확인 |
|---------|------|
| 정상 로그인 | authCode → 토큰 → 사용자 정보 |
| 신규 가입 | 5건 무료 이용권 지급 |
| 토큰 갱신 | 1시간 후 자동 갱신 |
| 로그아웃 | 상태 초기화 |

#### 인앱결제
| 시나리오 | 확인 |
|---------|------|
| 정상 결제 | 이용권 +10 확인 |
| 결제 취소 | 이용권 변동 없음 |
| 중복 구매 방지 | 409 에러 |
| 미지급 복구 | getPendingOrders → 처리 |

### 6.3 검수 요청

| 항목 | 입력값 |
|------|--------|
| 이동 URL | `/` |
| Screen Name | `Home` 또는 `홈` |

### 6.4 출시 프로세스

```
1. 빌드 업로드 (granite build)
2. 1회 이상 테스트
3. "검토 요청하기" 버튼
4. 검수 (영업일 3일 이내)
5. "출시하기" 버튼
```

---

## 7. 구현 완료 현황

### Phase 1: 토스 로그인 연동 ✅

| 파일 | 설명 |
|------|------|
| `src/contexts/AuthContext.tsx` | 인증 상태 관리 |
| `src/services/authService.ts` | 백엔드 API 호출 |
| `src/pages/PaywallPage.tsx` | 로그인/구매 유도 |

### Phase 2: 백엔드 mTLS API ✅

| 파일 | 설명 |
|------|------|
| `backend/app/services/toss_api_client.py` | mTLS 클라이언트 |
| `backend/app/routes/toss_auth.py` | 토스 인증 API |
| `backend/app/routes/credits.py` | 이용권 API |

### Phase 3: 프론트엔드-백엔드 연동 ✅

- creditService.ts 구현
- IAP SDK 연동
- ReportPage 접근 제어

### Phase 4: 샌드박스 테스트 🔄

1. ✅ mTLS 인증서 발급
2. ✅ 샌드박스 앱 테스트
3. ✅ SDK 브릿지 초기화 대기 로직
4. ✅ 503 에러 수정 (mTLS 미설정 시 모의 응답)
5. ✅ 401 에러 수정 (Header 파싱)
6. 🔄 검토 요청 단계

---

## 8. 트러블슈팅

### 8.1 SDK 브릿지 미초기화

**증상**: 로그인 버튼 클릭해도 반응 없음

**원인**: SDK 브릿지가 초기화되기 전에 appLogin 호출

**해결**: 브릿지 초기화 대기 로직 추가 (최대 3초)

### 8.2 503 Service Unavailable

**증상**: `/api/auth/toss/token` 호출 시 503 에러

**원인**: mTLS 인증서 미설정 환경에서 API 호출

**해결**: `toss_auth.py`에서 mTLS 미설정 시 모의 응답 반환

```python
use_mock = (
    not _toss_client_available or
    settings.debug or
    request.referrer == "sandbox"
)
```

### 8.3 401 Unauthorized

**증상**: `/api/auth/toss/me` 호출 시 401 에러

**원인**: FastAPI에서 Authorization 헤더 미인식

**해결**: `Header(None)` 추가

```python
async def get_current_user(
    authorization: str = Header(None),  # Header() 필수!
    db: AsyncSession = Depends(get_db),
):
```

### 8.4 "서버에 연결할 수 없습니다"

**해결**:
1. `granite.config.ts`에 `--host` 추가
2. `web.host`를 실제 IP로 변경
3. 같은 와이파이 연결 확인

### 8.5 ERR_NETWORK

**원인**: mTLS 미적용 상태에서 API 호출

**해결**: 인증서/키 파일 경로 확인

---

## 참고 문서

| 문서 | URL |
|------|-----|
| 앱인토스 개발자 문서 | https://developers-apps-in-toss.toss.im/ |
| 토스 로그인 가이드 | https://developers-apps-in-toss.toss.im/login/develop.md |
| 인앱결제 가이드 | https://developers-apps-in-toss.toss.im/iap/intro.md |
| TDS Mobile | https://tossmini-docs.toss.im/tds-mobile/ |

---

*이 문서는 앱인토스 공식 문서와 RaymondsRisk 프로젝트 구현 내용을 기반으로 작성되었습니다.*
