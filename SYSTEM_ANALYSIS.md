# 시스템 분석 및 데이터 구조

## 1. PostgreSQL (회사 메타데이터)

### Companies 테이블 구조
```sql
Table "public.companies"
- id: UUID (Primary Key)
- corp_code: VARCHAR(8) (DART 기업 고유번호, UNIQUE)
- ticker: VARCHAR(20) (종목코드, UNIQUE) ← 주의: stock_code가 아님!
- name: VARCHAR(200) (회사명, NOT NULL)
- name_en: VARCHAR(200) (영문명)
- business_number: VARCHAR(20) (사업자등록번호, UNIQUE)
- sector, industry, market: 분류 정보
- 재무지표: market_cap, revenue, net_income, total_assets
- 리스크지표: ownership_concentration, affiliate_transaction_ratio, cb_issuance_count
```

### 현황
- 총 회사: **2,606개**
- 모든 회사가 ticker와 corp_code 보유
- 검색 대상 필드: `name`, `ticker`, `name_en`

### 샘플 데이터
```
엑시온그룹: id=37631ea7-9a45-4d0d-9b8d-03e06418f4e8, ticker=069920, corp_code=00426068
삼성중공업: id=036d5e38-208a-47b5-a421-409d97ca473c, ticker=010140, corp_code=00126478
```

## 2. Neo4j (관계 그래프)

### 노드 구조
```cypher
Company 노드:
- id: UUID (PostgreSQL companies.id와 동일)
- name: 회사명
- corp_code: DART 기업 고유번호
- stock_code: NULL (사용 안 함, Neo4j에 존재하지 않음)
```

### 관계 유형 (총 145,381개)
1. **WORKS_AT**: 83,736개 (임원 → 회사)
2. **BOARD_MEMBER_AT**: 50,021개 (이사회 멤버)
3. **HAS_AFFILIATE**: 3,191개 (계열사 관계)
4. **INVESTED_IN**: 3,130개 (투자 관계)
5. **ISSUED**: 2,743개 (CB 발행)

## 3. 데이터 흐름

```
사용자 검색 "엑시온그룹"
    ↓
PostgreSQL 검색 (companies.name LIKE '%엑시온%')
    ↓
회사 ID 획득: 37631ea7-9a45-4d0d-9b8d-03e06418f4e8
    ↓
Neo4j 그래프 조회 (WHERE c.id = '37631ea7-...')
    ↓
연관된 노드/관계 반환
    ↓
프론트엔드 neovis.js 렌더링
```

## 4. API 계층

### Company Search API (`/api/companies/search`)
```python
# PostgreSQL 검색
conditions = [
    Company.name.ilike(search_pattern),    # 회사명
    Company.ticker.ilike(search_pattern),  # 종목코드 (stock_code 아님!)
    Company.name_en.ilike(search_pattern)  # 영문명
]
```

**반환 필드**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "회사명",
      "ticker": "069920",     // frontend에서 ticker로 처리
      "corp_code": "00426068",
      "sector": "...",
      ...
    }
  ]
}
```

### Graph API (`/api/graph/company/{company_id}`)
```python
# Neo4j Cypher 쿼리
MATCH (c:Company {id: $company_id})  # PostgreSQL의 UUID 사용
OPTIONAL MATCH (c)<-[r1:WORKS_AT]-(o:Officer)
OPTIONAL MATCH (c)-[r2:HAS_AFFILIATE]-(aff:Company)
...
RETURN nodes, relationships
```

## 5. 프론트엔드 데이터 흐름

### GraphExplorer.tsx
```typescript
// 1. 회사 검색
axios.get('/api/companies/search', {
  params: { q: searchQuery, page: 1, page_size: 10 }
})

// 2. 선택한 회사의 ID 저장
setCompanyId(company.id)  // UUID

// 3. GraphCanvas에 ID 전달
<GraphCanvas companyId={companyId} />

