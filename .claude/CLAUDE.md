# Raymontology 프로젝트 - Claude Code 필수 규칙

## 세션 시작 시 `/sc:load` 실행하세요

---

## 상태: 서비스 운영 중 (2025-12-28)
전체 17개 테이블 데이터 적재 완료. RaymondsIndex 시스템 운영 중.
**RaymondsIndex 독립 사이트**: https://raymondsindex.konnect-ai.net 배포 완료.
**최근 업데이트**: 투자괴리율 v2 계산 로직 수정, HTTPS 보안 헤더 추가 (2025-12-28)

---

## 핵심 참조 문서 (필수 확인)

| 문서 | 용도 | 경로 |
|------|------|------|
| **프로젝트 설정** | **구현 현황 및 환경 설정** | **`PROJECT_SETUP.md`** |
| 환경 변수 | 프로덕션 DB 접속정보 | `.env.production` |
| 스키마 레지스트리 | 모든 테이블명/컬럼명 참조 | `scripts/SCHEMA_REGISTRY.md` |
| 표준 작업 프로세스 | 모든 DB 작업 체크리스트 | `scripts/STANDARD_PROCESS.md` |
| 파싱 상태 | 상세 파싱 진행 상황 | `scripts/PARSING_STATUS.md` |
| **앱인토스 가이드** | **토스 앱인앱 연동 개발** | **`docs/APPS_IN_TOSS_GUIDE.md`** |
| **RaymondsIndex 화면기획** | **독립 사이트 UI/UX 설계** | **`docs/RAYMONDSINDEX_UI_SPEC_v2.md`** |
| **RaymondsIndex 개발계획** | **독립 사이트 개발 일정** | **`docs/RAYMONDSINDEX_DEVELOPMENT_PLAN.md`** |

---

## 앱인토스(Apps in Toss) 개발 규칙

### 서비스 범위 (중요!)
**앱인토스는 RaymondsRisk 서비스 전용입니다.**

| 서비스 | 앱인토스 포함 |
|--------|-------------|
| **RaymondsRisk** | ✅ 포함 |
| Raymontology | ❌ 미포함 |
| RaymondsIndex | ❌ 미포함 |

- 앱 이름: `raymondsrisk`
- 스킴: `intoss://raymondsrisk`

### 앱인토스 관련 작업 시 필수 확인
```
앱인토스 관련 개발/수정 작업 전 반드시 docs/APPS_IN_TOSS_GUIDE.md 참조
```

### 앱인토스란?
- 토스 앱 내에서 서비스를 앱인앱 형태로 제공하는 플랫폼
- 3,000만 토스 유저에게 서비스 노출 가능
- WebView/React Native 기반 SDK 제공

### 공식 문서
- 개발자 문서: https://developers-apps-in-toss.toss.im/
- 홈페이지: https://apps-in-toss.toss.im/

---

## 테이블명 규칙 (필수)

테이블명은 반드시 `scripts/SCHEMA_REGISTRY.md` 참조 후 사용. 테이블명 추측 금지.

| 틀린 이름 | 올바른 이름 |
|----------|------------|
| company | **companies** |
| officer | **officers** |
| position | **officer_positions** |
| cb | **convertible_bonds** |
| subscriber | **cb_subscribers** |

---

## 표준 작업 프로세스 (필수)

**모든 DB 작업은 `scripts/STANDARD_PROCESS.md` 체크리스트 준수**

---

## 절대 금지 사항

### 1. 백그라운드 실행 금지
```
금지: python script.py &
금지: python script.py 2>&1 &
필수: python script.py (포그라운드에서 완료까지 대기)
```

### 2. "시작했습니다" 보고 금지
```
금지: "파싱을 시작했습니다"
금지: "스크립트를 실행했습니다"
금지: "백그라운드에서 실행 중입니다"
```

### 3. 검증 없는 완료 보고 금지
```
금지: 스크립트 실행만 하고 "완료"
금지: DB COUNT 확인 없이 성공 주장
```

---

## 현재 DB 상태 (2025-12-28 기준)

| 테이블 | 레코드 수 | 상태 |
|--------|----------|------|
| companies | 3,922 | ✅ |
| officers | 44,679 | ✅ |
| officer_positions | 64,265 | ✅ |
| disclosures | 213,304 | ✅ |
| convertible_bonds | 1,463 | ✅ |
| cb_subscribers | 7,490 | ✅ |
| financial_statements | 9,432 | ✅ |
| risk_signals | 1,412 | ✅ |
| risk_scores | 3,912 | ✅ |
| major_shareholders | 47,453 | ✅ |
| affiliates | 973 | ✅ |
| **financial_details** | **10,314** | ✅ |
| **raymonds_index** | **7,646** (2,695개 기업) | ✅ |
| user_query_usage | - | ✅ |
| page_contents | - | ✅ |

---

## 임원 API 규칙

임원 조회는 `officer_positions` 테이블 사용 (`officers.current_company_id`는 대부분 NULL)

