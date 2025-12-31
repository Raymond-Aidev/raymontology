# 앱인토스 API 사용 가이드

> **출처**: https://developers-apps-in-toss.toss.im/development/integration-process.md
> **저장일**: 2025-12-31

---

# API 사용하기

앱인토스 API를 사용하려면 **mTLS 기반의 서버 간(Server-to-Server) 통신 설정이 반드시 필요해요.**
mTLS 인증서는 파트너사 서버와 앱인토스 서버 간 통신을 **암호화**하고 **쌍방 신원을 상호 검증**하는 데 사용됩니다.

## mTLS가 필요한 기능

| 기능 | 설명 |
|------|------|
| 토스 로그인 | `/login/intro.md` |
| 토스 페이 | `/tosspay/intro.md` |
| 인앱 결제 | `/iap/intro.md` |
| 기능성 푸시, 알림 | `/push/intro.md` |
| 프로모션(토스 포인트) | `/promotion/intro.md` |

## 통신 구조

```
파트너사 서버 → (mTLS) → 앱인토스 서버 → 토스 서버
```

앱인토스 API는 파트너사 서버에서 앱인토스 서버로 요청을 전송하고,
앱인토스 서버가 토스 서버에 연동 요청을 전달하는 구조로 동작해요.

## mTLS 인증서 발급 방법

### 1. 앱 선택하기
앱인토스 콘솔에 접속해 인증서를 발급받을 앱을 선택하세요.
왼쪽 메뉴에서 **mTLS 인증서** 탭을 클릭한 뒤, **+ 발급받기** 버튼을 눌러 발급을 진행해요.

### 2. 인증서 다운로드 및 보관
mTLS 인증서가 발급되면 **인증서 파일과 키 파일**을 다운로드할 수 있어요.

**주의사항:**
- 인증서와 키 파일은 유출되지 않도록 **안전한 위치에 보관**하세요.
- 인증서가 **만료되기 전에 반드시 재발급**해 주세요.

인증서는 일반적으로 하나만 사용하지만, **무중단 교체**를 위해 **두 개 이상 등록해 둘 수도 있어요.**

## API 요청 시 인증서 설정

앱인토스 서버에 요청하려면, 발급받은 **인증서/키 파일**을 서버 애플리케이션에 등록해야 해요.

### Python 예제

```python
import requests

class TLSClient:
    def __init__(self, cert_path, key_path):
        self.cert_path = cert_path
        self.key_path = key_path

    def make_request(self, url):
        response = requests.get(
            url,
            cert=(self.cert_path, self.key_path),
            headers={'Content-Type': 'application/json'}
        )
        return response.text

if __name__ == '__main__':
    client = TLSClient(
        cert_path='/path/to/client-cert.pem',
        key_path='/path/to/client-key.pem'
    )
    result = client.make_request('https://apps-in-toss-api.toss.im/endpoint')
    print(result)
```

### JavaScript(Node.js) 예제

```js
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
      console.log('Response:', data);
    });
  }
);

req.on('error', (e) => console.error(e));
req.end();
```

## 자주 묻는 질문

### `ERR_NETWORK` 에러가 발생해요
mTLS 미적용 상태에서 API를 호출하면 발생해요.
인증서와 키 파일이 올바르게 설정되었는지 확인하세요.

---

## 핵심 요약

1. **mTLS 필수**: 토스 로그인, 인앱 결제 등 모든 핵심 기능에 mTLS 인증서 필요
2. **서버 간 통신**: 클라이언트(앱) → 파트너 서버 → (mTLS) → 앱인토스 서버 → 토스 서버
3. **인증서 발급**: 앱인토스 콘솔에서 mTLS 인증서 발급 및 관리
4. **보안 주의**: 인증서/키 파일 유출 방지, 만료 전 재발급
