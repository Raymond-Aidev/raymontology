# Raymontology 프로젝트 설정 및 구현 현황

> **마지막 업데이트**: 2026-01-21
> **상태**: 서비스 운영 중 (RaymondsIndex 포함, 조회 기록 기능 추가)

---

## 1. 프로젝트 개요

**Raymontology**는 한국 상장사의 CB(전환사채) 발행, 임원 네트워크, 재무 리스크를 분석하는 플랫폼입니다.

### 기술 스택
- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Database**: PostgreSQL (Railway), Neo4j (미설정)
- **Deployment**: Railway

---

## 2. 환경 설정

### 2.1 프로덕션 데이터베이스 (Railway)

```bash
# PostgreSQL 접속
PGPASSWORD=ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR psql -h hopper.proxy.rlwy.net -p 41316 -U postgres -d railway

# API URL
https://raymontology-production.up.railway.app
```

### 2.2 로컬 개발 환경

```bash
# PostgreSQL (Docker)
PGPASSWORD=dev_password psql -h localhost -U postgres -d raymontology_dev

# Backend 실행
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend 실행
cd frontend
npm run dev
```

### 2.3 Neo4j (미설정)

`graph.py`에서 PostgreSQL fallback을 사용합니다.

---

## 3. 데이터베이스 현황 (2026-01-21 갱신)

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| companies | **3,109** | 상장사 목록 (**813개 삭제 후**: 3,021 LISTED + 88 ETF) |
| officers | 47,444 | 임원 정보 |
| officer_positions | 62,141 | 임원-회사 연결 |
| disclosures | 279,258 | 공시 원본 |
| convertible_bonds | 1,133 | CB 발행 정보 |
| cb_subscribers | 7,026 | CB 인수자 |
| financial_statements | 9,820 | 재무제표 |
| risk_signals | 1,412 | 리스크 신호 |
| risk_scores | **3,138** | 리스크 점수 (**774건 삭제 후**) |
| major_shareholders | 44,574 | 대주주 |
| affiliates | **864** | 계열회사 (**109건 삭제 후**) |
| **financial_details** | **10,288** | **RaymondsIndex용 상세 재무** |
| **raymonds_index** | **5,257** | **자본 배분 효율성 지수** |
| stock_prices | **126,506** | 주가 데이터 (**818건 삭제 후**) |
| largest_shareholder_info | 4,599 | 최대주주 기본정보 |
| user_query_usage | - | 월별 조회 사용량 추적 |
| page_contents | - | 페이지 콘텐츠 동적 관리 |
| **company_view_history** | **-** | **조회한 기업 기록 (2026-01-21 신규)** |

### 삭제된 기업 (2026-01-21)
- **유령 기업 39개**: LISTED이나 사업보고서/임원/재무 0건
- **상장폐지 기업 774개**: DELISTED + 사업보고서 0건
- **상세 내역**: `backend/scripts/COMPANY_MANAGEMENT.md` 참조

---

## 4. API 구조

### 4.1 주요 엔드포인트

```
/api/companies                    - 회사 목록
/api/companies/search?q=          - 회사 검색
/api/companies/{id}               - 회사 상세
/api/companies/{id}/officers      - 회사 임원 목록
/api/companies/{id}/convertible-bonds - 회사 CB 목록

/api/officers                     - 임원 목록
/api/officers/{id}                - 임원 상세
/api/officers/company/{id}        - 회사별 임원

/api/graph/company/{id}           - 회사 네트워크 그래프
/api/graph/officer/{id}/career    - 임원 경력 (PostgreSQL fallback)
/api/graph-fallback/*             - Neo4j 없을 때 대체 API

/api/subscription/usage           - 월별 조회 사용량 조회
/api/admin/users/{id}/subscription - 관리자: 사용자 구독 변경
/api/companies/view-history/list  - 조회한 기업 목록 (2026-01-21)

/api/content/{page}               - 페이지 콘텐츠 조회 (공개)
/api/content/{page}/{section}/{field} - 콘텐츠 수정 (관리자)
/api/content/{page}/{section}/image   - 이미지 업로드/삭제 (관리자)
```

### 4.2 임원 조회 로직 (중요!)

임원 조회는 `officer_positions` 테이블 기반입니다:

