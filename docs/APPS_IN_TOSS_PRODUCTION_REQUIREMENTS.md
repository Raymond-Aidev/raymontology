# RaymondsRisk 앱인토스 상용화 필수 요소

> **작성일**: 2025-12-31
> **목적**: 앱인토스 공식 문서 분석을 바탕으로 상용화에 필요한 모든 요소 정리

---

## 1. 토스 로그인 구현 (필수)

### 1.1 클라이언트 (SDK)

```typescript
import { appLogin } from '@apps-in-toss/web-framework'

// Step 1: 인가 코드 요청
const { authorizationCode, referrer } = await appLogin()
// ⚠️ authorizationCode 유효기간: 10분
```

### 1.2 서버 API (mTLS 필수)

| 단계 | API 엔드포인트 | 설명 |
|------|---------------|------|
| 토큰 발급 | `POST /api-partner/v1/apps-in-toss/user/oauth2/generate-token` | authorizationCode → accessToken (1시간) |
| 토큰 갱신 | `POST /api-partner/v1/apps-in-toss/user/oauth2/refresh-token` | refreshToken (14일) → 새 accessToken |
| 사용자 정보 | `GET /api-partner/v1/apps-in-toss/user/oauth2/login-me` | Bearer 토큰으로 사용자 정보 조회 |
| 로그아웃 | `POST /api-partner/v1/apps-in-toss/user/oauth2/disconnect` | 로그인 연결 해제 |

**Base URL**: `https://apps-in-toss-api.toss.im`

### 1.3 데이터 암호화

- 모든 개인정보는 **AES-256 GCM** 암호화되어 반환
- 복호화 키는 **이메일로 별도 제공**
- IV(nonce)는 암호화 데이터 앞에 붙어있음 → 분리 후 복호화
- **userKey와 scope만 평문으로 제공**

---

## 2. 인앱결제 (IAP) 구현 (필수)

### 2.1 SDK 버전 요구사항

| 버전 | 필수 기능 |
|------|----------|
| **1.1.3+** | 상품 지급 완료 처리 (processProductGrant) |
| **1.2.2+** | 구매 복원 기능 (getPendingOrders) |

### 2.2 구현 필수 단계

#### Step 1: 상품 목록 조회
```typescript
import { IAP } from '@apps-in-toss/web-framework'

const products = await IAP.getProducts()
// IapProductListItem[] 반환
```

#### Step 2: 구매 요청
```typescript
IAP.createOneTimePurchaseOrder({
  options: {
    sku: 'report_10',
    processProductGrant: async ({ orderId }) => {
      // ⚠️ 반드시 서버에서 상품 지급 처리
      const result = await serverGrantProduct(orderId)
      return result.success  // true: 성공, false: PRODUCT_NOT_GRANTED_BY_PARTNER 에러
    },
  },
  onEvent: () => {
    // 결제 + 상품 지급 모두 성공
  },
  onError: (error) => {
    // 에러 처리
  },
})
```

#### Step 3: 미지급 주문 복원 (필수!)
```typescript
// 앱 시작 시 또는 주기적으로 호출
const pendingOrders = await IAP.getPendingOrders()

for (const order of pendingOrders) {
  const granted = await serverGrantProduct(order.orderId)
  if (granted) {
    await IAP.completeProductGrant({ orderId: order.orderId })
  }
}
```

#### Step 4: 주문 상태 조회
```typescript
// SDK 방식
const orders = await IAP.getCompletedOrRefundedOrders()

// API 방식 (서버)
// GET /api-partner/v1/apps-in-toss/order/get-order-status
// Header: x-toss-user-key
// Param: orderId
```

### 2.3 주문 상태 코드

| 상태 | 설명 |
|------|------|
| PURCHASED | 구매 완료 |
| PAYMENT_COMPLETED | 결제 완료 (상품 지급 전) |
| FAILED | 실패 |
| REFUNDED | 환불됨 |
| ORDER_IN_PROGRESS | 진행 중 |
| NOT_FOUND | 찾을 수 없음 |
| PRODUCT_NOT_GRANTED_BY_PARTNER | 파트너 상품 지급 실패 |

---

## 3. mTLS 인증서 설정 (필수)

### 3.1 발급 방법

1. 앱인토스 콘솔 접속
2. 앱 선택 → **mTLS 인증서** 탭
3. **+ 발급받기** 클릭
4. 인증서 파일 (`.pem`) + 키 파일 (`.key`) 다운로드

### 3.2 서버 적용 (Python 예시)