```python
# 올바른 방법
query = (
    select(Officer, OfficerPosition.position)
    .join(OfficerPosition, Officer.id == OfficerPosition.officer_id)
    .where(OfficerPosition.company_id == company_id)
    .where(OfficerPosition.is_current == True)
)
```

Neo4j 미설정 시 `graph.py`가 자동으로 PostgreSQL fallback 사용

---

## 구독 시스템

| 이용권 | 가격 | 월 조회 제한 |
|--------|------|-------------|
| Free | 무료 | 5건 |
| Light | 3,000원/월 | 30건 |
| Max | 30,000원/월 | 무제한 |

관련: `backend/app/services/usage_service.py`, `backend/app/routes/subscription.py`

---

## RaymondsIndex 시스템

자본 배분 효율성 지수. 4,951개 기업 평가 완료.

| 등급 | 점수 범위 | 기업 수 |
|------|----------|--------|
| A | 80+ | 0 |
| B | 60-79 | 88 |
| C | 40-59 | 1,187 |
| D | 20-39 | 2,595 |
| F | <20 | 1,081 |

관련 파일:
- `backend/app/models/financial_details.py`
- `backend/app/models/raymonds_index.py`
- `backend/app/services/raymonds_index_calculator.py`
- `frontend/src/pages/RaymondsIndexRankingPage.tsx`

---

## RaymondsIndex 독립 사이트 (배포 완료 ✅)

### 프로덕션 URL
- **사이트**: https://raymondsindex.konnect-ai.net
- **백엔드 API**: https://raymontology-production.up.railway.app/api

### 프로젝트 정보
- **프로젝트 경로**: `raymondsindex-web/` (별도 디렉토리)
- **기술 스택**: Next.js 14+, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **인증**: Zustand 기반 (JWT 토큰)
- **배포**: Railway

### 구현 완료 기능 (2025-12-28)
| 기능 | 상태 | 비고 |
|------|------|------|
| 홈페이지 (Hero + TOP 10 + 등급분포) | ✅ | |
| 스크리너 (필터, 정렬, 페이징) | ✅ | |
| 기업 상세 (레이더 차트, 지표 카드) | ✅ | |
| 평가 방법론 | ✅ | |
| 기업 검색 (자동완성) | ✅ | `/search/companies` API 사용 |
| 회원가입/로그인 | ✅ | 이용약관 모달 포함 |
| 관리자 페이지 | ✅ | superuser 전용 |
| HTTPS/SSL | ✅ | HSTS, CSP 보안 헤더 포함 |
| 지표 Tooltip 설명 | ✅ | Sub-Index, 핵심 지표 '?' 버튼 |
| 위험신호 패널 개선 | ✅ | 정상 상태 UI, 상태별 설명 |
| 투자괴리율 v2 계산 | ✅ | 재무상태표 기준 CAPEX |

### 9등급 체계
| 등급 | 점수 범위 | 색상 |
|------|----------|------|
| A++ | 95+ | #1E40AF |
| A+ | 90-94 | #2563EB |
| A | 85-89 | #3B82F6 |
| A- | 80-84 | #60A5FA |
| B+ | 70-79 | #22C55E |
| B | 60-69 | #84CC16 |
| B- | 50-59 | #EAB308 |
| C+ | 40-49 | #F97316 |
| C | <40 | #EF4444 |

### 페이지 구조
- `/` - 홈 (Hero + TOP 10 + 등급분포)
- `/screener` - 기업 스크리닝
- `/company/[id]` - 기업 상세
- `/methodology` - 평가 방법론
- `/login` - 로그인
- `/signup` - 회원가입
- `/admin` - 관리자 (superuser 전용)

---

## DB 접속 정보

```bash
# 로컬 (개발)
PGPASSWORD=dev_password psql -h localhost -U postgres -d raymontology_dev

# 프로덕션 (Railway)
PGPASSWORD=ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR psql -h hopper.proxy.rlwy.net -p 41316 -U postgres -d railway

# API URL
https://raymontology-production.up.railway.app
```

---

## 원시 데이터 위치

- **DART 공시**: `backend/data/dart/` (9.2GB, 228,395 ZIP)
- **Q3 2025 보고서**: `backend/data/q3_reports_2025/` (2,671 ZIP)
- **CB 공시 JSON**: `backend/data/cb_disclosures_by_company_full.json`

---

## 아키텍처 규칙

```
원시 파일 (DART) → PostgreSQL (마스터) → Neo4j (파생)
                        ↑
                   절대 삭제 금지
```

---

## 실행 금지 스크립트

| 스크립트 | 위험 |
|---------|------|
| `sync_neo4j_to_postgres.py` | PostgreSQL TRUNCATE |
| `init_database.py` | DROP TABLE |
| `db_migrate.py --action=reset` | drop_all |

**위 스크립트들은 `scripts/_deprecated/`로 이동됨**
