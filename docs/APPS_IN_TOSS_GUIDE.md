# 앱인토스(Apps in Toss) 개발 가이드

> 공식 문서: https://developers-apps-in-toss.toss.im/intro/overview.md

---

## 서비스 범위

**앱인토스는 RaymondsRisk 서비스 전용입니다.**

| 서비스 | 앱인토스 포함 여부 |
|--------|------------------|
| **RaymondsRisk** | ✅ 포함 |
| Raymontology (CB/임원 분석) | ❌ 미포함 |
| RaymondsIndex (자본배분 효율성) | ❌ 미포함 |

- 앱인토스 앱 이름: `raymondsrisk`
- 스킴: `intoss://raymondsrisk`

### 백엔드 API 서버 설정

| 환경 | API 서버 | 용도 |
|------|---------|------|
| **로컬 개발** | `http://localhost:8000/api` | 개발/디버깅 |
| **실기기 테스트** | `https://raymontology-production.up.railway.app/api` | 테스트 |
| **프로덕션** | `https://raymontology-production.up.railway.app/api` | 실서비스 |

**중요**: 실제 서비스 배포 시 반드시 Railway 프로덕션 서버를 사용해야 합니다.

```typescript
// 환경별 API URL 설정 예시
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://raymontology-production.up.railway.app/api'
  : 'http://localhost:8000/api';
```

## 문서 참조 URL

| 유형 | 설명 | URL |
|------|------|-----|
| **기본 문서 (권장)** | 앱인토스 기능을 사용하는 데 필요한 핵심 정보 | https://developers-apps-in-toss.toss.im/llms.txt |
| **전체 문서 (Full)** | 전체 문서 포함 확장 버전 (토큰 소모량 증가) | https://developers-apps-in-toss.toss.im/llms-full.txt |
| **예제 전용 문서** | 예제 코드만 빠르게 참고 | https://developers-apps-in-toss.toss.im/tutorials/examples.md |

---

## 개요

앱인토스(Apps in Toss)는 파트너사가 개발한 서비스를 토스 앱 내부에서 '앱인앱(App-in-App)'의 형태로 노출할 수 있게 하는 플랫폼입니다.

- **3,000만 누적 토스 사용자**에게 서비스 노출
- 사용자 확보와 매출 확장을 동시에 도모

---

## 앱인토스 제공 기능

### 1. 다양한 솔루션 도구

- **WebView 기반 SDK**: 웹 개발자가 쉽게 연동 가능
- **React Native 기반 SDK**: 네이티브 앱 개발 지원
- SDK 연동 → 빌드 결과물 업로드 → 내부 검수 → 출시

**개발 흐름:**
```
파트너사 앱 개발 → SDK 연동 → 빌드 업로드 → 검수 → 토스 앱 내 출시
```

### 2. 핵심 기능 제공

SDK와 API를 통해 직접 구현 없이 사용 가능한 기능:
- 로그인 (토스 계정 연동)
- 결제 (토스페이 연동)
- 인증 (본인인증)
- UI 컴포넌트

### 3. 전 과정 지원 솔루션

| 영역 | 지원 내용 |
|------|----------|
| 개발 | SDK, API, UI 컴포넌트 |
| 디자인 | 디자인 가이드라인 |
| 마케팅 | 노출, 광고, 푸시 알림 |
| 수익화 | 정산 관리 자동화 |

---

## 노출 채널

### 토스 앱 내 노출 위치

1. **전체 탭 홈**: 카테고리별 노출
2. **검색**: 키워드 기반 검색 노출
3. **푸시 알림**: 토스 앱 푸시 발송
4. **토스 홈 광고**: 광고 배너 노출

### 카테고리

- **논게임**: 일반 서비스 앱
- **게임**: 게임 카테고리

---

## WebView 개발 가이드

> 공식 문서: https://developers-apps-in-toss.toss.im/tutorials/webview.md

### 새 웹 프로젝트 시작하기

Vite(React + TypeScript) 기준 프로젝트 생성:

```bash
# npm
npm create vite@latest {project명} -- --template react-ts
cd {project명}
npm install
npm run dev

# yarn
yarn create vite {project명} --template react-ts
cd {project명}
yarn
yarn dev

# pnpm
pnpm create vite@latest {project명} --template react-ts
cd {project명}
pnpm install
pnpm dev
```

### 1. 패키지 설치

기존 웹 프로젝트에 `@apps-in-toss/web-framework` 설치:

```bash
# npm
npm install @apps-in-toss/web-framework

# pnpm
pnpm install @apps-in-toss/web-framework

# yarn
yarn add @apps-in-toss/web-framework
```

