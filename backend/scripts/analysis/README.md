# Analysis Scripts (데이터 분석)

인덱스 계산, Neo4j 네트워크 분석, 통계 생성 스크립트입니다.

## 파일 패턴
- `calculate_*` - 지표/인덱스 계산
- `generate_*` - 신호/보고서 생성
- `aggregate_*` - 데이터 집계
- `neo4j_*` - Neo4j 그래프 분석
- `query_*` - 데이터 조회/검색
- `build_*` - 온톨로지/구조 생성

## 주요 스크립트

| 스크립트 | 용도 |
|---------|------|
| `calculate_raymonds_index.py` | RaymondsIndex 계산 |
| `calculate_risk_scores.py` | 투자등급 계산 |
| `generate_risk_signals.py` | 위험신호 생성 |
| `neo4j_officer_network.py` | 임원 관계 네트워크 |
| `neo4j_cb_network.py` | CB 인수자 네트워크 |

## 사용 예시
```bash
cd backend
source .venv/bin/activate

# RaymondsIndex 계산
DATABASE_URL="..." python scripts/analysis/calculate_raymonds_index.py

# Neo4j 네트워크 분석 (Neo4j 필요)
NEO4J_URI="..." python scripts/analysis/neo4j_officer_network.py
```

## 주의사항
- **분기별 인덱스 계산은 `pipeline/calculate_index.py` 사용 권장**
- Neo4j 스크립트는 Neo4j 서버 연결 필요
