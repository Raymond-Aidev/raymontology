# RaymondsRisk 앱인토스 개발계획

> 작성일: 2025-12-30
> 최종 업데이트: 2026-01-06
> 상태: 샌드박스 테스트 진행 중 (토스 로그인 연동 완료)

---

## ⚠️ 중요: TDS 비필수 확인 (2026-01-06)

**TDS(@toss/tds-mobile) 컴포넌트 사용은 필수 조건이 아님을 확인받았습니다.**

| 항목 | 결정 |
|------|:----:|
| TDS 컴포넌트 필수 여부 | ❌ 아님 |
| 현재 개발 방식 승인 | ✅ 승인됨 |
| TDS 마이그레이션 필요 | ❌ 불필요 |

**승인된 현재 개발 방식:**
- 인라인 스타일 (React style prop)
- 커스텀 colors 상수 (`src/constants/colors.ts`)
- 직접 구현한 컴포넌트 (ListItem, DebugPanel 등)

**따라서 Phase 2, 3의 TDS 관련 작업은 불필요합니다.**

---

## 최근 변경 이력 (2026-01-06)

### 커밋 내역
| 커밋 | 설명 |
|------|------|
| `b71ffab` | feat: mTLS 인증서 환경변수 내용 방식 지원 |
| `362619e` | fix: 샌드박스 환경에서 실제 토스 API 호출하도록 수정 |
| `c86ad91` | fix: user_key 타입 불일치 수정 (정수 → 문자열) |

### 주요 수정 사항

1. **mTLS 인증서 환경변수 지원** (`toss_api_client.py`)
   - `TOSS_MTLS_CERT_CONTENT`: 인증서 PEM 내용 (BEGIN/END 포함)
   - `TOSS_MTLS_KEY_CONTENT`: 개인키 PEM 내용 (BEGIN/END 포함)
   - Railway 환경변수에 직접 인증서 내용 저장 가능

2. **샌드박스 Mock 모드 수정** (`toss_auth.py`)
   - 기존: 샌드박스 환경에서 mock 응답 반환
   - 수정: mTLS 인증서 미설정 시에만 mock 사용
   - 샌드박스에서도 실제 토스 API 호출하여 인가코드 검증

3. **user_key 타입 수정** (`toss_auth.py`)
   - 토스 API는 `user_key`를 정수(823394295)로 반환
   - DB 컬럼은 VARCHAR 타입
   - `user_key = str(user_info.user_key)` 변환 추가

### 딥링크 형식
검토요청 시 screenName: `/home` 또는 `/`

---

## 1. 현재 구현 상태

### 완료된 기능

| 기능 | 상태 | 파일 |
|------|:----:|------|
| 홈페이지 | ✅ | `pages/HomePage.tsx` |
| 기업 검색 | ✅ | `pages/SearchPage.tsx` |
| 기업 리포트 | ✅ | `pages/ReportPage.tsx` |
| Paywall | ✅ | `pages/PaywallPage.tsx` |
| 구매 페이지 | ✅ | `pages/PurchasePage.tsx` |
| 토스 로그인 연동 | ✅ | `contexts/AuthContext.tsx` |
| mTLS 인증서 연동 | ✅ | `backend/app/services/toss_api_client.py` |
| API 클라이언트 | ✅ | `api/client.ts` |
| 이용권 관리 | ✅ | `services/creditService.ts` |

### 기술 스택

| 항목 | 버전 |
|------|------|
| `@apps-in-toss/web-framework` | v1.6.2 |
| React | v18.2.0 |
| TypeScript | ~5.9.3 |
| Vite | v7.2.4 |
| React Router | v6.28.0 |
| TanStack Query | v5.90.15 |
| Zustand | v5.0.9 |
| Axios | v1.13.2 |

---

## 2. 개발 Phase (수정됨)

### Phase 1: 핵심 기능 ✅ 완료
> **목표: 앱인토스 연동 및 핵심 기능 구현**