### 2. 환경 구성 (ait init)

```bash
# npm
npx ait init

# pnpm
pnpm ait init

# yarn
yarn ait init
```

**설정 단계:**
1. `web-framework` 선택
2. 앱 이름(`appName`) 입력 - 앱인토스 콘솔에서 만든 이름과 동일해야 함
3. 웹 번들러의 dev 명령어 입력
4. 웹 번들러의 build 명령어 입력
5. 웹 개발 서버 포트 번호 입력

### 3. 설정 파일 (granite.config.ts)

```typescript
import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'raymondsrisk', // 앱인토스 콘솔에서 설정한 앱 이름
  brand: {
    displayName: '레이몬즈리스크', // 화면에 노출될 앱의 한글 이름
    primaryColor: '#3182F6', // 앱의 기본 색상 (RGB HEX)
    icon: '', // 앱 아이콘 이미지 주소 (빈 문자열로 테스트 가능)
  },
  web: {
    host: 'localhost', // 앱 내 웹뷰에 사용될 host
    port: 5173,
    commands: {
      dev: 'vite', // 개발 모드 실행
      build: 'vite build', // 빌드 명령어
    },
  },
  permissions: [],
});
```

**주요 설정 항목:**
- `brand.displayName`: 브릿지 뷰에 표시할 앱 이름
- `brand.icon`: 앱 아이콘 이미지 주소
- `brand.primaryColor`: TDS 컴포넌트 대표 색상
- `web.commands.dev`: `granite dev` 실행 시 함께 실행할 명령어
- `web.commands.build`: `granite build` 실행 시 함께 실행할 명령어
- `webViewProps.type`: `partner`(기본) 또는 `game`(전체화면)

**빌드 시 주의사항:**
- `granite build` 결과물은 `outdir` 경로(기본값: `dist`)와 일치해야 함

### 4. TDS 패키지 설치 (필수)

TDS (Toss Design System)는 모든 비게임 WebView 미니앱에서 **필수**이며, 검수 승인 기준에 포함됨.

| web-framework 버전 | 사용할 패키지 |
|-------------------|--------------|
| < 1.0.0 | @toss-design-system/mobile |
| >= 1.0.0 | @toss/tds-mobile |

TDS 가이드: https://tossmini-docs.toss.im/tds-mobile/

### 5. 로컬 개발 서버 실행

```bash
# npm
npm run dev

# pnpm
pnpm run dev

# yarn
yarn dev
```

웹 개발 서버와 React Native 개발 서버가 함께 실행되며, HMR(Hot Module Replacement) 지원.

**실기기 테스트 시 설정:**

```typescript
// granite.config.ts
export default defineConfig({
  appName: 'raymondsrisk',
  web: {
    host: '192.168.0.100', // 실기기에서 접근 가능한 IP
    port: 5173,
    commands: {
      dev: 'vite --host', // --host 옵션 필수
      build: 'vite build',
    },
  },
  permissions: [],
});
```

### 6. 샌드박스 앱에서 테스트

**준비물:** 샌드박스 앱(테스트앱) 설치 필수

#### iOS 시뮬레이터/실기기

1. 앱인토스 샌드박스 앱 실행
2. 스킴 입력: `intoss://{appName}` (예: `intoss://raymondsrisk`)
3. "스키마 열기" 버튼 클릭

**실기기 추가 설정:**
- 로컬 서버와 같은 와이파이 연결 필요
- "로컬 네트워크" 권한 허용
- 서버 IP 주소 입력 (macOS: `ipconfig getifaddr en0`로 확인)

#### Android 실기기/에뮬레이터

1. USB 연결
2. adb 포트 연결:
```bash
adb reverse tcp:8081 tcp:8081
adb reverse tcp:5173 tcp:5173

# 특정 기기 연결
adb -s {디바이스아이디} reverse tcp:8081 tcp:8081
adb -s {디바이스아이디} reverse tcp:5173 tcp:5173

# 연결 상태 확인
adb reverse --list
```
3. 샌드박스 앱에서 스킴 실행: `intoss://{appName}`

**자주 쓰는 adb 명령어:**
```bash
# 연결 끊기
adb kill-server

# 포트 연결
adb reverse tcp:8081 tcp:8081
adb reverse tcp:5173 tcp:5173

# 연결 확인
adb reverse --list
```

### 7. 트러블슈팅

#### "서버에 연결할 수 없습니다" 에러
1. `granite.config.ts`의 `web.commands.dev`에 `--host` 추가
2. `web.host`를 실제 호스트 주소로 변경
3. 샌드박스 앱에서 metro 서버 주소도 호스트 주소로 변경

