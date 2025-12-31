# RaymondsRisk 앱인토스 로그인 문제 해결 프롬프트

> 새 세션에서 이 내용을 복사하여 사용하세요.

---

RaymondsRisk 앱인토스 앱의 "토스로 시작하기" 버튼 문제를 해결해줘.

## 현재 상황
- `granite dev`(로컬 개발 서버)에서는 로그인이 정상 작동
- `.ait` 파일을 샌드박스 앱에 업로드하면 로그인 버튼이 작동하지 않음

## 이미 시도한 방법들 (모두 실패)

### 1. SDK import 방식 변경
- `window.AppsInToss.appLogin()` → `@apps-in-toss/web-framework`의 `appLogin()` 변경
- 결과: 해결 안됨

### 2. getOperationalEnvironment() 에러 핸들링
- 에러 발생 시 'sandbox'로 폴백하도록 변경
- 결과: 해결 안됨

### 3. SDK 브릿지 초기화 확인 로직 추가
- `window.__CONSTANT_HANDLER_MAP`, `window.ReactNativeWebView` 존재 여부 확인
- 브릿지 미초기화 시 모의 로그인 실행
- 결과: 테스트 필요 (최신 수정)

## 기술적 발견 사항

### SDK 브릿지 구조 (분석 완료)
```javascript
// getOperationalEnvironment - createConstantBridge 사용
// window.__CONSTANT_HANDLER_MAP['getOperationalEnvironment']에서 값 읽음

// appLogin - createAsyncBridge 사용
// window.ReactNativeWebView.postMessage()로 네이티브에 메시지 전송
// window.__GRANITE_NATIVE_EMITTER.on()으로 응답 수신
```

### 환경별 차이
| 환경 | import.meta.env.DEV | 동작 |
|------|---------------------|------|
| `granite dev` | `true` | 모의 로그인 (정상) |
| `.ait` 파일 | `false` | 실제 SDK 호출 (문제 발생) |

### 공식 문서 확인 사항
- 샌드박스에서도 mTLS가 필수 (서버 연동 시)
- referrer: 샌드박스='sandbox', 토스앱='DEFAULT'
- appLogin은 인가 코드 반환, 서버에서 토큰 교환 필요

## 새로운 접근 방식 제안

1. **실제 에러 확인**: .ait 파일에서 어떤 에러가 발생하는지 정확히 파악
   - 콘솔 로그 확인 방법 또는 에러 UI 표시 추가

2. **React Native WebView 초기화 타이밍 문제 확인**
   - SDK 브릿지가 주입되기 전에 login 함수가 호출될 수 있음
   - window 객체 상태를 로드 시점에 기록

3. **앱인토스 테크챗 커뮤니티 질문 고려**
   - https://techchat-apps-in-toss.toss.im/

## 관련 파일
| 파일 | 설명 |
|------|------|
| `/src/contexts/AuthContext.tsx` | 로그인 로직 (핵심) |
| `/src/pages/PurchasePage.tsx` | 로그인 버튼 있는 페이지 |
| `/src/types/auth.ts` | 타입 정의 |
| `/granite.config.ts` | 앱 설정 |

## 참고 문서
- [앱인토스 개발자센터 로그인 가이드](https://developers-apps-in-toss.toss.im/login/develop.html)
- [앱인토스 FAQ](https://developers-apps-in-toss.toss.im/faq.html)
- [앱인토스 테크챗 커뮤니티](https://techchat-apps-in-toss.toss.im/)

## 요청사항
위 시행착오를 참고하여 다른 관점에서 문제 원인을 추적하고 해결책을 제시해줘.
특히 .ait 파일이 샌드박스 앱에서 로드될 때 SDK 브릿지 초기화 과정에서
무엇이 잘못되는지 파악하는 것이 핵심이야.
