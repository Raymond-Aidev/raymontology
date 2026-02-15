# INDEX-WEB (RaymondsIndex 독립 사이트)

> 경로: `raymondsindex-web/` | 배포: https://raymondsindex.konnect-ai.net | 완성도: 100%

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

## 페이지 구조 (9개)

| 경로 | 파일 | 설명 |
|------|------|------|
| `/` | `app/page.tsx` | 홈 (위험기업 TOP 10 + Sub-Index 탭 + M&A 취약기업) ⭐ |
| `/screener` | `app/screener/page.tsx` | 기업 스크리닝 (필터, 정렬, 페이징) |
| `/company/[id]` | `app/company/[id]/page.tsx` | 기업 상세 (레이더 차트, 지표 카드) |
| `/methodology` | `app/methodology/page.tsx` | 평가 방법론 설명 |
| `/ma-target` | `app/ma-target/page.tsx` | 적대적 M&A 스크리닝 ⭐ |
| `/login` | `app/login/page.tsx` | 로그인 |
| `/signup` | `app/signup/page.tsx` | 회원가입 |
| `/admin` | `app/admin/page.tsx` | 관리자 (superuser 전용, **ML 대시보드 탭 포함** ⭐) |

---

## 컴포넌트 구조 (31개)

### UI 컴포넌트 (`/components/ui/`) - 13개
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
| `collapsible.tsx` | 접기/펼치기 |

### 비즈니스 컴포넌트 - 19개
| 컴포넌트 | 설명 |
|----------|------|
| `grade-badge.tsx` | 9등급 배지 (A++ ~ C) |
| `score-display.tsx` | 점수 표시 |
| `grade-distribution.tsx` | 등급 분포 차트 |
| `sub-index-radar.tsx` | 4대 Sub-Index 레이더 차트 |
| `metric-card.tsx` | 지표 카드 |
| `kpi-card.tsx` | KPI 카드 |
| `risk-flags-panel.tsx` | 위험 신호 패널 |
| `company-search-bar.tsx` | 기업 검색 (자동완성) |
| `top-companies-table.tsx` | TOP 10 기업 테이블 |
| `risk-companies-table.tsx` | 위험기업 TOP 10 (2열 그리드) ⭐ |
| `sub-index-tabs.tsx` | Sub-Index별 위험기업 TOP 5 (4개 독립 카드, 2x2 그리드) ⭐ |
| `vulnerable-ma-cards.tsx` | 적대적 M&A 취약기업 카드 ⭐ |
| `stock-price-chart.tsx` | 주가 차트 |
| `market-badge.tsx` | 시장 배지 (KOSPI/KOSDAQ/KONEX/ETF) |
| `ai-analysis-section.tsx` | AI 분석 섹션 |
| `compare-bar.tsx` | 기업 비교 바 (하단 고정) ⭐ |
| `compare-modal.tsx` | 기업 비교 모달 ⭐ |
| `range-input.tsx` | 범위 필터 입력 (직접 입력 지원) ⭐ |
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
- [x] 홈페이지 개편 (위험기업 중심 대시보드) ⭐ (2026-02-02)
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
- [x] ~~다크 모드 지원~~ → **라이트 테마로 전환** (2026-02-09) ⭐
- [x] **적대적 M&A 스크리닝** ⭐ (2026-01 신규, 2026-02 필터 직접 입력 지원)
- [x] **기업 비교 기능** ⭐ (최대 4개 기업 비교)
- [x] **CSV 내보내기** ⭐ (스크리너 결과 다운로드)
- [x] **주가 차트** ⭐ (3년 추이)
- [x] **ML 관리 대시보드** ⭐ (2026-02-08 추가, 관리자 전용)

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

### RaymondsIndex API
| 엔드포인트 | 용도 |
|-----------|------|
| `/api/raymonds-index/ranking/list` | 인덱스 랭킹 목록 |
| `/api/raymonds-index/{company_id}` | 기업 상세 |
| `/api/raymonds-index/statistics/summary` | 통계 요약 |
| `/api/raymonds-index/search/companies` | 기업 검색 |

### 적대적 M&A API ⭐
| 엔드포인트 | 용도 |
|-----------|------|
| `/api/ma-target/ranking` | 적대적 M&A 랭킹 |
| `/api/ma-target/stats` | 적대적 M&A 통계 |
| `/api/ma-target/company/{id}` | 적대적 M&A 상세 |
| `/api/raymonds-index/vulnerable-ma/ranking` | M&A 취약기업 랭킹 (홈 위젯용) ⭐ |

### 주가 API
| 엔드포인트 | 용도 |
|-----------|------|
| `/api/stock-prices/company/{id}/chart` | 주가 차트 데이터 |
| `/api/stock-prices/status` | 주가 수집 현황 |

### 인증 API
| 엔드포인트 | 용도 |
|-----------|------|
| `/api/auth/login` | 로그인 |
| `/api/auth/register` | 회원가입 |

---

## lib 모듈 (8개)

