# Raymontology 프로젝트 - Claude Code 필수 규칙

## 세션 시작 시 `/sc:load` 실행하세요

세션 시작 시 `PROJECT_SETUP.md`를 참조하여 현재 구현 상태를 확인합니다.

---

## 상태: 서비스 운영 중 (2025-12-25)
전체 15개 테이블 데이터 적재 완료. 프론트엔드/백엔드 연동 정상.

### 최근 수정 (2025-12-25)
- **RaymondsIndex 시스템 구현 중**: 자본 배분 효율성 지수
- **financial_details 테이블 추가**: 상세 재무 데이터 (유동/비유동 자산·부채)
- **raymonds_index 테이블 추가**: 지수 계산 결과 저장
- **구독 시스템 구현**: Light (3,000원/월, 30건 조회), Max (30,000원/월, 무제한)
- **조회 제한 시스템**: `user_query_usage` 테이블로 월별 사용량 추적
- **콘텐츠 관리 시스템**: 어드민에서 AboutPage 텍스트/이미지 편집 가능
- **page_contents 테이블**: 페이지별 콘텐츠 동적 관리

### 이전 수정 (2025-12-24)
- **임원 API 리팩토링**: `officer_positions` 테이블 기반으로 변경
- **중복 데이터 정리**: 243,398건 삭제 → 64,265건
- **OfficerPosition 모델 추가**: `backend/app/models/officer_positions.py`
- **PostgreSQL fallback**: Neo4j 없을 때 자동 대체

### 이전 수정 (2025-12-17)
- 임원-회사 매칭 데이터 정제: 7,277건 삭제
- 원본 공시와 비교 검증 스크립트: `scripts/verify_officer_company_match.py`

### 이전 수정 (2025-12-16)
- 스키마 레지스트리 도입: `scripts/SCHEMA_REGISTRY.md`
- 표준 작업 프로세스 도입: `scripts/STANDARD_PROCESS.md`
- 테이블명 검증 유틸리티: `scripts/utils/schema_validator.py`

## 과거 경고: 반복된 실패 이력 (개선 중)
- 완료 보고 후 데이터 없음 반복 발생
- 테이블명 혼동으로 데이터 못 찾는 문제 발생
- 중복 제거 후 실제 데이터 삭제 문제 발생
- **해결책**: 아래 규칙 및 표준 프로세스 준수 필수

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

---

## 앱인토스(Apps in Toss) 개발 규칙

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

### 테이블명은 반드시 SCHEMA_REGISTRY.md 참조 후 사용

```
금지: 테이블명 추측 또는 직접 타이핑
필수: SCHEMA_REGISTRY.md에서 복사-붙여넣기
```

### 자주 혼동되는 테이블명

| 틀린 이름 | 올바른 이름 |
|----------|------------|
| company | **companies** |
| officer | **officers** |
| position | **officer_positions** |
| cb | **convertible_bonds** |
| subscriber | **cb_subscribers** |

### 프로그래밍 시 검증

```python
from scripts.utils.schema_validator import validate_table_name

# 테이블명 검증 (오류 시 ValueError 발생)
table = validate_table_name("companies")  # OK
table = validate_table_name("company")    # ValueError!
```

---

## 표준 작업 프로세스 (필수)

모든 DB 작업은 `scripts/STANDARD_PROCESS.md` 체크리스트 준수:

```
[작업 전]
1. DB 현재 상태 COUNT 확인 및 기록
2. SCHEMA_REGISTRY.md에서 테이블명 확인
3. 작업 내용 및 예상 결과 기록

[작업 중]
4. 포그라운드 실행 (백그라운드 금지)
5. 에러 메시지 전체 확인
6. 부분 성공 기록

[작업 후]
7. DB 상태 재확인 (동일 COUNT 쿼리)
8. 증감분 계산: "X건 → Y건 (+Z건)"
9. PARSING_STATUS.md 업데이트
```

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

## 필수 작업 프로세스

### 모든 DB 작업 시 반드시:

1. **작업 전 COUNT 확인**
```sql
SELECT 'officers' as tbl, COUNT(*) FROM officers
UNION ALL SELECT 'disclosures', COUNT(*) FROM disclosures
...
```

2. **포그라운드 실행** (완료까지 대기)

3. **에러 확인** (출력 전체 확인)

4. **작업 후 COUNT 확인**

5. **증가분 보고** (필수 형식):
```
officers: 0건 → 1,234건 (+1,234건)
disclosures: 0건 → 5,678건 (+5,678건)
```

---

## 현재 DB 상태 (2025-12-25 기준)

