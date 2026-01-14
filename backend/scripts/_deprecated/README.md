# DEPRECATED SCRIPTS - DO NOT USE

These scripts have been deprecated because they **DELETE PostgreSQL data**.

## Why these are dangerous

| Script | Risk |
|--------|------|
| `sync_neo4j_to_postgres.py` | `TRUNCATE CASCADE` on all tables |
| `init_database.py` | `DROP TABLE CASCADE` on all tables |
| `db_migrate.py` | `drop_all` function deletes everything |

## History

2025-12-08: These scripts caused 4 data loss incidents over 1 month.
Root cause: Claude executed these without understanding they delete PostgreSQL.

## Correct Architecture

```
Raw Files (DART) --> PostgreSQL (MASTER) --> Neo4j (DERIVED)
                           ^
                      NEVER DELETE
```

- PostgreSQL = Source of truth
- Neo4j = Can be rebuilt from PostgreSQL anytime
- These scripts incorrectly treated Neo4j as the source

## If you need to reset Neo4j

```bash
# Safe: Only clears Neo4j
cypher-shell -u neo4j -p password "MATCH (n) DETACH DELETE n"

# Then rebuild from PostgreSQL
python3 scripts/neo4j_cb_network.py
```

---

## Cleanup (2026-01-14)

### DART API 직접 호출 스크립트
| 파일 | 대체 방법 |
|------|----------|
| `collect_financial_statements.py` | `scripts.pipeline.run_quarterly_pipeline` |
| `collect_financial_details.py` | `scripts.pipeline.run_quarterly_pipeline` |

### 레거시 버전 스크립트
| 파일 | 최신 버전 |
|------|----------|
| `parse_major_shareholders_v2.py` | `parse_major_shareholders.py` |
| `reparse_financial_details_v2.py` | `scripts.pipeline.run_unified_parser` |
| `reparse_officer_careers_v2.py` | `maintenance/reparse_officer_careers.py`
