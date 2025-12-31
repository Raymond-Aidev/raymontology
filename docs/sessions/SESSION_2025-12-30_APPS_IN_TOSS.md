# 세션 저장: 앱인토스 RaymondsRisk 프로젝트 초기 설정

> 저장 시간: 2025-12-30 18:45 KST

---

## 세션 개요

| 항목 | 내용 |
|------|------|
| **작업 목표** | RaymondsRisk 앱인토스 프로젝트 생성 및 샌드박스 테스트 준비 |
| **작업 결과** | ✅ 성공 - 프로젝트 생성 완료, 개발 서버 실행 중 |
| **다음 단계** | 샌드박스 앱에서 실제 테스트 진행 |

---

## 완료된 작업

### 1. 프로젝트 생성 ✅
- `raymondsrisk-app/` 폴더 생성
- Vite + React 19 + TypeScript 초기화
- 기본 패키지 설치 완료

### 2. 앱인토스 SDK 설치 ✅
- `@apps-in-toss/web-framework` v1.6.2 설치
- `@toss/tds-mobile` v2.2.0 설치 (--legacy-peer-deps)

### 3. 설정 파일 구성 ✅
- `granite.config.ts` 생성 및 설정
  - appName: `raymondsrisk`
  - primaryColor: `#E74C3C`
  - host: `192.168.100.24` (실기기 테스트용)
  - port: `5173`

### 4. 기본 페이지 구현 ✅
- `HomePage.tsx` - 홈 (검색 + 통계)
- `SearchPage.tsx` - 검색 결과
- `ReportPage.tsx` - 기업 리포트

### 5. API 클라이언트 설정 ✅
- `api/client.ts` - Axios 인스턴스, 인터셉터
- `api/company.ts` - 회사 검색/통계 API
- 프로덕션 API: `https://raymontology-production.up.railway.app`

### 6. 타입 정의 ✅
- `types/company.ts` - 회사, 리스크 레벨, 투자등급
- `types/report.ts` - 리포트, CB, 임원, 재무제표

### 7. 개발 서버 실행 ✅
- 외부 접속 허용 (`--host` 옵션)
- Network URL: `http://192.168.100.24:5173`
- HTTP 200 응답 확인

### 8. 문서 생성 ✅
- `APPS_IN_TOSS_PROJECT.md` - 프로젝트 관리 문서
- `SANDBOX_TEST_GUIDE.md` - 샌드박스 테스트 가이드

---

## 핵심 발견 사항

### 앱인토스 아키텍처
```
토스 앱 → 앱인토스 컨테이너 (WebView) → raymondsrisk-app (웹앱)
```
- **안드로이드 네이티브 앱 개발 불필요**
- WebView 기반이므로 React 웹앱만 개발하면 iOS/Android 모두 지원
- 기존 `android/` 폴더는 앱인토스와 무관한 별도 프로젝트

### TDS 필수 요건
- 비게임 WebView 앱은 **TDS (Toss Design System) 적용 필수**
- 검수 승인 기준에 포함됨
- 현재 inline 스타일 → TDS 컴포넌트로 교체 필요

### HTTP vs HTTPS
- **샌드박스**: HTTP 통신 허용 (ATS 예외)
- **프로덕션**: HTTPS만 지원

---

## 현재 개발 서버 상태

```
┌──────────────────────────────────────────────────┐
│   RaymondsRisk 개발 서버 실행 중                  │
│                                                  │
│   Local:   http://localhost:5173                 │
│   Network: http://192.168.100.24:5173            │
│                                                  │
│   샌드박스 스킴: intoss://raymondsrisk            │
└──────────────────────────────────────────────────┘
```

---

## 다음 세션 작업 예정

### 즉시 진행
1. [ ] 샌드박스 앱에서 `intoss://raymondsrisk` 접속 테스트
2. [ ] 연결 성공 확인 후 기능 검증

### 이후 작업
1. [ ] TDS 컴포넌트로 UI 교체 (검수 필수)
2. [ ] ReportPage 실제 API 연동
3. [ ] 앱 아이콘 설정
4. [ ] 에러 처리 및 로딩 상태 개선
5. [ ] 토스앱 QR 테스트
6. [ ] 검수 신청

---

## 프로젝트 파일 구조

```
raymontology/
├── raymondsrisk-app/              ← 앱인토스 프로젝트 (신규)
│   ├── APPS_IN_TOSS_PROJECT.md    ← 프로젝트 관리 문서
│   ├── SANDBOX_TEST_GUIDE.md      ← 샌드박스 가이드
│   ├── granite.config.ts          ← 앱인토스 설정
│   ├── .env                       ← 환경 변수
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── company.ts
│   │   ├── types/
│   │   │   ├── company.ts
│   │   │   └── report.ts
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── SearchPage.tsx
│   │   │   └── ReportPage.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── dist/                      ← 빌드 결과물
├── frontend/                       ← 기존 웹 (www.konnect-ai.net)
├── raymondsindex-web/             ← RaymondsIndex 독립 사이트
├── backend/                        ← FastAPI 백엔드 (공용)
└── docs/
    └── APPS_IN_TOSS_GUIDE.md      ← 앱인토스 개발 가이드
```

---

## 주요 명령어

```bash
# 프로젝트 폴더 이동
cd /Users/jaejoonpark/raymontology/raymondsrisk-app

# 개발 서버 실행 (외부 접속)
npm run dev -- --host

# 빌드
npm run build

# 앱인토스 빌드
npm run granite:build

# 로컬 IP 확인
ipconfig getifaddr en0
```

---

## 참고 문서

| 문서 | 경로/URL |
|------|----------|
| 프로젝트 관리 | `raymondsrisk-app/APPS_IN_TOSS_PROJECT.md` |
| 샌드박스 가이드 | `raymondsrisk-app/SANDBOX_TEST_GUIDE.md` |
| 앱인토스 가이드 | `docs/APPS_IN_TOSS_GUIDE.md` |
| 앱인토스 콘솔 | https://console.apps-in-toss.toss.im |
| TDS 문서 | https://tossmini-docs.toss.im/tds-mobile/ |

---

*세션 저장 완료: 2025-12-30 18:45 KST*
