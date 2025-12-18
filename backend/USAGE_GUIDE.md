# Neo4j 그래프 네트워크 사용 가이드

## 1. Neo4j Browser 접속

1. 웹 브라우저에서 접속: http://localhost:7474
2. 연결 URL: `neo4j://localhost:7687`
3. 로그인 정보:
   - Username: `neo4j`
   - Password: `your_password` (설정한 비밀번호)

## 2. 유용한 Cypher 쿼리 예제

### 🔍 기본 탐색

#### 전체 노드 개수 확인
```cypher
MATCH (n)
RETURN labels(n)[0] as type, COUNT(n) as count
ORDER BY count DESC
```

#### 전체 관계 개수 확인
```cypher
MATCH ()-[r]->()
RETURN type(r) as relationship, COUNT(r) as count
ORDER BY count DESC
```

### 🏢 회사 분석

#### 특정 회사의 모든 정보 조회 (예: 삼성전자)
```cypher
MATCH (c:Company {name: "삼성전자"})
OPTIONAL MATCH (c)<-[:WORKS_AT]-(o:Officer)
OPTIONAL MATCH (c)-[:HAS_AFFILIATE]->(a:Company)
OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
RETURN c,
       COUNT(DISTINCT o) as officer_count,
       COUNT(DISTINCT a) as affiliate_count,
       COUNT(DISTINCT cb) as cb_count
```

#### 임원이 가장 많은 회사 TOP 10
```cypher
MATCH (c:Company)<-[:WORKS_AT]-(o:Officer)
WITH c, COUNT(o) as officer_count
RETURN c.name as company, officer_count
ORDER BY officer_count DESC
LIMIT 10
```

#### 계열사가 가장 많은 회사 TOP 10
```cypher
MATCH (c:Company)-[:HAS_AFFILIATE]->(a:Company)
WITH c, COUNT(a) as affiliate_count
RETURN c.name as company, affiliate_count
ORDER BY affiliate_count DESC
LIMIT 10
```

### 👔 임원 분석

#### 특정 임원의 회사 조회
```cypher
MATCH (o:Officer {name: "홍길동"})-[:WORKS_AT]->(c:Company)
RETURN o.name as officer,
       o.position as position,
       c.name as company
```

#### 이사회 멤버 조회
```cypher
MATCH (o:Officer)-[:BOARD_MEMBER_AT]->(c:Company)
RETURN o.name as officer,
       o.position as position,
       c.name as company
LIMIT 20
```

#### 여러 회사에 겸직 중인 임원 찾기
```cypher
MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
WITH o, COLLECT(c.name) as companies, COUNT(c) as company_count
WHERE company_count > 1
RETURN o.name as officer, company_count, companies
ORDER BY company_count DESC
```

### 💰 CB (전환사채) 분석

#### 특정 회사의 CB 발행 내역
```cypher
MATCH (c:Company {name: "삼성전자"})-[:ISSUED]->(cb:ConvertibleBond)
RETURN cb.bond_name as bond_name,
       cb.issue_date as issue_date,
       cb.issue_amount as amount
ORDER BY cb.issue_date DESC
```

#### CB를 가장 많이 발행한 회사
```cypher
MATCH (c:Company)-[:ISSUED]->(cb:ConvertibleBond)
WITH c, COUNT(cb) as cb_count
RETURN c.name as company, cb_count
ORDER BY cb_count DESC
LIMIT 10
```

#### 특정 CB의 인수자 조회
```cypher
MATCH (c:Company)-[:ISSUED]->(cb:ConvertibleBond {bond_name: "제1회 무보증 사모 전환사채"})
MATCH (s:Subscriber)-[:SUBSCRIBED]->(cb)
RETURN c.name as issuer,
       cb.bond_name as bond,
       s.name as subscriber,
       s.subscription_amount as amount
```

#### 가장 활발한 CB 투자자
```cypher
MATCH (s:Subscriber)-[:SUBSCRIBED]->(cb:ConvertibleBond)
WITH s, COUNT(cb) as cb_count
RETURN s.name as investor, cb_count
ORDER BY cb_count DESC
LIMIT 10
```