| 테이블 | 레코드 수 | 상태 | 비고 |
|--------|----------|------|------|
| companies | 3,922 | ✅ 완료 | |
| officers | 44,679 | ✅ 완료 | |
| officer_positions | 64,265 | ✅ 완료 | **중복 243,398건 삭제됨** |
| disclosures | 213,304 | ✅ 완료 | |
| convertible_bonds | 1,463 | ✅ 완료 | |
| cb_subscribers | 7,490 | ✅ 완료 | |
| financial_statements | 9,432 | ✅ 완료 | |
| risk_signals | 1,412 | ✅ 완료 | |
| risk_scores | 3,912 | ✅ 완료 | |
| major_shareholders | 95,191 | ✅ 완료 | |
| affiliates | 973 | ✅ 완료 | |
| user_query_usage | - | ✅ 완료 | 조회 제한 추적 |
| page_contents | - | ✅ 완료 | 페이지 콘텐츠 관리 |
| financial_details | 0 | 🔄 스키마완료 | RaymondsIndex용 상세 재무 |
| raymonds_index | 0 | 🔄 스키마완료 | 지수 계산 결과 |

---

## 임원 API 규칙 (2025-12-24 확정)

### 임원 조회는 officer_positions 테이블 사용

```
주의: officers.current_company_id는 대부분 NULL (8건만 존재)
실제 임원-회사 관계는 officer_positions 테이블에 저장됨
```

```python
# 올바른 방법 (officer_positions 사용)
query = (
    select(Officer, OfficerPosition.position)
    .join(OfficerPosition, Officer.id == OfficerPosition.officer_id)
    .where(OfficerPosition.company_id == company_id)
    .where(OfficerPosition.is_current == True)
)

# 잘못된 방법 (current_company_id 사용 - 대부분 NULL)
query = select(Officer).where(Officer.current_company_id == company_id)
```

### Neo4j 미설정 시 PostgreSQL fallback

`graph.py`의 `/officer/{id}/career` 엔드포인트는 Neo4j 없으면 자동으로 PostgreSQL 사용

---

## 구독 시스템 (2025-12-25 추가)

### 이용권 종류

| 이용권 | 가격 | 월 조회 제한 | 설명 |
|--------|------|-------------|------|
| Free | 무료 | 5건 | 기본 상태 (구독 없음) |
| Light | 3,000원/월 | 30건 | 개인 투자자용 |
| Max | 30,000원/월 | 무제한 | 전문 투자자용 |

### 관련 파일

```
backend/app/models/subscriptions.py    - SUBSCRIPTION_LIMITS, UserQueryUsage 모델
backend/app/services/usage_service.py  - 조회 제한 체크 및 사용량 추적
backend/app/routes/subscription.py     - 구독 관리 API
backend/app/api/endpoints/companies.py - 조회 제한 적용
frontend/src/components/UsageIndicator.tsx - 사용량 표시 UI
```

### 조회 제한 로직

```python
# 회사 상세 조회 시 사용량 체크
from app.services.usage_service import check_and_increment_usage

can_query, remaining, limit = await check_and_increment_usage(db, user)
if not can_query:
    raise HTTPException(status_code=429, detail="월 조회 한도 초과")
```

---

## 콘텐츠 관리 시스템 (2025-12-25 추가)

### 개요

어드민 페이지에서 서비스 소개(AboutPage) 콘텐츠를 동적으로 편집 가능

### 관련 파일

```
backend/app/models/content.py      - PageContent 모델, DEFAULT_ABOUT_CONTENT
backend/app/routes/content.py      - 콘텐츠 CRUD API
frontend/src/pages/AdminPage.tsx   - 콘텐츠 편집 탭
frontend/src/pages/AboutPage.tsx   - 동적 콘텐츠 로딩
```

### API 엔드포인트

```
GET    /api/content/{page}                    - 페이지 콘텐츠 조회 (공개)
PUT    /api/content/{page}/{section}/{field}  - 텍스트 수정 (관리자)
POST   /api/content/{page}/{section}/image    - 이미지 업로드 (관리자)
DELETE /api/content/{page}/{section}/image    - 이미지 삭제 (관리자)
```

### 편집 가능 섹션 (AboutPage)

- hero: 배지, 제목, 설명
- why_section: 제목, 설명
- advantage1~5: 각각 제목, 설명
- features_section: 제목, 설명
- feature1~4: 각각 배지, 제목, 설명, 이미지(640x360)
- stats_section: 제목
- cta_section: 제목, 설명

---

## 임원 임기(term) 정보 규칙 (2025-12-16 확정)

### 상장사/비상장사 구분
- **상장사** (KOSPI, KOSDAQ, KONEX): 임기 정보(term_start_date, term_end_date) 파싱
- **비상장사** (ETF 등): 임기 정보 NULL (파싱하지 않음)

### 현재 적재 현황 (상장사만)
| 시장 | 총 레코드 | 임기 있음 | 적재율 |
|------|----------|----------|--------|
| KOSDAQ | 167,497 | 19,490 | 11.6% |
| KOSPI | 88,633 | 6,547 | 7.4% |
| KONEX | 3,156 | 326 | 10.3% |
| **합계** | **259,286** | **26,363** | **10.2%** |

### 수정된 파일
- `scripts/parse_officers_from_local.py`: `is_listed_company()` 메서드 추가, 비상장사 term NULL 처리
- ETF 기존 데이터 12,227건 NULL 처리 완료

