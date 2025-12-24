# Raymontology 프로젝트 설정 및 구현 현황

> **마지막 업데이트**: 2025-12-24
> **상태**: 서비스 운영 중

## 세션 시작 시 `/sc:load` 로 이 파일을 로드하세요

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

Railway 대시보드의 Neo4j 설정은 placeholder 상태입니다.
`graph.py`에서 PostgreSQL fallback을 사용합니다.

---

## 3. 데이터베이스 현황 (2025-12-24)

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| companies | 3,922 | 상장사 목록 |
| officers | 44,679 | 임원 정보 |
| officer_positions | 64,265 | 임원-회사 연결 (중복 제거 완료) |
| disclosures | 213,304 | 공시 원본 |
| convertible_bonds | 1,463 | CB 발행 정보 |
| cb_subscribers | 7,490 | CB 인수자 |
| financial_statements | 9,432 | 재무제표 |
| risk_signals | 1,412 | 리스크 신호 |
| risk_scores | 3,912 | 리스크 점수 |
| major_shareholders | 95,191 | 대주주 |
| affiliates | 973 | 계열회사 |

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

### 2025-12-24: 임원 API 리팩토링

**문제**: `officers.current_company_id`가 대부분 NULL (8명만 존재)

**해결**:
1. 중복 데이터 243,398건 삭제
2. `OfficerPosition` SQLAlchemy 모델 추가
3. API를 `officer_positions` 테이블 기반으로 변경
4. `graph.py`에 PostgreSQL fallback 추가

**영향받은 파일**:
- `backend/app/models/officer_positions.py` (신규)
- `backend/app/models/__init__.py`
- `backend/app/api/endpoints/officers.py`
- `backend/app/api/endpoints/companies.py`
- `backend/app/api/endpoints/graph.py`

### 2025-12-17: 임원-회사 매칭 정제

- 잘못된 데이터 7,277건 삭제
- 검증 스크립트: `scripts/verify_officer_company_match.py`

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

---

## 11. 문서 참조

| 문서 | 경로 | 용도 |
|------|------|------|
| Claude 규칙 | `.claude/CLAUDE.md` | 세션별 규칙 |
| 스키마 레지스트리 | `scripts/SCHEMA_REGISTRY.md` | 테이블명/컬럼명 |
| 표준 프로세스 | `scripts/STANDARD_PROCESS.md` | DB 작업 체크리스트 |
| 파싱 상태 | `scripts/PARSING_STATUS.md` | 파싱 진행 상황 |
| 환경 변수 | `.env.production` | 프로덕션 설정 |
