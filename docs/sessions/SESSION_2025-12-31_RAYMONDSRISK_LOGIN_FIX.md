# RaymondsRisk 앱인토스 로그인 복원 세션

**날짜**: 2025-12-31
**상태**: 빌드 완료, 테스트 대기

---

## 세션 요약

토스 로그인 버튼("토스로 시작하기")이 .ait 파일에서 작동하지 않는 문제를 해결하기 위해 실제 서버 연동을 복원함.

### 이전 문제
- `granite dev`에서는 모의 로그인으로 정상 작동
- `.ait` 파일을 샌드박스 앱에 업로드하면 로그인 버튼 작동 안됨
- 디버그 패널에서 `getOperationalEnvironment() = "toss"` 확인
- 서버 API `/api/auth/toss/token`에서 404 에러 발생

### 해결 작업
1. **AuthContext.tsx 복원**: 실제 `appLogin()` SDK 호출 복원
2. **creditService.ts 복원**: 모의 데이터 제거, 실제 API 연동
3. **빌드 완료**: `raymondsrisk.ait` (1.8MB) 생성

---

## 수정된 파일

### 1. `/src/contexts/AuthContext.tsx`
- `appLogin()` SDK import 복원
- `getOperationalEnvironment()`로 환경 감지
- 실제 토스 OAuth 플로우 복원:
  - `appLogin()` → 인가 코드 발급
  - `authService.exchangeCodeForToken()` → 토큰 교환
  - `authService.fetchUserInfo()` → 사용자 정보 조회
  - `authService.fetchCredits()` → 이용권 조회

### 2. `/src/services/creditService.ts`
- `isTestEnvironment()` 함수 제거
- `getProducts()`: API 실패 시 기본 상품 폴백 추가
- `purchaseCredits()`: 모의 데이터 체크 제거, 실제 API 호출
- `useCreditsForReport()`: 모의 데이터 체크 제거, 실제 API 호출

---

## 기술적 발견

### SDK 브릿지 구조
```javascript
// getOperationalEnvironment - createConstantBridge 사용
// window.__CONSTANT_HANDLER_MAP['getOperationalEnvironment']에서 값 읽음

// appLogin - createAsyncBridge 사용
// window.ReactNativeWebView.postMessage()로 네이티브에 메시지 전송
// window.__GRANITE_NATIVE_EMITTER.on()으로 응답 수신
```

### 환경별 동작
| 환경 | import.meta.env.DEV | 동작 |
|------|---------------------|------|
| `granite dev` | `true` | 모의 로그인 |
| `.ait` 파일 (sandbox) | `false` | 실제 SDK 호출 |
| `.ait` 파일 (toss) | `false` | 실제 SDK 호출 |

---

## 남은 과제

### 백엔드 구현 필요
현재 `raymontology-production.up.railway.app`에서 토스 OAuth 엔드포인트가 구현되지 않음:

1. **`/api/auth/toss/token`**: 인가 코드 → 토큰 교환
   - 토스 OAuth 서버에 mTLS로 토큰 요청
   - access_token, refresh_token 반환

2. **`/api/auth/toss/me`**: 사용자 정보 조회
   - 토스 OAuth 서버에서 사용자 정보 조회
   - userKey, name 반환

### mTLS 설정 필요
- 토스 개발자센터에서 인증서 발급
- 백엔드 서버에 인증서 설정
- Railway 환경변수로 인증서 경로 설정

---

## 테스트 방법

1. 앱인토스 개발자센터 → 앱 출시 → 테스트 기기 등록
2. `raymondsrisk.ait` 파일 업로드
3. 샌드박스 앱에서 테스트
4. 디버그 패널(디버그 보기 버튼)에서 실제 에러 메시지 확인

---

## 참고 문서

- [앱인토스 로그인 가이드](https://developers-apps-in-toss.toss.im/login/develop.html)
- [앱인토스 FAQ](https://developers-apps-in-toss.toss.im/faq.html)
- `/Users/jaejoonpark/raymontology/docs/APPS_IN_TOSS_GUIDE.md`
- `/Users/jaejoonpark/raymontology/raymondsrisk-app/TROUBLESHOOTING_PROMPT.md`

---

## 빌드 아티팩트

- **파일**: `raymondsrisk.ait`
- **크기**: 1.8MB
- **생성일**: 2025-12-31 00:59