### 🌐 네트워크 분석

#### 특정 회사의 1차 연결 네트워크 시각화
```cypher
MATCH (c:Company {name: "삼성전자"})
OPTIONAL MATCH (c)<-[r1:WORKS_AT]-(o:Officer)
OPTIONAL MATCH (c)-[r2:HAS_AFFILIATE]->(a:Company)
OPTIONAL MATCH (c)-[r3:ISSUED]->(cb:ConvertibleBond)
RETURN c, r1, r2, r3, o, a, cb
LIMIT 100
```

#### 회사 간 계열사 관계 시각화
```cypher
MATCH (c1:Company)-[r:HAS_AFFILIATE]->(c2:Company)
RETURN c1, r, c2
LIMIT 50
```

#### CB 투자 네트워크 (회사 → CB → 투자자)
```cypher
MATCH (c:Company)-[:ISSUED]->(cb:ConvertibleBond)<-[:SUBSCRIBED]-(s:Subscriber)
RETURN c, cb, s
LIMIT 100
```

### 🔗 고급 분석

#### 자사 CB 인수 케이스 찾기
```cypher
MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
MATCH (s:Subscriber)-[:SUBSCRIBED]->(cb)
WHERE s.name CONTAINS o.name OR o.name CONTAINS s.name
RETURN c.name as company,
       o.name as officer,
       s.name as subscriber,
       cb.bond_name as bond
```

#### 순환 소유 구조 찾기
```cypher
MATCH path = (c:Company)-[:HAS_AFFILIATE*2..5]->(c)
RETURN path
LIMIT 10
```

#### 특정 투자자가 투자한 모든 회사
```cypher
MATCH (s:Subscriber {name: "신한투자증권 주식회사"})-[:INVESTED_IN]->(c:Company)
RETURN c.name as company
ORDER BY c.name
```

#### 회사의 임원 + 계열사 + CB 통합 조회
```cypher
MATCH (c:Company {name: "LG전자"})
OPTIONAL MATCH (c)<-[:WORKS_AT]-(o:Officer)
OPTIONAL MATCH (c)-[:HAS_AFFILIATE]->(a:Company)
OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
RETURN c.name as company,
       COLLECT(DISTINCT o.name)[..10] as officers,
       COLLECT(DISTINCT a.name) as affiliates,
       COLLECT(DISTINCT cb.bond_name) as bonds
```

## 3. 검색 팁

### 회사 이름으로 검색
```cypher
MATCH (c:Company)
WHERE c.name CONTAINS "삼성"
RETURN c.name
LIMIT 10
```

### 임원 이름으로 검색
```cypher
MATCH (o:Officer)
WHERE o.name CONTAINS "김"
RETURN o.name, o.position
LIMIT 10
```

### 직책으로 검색
```cypher
MATCH (o:Officer)
WHERE o.position CONTAINS "대표이사"
RETURN o.name, o.position
LIMIT 10
```

## 4. 시각화 모드

Neo4j Browser에서는 결과를 다음 형태로 볼 수 있습니다:
- **Graph**: 노드와 관계를 시각적으로 표시
- **Table**: 테이블 형태로 데이터 표시
- **Text**: 텍스트로 결과 표시

쿼리 결과 우측 상단에서 모드를 전환할 수 있습니다.

## 5. 데이터 내보내기

### CSV로 내보내기
```cypher
MATCH (c:Company)<-[:WORKS_AT]-(o:Officer)
WITH c.name as company, COUNT(o) as officer_count
RETURN company, officer_count
ORDER BY officer_count DESC
```
실행 후 우측 상단의 다운로드 버튼 클릭

## 6. 주의사항

- 대량의 데이터를 조회할 때는 `LIMIT`을 사용하세요
- 복잡한 쿼리는 시간이 걸릴 수 있습니다
- 시각화는 노드 100-200개 정도가 적당합니다

## 7. 도움말

Neo4j Browser에서 `:help` 명령어를 입력하면 더 많은 정보를 볼 수 있습니다.

```cypher
:help MATCH
:help RETURN
:help WHERE
```