### 임기 파싱 패턴 (SH5_PER 필드)
```
지원 패턴:
- YYYY.MM ~ (예: 2017.02 ~)
- YYYY-MM-DD ~ (예: 2017-02-01 ~)
- YYYY/MM ~ (예: 2017/02 ~)
- YYYY년 MM월 ~ (예: 2017년 02월 ~)
- YYYY.MM.DD ~ (예: 2017.02.01 ~)

미지원 패턴 (향후 개선 필요):
- 20.03 ~ (2자리 연도)
- 2020년 3월 ~ (한글 월)
```

---

## 상세 파싱 상태 파일

**상세 파싱 계획 및 진행 상황**: `backend/scripts/PARSING_STATUS.md`

---

## 원시 데이터 위치

### 로컬 다운로드 완료 (API 호출 불필요)
- **DART 공시**: `backend/data/dart/` (9.2GB, 228,395 ZIP 파일)
  - 2022년: 30,973개
  - 2023년: 51,565개
  - 2024년: 84,655개
  - 2025년: 61,202개
- **CB 공시 JSON**: `backend/data/cb_disclosures_by_company_full.json`
  - 전체: 4,913건
  - 전환사채 발행결정: 1,686건 (필터 대상)
- **회사 목록**: DB companies 테이블 (3,922개)

---

## DB 접속 정보

### 로컬 (개발)
```bash
PGPASSWORD=dev_password psql -h localhost -U postgres -d raymontology_dev
```

### 프로덕션 (Railway)
```bash
# PostgreSQL
PGPASSWORD=ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR psql -h hopper.proxy.rlwy.net -p 41316 -U postgres -d railway

# API URL
https://raymontology-production.up.railway.app
```

### Neo4j (미설정 - placeholder 상태)
```
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_strong_neo4j_password_here
# 주의: 실제 Neo4j Aura 설정 필요
```

---

## 세션 시작 시 필수 확인

매 세션 시작 시 아래 쿼리로 현재 상태 확인:
```sql
SELECT 'companies' as tbl, COUNT(*) FROM companies
UNION ALL SELECT 'officers', COUNT(*) FROM officers
UNION ALL SELECT 'officer_positions', COUNT(*) FROM officer_positions
UNION ALL SELECT 'disclosures', COUNT(*) FROM disclosures
UNION ALL SELECT 'convertible_bonds', COUNT(*) FROM convertible_bonds
UNION ALL SELECT 'cb_subscribers', COUNT(*) FROM cb_subscribers
UNION ALL SELECT 'financial_statements', COUNT(*) FROM financial_statements
UNION ALL SELECT 'risk_signals', COUNT(*) FROM risk_signals
UNION ALL SELECT 'risk_scores', COUNT(*) FROM risk_scores
UNION ALL SELECT 'major_shareholders', COUNT(*) FROM major_shareholders
UNION ALL SELECT 'affiliates', COUNT(*) FROM affiliates
ORDER BY 1;
```

---

## 스크립트 실행 규칙

### 타임아웃 설정
- 짧은 작업: 2분
- 긴 작업: 10분 (timeout 600000)

### 실행 예시
```bash
# 올바른 방법
PYTHONPATH=/Users/jaejoonpark/raymontology/backend python3 scripts/parse_cb_disclosures.py --limit 100

# 틀린 방법 (백그라운드)
PYTHONPATH=/Users/jaejoonpark/raymontology/backend python3 scripts/parse_cb_disclosures.py &
```

---

## 아키텍처 규칙 (중요)

### 데이터 흐름
```
원시 파일 (DART) → PostgreSQL (마스터) → Neo4j (파생)
                        ↑
                   절대 삭제 금지
```

### PostgreSQL = 마스터 데이터
- 모든 파싱 결과는 PostgreSQL에 저장
- Neo4j는 PostgreSQL 기반으로 재생성 가능
- PostgreSQL 데이터 삭제 시 복구 불가

### Neo4j = 파생 데이터
- PostgreSQL 데이터로 언제든 재구축 가능
- Neo4j 초기화해도 PostgreSQL에 영향 없음

---

## 실행 금지 스크립트 (PostgreSQL 삭제됨)

다음 스크립트는 **절대 실행 금지**:

| 스크립트 | 위험 | 이유 |
|---------|------|------|
| `sync_neo4j_to_postgres.py` | TRUNCATE CASCADE | PostgreSQL 전체 삭제 |
| `init_database.py` | DROP TABLE CASCADE | 모든 테이블 삭제 |
| `db_migrate.py --action=reset` | drop_all | 전체 리셋 |

**경고**: 위 스크립트들은 `scripts/_deprecated/`로 이동됨

---

## 안전한 Neo4j 재구축 방법

Neo4j만 초기화하려면:
```bash
# Neo4j만 초기화 (PostgreSQL 영향 없음)
cypher-shell -u neo4j -p password "MATCH (n) DETACH DELETE n"

# PostgreSQL → Neo4j 동기화 (안전)
python3 scripts/neo4j_cb_network.py  # CB 네트워크만 재구축
```

---

## 이 파일의 목적

Claude Code는 세션 간 메모리가 없음.
이 파일을 통해 매 세션마다 동일한 규칙을 적용.