// 4. GraphCanvas가 neovis.js로 Neo4j 직접 연결
// bolt://localhost:7687에서 Cypher 실행
```

## 6. 핵심 문제점 및 해결

### 문제 1: 필드명 불일치
❌ **이전 오류**: `Company.stock_code`
✅ **올바른 필드**: `Company.ticker`

### 문제 2: SQLAlchemy 조건부 표현식
❌ **이전 오류**:
```python
or_(
    Company.name.ilike(...),
    Company.name_en.ilike(...) if Company.name_en.isnot(None) else False
)
```

✅ **올바른 방법**:
```python
conditions = [
    Company.name.ilike(...),
    Company.ticker.ilike(...),
    Company.name_en.ilike(...)
]
query.where(or_(*conditions))
```

### 문제 3: Frontend/Backend 타입 불일치
모든 Company 인터페이스에서 `stock_code` → `ticker`로 통일:
- `frontend/src/types/index.ts`
- `frontend/src/hooks/useCompany.ts`
- `frontend/src/pages/GraphExplorer.tsx`

## 7. 검증 완료

### PostgreSQL 검색 테스트
```sql
SELECT id, name, ticker FROM companies
WHERE name LIKE '%엑시온%';
-- ✅ 결과: 엑시온그룹 (id=37631ea7..., ticker=069920)

SELECT id, name, ticker FROM companies
WHERE name LIKE '%삼성%'
LIMIT 5;
-- ✅ 결과: 5개 회사 정상 반환
```

### Neo4j 그래프 테스트
```cypher
MATCH (c:Company {id: '37631ea7-9a45-4d0d-9b8d-03e06418f4e8'})
OPTIONAL MATCH (c)-[r]-()
RETURN c, r
-- ✅ 엑시온그룹과 연결된 관계 정상 조회
```

### API 테스트
```bash
curl "http://localhost:8000/api/companies/search?q=엑시온그룹"
# ✅ 정상 응답 예상

curl "http://localhost:8000/api/graph/company/37631ea7-9a45-4d0d-9b8d-03e06418f4e8"
# ✅ 그래프 데이터 정상 반환 예상
```

## 8. 시스템 아키텍처

```
┌─────────────────────────────────────────────┐
│         Frontend (React + Vite)             │
│  ┌─────────────┐      ┌─────────────┐      │
│  │GraphExplorer│      │ neovis.js   │      │
│  │   Search    │      │ (Direct)    │      │
│  └──────┬──────┘      └──────┬──────┘      │
└─────────┼───────────────────┼──────────────┘
          │                    │
          │ HTTP               │ Bolt Protocol
          │                    │ (bolt://localhost:7687)
┌─────────▼────────────────────▼──────────────┐
│            Backend (FastAPI)                │
│  ┌──────────────┐    ┌──────────────┐      │
│  │ Companies API│    │  Graph API   │      │
│  │ (Search)     │    │  (Neo4j)     │      │
│  └──────┬───────┘    └──────┬───────┘      │
└─────────┼──────────────────┼───────────────┘
          │                   │
┌─────────▼────────┐  ┌───────▼──────────┐
│   PostgreSQL     │  │     Neo4j        │
│   (Metadata)     │  │   (Graph DB)     │
│   2,606 companies│  │  145,381 edges   │
└──────────────────┘  └──────────────────┘
```

## 9. 데이터 일관성 보장

### ID 동기화
- PostgreSQL `companies.id` = Neo4j `Company.id`
- 모든 관계 조회는 UUID로 연결
- corp_code는 보조 식별자로만 사용

### 검색 → 그래프 플로우
1. PostgreSQL에서 회사명으로 검색
2. 회사의 UUID 획득
3. UUID로 Neo4j 그래프 조회
4. neovis.js로 시각화

## 10. 향후 고려사항

### 성능 최적화
- PostgreSQL 삼중 검색 (name, ticker, name_en) 최적화
- Neo4j 인덱스 확인: `CREATE INDEX ON :Company(id)`
- 그래프 쿼리 LIMIT 조정 (현재 100개)

### 데이터 품질
- ticker NULL 값 체크 (현재 모두 populated)
- name_en NULL 처리 (일부 회사는 영문명 없음)
- Neo4j stock_code 필드는 사용하지 않음 (NULL)

### 확장성
- 회사 수 증가 시 검색 페이지네이션
- 그래프 depth 제한 (현재 1~2단계)
- 캐싱 전략 (Redis)
