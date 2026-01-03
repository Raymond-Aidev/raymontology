# Raymontology 프로젝트 - Claude Code 필수 규칙

## 세션 시작 시 `/sc:load` 실행하세요

---

## 상태: 데이터 보완 작업 완료 (2026-01-02)
전체 17개 테이블 데이터 적재 완료. **RaymondsIndex 계산 완료 (2,698건)**.
**RaymondsIndex 독립 사이트**: https://raymondsindex.konnect-ai.net 배포 완료.
**RaymondsRisk 앱인토스**: 토스 로그인 연동 완료, 샌드박스 테스트 진행 중.
**최근 업데이트**: 주의 필요 기업 API 개선, 임원 주의 표시 로직 구현 (2026-01-02)

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

## 서비스 및 도메인 구분 (중요!)

| 도메인 | 서비스 | 프로젝트 디렉토리 |
|--------|--------|------------------|
| **www.konnect-ai.net** | **RaymondsRisk** | `frontend/` |
| **raymondsindex.konnect-ai.net** | **RaymondsIndex** | `raymondsindex-web/` |

### 작업 시 주의사항
- `www.konnect-ai.net` 관련 작업 → `frontend/` 디렉토리 수정
- `raymondsindex.konnect-ai.net` 관련 작업 → `raymondsindex-web/` 디렉토리 수정
- **두 서비스를 혼동하지 말 것!**

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

## 현재 DB 상태 (2026-01-02 기준)

| 테이블 | 레코드 수 | 상태 |
|--------|----------|------|
| companies | 3,922 | ✅ |
| officers | 44,679 | ✅ |
| officer_positions | 64,265 | ✅ (중복 정리 완료) |
| disclosures | 213,304 | ✅ |
| convertible_bonds | 1,133 | ✅ (중복 정리 완료, 330건 제거) |
| cb_subscribers | 7,026 | ✅ (CB 정리에 따른 연쇄 정리) |
| financial_statements | 9,432 | ✅ |
| risk_signals | 1,412 | ✅ |
| risk_scores | 3,912 | ✅ |
| major_shareholders | 47,453 | ✅ |
| affiliates | 973 | ✅ |
| financial_details | 7,689 | ⚠️ 2025 Q3 파싱 필요 |
| **raymonds_index** | **2,698** | ✅ 계산 완료 |
| **stock_prices** | **127,324** | ✅ 신규 |
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

## 임원 주의 표시 기준 (그래프 UI)

| 표시 | 조건 | 색상 | 파일 |
|------|------|------|------|
| **붉은색 노드** | 상장사 경력 ≥ 3개 | `#EF4444` (red-500) | `ForceGraph.tsx:48-55` |
| **"주의" 배지** | 적자기업 경력 ≥ 1개 | `#F97316` (orange-500) | `ForceGraph.tsx:337-365` |

### 계산 로직 (`graph_fallback.py`)
- **상장사 경력**: `COUNT(DISTINCT company_id)` - 동일 회사 재임은 1회로 계산
- **적자기업**: `financial_statements`에서 최근 2년 `net_income < 0`인 회사
- **동명이인 방지**: `이름 + 출생년월` 조합으로 동일인 식별

---

## 주의 필요 기업 API

### 엔드포인트
```
GET /api/companies/high-risk
```

### 파라미터
| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `limit` | 6 | 결과 개수 (1-50) |
| `min_grade` | B | 최소 등급 (B, CCC, CC, C, D) |
| `has_cb` | true | CB 발행 여부 필터 |

### 동작 방식
- `risk_scores.investment_grade` 기준 필터링
- `ORDER BY RANDOM()` 으로 매번 다른 기업 표시
- 상장폐지 기업 제외 (`listing_status = 'LISTED'`)

관련 파일: `backend/app/api/endpoints/companies.py:363-451`

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

자본 배분 효율성 지수. 2,698개 기업 평가 완료 (v2.1).

| 등급 | 점수 범위 | 기업 수 |
|------|----------|--------|
| A- | 80-84 | 11 |
| B+ | 70-79 | 101 |
| B | 60-69 | 311 |
| B- | 50-59 | 917 |
| C+ | 40-49 | 1,213 |
| C | <40 | 145 |

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

### 구현 완료 기능 (2025-12-31)
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
| **데이터 품질 모니터링** | ✅ | 관리자 대시보드 (2025-12-31) |
| **관계도 전체화면 모드** | ✅ | ESC/빈영역 클릭 복귀 (2025-12-31) |

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