#### "잠시 문제가 생겼어요" 메시지
- adb 연결 끊고 다시 8081 포트 연결

#### PC웹에서 Not Found 오류
- 8081 포트는 샌드박스 전용, PC웹에서는 Not Found 정상

#### 플러그인 옵션 오류
- `granite.config.ts`의 `icon` 설정 확인 (빈 문자열 가능)

### 8. 출시하기

- 토스앱 테스트: [토스앱 문서](https://developers-apps-in-toss.toss.im/development/test/toss) 참고
- 미니앱 출시: [출시 문서](https://developers-apps-in-toss.toss.im/development/deploy) 참고

---

## API 사용하기

> 공식 문서: https://developers-apps-in-toss.toss.im/development/integration-process.md

앱인토스 API를 사용하려면 **mTLS 기반의 서버 간(Server-to-Server) 통신 설정이 필수**입니다.
mTLS 인증서는 파트너사 서버와 앱인토스 서버 간 통신을 **암호화**하고 **쌍방 신원을 상호 검증**합니다.

### mTLS 인증서가 필요한 기능

| 기능 | 설명 |
|------|------|
| 토스 로그인 | 토스 계정 연동 로그인 |
| 토스페이 | 결제 연동 |
| 인앱 결제 | 앱 내 결제 처리 |
| 기능성 푸시/알림 | 푸시 알림 발송 |
| 프로모션(토스 포인트) | 포인트 적립/사용 |

### 통신 구조

```
파트너사 서버 → 앱인토스 서버 → 토스 서버
     ↑               ↑
     └── mTLS 인증 ──┘
```

### mTLS 인증서 발급 방법

1. **앱인토스 콘솔 접속** → 앱 선택
2. **mTLS 인증서** 탭 클릭 → **+ 발급받기** 버튼
3. **인증서 파일(.pem)과 키 파일(.pem)** 다운로드

**주의사항:**
- 인증서와 키 파일은 **안전한 위치에 보관**
- 인증서 **만료 전 반드시 재발급**
- 무중단 교체를 위해 **다중 인증서 등록 가능**

---

### API 요청 예제 (언어별)

#### Python 예제

```python
import requests

class TLSClient:
    def __init__(self, cert_path, key_path):
        self.cert_path = cert_path
        self.key_path = key_path

    def make_request(self, url, method='GET', data=None):
        response = requests.request(
            method,
            url,
            cert=(self.cert_path, self.key_path),
            headers={'Content-Type': 'application/json'},
            json=data
        )
        return response.json()

# 사용 예시
client = TLSClient(
    cert_path='/path/to/client-cert.pem',
    key_path='/path/to/client-key.pem'
)
result = client.make_request('https://apps-in-toss-api.toss.im/endpoint')
print(result)
```

#### JavaScript (Node.js) 예제

```javascript
const https = require('https');
const fs = require('fs');

const options = {
  cert: fs.readFileSync('/path/to/client-cert.pem'),
  key: fs.readFileSync('/path/to/client-key.pem'),
  rejectUnauthorized: true,
};

const req = https.request(
  'https://apps-in-toss-api.toss.im/endpoint',
  { method: 'GET', ...options },
  (res) => {
    let data = '';
    res.on('data', (chunk) => (data += chunk));
    res.on('end', () => {
      console.log('Response:', JSON.parse(data));
    });
  }
);

req.on('error', (e) => console.error(e));
req.end();
```

#### Kotlin 예제

```kotlin
import java.security.KeyStore
import java.security.cert.X509Certificate
import java.security.KeyFactory
import java.security.spec.PKCS8EncodedKeySpec
import java.io.FileReader
import java.io.ByteArrayInputStream
import java.util.Base64
import javax.net.ssl.*
import java.net.URL
import javax.net.ssl.HttpsURLConnection
import java.security.cert.CertificateFactory

class TLSClient {
    fun createSSLContext(certPath: String, keyPath: String): SSLContext {
        val cert = loadCertificate(certPath)
        val key = loadPrivateKey(keyPath)

        val keyStore = KeyStore.getInstance(KeyStore.getDefaultType())
        keyStore.load(null, null)
        keyStore.setCertificateEntry("client-cert", cert)
        keyStore.setKeyEntry("client-key", key, "".toCharArray(), arrayOf(cert))

        val kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm())
        kmf.init(keyStore, "".toCharArray())

        return SSLContext.getInstance("TLS").apply {
            init(kmf.keyManagers, null, null)
        }
    }

    private fun loadCertificate(path: String): X509Certificate {
        val content = FileReader(path).readText()
            .replace("-----BEGIN CERTIFICATE-----", "")
            .replace("-----END CERTIFICATE-----", "")
            .replace("\\s".toRegex(), "")
        val bytes = Base64.getDecoder().decode(content)
        return CertificateFactory.getInstance("X.509")
            .generateCertificate(ByteArrayInputStream(bytes)) as X509Certificate
    }

    private fun loadPrivateKey(path: String): java.security.PrivateKey {
        val content = FileReader(path).readText()
            .replace("-----BEGIN PRIVATE KEY-----", "")
            .replace("-----END PRIVATE KEY-----", "")
            .replace("\\s".toRegex(), "")
        val bytes = Base64.getDecoder().decode(content)
        val spec = PKCS8EncodedKeySpec(bytes)
        return KeyFactory.getInstance("RSA").generatePrivate(spec)
    }

    fun makeRequest(url: String, context: SSLContext): String {
        val connection = (URL(url).openConnection() as HttpsURLConnection).apply {
            sslSocketFactory = context.socketFactory
            requestMethod = "GET"
            connectTimeout = 5000
            readTimeout = 5000
        }

        return connection.inputStream.bufferedReader().use { it.readText() }.also {
            connection.disconnect()
        }
    }
}

// 사용 예시
fun main() {
    val client = TLSClient()
    val context = client.createSSLContext("/path/to/client-cert.pem", "/path/to/client-key.pem")
    val response = client.makeRequest("https://apps-in-toss-api.toss.im/endpoint", context)
    println(response)
}
```

#### C# 예제

```csharp
using System;
using System.Net.Http;
using System.Security.Cryptography.X509Certificates;
using System.Threading.Tasks;

class Program {
    static async Task Main(string[] args) {
        var handler = new HttpClientHandler();
        handler.ClientCertificates.Add(
            new X509Certificate2("/path/to/client-cert.pem")
        );

        using var client = new HttpClient(handler);
        var response = await client.GetAsync("https://apps-in-toss-api.toss.im/endpoint");
        string body = await response.Content.ReadAsStringAsync();
        Console.WriteLine(body);
    }
}
```

#### C++ 예제 (libcurl)

```cpp
#include <curl/curl.h>
#include <iostream>
#include <string>

size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* userp) {
    userp->append((char*)contents, size * nmemb);
    return size * nmemb;
}

int main() {
    CURL* curl = curl_easy_init();
    if (curl) {
        std::string response;
        curl_easy_setopt(curl, CURLOPT_URL, "https://apps-in-toss-api.toss.im/endpoint");
        curl_easy_setopt(curl, CURLOPT_SSLCERT, "/path/to/client-cert.pem");
        curl_easy_setopt(curl, CURLOPT_SSLKEY, "/path/to/client-key.pem");
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);

        CURLcode res = curl_easy_perform(curl);
        if (res == CURLE_OK) {
            std::cout << "Response: " << response << std::endl;
        } else {
            std::cerr << "Error: " << curl_easy_strerror(res) << std::endl;
        }

        curl_easy_cleanup(curl);
    }
    return 0;
}
```

---

### API 트러블슈팅

#### `ERR_NETWORK` 에러
- **원인**: mTLS 미적용 상태에서 API 호출
- **해결**: 인증서와 키 파일을 올바르게 설정했는지 확인

#### 인증서 관련 오류
- 인증서 경로가 올바른지 확인
- 인증서가 만료되지 않았는지 확인
- 키 파일과 인증서 파일이 매칭되는지 확인

---

## 검수 및 출시 프로세스

1. **빌드 업로드**: 개발 완료된 앱 빌드 제출
2. **내부 검수**: 토스 검수팀 리뷰
3. **피드백 반영**: 수정 사항 반영
4. **출시 승인**: 최종 승인 후 출시
5. **라이브**: 토스 앱 내 서비스 노출

---

## 참고 자료

- 공식 홈페이지: https://apps-in-toss.toss.im/
- 개발자 문서: https://developers-apps-in-toss.toss.im/
- 블로그: 앱인토스 공식 블로그

---

## 자주 묻는 질문

### Q: 앱인토스 서비스는 누구를 대상으로 제공되나요?
A: 파트너사 계약을 체결한 사업자가 이용 가능합니다.

### Q: 지원하는 OS 버전은?
A: iOS, Android 모두 지원하며, 최소 버전은 공식 문서 참조.

### Q: 개발 기간은 얼마나 걸리나요?
A: SDK 연동만으로 기본 기능 구현 가능, 복잡도에 따라 상이.

---

*이 문서는 앱인토스 공식 문서를 기반으로 작성되었습니다.*
*최신 정보는 공식 개발자 문서를 참조하세요.*
