# RaymondsRisk 앱인토스 프로젝트 진행 현황

> **최종 업데이트**: 2025-12-31 15:00
> **프로젝트 경로**: `raymondsrisk-app/`

---

## 프로젝트 개요

### 서비스 설명
- **서비스명**: RaymondsRisk (레이먼즈리스크)
- **서비스 유형**: 기업 리스크 분석 리포트 서비스
- **플랫폼**: 앱인토스 (Apps in Toss) - 토스 앱 내 서비스
- **앱 이름**: `raymondsrisk`
- **스킴**: `intoss://raymondsrisk`

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

| 파일 | 설명 |
|------|------|
| `src/types/auth.ts` | 인증 관련 타입 정의 |
| `src/contexts/AuthContext.tsx` | React Context 기반 인증 상태 관리 |
| `src/services/authService.ts` | 백엔드 API 호출 서비스 |
| `src/pages/PaywallPage.tsx` | 유료 서비스 안내 및 로그인/구매 유도 |
| `src/pages/PurchasePage.tsx` | 이용권 구매 페이지 |

### Phase 2: 백엔드 mTLS API ✅ 완료

**토스 인증 API** (`backend/app/routes/toss_auth.py`)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/auth/toss/token` | 인가 코드로 토큰 발급 |
| GET | `/api/auth/toss/me` | 현재 사용자 정보 조회 |
| POST | `/api/auth/toss/refresh` | 토큰 갱신 |
| POST | `/api/auth/toss/logout` | 로그아웃 |
| GET | `/api/auth/toss/status` | mTLS 상태 확인 |

**이용권 API** (`backend/app/routes/credits.py`)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/credits/balance` | 이용권 잔액 조회 |
| GET | `/api/credits/products` | 상품 목록 조회 |
| POST | `/api/credits/purchase` | 이용권 구매 (IAP 검증) |
| GET | `/api/credits/history` | 거래 내역 조회 |
| POST | `/api/credits/use` | 리포트 조회용 이용권 차감 |
| GET | `/api/credits/viewed-companies` | 조회한 기업 목록 |

### Phase 3: 프론트엔드-백엔드 연동 ✅ 완료

- `creditService.ts` 구현 완료
- IAP SDK 연동 (`IAP.createOneTimePurchaseOrder`)
- ReportPage 접근 제어 API 연동

### Phase 4: 샌드박스 테스트 🔄 진행 중

**진행 상황**:
1. ✅ mTLS 인증서 발급 완료
2. ✅ 샌드박스 앱에서 스킴 실행 테스트
3. ✅ SDK 브릿지 초기화 대기 로직 추가
4. ✅ 503 에러 수정 (mTLS 미설정 시 모의 응답)
5. ✅ 401 에러 수정 (Header 파싱 오류)
6. 🔄 기본 기능 확인 후 검토 요청 단계

---

## 오늘 수정 이력 (2025-12-31)

### 1. SDK 브릿지 초기화 문제 해결
- **문제**: 샌드박스 앱에서 브릿지 미초기화 시 자동 로그인되어 Paywall 우회
- **수정**: `AuthContext.tsx` - 자동 로그인 제거, 브릿지 초기화 최대 3초 대기 로직 추가

### 2. 503 에러 (Service Unavailable) 해결
- **문제**: mTLS 인증서 미설정 시 `/api/auth/toss/token` 호출 실패
- **수정**: `toss_auth.py` - mTLS 미설정 시에도 모의 응답 반환하도록 조건 확장

### 3. 401 에러 (Unauthorized) 해결
- **문제**: FastAPI에서 Authorization 헤더를 읽지 못함
- **수정**: `toss_auth.py` - `authorization: str = Header(None)` 추가

### 4. 에러 메시지 UI 추가
- **수정**: `PaywallPage.tsx` - 로그인 에러 시 화면에 메시지 표시

---

## 커밋 이력

| 커밋 | 설명 |
|------|------|
| `d047c2b` | fix: Authorization 헤더 파싱 오류 수정 (401 에러 해결) |
| `778387d` | fix: RaymondsRisk 로그인 503 에러 및 SDK 브릿지 초기화 문제 해결 |
| `6c195eb` | fix: 토스 API 응답 방어적 코딩 적용 및 SDK 가이드 문서 추가 |
| `d63ff9e` | feat: RaymondsRisk 앱인토스 프론트엔드 앱 추가 |
| `9e82ec8` | feat: RaymondsRisk 앱인토스 mTLS 기반 토스 로그인 및 인앱결제 API 구현 |

---

## 검수 요청 정보

### 콘솔 입력값
| 항목 | 입력값 |
|------|--------|
| **이동 URL** | `/` |
| **Screen Name** | `Home` 또는 `홈` |

### 검수 프로세스
1. 테스트 1회 이상 완료 후 "검토 요청하기" 버튼 활성화
2. 검수 기간: 영업일 기준 최대 3일
3. 승인 후 "출시하기" 버튼으로 배포

---

## 프로젝트 구조

```
raymondsrisk-app/
├── src/
│   ├── api/
│   │   ├── client.ts           # Axios API 클라이언트
│   │   └── company.ts          # 기업 관련 API
│   ├── contexts/
│   │   └── AuthContext.tsx     # 인증 상태 관리
│   ├── services/
│   │   ├── authService.ts      # 인증 API 서비스
│   │   └── creditService.ts    # 이용권 API 서비스
│   ├── pages/
│   │   ├── HomePage.tsx        # 홈페이지 (무료)
│   │   ├── SearchPage.tsx      # 기업 검색 (무료)
│   │   ├── PaywallPage.tsx     # 유료 서비스 안내
│   │   ├── PurchasePage.tsx    # 이용권 구매
│   │   └── ReportPage.tsx      # 기업 리포트 (유료)
│   └── App.tsx                 # 라우팅 설정
├── granite.config.ts           # 앱인토스 설정
├── raymondsrisk.ait            # 빌드 결과물
└── package.json
```

---

## 환경 설정

### API 서버
| 환경 | URL |
|------|-----|
| 로컬 개발 | `http://localhost:8000` |
| 프로덕션 | `https://raymontology-production.up.railway.app` |

### 필수 환경변수 (백엔드)
```bash
TOSS_MTLS_CERT_PATH=/path/to/cert.pem
TOSS_MTLS_KEY_PATH=/path/to/key.pem
```

---

## 참조 문서

| 문서 | 경로/URL |
|------|----------|
| **통합 개발 가이드** | `docs/APPS_IN_TOSS_COMPLETE_GUIDE.md` |
| 앱인토스 공식 문서 | https://developers-apps-in-toss.toss.im/ |
| 토스 로그인 가이드 | https://developers-apps-in-toss.toss.im/login/develop.md |
| 인앱결제 가이드 | https://developers-apps-in-toss.toss.im/iap/intro.md |
