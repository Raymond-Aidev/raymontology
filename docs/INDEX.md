# Raymontology 문서 허브

> 실제 구현 현황을 반영한 모듈형 문서 체계 (v1.0, 2026-01-23)

---

## 프로젝트 개요

**Raymontology**는 한국 상장기업의 리스크를 관계망 기반으로 분석하는 플랫폼입니다.

| 서비스 | 설명 | 상태 |
|--------|------|------|
| **RaymondsRisk** | 임원 관계망 + 리스크 신호 분석 | 프로덕션 |
| **RaymondsIndex** | 자본배분효율성 지수 평가 | 프로덕션 |

---

## 앱별 빠른 참조

| 앱 | 경로 | 기술 스택 | 배포 URL | 문서 |
|----|------|-----------|----------|------|
| **RISK-WEB** | `frontend/` | Vite + React 18 + D3.js | www.konnect-ai.net | [README](apps/risk-web/README.md) |
| **INDEX-WEB** | `raymondsindex-web/` | Next.js 16 + React 19 | raymondsindex.konnect-ai.net | [README](apps/index-web/README.md) |
| **RISK-APP** | `raymondsrisk-app/` | Vite + React 18 + Toss SDK | 토스 앱인앱 | [README](apps/risk-app/README.md) |
| **BACKEND** | `backend/` | FastAPI + PostgreSQL + Neo4j | Railway API | [README](apps/backend/README.md) |

---

## 문서 구조

```
docs/
├── INDEX.md                          ← 현재 문서
│
├── product/                          ← 제품 기획
│   └── PRD_Overview.md              ← 제품 비전 및 개요
│
├── apps/                             ← 앱별 구현 문서
│   ├── risk-web/README.md           ← [RISK-WEB] 프론트엔드
│   ├── index-web/README.md          ← [INDEX-WEB] 인덱스 사이트
│   ├── risk-app/README.md           ← [RISK-APP] 토스 앱
│   └── backend/README.md            ← [BACKEND] API 서버
│
├── technical/                        ← 기술 명세
│   ├── SRD_Architecture.md          ← 시스템 아키텍처
│   └── SRD_Database.md              ← DB 스키마
│
└── data/                             ← 데이터 현황
    └── DATA_STATUS.md               ← 단일 진실 공급원
```

---

## 핵심 지표 (2026-01-23 기준)

| 지표 | 값 | 상세 |
|------|-----|------|
| **관리 기업 수** | 3,109개 | LISTED 3,021 + ETF 88 |
| **임원 데이터** | 47,444건 | |
| **RaymondsIndex** | 5,257건 | v2.1 계산 완료 |
| **주가 데이터** | 126,506건 | |

> 상세 현황: [DATA_STATUS.md](data/DATA_STATUS.md)

---

## 기존 참조 문서

기존 문서들은 점진적으로 새 구조로 통합 예정입니다.

### 제품 기획
- [PRD.md](PRD.md) - 프론트엔드 화면 기획서 (v2.1)
- [PRD_RaymondsRisk_v4.0.md](PRD_RaymondsRisk_v4.0.md) - 백엔드 구현 명세 (v4.8)

### 앱인토스 관련
- [APPS_IN_TOSS_GUIDE.md](APPS_IN_TOSS_GUIDE.md) - 토스 연동 가이드 (통합본)
- [APPS_IN_TOSS_LOGIN_GUIDE.md](APPS_IN_TOSS_LOGIN_GUIDE.md) - 로그인 연동
- [APPS_IN_TOSS_API_GUIDE.md](APPS_IN_TOSS_API_GUIDE.md) - SDK API

### RaymondsIndex 관련
- [RAYMONDSINDEX_UI_SPEC_v2.md](RAYMONDSINDEX_UI_SPEC_v2.md) - UI 상세 기획
- [RAYMONDSINDEX_DEVELOPMENT_PLAN.md](RAYMONDSINDEX_DEVELOPMENT_PLAN.md) - 개발 계획
- [RAYMONDS_INDEX_v3_DESIGN.md](RAYMONDS_INDEX_v3_DESIGN.md) - v3 설계

### 기술 문서
- [DATA_PIPELINE_IMPROVEMENT_PLAN.md](DATA_PIPELINE_IMPROVEMENT_PLAN.md) - 파이프라인 자동화
- [FRONTEND_SPECIFICATION.md](FRONTEND_SPECIFICATION.md) - 프론트엔드 명세
- [FINANCIAL_RATIOS_IMPLEMENTATION_PLAN.md](FINANCIAL_RATIOS_IMPLEMENTATION_PLAN.md) - 재무비율 구현

---

## 작업 지시 태그 (Claude Code)

작업 요청 시 프로젝트 태그를 명시하여 혼동을 방지합니다.

| 태그 | 대상 폴더 | 예시 |
|------|----------|------|
| `[RISK-WEB]` | `frontend/` | 기업 상세 화면 수정 |
| `[INDEX-WEB]` | `raymondsindex-web/` | 스크리너 필터 추가 |
| `[RISK-APP]` | `raymondsrisk-app/` | 토스 로그인 연동 |
| `[BACKEND]` | `backend/` | API 엔드포인트 추가 |

---

## 관련 링크

- **프로덕션 사이트**: https://www.konnect-ai.net
- **인덱스 사이트**: https://raymondsindex.konnect-ai.net
- **API 서버**: https://raymontology-production.up.railway.app
- **GitHub**: (비공개)

---

*마지막 업데이트: 2026-01-23*