| 모듈 | 설명 |
|------|------|
| `api.ts` | API 클라이언트 (fetch 래퍼) |
| `types.ts` | 타입 정의 (RaymondsIndex, MATarget, VulnerableMA 등) |
| `constants.ts` | 상수 (등급 색상, API URL 등) |
| `utils.ts` | 유틸리티 함수 |
| `auth.ts` | 인증 상태 관리 (Zustand) |
| `chart-theme.ts` | Recharts 테마 설정 |
| `compare-store.ts` | 기업 비교 상태 관리 (Zustand) ⭐ |
| `export-csv.ts` | CSV 내보내기 유틸리티 ⭐ |

---

## hooks 모듈 (5개)

| Hook | 파일 | 설명 |
|------|------|------|
| `useRanking` | `hooks/use-ranking.ts` | 전체 랭킹 조회 |
| `useTopRanking` | `hooks/use-ranking.ts` | TOP N 우수 기업 조회 |
| `useBottomRanking` | `hooks/use-ranking.ts` | TOP N 위험 기업 조회 (낮은 점수순) ⭐ |
| `useSubIndexRanking` | `hooks/use-ranking.ts` | Sub-Index별 랭킹 (CEI/RII/CGI/MAI) ⭐ |
| `useVulnerableMA` | `hooks/use-ranking.ts` | 적대적 M&A 취약기업 조회 ⭐ |

---

## 보안 설정

- HTTPS 강제 (HSTS)
- CSP (Content Security Policy) 헤더
- XSS 방지
- CORS 설정

---

## 적대적 M&A 등급 체계 (7등급) ⭐

| 등급 | 의미 | 색상 |
|------|------|------|
| A+ | 최우수 | #2563EB |
| A | 우수 | #3B82F6 |
| B+ | 양호 | #22C55E |
| B | 보통 | #84CC16 |
| C+ | 주의 | #EAB308 |
| C | 경고 | #F97316 |
| D | 위험 | #6B7280 |

### 적대적 M&A 필터 (CompactRangeInput) ⭐

| 필터 항목 | 범위 | Step | 직접 입력 |
|----------|------|------|----------|
| 시가총액 | 100억 ~ 10조 | 100억 | ✅ (억/조 단위 지원) |
| 현금성자산 | 0 ~ 5조 | 100억 | ✅ (억/조 단위 지원) |
| 현금/시총 비율 | 0 ~ 100% | 10% | ✅ |
| 매출 성장률 | -50 ~ 100% | 10% | ✅ |
| 유형자산 증가율 | -50 ~ 100% | 10% | ✅ |

**직접 입력 기능** (2026-02-03 추가):
- 값 표시 영역 클릭 시 편집 모드 전환
- 숫자 직접 입력 가능 (예: "500억", "1조", "50")
- 범위 벗어나는 값은 무효 처리 (원래 값 유지)
- Enter 키로 확정, Escape 키로 취소

---

---

## 홈페이지 레이아웃 (2026-02-02 개편) ⭐

**변경 내역**: 우수 기업 중심 → 위험 기업 중심 대시보드

```
┌─────────────────────────────────────────────────┐
│ KPI Cards (4열) - C등급 이하 기업 수 표시       │
├─────────────────────────┬───────────────────────┤
│ 위험기업 TOP 10 (2열)   │ M&A 취약기업 TOP 5    │
│ (컴팩트 그리드 카드)    │                       │
├────────────┬────────────┤ 등급 분포 차트        │
│ CEI TOP 5  │ RII TOP 5  │                       │
├────────────┼────────────┤ 빠른 탐색 링크        │
│ CGI TOP 5  │ MAI TOP 5  │                       │
└────────────┴────────────┴───────────────────────┘
```

| 영역 | 변경 전 | 변경 후 |
|------|---------|---------|
| 메인 테이블 | TOP 10 우수기업 | **위험기업 TOP 10** (2열 그리드) |
| Sub-Index | 탭 1개 (TOP 10) | **4개 독립 카드 2x2 그리드 (TOP 5)** |
| 사이드 패널 | 없음 | **적대적 M&A 취약기업 TOP 5** |
| KPI 카드 | A등급 이상 | **C등급 이하** (위험 기업 수) |

---

## ML 관리 대시보드 (관리자 전용) ⭐신규

`/admin` 페이지의 4번째 탭으로 추가 (2026-02-08).

### 탭 구조
```
관리자 페이지: [Users] [Database] [Quality] [ML Management ⭐]
```

### ML 탭 서브패널 (4개)
| 서브패널 | 설명 |
|---------|------|
| 모델 현황 | 활성 모델 지표 (AUC, Recall 등), 모델 버전 비교/전환 |
| 예측 분포 | 확률 히스토그램, 등급별 분포, 시장별 분포 |
| 피처 모니터링 | 32개 피처별 NULL 비율, 분포 통계, 건강 상태 |
| 학습 제어 | 하이퍼파라미터 수정, Risk Level 임계값 조정, 학습 실행 |

### 관련 파일
| 파일 | 역할 |
|------|------|
| `app/admin/page.tsx` | 관리자 페이지 (TabType에 'ml' 추가) |
| `app/admin/ml-tab.tsx` | ML 탭 컴포넌트 |
| `backend/app/routes/ml_admin.py` | ML 관리 API (9개 엔드포인트) |

---

*마지막 업데이트: 2026-02-15*