## 데이터 수집 규칙 (중요!)

### 핵심 원칙: 로컬 다운로드 → 파싱 (DART API 직접 호출 X)

모든 DART 데이터는 **로컬에 먼저 다운로드 후 파싱**합니다.
DART API를 직접 호출하는 스크립트 사용 금지.

### 로컬 데이터 위치
| 데이터 | 경로 | 용도 |
|--------|------|------|
| **사업보고서 (연간)** | `data/dart/batch_*` | 2022-2024년 연간 재무 데이터 |
| **3분기보고서 (2025)** | `data/q3_reports_2025/` | 2025년 3분기 재무 데이터 |
| **CB 공시 JSON** | `data/cb_disclosures_by_company_full.json` | 전환사채 정보 |

### 파싱 스크립트 매핑
| 데이터 | 올바른 스크립트 | 잘못된 스크립트 (사용 금지) |
|--------|----------------|---------------------------|
| **financial_details (2022-2024)** | `parse_local_financial_details.py` | ~~`collect_financial_details.py`~~ |
| **financial_details (2025 Q3)** | `parse_q3_reports_2025.py` | - |
| **financial_details 재파싱** | `reparse_financial_details_v2.py` | - |
| **raymonds_index** | `calculate_raymonds_index.py` | - |

### 수집 순서
1. `parse_local_financial_details.py` → 2022-2024년 연간 데이터
2. `parse_q3_reports_2025.py` → 2025년 3분기 데이터
3. `calculate_raymonds_index.py` → RaymondsIndex 계산

### 재파싱 (데이터 수정 필요시)
```bash
cd backend
source .venv/bin/activate
DATABASE_URL="postgresql://..." python3 scripts/reparse_financial_details_v2.py --year 2024
```

### 사용 금지 스크립트
```
금지: collect_financial_details.py (DART API 직접 호출)
금지: collect_financial_statements.py (DART API 직접 호출)
```

---

## 파서 v2.0 (parse_local_financial_details.py)

### 핵심 개선 (2026-01-02)
기존 파서가 재무상태표 섹션만 추출하여 손익계산서/현금흐름표 데이터가 누락되거나 단위가 잘못 적용되는 문제 해결

| 항목 | v1.0 (기존) | v2.0 (개선) |
|------|------------|------------|
| 섹션 추출 | 재무상태표만 | 재무상태표 + 손익계산서 + 현금흐름표 |
| 단위 감지 | 문서 전체에서 첫 번째 | 각 섹션별 독립 감지 |
| XML 선택 | 첫 번째 XML | 사업보고서(11011) 우선 |
| 기본 단위 | 천원 | 원 |

### 주요 함수
- `extract_xml_content()`: ZIP에서 사업보고서(11011) 우선 추출
- `_extract_values_from_all_statements()`: 각 재무제표 섹션 독립 파싱
- `_detect_unit_from_content()`: 섹션 내용에서 단위 감지

### 재파싱 스크립트 (`reparse_financial_details_v2.py`)
```bash
# 2024년 데이터 재파싱
python scripts/reparse_financial_details_v2.py --year 2024

# 샘플 테스트
python scripts/reparse_financial_details_v2.py --sample 10 --dry-run

# 옵션
--year 2024    # 특정 연도만
--sample 50    # 샘플 개수
--dry-run      # 실제 DB 업데이트 없이 테스트
```

### data_source 구분
- `LOCAL_DART`: 기존 파서로 파싱된 데이터
- `LOCAL_DART_V2`: v2.0 파서로 재파싱된 데이터
- `LOCAL_Q3_2025`: Q3 보고서에서 파싱된 데이터

---

## 실행 금지 스크립트

| 스크립트 | 위험 |
|---------|------|
| `sync_neo4j_to_postgres.py` | PostgreSQL TRUNCATE |
| `init_database.py` | DROP TABLE |
| `db_migrate.py --action=reset` | drop_all |

**위 스크립트들은 `scripts/_deprecated/`로 이동됨**

---

## Railway 배포 트러블슈팅

### 캐시 문제로 새 코드가 반영되지 않을 때
1. Railway Variables 탭에서 `NO_CACHE=1` 환경 변수 추가
2. 배포 완료 후 해당 변수 **제거** (빌드 속도 복원)

### FastAPI 라우트 순서 주의
- 동적 라우트 (`/{company_id}`) **앞에** 정적 라우트 (`/high-risk`) 배치
- 순서 잘못되면 404 오류 발생 (동적 라우트가 먼저 매칭됨)