```python
# officers.current_company_id (X) - 대부분 NULL
# officer_positions.company_id (O) - 실제 데이터

query = (
    select(Officer, OfficerPosition.position)
    .join(OfficerPosition, Officer.id == OfficerPosition.officer_id)
    .where(OfficerPosition.company_id == company_id)
    .where(OfficerPosition.is_current == True)
)
```

---

## 5. 핵심 모델

### 5.1 OfficerPosition (신규 추가)

```python
# backend/app/models/officer_positions.py
class OfficerPosition(Base):
    __tablename__ = "officer_positions"

    id = Column(UUID, primary_key=True)
    officer_id = Column(UUID, ForeignKey("officers.id"))
    company_id = Column(UUID, ForeignKey("companies.id"))
    position = Column(String(100))  # 대표이사, 사내이사 등
    term_start_date = Column(Date)
    term_end_date = Column(Date)
    is_current = Column(Boolean, default=True)
```

### 5.2 주요 관계

```
Company ──1:N── OfficerPosition ──N:1── Officer
    │                                       │
    └──1:N── ConvertibleBond ──1:N── CBSubscriber
```

---

## 6. 최근 변경사항

### 2026-01-21: 기업 데이터 정리 및 문서화

**유령 기업 및 상장폐지 기업 삭제**:
- 유령 기업 39개 삭제 (LISTED이나 사업보고서 0건)
- 상장폐지 기업 774개 삭제 (DELISTED + 사업보고서 0건)
- 총 813개 기업 정리, 현재 3,109개 기업 관리 중

**기업 관리 문서 신규**:
- `backend/scripts/COMPANY_MANAGEMENT.md` 생성
- 삭제 이력, 관리 대상 기업 기준, 파이프라인 규칙 문서화
- CLAUDE.md에 파이프라인 실행 체크리스트 추가

**관련 스크립트**:
- `maintenance/delete_ghost_companies.py`: 유령 기업 삭제
- `maintenance/delete_delisted_companies.py`: 상장폐지 기업 삭제

### 2026-01-21: 조회 기록 및 Trial 이용권 개선

**조회한 기업 목록 기능 추가**:
- `company_view_history` 테이블 신규 생성
- `/api/companies/view-history/list` API 추가
- `ViewedCompaniesPage.tsx` 프론트엔드 구현
- 유료 회원만 접근 가능

**Trial 이용권 정책 개선**:
- 30일 후 자동 만료 로직 구현
- 이전 조회 기업 재조회 허용 (30일 이내)
- 조회 제한 UX 개선 (사전 체크 API)

**공유 Header 전체 적용**:
- 모든 페이지에 일관된 Header 컴포넌트 적용
- 로그인 상태에 따른 메뉴 표시

**관련 파일**:
- Backend: `app/routes/view_history.py`, `app/models/subscriptions.py`, `app/services/usage_service.py`
- Frontend: `pages/ViewedCompaniesPage.tsx`, `components/common/Header.tsx`, `api/company.ts`, `api/graph.ts`

### 2025-12-26: RaymondsIndex 시스템 완료

**RaymondsIndex (자본 배분 효율성 지수)**:
- `financial_details`: 10,314건 (2025 Q3 보고서 기반)
- `raymonds_index`: 7,646건 (2025 Q3 데이터 포함)
- 등급 분포: A(121), B(1,740), C(3,722), D(2,063)

**관련 파일**:
- `backend/app/models/financial_details.py`
- `backend/app/models/raymonds_index.py`
- `backend/app/services/raymonds_index_calculator.py`
- `frontend/src/pages/RaymondsIndexRankingPage.tsx`

### 2025-12-25: 구독 및 콘텐츠 관리 시스템

**구독 시스템**: Light (3,000원/월, 30건), Max (30,000원/월, 무제한)
**콘텐츠 관리**: AboutPage 동적 편집

### 2025-12-24: 임원 API 리팩토링

- `officer_positions` 테이블 기반으로 변경
- 중복 243,398건 삭제
- PostgreSQL fallback 추가

---

## 7. 스크립트 참조

### 7.1 데이터 파싱

```bash
# 임원 파싱 (로컬 DART 파일 기반)
PYTHONPATH=/Users/jaejoonpark/raymontology/backend python3 scripts/parse_officers_from_local.py

# CB 파싱
PYTHONPATH=/Users/jaejoonpark/raymontology/backend python3 scripts/parse_cb_disclosures.py
```

