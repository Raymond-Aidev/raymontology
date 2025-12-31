# RaymondsRisk 앱인토스 프로젝트 관리

> 최종 업데이트: 2025-12-30

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **프로젝트명** | RaymondsRisk (관계형 리스크 분석) |
| **앱 이름 (appName)** | `raymondsrisk` |
| **앱 스킴** | `intoss://raymondsrisk` |
| **개발 방식** | WebView (Vite + React + TypeScript) |
| **프로젝트 경로** | `/raymontology/raymondsrisk-app/` |

---

## 2. 기술 스택

| 구분 | 기술 | 버전 |
|------|------|------|
| 프레임워크 | React | 19.2.0 |
| 빌드 도구 | Vite | 7.2.4 |
| 언어 | TypeScript | 5.9.3 |
| 앱인토스 SDK | @apps-in-toss/web-framework | 1.6.2 |
| 디자인 시스템 | @toss/tds-mobile | 2.2.0 |
| 상태 관리 | Zustand | 5.0.9 |
| 서버 상태 | @tanstack/react-query | 5.90.15 |
| HTTP 클라이언트 | Axios | 1.13.2 |
| 라우팅 | react-router-dom | 7.11.0 |

---

## 3. 개발 현황

### 완료된 작업 ✅

| 작업 | 상태 | 날짜 |
|------|:----:|------|
| 프로젝트 폴더 생성 | ✅ | 2025-12-30 |
| Vite + React + TypeScript 초기화 | ✅ | 2025-12-30 |
| @apps-in-toss/web-framework 설치 | ✅ | 2025-12-30 |
| granite.config.ts 설정 | ✅ | 2025-12-30 |
| @toss/tds-mobile 설치 | ✅ | 2025-12-30 |
| 기본 페이지 구현 (Home, Search, Report) | ✅ | 2025-12-30 |
| API 클라이언트 설정 | ✅ | 2025-12-30 |
| 타입 정의 (company, report) | ✅ | 2025-12-30 |
| 빌드 성공 확인 | ✅ | 2025-12-30 |
| 개발 서버 실행 (외부 접속 가능) | ✅ | 2025-12-30 |

### 진행 중인 작업 🔄

| 작업 | 상태 | 비고 |
|------|:----:|------|
| 샌드박스 테스트 | 🔄 | 개발 서버 실행 완료, 샌드박스 앱 접속 대기 |

### 예정된 작업 📋

| 작업 | 우선순위 | 비고 |
|------|:--------:|------|
| TDS 컴포넌트로 UI 교체 | 높음 | 검수 필수 요건 |
| 실제 API 연동 (Report 페이지) | 높음 | |
| 앱 아이콘 설정 | 중간 | granite.config.ts |
| 에러 처리 및 로딩 상태 개선 | 중간 | |
| 토스 로그인 연동 | 낮음 | 선택 사항 |

---

## 4. 프로젝트 구조

```
raymondsrisk-app/
├── granite.config.ts       # 앱인토스 설정
├── package.json
├── .env                    # 환경 변수
├── src/
│   ├── App.tsx             # 라우팅 설정
│   ├── main.tsx            # 엔트리 포인트
│   ├── index.css           # 글로벌 스타일
│   ├── api/
│   │   ├── client.ts       # Axios 설정
│   │   └── company.ts      # 회사 API
│   ├── types/
│   │   ├── company.ts      # 회사 타입
│   │   └── report.ts       # 리포트 타입
│   ├── pages/
│   │   ├── HomePage.tsx    # 홈 (검색 + 통계)
│   │   ├── SearchPage.tsx  # 검색 결과
│   │   └── ReportPage.tsx  # 기업 리포트
│   ├── components/         # (예정)
│   ├── hooks/              # (예정)
│   ├── store/              # (예정)
│   └── utils/              # (예정)
└── dist/                   # 빌드 결과물
```

---

## 5. 설정 파일

### granite.config.ts
```typescript
import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'raymondsrisk',
  brand: {
    displayName: 'RaymondsRisk',
    primaryColor: '#E74C3C',
    icon: '',  // TODO: 앱 아이콘 URL 설정
  },
  web: {
    host: '192.168.100.24',  // 로컬 IP (변경 필요)
    port: 5173,
    commands: {
      dev: 'vite --host',
      build: 'vite build',
    },
  },
  webViewProps: {
    type: 'partner',
  },
  permissions: [],
});
```

### .env
```
VITE_API_URL=https://raymontology-production.up.railway.app
```

---

## 6. 실행 명령어

```bash
# 개발 서버 (로컬)
npm run dev

# 개발 서버 (외부 접속 허용)
npm run dev -- --host

# 앱인토스 개발 모드
npm run granite:dev

# 빌드
npm run build

# 앱인토스 빌드 (배포용)
npm run granite:build
```

---

## 7. 개발 서버 정보

| 항목 | 값 |
|------|-----|
| Local URL | http://localhost:5173 |
| Network URL | http://192.168.100.24:5173 |
| 샌드박스 스킴 | intoss://raymondsrisk |

---

## 8. 백엔드 API

| 환경 | URL |
|------|-----|
| 프로덕션 | https://raymontology-production.up.railway.app |
| 로컬 | http://localhost:8000 |

### 주요 API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| GET /api/companies/search | 회사 검색 |
| GET /api/companies/stats | 플랫폼 통계 |
| GET /api/companies/{id} | 회사 상세 |
| GET /health | API 상태 확인 |

---

## 9. 배포 체크리스트

### 샌드박스 테스트 전
- [x] 앱인토스 SDK 설치
- [x] granite.config.ts 설정
- [x] TDS 패키지 설치
- [x] 개발 서버 외부 접속 가능
- [ ] 샌드박스 앱에서 테스트 완료

### 검수 신청 전
- [ ] TDS 컴포넌트 적용 (필수)
- [ ] 앱 아이콘 설정
- [ ] 에러 처리 구현
- [ ] 로딩 상태 구현
- [ ] HTTPS 통신 확인

### 출시 전
- [ ] 토스앱에서 QR 테스트
- [ ] 검수 피드백 반영
- [ ] 최종 빌드 업로드

---

## 10. 참고 문서

| 문서 | 경로/URL |
|------|----------|
| 앱인토스 개발 가이드 | `/docs/APPS_IN_TOSS_GUIDE.md` |
| 샌드박스 테스트 가이드 | `./SANDBOX_TEST_GUIDE.md` |
| TDS 문서 | https://tossmini-docs.toss.im/tds-mobile/ |
| 앱인토스 콘솔 | https://console.apps-in-toss.toss.im |

---

## 11. 이슈 및 메모

### 알려진 이슈
- `@toss/tds-mobile`이 React 19와 peer dependency 충돌 → `--legacy-peer-deps`로 설치

### 메모
- 앱인토스는 WebView 기반이므로 네이티브 앱 개발 불필요
- 기존 `android/` 폴더는 앱인토스와 무관 (별도 프로젝트)
- 샌드박스에서 HTTP 허용, 프로덕션에서는 HTTPS만 지원

---

*이 문서는 개발 진행에 따라 업데이트됩니다.*
