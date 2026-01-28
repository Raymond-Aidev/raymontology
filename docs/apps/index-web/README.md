# INDEX-WEB (RaymondsIndex 독립 사이트)

> 경로: `raymondsindex-web/` | 배포: https://raymondsindex.konnect-ai.net | 완성도: 95%

---

## 개요

한국 상장기업의 자본배분효율성을 평가하는 RaymondsIndex 전용 사이트입니다.

---

## 기술 스택

| 카테고리 | 기술 | 버전 |
|----------|------|------|
| 프레임워크 | Next.js | 16.1.1 |
| UI 프레임워크 | React | 19.2.3 |
| 차트 | Recharts | 3.6.0 |
| UI 컴포넌트 | Radix UI | 최신 |
| 서버 상태 | TanStack Query | 5.90.12 |
| 클라이언트 상태 | Zustand | 5.0.9 |
| 스타일링 | Tailwind CSS | 4.0 |
| 아이콘 | Lucide React | 0.562.0 |

---

## 페이지 구조 (7개)

| 경로 | 파일 | 설명 |
|------|------|------|
| `/` | `app/page.tsx` | 홈 (Hero + TOP 10 + 등급분포) |
| `/screener` | `app/screener/page.tsx` | 기업 스크리닝 (필터, 정렬, 페이징) |
| `/company/[id]` | `app/company/[id]/page.tsx` | 기업 상세 (레이더 차트, 지표 카드) |
| `/methodology` | `app/methodology/page.tsx` | 평가 방법론 설명 |
| `/login` | `app/login/page.tsx` | 로그인 |
| `/signup` | `app/signup/page.tsx` | 회원가입 |
| `/admin` | `app/admin/page.tsx` | 관리자 (superuser 전용) |

---

## 컴포넌트 구조 (26개)

### UI 컴포넌트 (`/components/ui/`) - 11개
| 컴포넌트 | 설명 |
|----------|------|
| `button.tsx` | 버튼 |
| `card.tsx` | 카드 |
| `table.tsx` | 테이블 |
| `input.tsx` | 입력 필드 |
| `select.tsx` | 셀렉트 박스 |
| `badge.tsx` | 배지 |
| `dialog.tsx` | 다이얼로그 |
| `slider.tsx` | 슬라이더 |
| `checkbox.tsx` | 체크박스 |
| `tabs.tsx` | 탭 |
| `tooltip.tsx` | 툴팁 |
| `separator.tsx` | 구분선 |

### 비즈니스 컴포넌트 - 12개
| 컴포넌트 | 설명 |
|----------|------|
| `grade-badge.tsx` | 9등급 배지 (A++ ~ C) |
| `score-display.tsx` | 점수 표시 |
| `grade-distribution.tsx` | 등급 분포 차트 |
| `sub-index-radar.tsx` | 4대 Sub-Index 레이더 차트 |
| `metric-card.tsx` | 지표 카드 |
| `risk-flags-panel.tsx` | 위험 신호 패널 |
| `company-search-bar.tsx` | 기업 검색 (자동완성) |
| `top-companies-table.tsx` | TOP 10 기업 테이블 |
| `stock-price-chart.tsx` | 주가 차트 |
| `market-badge.tsx` | 시장 배지 (KOSPI/KOSDAQ/KONEX/ETF) |
| `ai-analysis-section.tsx` | AI 분석 섹션 |
| `providers.tsx` | 전역 Provider |

### 레이아웃 (`/components/layout/`) - 2개
| 컴포넌트 | 설명 |
|----------|------|
| `header.tsx` | 공통 헤더 |
| `footer.tsx` | 공통 푸터 |

---

## RaymondsIndex 9등급 체계

| 등급 | 점수 범위 | 색상 | 의미 |
|------|----------|------|------|
| A++ | 95+ | #1E40AF | 최우수 |
| A+ | 90-94 | #2563EB | 우수 |
| A | 85-89 | #3B82F6 | 양호 |
| A- | 80-84 | #60A5FA | 양호 |
| B+ | 70-79 | #22C55E | 보통 상위 |
| B | 60-69 | #84CC16 | 보통 |
| B- | 50-59 | #EAB308 | 보통 하위 |
| C+ | 40-49 | #F97316 | 주의 |
| C | <40 | #EF4444 | 경고 |

---

## 4대 Sub-Index

| Sub-Index | 약어 | 비중 | 평가 항목 |
|-----------|------|------|----------|
| 자본효율성 | CEI | 20% | ROE, ROA |
| 재투자강도 | RII | 35% | 투자괴리율, CAPEX 비율 |
| 성장건전성 | CGI | 25% | 이익잉여금 증가율 |
| 시장정렬도 | MAI | 20% | PBR 적정성 |

---

## 주요 기능

### 구현 완료
- [x] 홈페이지 (Hero + TOP 10 + 등급분포)
- [x] 스크리너 (필터, 정렬, 페이징)
- [x] 기업 상세 (레이더 차트, 지표 카드)
- [x] 평가 방법론 페이지
- [x] 기업 검색 (자동완성)
- [x] 회원가입/로그인
- [x] 관리자 페이지 (데이터 품질 모니터링)
- [x] HTTPS/SSL (HSTS, CSP 보안 헤더)
- [x] 지표 Tooltip 설명
- [x] 위험신호 패널
- [x] 시장 필터 (KOSPI/KOSDAQ/KONEX)
- [x] 다크 모드 지원

### 구현 예정
- [ ] 관심 기업 저장
- [ ] 알림 서비스

---

## 개발 명령어

```bash
cd raymondsindex-web

# 개발 서버
npm run dev

# 프로덕션 빌드
npm run build

# 프로덕션 서버
npm run start

# 린트
npm run lint
```

---

## 환경 변수

```env
NEXT_PUBLIC_API_URL=https://raymontology-production.up.railway.app/api
```

---

## API 연동

| 엔드포인트 | 용도 |
|-----------|------|
| `/api/raymonds-index` | 인덱스 데이터 |
| `/api/raymonds-index/screener` | 스크리너 데이터 |
| `/api/raymonds-index/top` | TOP N 기업 |
| `/api/raymonds-index/grade-distribution` | 등급 분포 |
| `/api/companies/{id}` | 기업 상세 |
| `/api/search/companies` | 기업 검색 |
| `/api/stock-prices` | 주가 데이터 |
| `/api/auth` | 인증 |

---

## 보안 설정

- HTTPS 강제 (HSTS)
- CSP (Content Security Policy) 헤더
- XSS 방지
- CORS 설정

---

*마지막 업데이트: 2026-01-23*