```python
import requests

class TossAPIClient:
    BASE_URL = "https://apps-in-toss-api.toss.im"

    def __init__(self, cert_path: str, key_path: str):
        self.cert = (cert_path, key_path)

    def generate_token(self, authorization_code: str, referrer: str):
        return requests.post(
            f"{self.BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/generate-token",
            cert=self.cert,
            json={
                "authorizationCode": authorization_code,
                "referrer": referrer
            }
        )

    def get_user_info(self, access_token: str):
        return requests.get(
            f"{self.BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/login-me",
            cert=self.cert,
            headers={"Authorization": f"Bearer {access_token}"}
        )
```

### 3.3 주의사항

- 인증서/키 파일 **유출 금지** (환경변수 또는 시크릿 관리)
- 인증서 **만료 전 재발급** 필요
- **무중단 교체**를 위해 2개 이상 등록 가능

---

## 4. 샌드박스 테스트 필수 시나리오

### 4.1 결제 테스트 (필수 3가지)

| 시나리오 | 테스트 내용 |
|---------|-----------|
| **정상 결제** | 콜백 수신 + 상품 지급 로직 확인 |
| **결제 성공 + 서버 실패** | 복원 워크플로우 테스트 |
| **에러 처리** | 네트워크 실패, 취소, 내부 에러 |

### 4.2 로그인 테스트

| 시나리오 | 테스트 내용 |
|---------|-----------|
| 정상 로그인 | authorizationCode → 토큰 발급 → 사용자 정보 |
| 토큰 만료 | refreshToken으로 갱신 |
| 로그아웃 | 연결 해제 + 상태 초기화 |

---

## 5. 현재 RaymondsRisk 구현 상태 vs 필수 요구사항

### 5.1 구현 완료 항목 ✅

| 항목 | 상태 | 파일 |
|------|------|------|
| appLogin SDK 호출 | ✅ | `AuthContext.tsx` |
| 프론트엔드 인증 상태 관리 | ✅ | `AuthContext.tsx` |
| 이용권 상태 관리 | ✅ | `AuthContext.tsx`, `creditService.ts` |
| 접근 제어 (Paywall) | ✅ | `ReportPage.tsx`, `SearchPage.tsx` |
| IAP SDK 호출 | ✅ | `PurchasePage.tsx` |

### 5.2 구현 상태 (2025-12-31 업데이트)

| 항목 | 상태 | 파일 |
|------|------|------|
| **mTLS 인증서** | ✅ 발급완료 | `backend/certs/` |
| **TossAPIClient (mTLS)** | ✅ 구현완료 | `backend/app/services/toss_api_client.py` |
| **서버 토큰 발급 API** | ✅ 구현완료 | `backend/app/routes/toss_auth.py` |
| **서버 사용자 정보 API** | ✅ 구현완료 | `backend/app/routes/toss_auth.py` |
| **서버 IAP 검증 API** | ✅ 구현완료 | `backend/app/routes/credits.py` |
| **AES-256 복호화** | ⏳ 키 수령 대기 | 토스에서 이메일 발송 예정 |
| **미지급 주문 복원** | ⏳ 프론트엔드 연동 필요 | `getPendingOrders()` 호출 추가 필요 |

---

## 6. 상용화 로드맵 (진행 상황)

### Phase 1: mTLS 설정 ✅ 완료 (2025-12-31)

1. ✅ 앱인토스 콘솔에서 mTLS 인증서 발급
2. ✅ `backend/certs/` 디렉토리에 인증서/키 저장
3. ✅ `TossAPIClient` 클래스 구현 (`backend/app/services/toss_api_client.py`)
4. ✅ 환경변수 설정 (`TOSS_MTLS_CERT_PATH`, `TOSS_MTLS_KEY_PATH`)

### Phase 2: 토스 로그인 연동 ✅ 완료 (2025-12-31)

1. ✅ `POST /api/auth/toss/token` - authorizationCode → accessToken
2. ✅ `GET /api/auth/toss/me` - 사용자 정보 조회
3. ✅ `POST /api/auth/toss/refresh` - 토큰 갱신
4. ✅ `POST /api/auth/toss/logout` - 연결 해제
5. ✅ `GET /api/auth/toss/status` - mTLS 상태 확인

### Phase 3: 인앱결제 연동 ✅ 완료 (2025-12-31)

1. ✅ `POST /api/credits/purchase` - 주문 검증 + 이용권 지급
2. ✅ `verify_purchase()` - 토스 서버 결제 검증
3. ✅ `order_id` 중복 구매 방지
4. ⏳ 미지급 주문 복원 (프론트엔드 연동 필요)

### Phase 4: QA 및 출시 🔄 진행 중

1. ⏳ 샌드박스 테스트 시나리오 실행
2. ⏳ 앱인토스 QA 검수 신청
3. ⏳ 피드백 반영 및 수정
4. ⏳ 프로덕션 출시

---

## 7. 샌드박스 테스트 체크리스트

### 7.1 배포 전 준비사항

