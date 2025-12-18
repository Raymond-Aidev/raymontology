# 🔴 Neo4j 그래프 시각화 문제 진단 보고서

**작성일시**: 2025-11-21
**문제**: Neo4j 그래프가 데이터를 제대로 시각화하지 못함

---

## 문제 요약

**증상**: 삼성전자 검색 시 그래프에 노드/관계가 표시되지 않음

**근본 원인**: 삼성전자를 포함한 1,416개 회사에 임원 데이터가 없어 Neo4j에서 고립된 노드로 존재

---

## 상세 진단

### 1. Neo4j 데이터 현황

```
전체 노드: 92,617개
  - Company: 3,911개
  - Officer: 83,736개
  - ConvertibleBond: 2,743개
  - Subscriber: 2,227개

전체 관계: 145,521개
  - WORKS_AT: 83,736개
  - BOARD_MEMBER_AT: 50,021개
  - SUBSCRIBED: 4,014개
  - INVESTED_IN: 3,130개
  - ISSUED: 2,743개
  - HAS_AFFILIATE: 1,877개
```

### 2. 삼성전자 상태

#### PostgreSQL
```
회사명: 삼성전자
ID: 30bb9747-e6f7-48dd-ab40-1933602fdb21
Ticker: 005930
임원 수: 0명 ❌
```

#### Neo4j
```
회사 노드: ✅ 존재
연결된 관계: 0개 ❌
상태: 고립된 노드 (Isolated Node)
```

### 3. 비교: LG전자 (정상 케이스)

#### PostgreSQL
```
회사명: LG전자
ID: 8e1d4a2c-4413-4d99-adc8-f8b7f8422dd7
Ticker: 066570
임원 수: 530명 ✅
```

#### Neo4j
```
회사 노드: ✅ 존재
연결된 관계: 538개 ✅
관계 유형: WORKS_AT, BOARD_MEMBER_AT 등
```

### 4. 전체 영향 범위

```
전체 회사: 3,911개
고립된 회사: 1,416개 (36.2%) ❌
정상 회사: 2,495개 (63.8%) ✅
```

---

## 문제 원인 분석

### 근본 원인

**삼성전자의 사업보고서에서 임원 데이터가 파싱되지 않음**

가능한 원인:
1. 사업보고서 다운로드 실패
2. XML 파싱 실패
3. 임원 정보 추출 로직 문제
4. 데이터 매핑 오류

### 데이터 파이프라인 검증 필요 단계

```
1. DART API → 사업보고서 다운로드
   ↓
2. ZIP 압축 해제 → XML 파일 추출
   ↓
3. XML 파싱 → 임원 정보 추출
   ↓
4. PostgreSQL 저장 (officers 테이블)
   ↓
5. Neo4j 동기화 (Officer 노드 + WORKS_AT 관계)
```

**중단 지점**: 3번 또는 4번 단계에서 삼성전자 임원 데이터 누락 추정

---

## GraphCanvas.tsx 쿼리 검증

### 현재 쿼리 (프론트엔드)
```cypher
MATCH (c:Company {id: '30bb9747-e6f7-48dd-ab40-1933602fdb21'})-[r]-(n)
RETURN c, r, n
LIMIT 100
```

### 결과
```
반환된 레코드: 0개 ❌
```

### LG전자로 테스트
```cypher
MATCH (c:Company {name: 'LG전자'})-[r]-(n)
RETURN c, r, n
LIMIT 100
```

### 결과
```
반환된 레코드: 10개 ✅
관계 유형: WORKS_AT → Officer
```

**결론**: 쿼리는 정상, 데이터 부족이 문제

---

## 해결 방안

### 즉시 조치 (임시 해결)

**Option 1: LG전자로 대체 테스트**
- 프론트엔드에서 LG전자 ID로 테스트하면 즉시 그래프 확인 가능
- LG전자 ID: `8e1d4a2c-4413-4d99-adc8-f8b7f8422dd7`

**Option 2: 정상 회사 목록 사용**
```sql
-- 관계가 있는 회사 상위 10개
SELECT c.name, c.ticker, COUNT(r) as rel_count
FROM (
  SELECT c.id, c.name, c.ticker
  FROM companies c
) c
CROSS JOIN (
  SELECT DISTINCT company_id FROM officers WHERE current_company_id IS NOT NULL
) r
WHERE c.id = r.company_id
GROUP BY c.id
ORDER BY rel_count DESC
LIMIT 10;
```

### 근본 해결 (필수)

**1. 삼성전자 사업보고서 재수집**
```bash
# backend 디렉토리에서
python3 scripts/company_collector.py \
  --data-dir ./data/dart \
  --api-key 1fd0cd12ae5260eafb7de3130ad91f16aa61911b \
  --companies "005930"  # 삼성전자만 재수집
```

**2. 사업보고서 재파싱**
```bash
# 삼성전자 보고서 파싱
python3 scripts/batch_parser.py \
  --corp-code <삼성전자_corp_code> \
  --force  # 강제 재파싱
```

**3. Neo4j 재동기화**
```bash
# 1. PostgreSQL → Neo4j 회사 동기화
python3 scripts/sync_companies_to_neo4j.py

# 2. Officer 네트워크 재구축
python3 scripts/neo4j_officer_network.py
```

**4. 검증**
```bash
# PostgreSQL 확인
psql -d raymontology -U raymontology -c "
  SELECT COUNT(*) FROM officers
  WHERE current_company_id = '30bb9747-e6f7-48dd-ab40-1933602fdb21';
"

# Neo4j 확인
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
with driver.session() as session:
    result = session.run('''
        MATCH (c:Company {ticker: '005930'})-[r]-()
        RETURN count(r) as rel_count
    ''')
    print(f'삼성전자 관계: {result.single()[\"rel_count\"]}개')
driver.close()
"
```

---

## 시스템 개선 권장사항

### 1. 데이터 검증 파이프라인 추가

**각 단계마다 검증 로직 추가**:
```python
def validate_company_data(company_id: str):
    # 1. 사업보고서 존재 확인
    # 2. 임원 수 확인
    # 3. Neo4j 관계 확인
    # 4. 이상 발견 시 알림
    pass
```

### 2. 모니터링 대시보드

**핵심 지표 추적**:
- 고립된 회사 노드 개수
- 임원이 없는 회사 개수
- Neo4j ↔ PostgreSQL 동기화 상태
- 최근 업데이트 시간

### 3. 자동 복구 스크립트

```bash
# 매일 실행하여 고립된 노드 자동 복구
python3 scripts/auto_fix_isolated_nodes.py
```

---

## 참고: 정상 작동하는 회사 목록

```
LG전자 (066570): 538개 관계
HL만도 (204320): 376개 관계
롯데웰푸드 (280360): 363개 관계
안국약품 (001540): 284개 관계
신원 (009270): 284개 관계
디아이 (003160): 282개 관계
삼양사 (145990): 273개 관계
삼성생명 (032830): 269개 관계
하나제약 (293480): 258개 관계
계양전기 (012200): 257개 관계
```

**임시 테스트용으로 위 회사 사용 가능**

---

## 결론

1. **즉시 해결**: LG전자 등 정상 회사로 프론트엔드 테스트
2. **근본 해결**: 삼성전자 사업보고서 재수집 + 재파싱 필요
3. **시스템 개선**: 데이터 검증 및 모니터링 파이프라인 추가

**우선순위**:
- 🔴 High: 삼성전자 임원 데이터 수집
- 🟡 Medium: 1,416개 고립 노드 해결
- 🟢 Low: 자동 복구 시스템 구축