| 작업 | 상태 |
|------|:----:|
| SDK 설치 및 설정 | ✅ |
| granite.config.ts 설정 | ✅ |
| 토스 로그인 연동 | ✅ |
| 홈/검색/리포트 페이지 | ✅ |
| Paywall 흐름 | ✅ |
| Railway API 연동 | ✅ |
| .ait 빌드 | ✅ |
| mTLS 환경변수 설정 (Railway) | ✅ |

### ~~Phase 2: TDS 디자인 시스템~~ (불필요)
> ~~TDS 비필수 확인으로 생략~~

### ~~Phase 3: TDS 컴포넌트 교체~~ (불필요)
> ~~TDS 비필수 확인으로 생략~~

### Phase 4: 선택 기능 (필요시)
> **목표: 결제 연동**

| 작업 | 상태 | 필요 조건 |
|------|:----:|----------|
| 토스페이 결제 | ⬜ | mTLS 인증서 (✅ 보유) |
| 인앱 결제 | ⬜ | 비즈니스 결정 |

---

## 3. 파일 구조

```
raymondsrisk-app/
├── granite.config.ts          # 앱인토스 설정
├── package.json               # 의존성
├── .env                       # API URL
├── raymondsrisk.ait           # 빌드 결과물
├── mTLS_인증서_20251231/       # mTLS 인증서
├── src/
│   ├── App.tsx                # 라우팅
│   ├── main.tsx               # 엔트리포인트
│   ├── contexts/
│   │   └── AuthContext.tsx    # 토스 인증 Context
│   ├── services/
│   │   ├── authService.ts     # 인증 서비스
│   │   └── creditService.ts   # 이용권 서비스
│   ├── api/
│   │   ├── client.ts          # Axios 인스턴스
│   │   └── company.ts         # 기업 API
│   ├── pages/
│   │   ├── HomePage.tsx       # 홈
│   │   ├── SearchPage.tsx     # 검색
│   │   ├── ReportPage.tsx     # 리포트 (유료)
│   │   ├── PaywallPage.tsx    # Paywall
│   │   └── PurchasePage.tsx   # 구매
│   ├── components/
│   │   ├── ListItem.tsx       # 커스텀 리스트
│   │   └── DebugPanel.tsx     # 디버그 패널
│   ├── types/
│   │   ├── auth.ts
│   │   ├── company.ts
│   │   └── report.ts
│   └── constants/
│       └── colors.ts          # 커스텀 색상
└── docs/
    ├── APPS_IN_TOSS_PROJECT.md
    └── SANDBOX_TEST_GUIDE.md
```

---

## 4. 검수 체크리스트

### 필수 (검수 통과 기준)
- [x] SDK 설치 및 설정 완료
- [x] granite.config.ts 올바른 설정
- [x] 모든 페이지에 헤더/내비게이션 적용
- [x] 로딩 상태 처리
- [x] 에러 상태 처리
- [x] HTTPS 통신 (Railway API)
- [x] 토스 로그인 연동

### TDS 관련 (비필수로 확인됨)
- [x] ~~TDS Provider 설정~~ → 불필요
- [x] ~~TDS 컴포넌트 사용~~ → 커스텀 컴포넌트 승인됨
- [x] ~~TDS 색상 시스템~~ → 커스텀 색상 승인됨

### 권장
- [x] 다크패턴 없음
- [x] 명확한 UX 라이팅
- [x] 접근성 고려 (aria-label 등)

---

## 5. 실행 명령어

```bash
# 개발 서버
npm run dev

# Granite 개발 서버 (샌드박스 테스트용)
npm run granite:dev

# .ait 빌드
npm run granite:build
```

---

## 6. 참고 문서

| 문서 | URL |
|------|-----|
| 앱인토스 개발자 문서 | https://developers-apps-in-toss.toss.im/ |
| 앱인토스 콘솔 | https://console.apps-in-toss.toss.im |
| 프로젝트 가이드 | `docs/APPS_IN_TOSS_GUIDE.md` |
| 샌드박스 테스트 | `SANDBOX_TEST_GUIDE.md` |

---

*최종 업데이트: 2026-01-06 - mTLS 연동 완료, 토스 로그인 버그 수정*
