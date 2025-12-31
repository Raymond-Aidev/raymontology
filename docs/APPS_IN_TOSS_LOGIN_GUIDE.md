# 앱인토스 토스 로그인 개발 가이드

> **출처**: https://developers-apps-in-toss.toss.im/login/develop.md
> **저장일**: 2025-12-31

---

## 개발 흐름 (7단계)

```
1. 인가 코드 받기 (SDK appLogin)
2. AccessToken 발급 (서버 API)
3. AccessToken 재발급 (서버 API)
4. 사용자 정보 조회 (서버 API)
5. 사용자 정보 복호화 (AES-256-GCM)
6. 로그인 끊기 (서버 API)
7. 콜백으로 로그인 끊기 (토스앱에서 연결 해제 시)
```

---

## 1. 인가 코드 받기

**SDK의 `appLogin` 함수 사용**

```typescript
import { appLogin } from '@apps-in-toss/web-framework'

const { authorizationCode, referrer } = await appLogin()
// referrer: 'sandbox' (샌드박스앱) 또는 'DEFAULT' (토스앱)
```

**주의사항:**
- 인가코드 유효시간: **10분**
- 인가코드는 **중복 사용 불가**

**토스 로그인 처음 진행 시:**
- 토스 로그인 창 + 약관 동의 화면 노출
- 필수 약관 동의 후 인가 코드 반환

**이미 로그인한 사용자:**
- 별도 로그인 창 없이 바로 인가 코드 반환

---

## 2. AccessToken 발급

- **Method**: POST
- **URL**: `/api-partner/v1/apps-in-toss/user/oauth2/generate-token`
- **Content-Type**: application/json

**요청:**
| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| authorizationCode | string | Y | 인가코드 |
| referrer | string | Y | referrer |

**성공 응답:**
```json
{
  "resultType": "SUCCESS",
  "success": {
    "accessToken": "eyJ...",
    "refreshToken": "xNEY...",
    "scope": "user_ci user_birthday user_name user_phone user_gender",
    "tokenType": "Bearer",
    "expiresIn": 3599
  }
}
```

**실패 응답:**
```json
{
  "error": "invalid_grant"
}
// 또는
{
  "resultType": "FAIL",
  "error": {
    "errorCode": "INTERNAL_ERROR",
    "reason": "요청을 처리하는 도중에 문제가 발생했습니다."
  }
}
```

**주의사항:**
- AccessToken 유효시간: **1시간**

---

## 3. AccessToken 재발급

- **Method**: POST
- **URL**: `/api-partner/v1/apps-in-toss/user/oauth2/refresh-token`

**요청:**
| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| refreshToken | string | Y | 발급받은 RefreshToken |

**주의사항:**
- refreshToken 유효시간: **14일**

---

## 4. 사용자 정보 조회

- **Method**: GET
- **URL**: `/api-partner/v1/apps-in-toss/user/oauth2/login-me`
- **Header**: `Authorization: Bearer ${AccessToken}`

**성공 응답:**
```json
{
  "resultType": "SUCCESS",
  "success": {
    "userKey": 443731104,
    "scope": "user_ci,user_birthday,user_name,user_phone,user_gender,user_key",
    "agreedTerms": ["terms_tag1", "terms_tag2"],
    "name": "ENCRYPTED_VALUE",
    "phone": "ENCRYPTED_VALUE",
    "birthday": "ENCRYPTED_VALUE",
    "ci": "ENCRYPTED_VALUE",
    "gender": "ENCRYPTED_VALUE",
    "nationality": "ENCRYPTED_VALUE"
  }
}
```

**주의사항:**
- 모든 개인정보는 **암호화된 형태**로 제공
- 복호화 키는 콘솔에서 이메일로 전달

---

## 5. 사용자 정보 복호화

**암호화 알고리즘:**
- AES-256-GCM
- AAD: 복호화 키와 함께 이메일로 전달

**Python 예제:**
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64

def decrypt_toss_data(encrypted_text: str, base64_key: str, aad: str) -> str:
    IV_LENGTH = 12
    decoded = base64.b64decode(encrypted_text)
    key = base64.b64decode(base64_key)
    iv = decoded[:IV_LENGTH]
    ciphertext = decoded[IV_LENGTH:]

    aesgcm = AESGCM(key)
    decrypted = aesgcm.decrypt(iv, ciphertext, aad.encode())
    return decrypted.decode('utf-8')
```

---

## 6. 로그인 끊기

**AccessToken으로 연결 끊기:**
- **Method**: POST
- **URL**: `/api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-access-token`
- **Header**: `Authorization: Bearer ${AccessToken}`

**userKey로 연결 끊기:**
- **Method**: POST
- **URL**: `/api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-user-key`
- **Body**: `{"userKey": 443731103}`

---

## 7. 콜백으로 로그인 끊기

사용자가 토스앱에서 연결 해제 시 가맹점 서버로 알림.

**referrer 값:**
| referrer | 설명 |
|----------|------|
| `UNLINK` | 사용자가 토스앱에서 직접 연결 끊음 |
| `WITHDRAWAL_TERMS` | 약관 동의 철회 |
| `WITHDRAWAL_TOSS` | 토스 회원 탈퇴 |

---

## 핵심 요약

| 항목 | 값 |
|------|-----|
| 인가코드 유효시간 | 10분 |
| AccessToken 유효시간 | 1시간 |
| RefreshToken 유효시간 | 14일 |
| 개인정보 암호화 | AES-256-GCM |
| 인가코드 중복 사용 | 불가 |

---

## RaymondsRisk 구현 체크리스트

| 항목 | 상태 | 비고 |
|------|------|------|
| appLogin SDK 호출 | ✅ | AuthContext.tsx |
| 서버 토큰 발급 API | ✅ | toss_auth.py |
| 서버 토큰 갱신 API | ✅ | toss_auth.py |
| 사용자 정보 조회 API | ✅ | toss_auth.py |
| resultType 응답 처리 | ✅ | 방어적 코딩 적용 |
| AES-256-GCM 복호화 | ⏳ | 키 수령 대기 |
| **로그인 필수 체크** | ✅ | **수정 완료** (2025-12-31) |

---

## 수정 이력

### 2025-12-31: 로그인 필수 체크 수정
- **문제**: SDK 브릿지 미초기화 시 자동 로그인되어 Paywall 우회
- **수정**: `AuthContext.tsx`에서 브릿지 미초기화 시 에러 반환
- **결과**: 사용자가 명시적으로 로그인 버튼을 눌러야만 로그인 진행
