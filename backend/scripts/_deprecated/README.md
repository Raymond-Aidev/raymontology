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
