# 앱인토스 샌드박스 테스트 가이드

> 출처: https://developers-apps-in-toss.toss.im/development/test/sandbox.md

---

## 개요

앱인토스는 개발용 토스앱을 별도로 제공하지 않습니다.
대신 **전용 샌드박스 앱**을 통해 개발·테스트 환경을 구성할 수 있습니다.

> **중요**: 실서비스 출시 전, 샌드박스 앱에서 **기능 검증을 완료**해야 합니다.
> 샌드박스 검증 없이 진행한 기능은 런칭 또는 검수 단계에서 **반려될 수 있습니다.**

---

## 1. 샌드박스 앱이란?

앱인토스는 토스앱 안에서 파트너사의 서비스를 **앱인앱(App-in-App)** 형태로 제공합니다.
별도의 개발용 토스앱 대신, **개발·QA 전용 샌드박스 앱**을 통해 연동 테스트를 진행할 수 있습니다.

### 샌드박스 앱 다운로드

| 구분 | 빌드번호 | 다운로드 |
|------|----------|----------|
| Android | 2025-12-16 | APK 다운로드 |
| iOS (시뮬레이터) | 2025-12-07 | 다운로드 |
| iOS (실기기) | 2025-11-11 | TestFlight |

### 지원 OS 버전

| 구분 | 최소 버전 |
|------|----------|
| Android | Android 7 |
| iOS | iOS 16 |

### HTTP 통신 정책

- **샌드박스**: App Transport Security(ATS) 정책 위반 방지를 위해 **http 통신 허용**
- **프로덕션**: **https만 지원** (http 기반 기능은 샌드박스에서만 동작)

---

## 2. 샌드박스 앱 사용하기

### Step 1: 최신 버전 설치

샌드박스 앱은 수시로 업데이트됩니다.
오류가 보이면 **최신 버전으로 업데이트**해 주세요.

### Step 2: 개발자 로그인

콘솔에서 사용하는 **토스 비즈니스 계정**으로 로그인하세요.
토스 비즈니스 가입이 필요하다면 콘솔에서 앱 등록하기를 참조하세요.

### Step 3: 앱 선택

소속된 워크스페이스의 앱 목록이 노출됩니다.
**테스트할 앱**을 선택하세요.

### Step 4: 토스 인증

콘솔에 등록한 **토스 계정**으로 본인 인증을 진행합니다.
해당 계정의 **토스앱이 설치된 스마트폰**에서 푸시를 열어 인증을 완료해 주세요.

### Step 5: 앱 스킴(URL)로 접속

접속할 스킴을 입력하면 미니앱이 실행됩니다.

```
intoss://{appName}
```

**RaymondsRisk 접속 스킴:**
```
intoss://raymondsrisk
```

---

## 3. 샌드박스 테스트 가능 기능

샌드박스에서 바로 확인 가능한 항목입니다.
샌드박스에서 미지원인 경우에는 콘솔 '출시하기'의 QR 코드로 토스앱에서 테스트해 주세요.

| 기능 | 테스트 가능 여부 |
|------|:----------------:|
| 토스 로그인 | ✅ 가능 |
| 게임 로그인 | ✅ 가능 (단, mock 데이터) |
| 토스페이 | ✅ 가능 |
| 인앱 결제 | ✅ 가능 |
| 게임 프로필 & 리더보드 | ✅ 가능 |
| 분석 | ❌ 불가능 |
| 공유 리워드 | ❌ 불가능 |
| 인앱 광고 | ❌ 불가능 |
| 가로 버전 게임 | ❌ 불가능 |
| 내비게이션 바 공유하기 | ❌ 불가능 |

---

## 4. 로컬 개발 서버 연결

### 4.1 granite.config.ts 설정

```typescript
import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'raymondsrisk',
  brand: {
    displayName: 'RaymondsRisk',
    primaryColor: '#E74C3C',
    icon: '',
  },
  web: {
    host: '192.168.x.x',  // 로컬 IP 주소로 변경
    port: 5173,
    commands: {
      dev: 'vite --host',  // --host 옵션 필수!
      build: 'vite build',
    },
  },
  permissions: [],
});
```

### 4.2 로컬 IP 확인

```bash
# macOS
ipconfig getifaddr en0

# 또는
ifconfig | grep "inet " | grep -v 127.0.0.1
```

### 4.3 iOS 실기기 연결

1. 로컬 서버와 **같은 WiFi** 연결 필요
2. **로컬 네트워크 권한** 허용
3. 서버 IP 주소 입력

### 4.4 Android 실기기 연결

```bash
# USB 연결 후 포트 포워딩
adb reverse tcp:8081 tcp:8081
adb reverse tcp:5173 tcp:5173

# 특정 기기 연결
adb -s {디바이스아이디} reverse tcp:8081 tcp:8081
adb -s {디바이스아이디} reverse tcp:5173 tcp:5173

# 연결 상태 확인
adb reverse --list

# 연결 끊기
adb kill-server
```

---

## 5. 트러블슈팅

### "서버에 연결할 수 없습니다" 에러

1. `granite.config.ts`의 `web.commands.dev`에 `--host` 추가
2. `web.host`를 실제 호스트 주소로 변경
3. 샌드박스 앱에서 metro 서버 주소도 호스트 주소로 변경

### "잠시 문제가 생겼어요" 메시지

- adb 연결 끊고 다시 8081 포트 연결
```bash
adb kill-server
adb reverse tcp:8081 tcp:8081
```

### PC웹에서 Not Found 오류

- 8081 포트는 샌드박스 전용
- PC웹에서 Not Found는 **정상**입니다

### 플러그인 옵션 오류

- `granite.config.ts`의 `icon` 설정 확인 (빈 문자열 가능)

### 샌드박스에서 테스트가 안 될 때

- 샌드박스 개발자 로그인 진행
- 앱인토스 콘솔에 앱 등록 확인
- 최신 버전 샌드박스 앱 설치

---

## 6. 자주 묻는 질문

### Q: 샌드박스에서 테스트 진행이 잘 안돼요.
A: 샌드박스 개발자 로그인을 진행해 주세요. 콘솔에서 사용하는 토스 비즈니스 계정으로 로그인이 필요합니다.

### Q: 실기기에서 연결이 안 됩니다.
A:
- iOS: 동일 WiFi 연결, 로컬 네트워크 권한 허용 확인
- Android: `adb reverse` 명령어 실행 확인

### Q: 앱 목록에 내 앱이 안 보여요.
A: 앱인토스 콘솔에서 앱 등록이 완료되었는지 확인하세요. 워크스페이스에 소속되어 있어야 합니다.

---

## 7. 다음 단계: 토스앱에서 테스트

샌드박스에서 기본 기능 검증 완료 후:

1. 앱인토스 콘솔 → **출시하기** 메뉴
2. **QR 코드** 생성
3. 실제 **토스앱**에서 QR 스캔
4. 샌드박스 미지원 기능 테스트 (분석, 공유 리워드 등)

---

## 8. 참고 링크

| 항목 | URL |
|------|-----|
| 앱인토스 공식 문서 | https://developers-apps-in-toss.toss.im/ |
| 앱인토스 콘솔 | https://console.apps-in-toss.toss.im |
| TDS 문서 | https://tossmini-docs.toss.im/tds-mobile/ |
| 토스앱 테스트 | https://developers-apps-in-toss.toss.im/development/test/toss |
| 출시 가이드 | https://developers-apps-in-toss.toss.im/development/deploy |

---

*이 문서는 앱인토스 공식 문서(2025-12-30 기준)를 기반으로 작성되었습니다.*