| 항목 | 확인 | 설명 |
|------|------|------|
| DB 마이그레이션 | ⬜ | `add_toss_users_tables.sql` + `add_iap_columns.sql` 실행 |
| Railway 환경변수 | ⬜ | `TOSS_MTLS_CERT_PATH`, `TOSS_MTLS_KEY_PATH` 설정 |
| Railway Secret Files | ⬜ | mTLS 인증서 파일 업로드 |
| 프론트엔드 빌드 | ⬜ | RaymondsRisk 앱 빌드 |

### 7.2 로그인 테스트

| 시나리오 | 확인 | 테스트 방법 |
|---------|------|------------|
| 정상 로그인 | ⬜ | 토스 앱에서 RaymondsRisk 접속 → 로그인 버튼 → 토스 인증 → 성공 |
| 신규 가입 | ⬜ | 처음 로그인 시 5건 무료 이용권 지급 확인 |
| 기존 사용자 재로그인 | ⬜ | 이용권 잔액 유지 확인 |
| 토큰 만료 후 갱신 | ⬜ | 1시간 후 자동 갱신 확인 |
| 로그아웃 | ⬜ | 로그아웃 후 상태 초기화 확인 |

### 7.3 인앱결제 테스트

| 시나리오 | 확인 | 테스트 방법 |
|---------|------|------------|
| 정상 결제 | ⬜ | 리포트 10건 구매 → 이용권 잔액 +10 확인 |
| 결제 취소 | ⬜ | 결제 화면에서 취소 → 이용권 변동 없음 확인 |
| 중복 구매 방지 | ⬜ | 같은 orderId로 재요청 → 409 에러 확인 |
| 결제 성공 + 서버 실패 복구 | ⬜ | `getPendingOrders()` 호출 → 미지급 주문 처리 |

### 7.4 이용권 사용 테스트

| 시나리오 | 확인 | 테스트 방법 |
|---------|------|------------|
| 리포트 최초 조회 | ⬜ | 기업 선택 → 이용권 -1 차감 확인 |
| 같은 기업 재조회 | ⬜ | 같은 기업 재접근 → 차감 없음 확인 |
| 이용권 0건일 때 조회 시도 | ⬜ | Paywall로 리다이렉트 확인 |

### 7.5 API 상태 확인

```bash
# mTLS 상태 확인
curl https://raymontology-production.up.railway.app/api/auth/toss/status

# 예상 응답 (프로덕션)
{
  "mTLS_available": true,
  "mTLS_error": null,
  "debug_mode": false,
  "environment": "production"
}
```

---

## 8. 참고 문서

| 문서 | URL |
|------|-----|
| 앱인토스 개발자 문서 | https://developers-apps-in-toss.toss.im/ |
| 토스 로그인 가이드 | https://developers-apps-in-toss.toss.im/login/intro.md |
| 인앱결제 가이드 | https://developers-apps-in-toss.toss.im/iap/intro.md |
| mTLS 설정 가이드 | https://developers-apps-in-toss.toss.im/development/integration-process.md |
| TDS Mobile (WebView) | https://tossmini-docs.toss.im/tds-mobile/llms-full.txt |

---

## 9. 해결된 문제 및 남은 작업

### 9.1 해결된 문제 ✅

**문제**: "인증됨 + 이용권 0건인데 리포트 접근 가능"

**근본 원인**: 프론트엔드가 localStorage 토큰으로 `isAuthenticated: true` 설정하지만,
실제로는 백엔드가 토스 서버와 통신하지 못해 **가짜 인증 상태**였음.

**해결 완료**:
1. ✅ 프론트엔드 접근 제어 강화 (`ReportPage.tsx`, `SearchPage.tsx`)
2. ✅ mTLS 인증서 발급 및 백엔드 적용
3. ✅ `TossAPIClient` mTLS 클라이언트 구현
4. ✅ 토스 로그인 API 연동 (토큰 발급/갱신/로그아웃)
5. ✅ 인앱결제 검증 API 연동

### 9.2 남은 작업

| 작업 | 우선순위 | 설명 |
|------|----------|------|
| Railway 인증서 배포 | 🔴 높음 | mTLS 인증서를 Railway Secret Files로 업로드 |
| DB 마이그레이션 | 🔴 높음 | `add_iap_columns.sql` 프로덕션 DB 적용 |
| AES-256 복호화 키 | 🟡 중간 | 토스에서 이메일로 발송 예정 |
| 미지급 주문 복원 | 🟡 중간 | 프론트엔드에 `getPendingOrders()` 호출 추가 |
| 샌드박스 테스트 | 🔴 높음 | 위 체크리스트 실행 |
| QA 검수 신청 | 🟢 낮음 | 테스트 완료 후 진행 |

