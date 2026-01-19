# Sync Scripts (DB 동기화)

PostgreSQL ↔ Neo4j 간 데이터 동기화 스크립트입니다.

## 파일 패턴
- `sync_*` - 데이터 동기화
- `resync_*` - 재동기화
- `convert_*` - 데이터 변환 후 동기화
- `full_*` - 전체 동기화

## 주요 스크립트

| 스크립트 | 용도 |
|---------|------|
| `full_neo4j_sync.py` | 전체 데이터 Neo4j 동기화 |
| `sync_companies_to_neo4j.py` | 회사 데이터 동기화 |
| `sync_cb_to_neo4j.py` | CB 데이터 동기화 |
| `resync_officers_to_neo4j.py` | 임원 데이터 재동기화 |
| `convert_officer_career_to_graph.py` | 임원 경력 그래프 변환 |

## 사용 예시
```bash
cd backend
source .venv/bin/activate

# 전체 Neo4j 동기화
NEO4J_URI="..." NEO4J_USER="neo4j" NEO4J_PASSWORD="..." \
  python scripts/sync/full_neo4j_sync.py
```

## 주의사항
- 대부분의 스크립트는 Neo4j 연결 필요
- `sync_neo4j_to_postgres.py`는 **사용 금지** (`_deprecated/`로 이동됨)