### 7.2 데이터 검증

```bash
# DB 상태 확인
PGPASSWORD=ooRdnLPpUTvrYODqhYqvhWwwQtsnmjnR psql -h hopper.proxy.rlwy.net -p 41316 -U postgres -d railway -c "
SELECT 'companies' as tbl, COUNT(*) FROM companies
UNION ALL SELECT 'officers', COUNT(*) FROM officers
UNION ALL SELECT 'officer_positions', COUNT(*) FROM officer_positions
ORDER BY 1;
"
```

### 7.3 실행 금지 스크립트

| 스크립트 | 위험 | 이유 |
|---------|------|------|
| `sync_neo4j_to_postgres.py` | TRUNCATE | PostgreSQL 삭제 |
| `init_database.py` | DROP TABLE | 테이블 삭제 |
| `db_migrate.py --action=reset` | drop_all | 전체 리셋 |

---

## 8. 트러블슈팅

### 8.1 "Neo4j not available" 에러

**원인**: Neo4j Aura 미설정
**해결**: `graph.py`가 자동으로 PostgreSQL fallback 사용

### 8.2 임원 수 0명으로 표시

**원인**: API가 `officers.current_company_id` 사용 (NULL)
**해결**: `officer_positions` 테이블 기반으로 API 수정 완료

### 8.3 임원 중복 표시

**원인**: `officer_positions` 중복 레코드
**해결**: 중복 243,398건 삭제 완료

```sql
-- 중복 재발생 시 정리
WITH duplicates AS (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY company_id, officer_id, position, is_current
               ORDER BY updated_at DESC NULLS LAST, id DESC
           ) as rn
    FROM officer_positions
)
DELETE FROM officer_positions
WHERE id IN (SELECT id FROM duplicates WHERE rn > 1);
```

---

## 9. Git 커밋 히스토리

```
d18eae3 refactor: 임원 조회 API를 officer_positions 테이블 기반으로 변경
b3cd8d9 fix: Neo4j 없을 때 PostgreSQL fallback으로 임원 경력 조회
70ca264 docs: CLAUDE.md에 프로덕션 DB 접속정보 추가
4f5de8a feat: 회원가입 약관/개인정보처리방침 팝업으로 변경
```

---

## 10. 다음 작업 (TODO)

- [ ] Neo4j Aura 실제 설정 (현재 placeholder)
- [ ] 임원 네트워크 시각화 개선
- [ ] 리스크 점수 계산 로직 고도화
- [ ] 파싱 스크립트 UPSERT 로직 추가 (중복 방지)
- [x] RaymondsIndex 스키마 설계 - 2025-12-25 완료
- [x] RaymondsIndex 데이터 파싱 - 2025-12-26 완료 (10,314건)
- [x] RaymondsIndex 계산 엔진 - 2025-12-26 완료 (4,951건)
- [x] 구독 시스템 구현 - 2025-12-25 완료
- [x] 조회 제한 시스템 구현 - 2025-12-25 완료
- [x] 콘텐츠 관리 시스템 - 2025-12-25 완료
- [x] 조회한 기업 목록 기능 - 2026-01-21 완료
- [x] Trial 이용권 30일 만료 로직 - 2026-01-21 완료
- [x] 조회 제한 UX 개선 - 2026-01-21 완료
- [x] 공유 Header 전체 적용 - 2026-01-21 완료

---

## 11. 문서 참조

| 문서 | 경로 | 용도 |
|------|------|------|
| Claude 규칙 | `.claude/CLAUDE.md` | 세션별 규칙 |
| 스키마 레지스트리 | `scripts/SCHEMA_REGISTRY.md` | 테이블명/컬럼명 |
| 표준 프로세스 | `scripts/STANDARD_PROCESS.md` | DB 작업 체크리스트 |
| 파싱 상태 | `scripts/PARSING_STATUS.md` | 파싱 진행 상황 |
| **기업 관리** | **`scripts/COMPANY_MANAGEMENT.md`** | **데이터 수집 대상 기업 관리** |
| 환경 변수 | `.env.production` | 프로덕션 설정 |
