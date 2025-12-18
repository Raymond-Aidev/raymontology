# Raymontology 유료 웹 서비스 구현 계획서

## 📌 프로젝트 개요

**서비스명**: Raymontology
**목적**: 기업 관계망 분석 및 위험신호 탐지 유료 웹 서비스
**핵심 가치**:
- 재무제표 분석
- 네트워크 시각화 (임원, 계열사, CB)
- 위험신호 자동 탐지
- 인터랙티브 그래프 탐색

---

## 🎯 Phase 0: 그래프 데이터 구조 재설계 (최우선)

### ⚠️ 현재 문제점

1. **임원 경력 데이터**
   - 현재: Officer.properties (JSON)에 경력 이력 저장
   - 문제: 그래프 관계로 표현 안 됨 → 클릭 탐색 불가능

2. **CB 인수자 데이터**
   - 현재: Subscriber 노드만 존재
   - 문제: "다른 CB에도 투자했는지" 탐색 불가능

### ✅ 해결 방안: 그래프 관계 확장

#### 1. 임원 경력 관계 추가

**새로운 관계 타입:**
```cypher
(Officer)-[:WORKED_AT {
  start_date: "2020-01",
  end_date: "2023-12",
  position: "사장",
  is_current: false
}]->(Company)

(Officer)-[:WORKS_AT {
  start_date: "2024-01",
  position: "대표이사",
  is_current: true
}]->(Company)
```

**Officer 노드 속성 추가:**
```
Officer {
  id: UUID,
  name: String,
  current_position: String,
  career_count: Integer,  // 총 경력 회사 수
  career_years: Integer,  // 총 경력 년수
  influence_score: Float  // 경력 기반 영향력 점수
}
```

**시각화 규칙:**
- `career_count` 0-2개: 옅은 파란색
- `career_count` 3-5개: 파란색
- `career_count` 6-10개: 진한 파란색
- `career_count` 11개 이상: 남색

#### 2. CB 투자 이력 관계 확장

**현재 구조:**
```cypher
(Company)-[:ISSUED]->(CB)<-[:SUBSCRIBED]-(Subscriber)
```

**확장 구조:**
```cypher
(Company)-[:ISSUED]->(CB)
(Subscriber)-[:SUBSCRIBED {
  subscription_amount: 1000000000,
  subscription_ratio: 15.5,
  subscription_date: "2024-01-15"
}]->(CB)

// 새로운 관계: 투자자 → 회사 직접 연결
(Subscriber)-[:INVESTED_IN {
  total_amount: 5000000000,  // 누적 투자액
  investment_count: 3,        // 투자 횟수
  first_investment: "2020-01",
  latest_investment: "2024-03"
}]->(Company)
```

**Subscriber 노드 속성 추가:**
```
Subscriber {
  id: UUID,
  name: String,
  type: String,  // "individual", "company", "institution"
  total_investments: Integer,  // 총 투자 건수
  total_companies: Integer,    // 투자한 회사 수
  total_amount: BigInt,        // 총 투자 금액
  investor_type: String        // "angel", "vc", "strategic", "financial"
}
```

**시각화 규칙:**
- `total_investments` 1-2건: 옅은 녹색
- `total_investments` 3-5건: 녹색
- `total_investments` 6-10건: 진한 녹색
- `total_investments` 11건 이상: 짙은 녹색

---

## 🔧 Phase 1: 그래프 데이터 변환 작업

### 작업 1-1: 임원 경력 이력 관계화

**파일:** `scripts/convert_officer_career_to_graph.py`

**처리 로직:**
1. PostgreSQL에서 모든 Officer 읽기
2. `properties` JSON에서 `career` 배열 추출
3. 각 경력마다:
   - 회사명으로 Company 노드 찾기 (매칭 로직 필요)
   - `WORKED_AT` 관계 생성 (과거 경력)
   - `WORKS_AT` 관계는 현재 회사만
4. Officer 노드의 `career_count` 계산
5. `influence_score` 계산 (경력 회사 수 + 직급 가중치)

**난이도:** 중
**예상 소요:** 2-3일

### 작업 1-2: CB 투자 이력 집계

**파일:** `scripts/aggregate_cb_investments.py`

**처리 로직:**
1. Neo4j에서 모든 `(Subscriber)-[:SUBSCRIBED]->(CB)<-[:ISSUED]-(Company)` 패턴 조회
2. Subscriber별로 그룹핑:
   - 투자한 회사 리스트
   - 회사별 총 투자액, 투자 건수
   - 첫/마지막 투자일
3. `INVESTED_IN` 관계 생성 (Subscriber → Company)
4. Subscriber 노드 속성 업데이트

**난이도:** 하
**예상 소요:** 1일

---

## 🎨 Phase 2: 인터랙티브 그래프 UI 구현

### 핵심 요구사항 정리

#### 요구사항 1: 임원 클릭 → 경력 회사 표시

**사용자 시나리오:**
```
1. 그래프에서 임원 노드 클릭
2. 우측 패널에 상세 정보 표시:
   - 이름, 현재 직책
   - 경력 이력 리스트 (시간순)
   - "경력 회사 보기" 버튼
3. 버튼 클릭 시:
   - 해당 임원의 WORKED_AT 관계 노드들 그래프에 추가 표시
4. 경력 회사 노드 클릭 시:
   - 그 회사 중심으로 네트워크 재구성
```

**Cypher 쿼리:**
```cypher
// 1. 임원 상세 정보
MATCH (o:Officer {id: $officer_id})
OPTIONAL MATCH (o)-[r:WORKED_AT]->(c:Company)
RETURN o,
       COLLECT({
         company: c.name,
         position: r.position,
         start_date: r.start_date,
         end_date: r.end_date
       }) as career_history
ORDER BY r.start_date DESC

// 2. 경력 회사 네트워크 확장
MATCH (o:Officer {id: $officer_id})-[r:WORKED_AT]->(c:Company)
OPTIONAL MATCH (c)<-[:WORKS_AT]-(other:Officer)
OPTIONAL MATCH (c)-[:HAS_AFFILIATE]->(aff:Company)
OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
RETURN o, r, c, other, aff, cb
LIMIT 100

// 3. 특정 회사 중심으로 전환
MATCH (c:Company {id: $company_id})
OPTIONAL MATCH (c)<-[:WORKS_AT]-(o:Officer)
OPTIONAL MATCH (c)-[:HAS_AFFILIATE]->(aff:Company)
OPTIONAL MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
OPTIONAL MATCH (cb)<-[:SUBSCRIBED]-(s:Subscriber)
RETURN c, o, aff, cb, s
LIMIT 100
```

#### 요구사항 2: CB 클릭 → 인수자 투자 이력 표시

**사용자 시나리오:**
```
1. 그래프에서 CB 노드 클릭
2. 우측 패널에 상세 정보 표시:
   - CB 명칭, 발행일, 발행금액
   - 인수자 리스트 (인수 비율 포함)
3. 인수자 항목 클릭 시:
   - 하위 패널 확장: "이 투자자의 다른 투자 이력"
   - 투자한 회사 리스트 표시
4. 회사명 클릭 시:
   - 그 회사가 발행한 CB들 그래프에 추가 표시
5. CB 노드 클릭 시:
   - 그 CB를 발행한 회사 중심으로 네트워크 재구성
```

**Cypher 쿼리:**
```cypher
// 1. CB 상세 정보 + 인수자
MATCH (c:Company)-[:ISSUED]->(cb:ConvertibleBond {id: $cb_id})
MATCH (s:Subscriber)-[r:SUBSCRIBED]->(cb)
RETURN c.name as issuer,
       cb,
       COLLECT({
         subscriber: s.name,
         amount: r.subscription_amount,
         ratio: r.subscription_ratio,
         date: r.subscription_date
       }) as subscribers

// 2. 특정 인수자의 투자 이력
MATCH (s:Subscriber {id: $subscriber_id})-[inv:INVESTED_IN]->(c:Company)
RETURN s,
       COLLECT({
         company: c.name,
         total_amount: inv.total_amount,
         investment_count: inv.investment_count,
         first_investment: inv.first_investment,
         latest_investment: inv.latest_investment
       }) as investment_history
ORDER BY inv.latest_investment DESC

// 3. 특정 인수자가 투자한 회사들의 CB 네트워크
MATCH (s:Subscriber {id: $subscriber_id})-[:INVESTED_IN]->(c:Company)
MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
OPTIONAL MATCH (cb)<-[:SUBSCRIBED]-(other:Subscriber)
RETURN s, c, cb, other
LIMIT 200

// 4. CB를 발행한 회사 중심으로 전환
MATCH (cb:ConvertibleBond {id: $cb_id})<-[:ISSUED]-(c:Company)
OPTIONAL MATCH (c)<-[:WORKS_AT]-(o:Officer)
OPTIONAL MATCH (c)-[:HAS_AFFILIATE]->(aff:Company)
OPTIONAL MATCH (c)-[:ISSUED]->(other_cb:ConvertibleBond)
RETURN c, o, aff, cb, other_cb
LIMIT 100
```

### 작업 2-1: Backend API 개발

**파일:** `app/api/endpoints/graph.py`

**엔드포인트:**

```python
# 1. 회사 중심 네트워크
GET /api/v1/graph/company/{company_id}?depth=1&limit=100
Response: {
  "nodes": [...],
  "relationships": [...],
  "center": {"type": "Company", "id": "..."}
}

# 2. 임원 경력 이력 조회
GET /api/v1/graph/officer/{officer_id}/career
Response: {
  "officer": {...},
  "career_history": [
    {
      "company_id": "...",
      "company_name": "LG전자",
      "position": "사장",
      "start_date": "2018-01",
      "end_date": "2022-12",
      "is_current": false
    }
  ]
}

# 3. 임원 경력 네트워크 확장
GET /api/v1/graph/officer/{officer_id}/career-network
Response: {
  "nodes": [...],
  "relationships": [...]
}

# 4. CB 인수자 투자 이력
GET /api/v1/graph/subscriber/{subscriber_id}/investments
Response: {
  "subscriber": {...},
  "investment_history": [
    {
      "company_id": "...",
      "company_name": "엑시온그룹",
      "total_amount": 1500000000,
      "investment_count": 2,
      "first_investment": "2022-03",
      "latest_investment": "2024-06",
      "cbs": [...]
    }
  ]
}

# 5. 인수자 투자 네트워크 확장
GET /api/v1/graph/subscriber/{subscriber_id}/investment-network
Response: {
  "nodes": [...],
  "relationships": [...]
}

# 6. 노드 중심 전환 (범용)
POST /api/v1/graph/recenter
Body: {
  "node_type": "Company|Officer|CB|Subscriber",
  "node_id": "...",
  "depth": 1,
  "limit": 100
}
Response: {
  "nodes": [...],
  "relationships": [...]
}
```

**난이도:** 중
**예상 소요:** 3-4일

### 작업 2-2: Frontend - 그래프 시각화

**기술 스택:**
- React 18
- neovis.js (Neo4j 공식)
- Tailwind CSS

**파일 구조:**
```
frontend/
├── src/
│   ├── components/
│   │   ├── GraphVisualization/
│   │   │   ├── GraphCanvas.tsx          // neovis.js 래핑
│   │   │   ├── NodeDetailPanel.tsx      // 노드 클릭 시 우측 패널
│   │   │   ├── OfficerCareerPanel.tsx   // 임원 경력 이력
│   │   │   ├── SubscriberInvestmentPanel.tsx  // 인수자 투자 이력
│   │   │   ├── GraphControls.tsx        // 확대/축소/필터
│   │   │   └── GraphLegend.tsx          // 범례
│   │   ├── SearchBar.tsx
│   │   └── CompanyDashboard.tsx
│   ├── hooks/
│   │   ├── useGraphData.ts
│   │   └── useNodeInteraction.ts
│   └── services/
│       ├── graphApi.ts
│       └── neovisConfig.ts
```

**GraphCanvas.tsx 핵심 로직:**

```typescript
interface GraphNode {
  id: string;
  type: 'Company' | 'Officer' | 'CB' | 'Subscriber';
  properties: any;
}

interface GraphRelationship {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: any;
}

const GraphCanvas: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [graphData, setGraphData] = useState<{nodes: GraphNode[], relationships: GraphRelationship[]}>();

  // neovis.js 초기화
  useEffect(() => {
    const config = {
      containerId: "graph-canvas",
      neo4j: {
        serverUrl: "bolt://localhost:7687",
        serverUser: "neo4j",
        serverPassword: "password"
      },
      labels: {
        Company: {
          label: "name",
          size: "total_connections",
          color: "#4A90E2"
        },
        Officer: {
          label: "name",
          size: "influence_score",
          color: (node) => {
            // 경력 회사 수에 따라 색상 진하기 조절
            const careerCount = node.properties.career_count || 0;
            if (careerCount <= 2) return "#A8D8FF";
            if (careerCount <= 5) return "#5AAEFF";
            if (careerCount <= 10) return "#2E7DD4";
            return "#1A4D8F";
          }
        },
        ConvertibleBond: {
          label: "bond_name",
          color: "#50C878"
        },
        Subscriber: {
          label: "name",
          color: (node) => {
            const investmentCount = node.properties.total_investments || 0;
            if (investmentCount <= 2) return "#C7F5C7";
            if (investmentCount <= 5) return "#6FD66F";
            if (investmentCount <= 10) return "#3BA13B";
            return "#1E5F1E";
          }
        }
      },
      relationships: {
        WORKS_AT: { color: "#999", width: 2 },
        WORKED_AT: { color: "#CCC", width: 1, dashed: true },
        HAS_AFFILIATE: { color: "#E67E22", width: 2 },
        ISSUED: { color: "#9B59B6", width: 2 },
        SUBSCRIBED: { color: "#27AE60", width: 2 },
        INVESTED_IN: { color: "#16A085", width: 2 }
      },
      onNodeClick: (node) => {
        handleNodeClick(node);
      }
    };

    const viz = new NeoVis(config);
    viz.render();
  }, []);

  // 노드 클릭 핸들러
  const handleNodeClick = async (node: any) => {
    const nodeData: GraphNode = {
      id: node.id,
      type: node.labels[0],
      properties: node.properties
    };
    setSelectedNode(nodeData);

    // 타입별 처리 로직
    if (nodeData.type === 'Officer') {
      // 임원 경력 이력 로드
      const careerData = await fetchOfficerCareer(nodeData.id);
      setCareerHistory(careerData);
    } else if (nodeData.type === 'Subscriber') {
      // 인수자 투자 이력 로드
      const investmentData = await fetchSubscriberInvestments(nodeData.id);
      setInvestmentHistory(investmentData);
    }
  };

  // 경력 네트워크 확장
  const handleExpandCareer = async (officerId: string) => {
    const networkData = await graphApi.getOfficerCareerNetwork(officerId);
    // 기존 그래프에 노드/관계 추가
    addNodesToGraph(networkData.nodes, networkData.relationships);
  };

  // 투자 네트워크 확장
  const handleExpandInvestments = async (subscriberId: string) => {
    const networkData = await graphApi.getSubscriberInvestmentNetwork(subscriberId);
    addNodesToGraph(networkData.nodes, networkData.relationships);
  };

  // 중심 노드 전환
  const handleRecenter = async (nodeType: string, nodeId: string) => {
    const newGraphData = await graphApi.recenterGraph(nodeType, nodeId);
    setGraphData(newGraphData);
    // 그래프 재렌더링
    rerenderGraph(newGraphData);
  };

  return (
    <div className="flex h-screen">
      <div id="graph-canvas" className="flex-1"></div>

      {selectedNode && (
        <NodeDetailPanel
          node={selectedNode}
          onExpandCareer={handleExpandCareer}
          onExpandInvestments={handleExpandInvestments}
          onRecenter={handleRecenter}
        />
      )}
    </div>
  );
};
```

**OfficerCareerPanel.tsx:**

```typescript
const OfficerCareerPanel: React.FC<{officer: Officer, onExpand: () => void, onRecenter: (companyId: string) => void}> = ({
  officer,
  onExpand,
  onRecenter
}) => {
  const [careerHistory, setCareerHistory] = useState<CareerHistory[]>([]);

  useEffect(() => {
    loadCareerHistory();
  }, [officer.id]);

  return (
    <div className="p-4 bg-white border-l">
      <h3 className="font-bold text-lg">{officer.name}</h3>
      <p className="text-gray-600">{officer.current_position}</p>

      <div className="mt-4">
        <div className="flex justify-between items-center mb-2">
          <h4 className="font-semibold">경력 이력</h4>
          <button
            onClick={onExpand}
            className="text-sm text-blue-600 hover:underline"
          >
            그래프에 표시
          </button>
        </div>

        <div className="space-y-2">
          {careerHistory.map((career, idx) => (
            <div
              key={idx}
              className="p-2 border rounded hover:bg-gray-50 cursor-pointer"
              onClick={() => onRecenter(career.company_id)}
            >
              <div className="font-medium">{career.company_name}</div>
              <div className="text-sm text-gray-600">{career.position}</div>
              <div className="text-xs text-gray-400">
                {career.start_date} ~ {career.end_date || '현재'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

**SubscriberInvestmentPanel.tsx:**

```typescript
const SubscriberInvestmentPanel: React.FC<{
  subscriber: Subscriber,
  onExpand: () => void,
  onRecenterToCompany: (companyId: string) => void,
  onRecenterToCB: (cbId: string) => void
}> = ({
  subscriber,
  onExpand,
  onRecenterToCompany,
  onRecenterToCB
}) => {
  const [investmentHistory, setInvestmentHistory] = useState<InvestmentHistory[]>([]);
  const [expandedCompany, setExpandedCompany] = useState<string | null>(null);

  return (
    <div className="p-4 bg-white border-l">
      <h3 className="font-bold text-lg">{subscriber.name}</h3>
      <p className="text-gray-600">총 {subscriber.total_investments}건 투자</p>

      <div className="mt-4">
        <div className="flex justify-between items-center mb-2">
          <h4 className="font-semibold">투자 이력</h4>
          <button
            onClick={onExpand}
            className="text-sm text-blue-600 hover:underline"
          >
            그래프에 표시
          </button>
        </div>

        <div className="space-y-2">
          {investmentHistory.map((inv) => (
            <div key={inv.company_id} className="border rounded">
              <div
                className="p-2 hover:bg-gray-50 cursor-pointer flex justify-between"
                onClick={() => {
                  if (expandedCompany === inv.company_id) {
                    setExpandedCompany(null);
                  } else {
                    setExpandedCompany(inv.company_id);
                  }
                }}
              >
                <div>
                  <div className="font-medium">{inv.company_name}</div>
                  <div className="text-sm text-gray-600">
                    {inv.investment_count}건 · {formatAmount(inv.total_amount)}
                  </div>
                </div>
                <ChevronDown className={expandedCompany === inv.company_id ? 'rotate-180' : ''} />
              </div>

              {expandedCompany === inv.company_id && (
                <div className="p-2 bg-gray-50 border-t">
                  <div className="text-sm font-medium mb-1">발행 CB 목록:</div>
                  {inv.cbs.map((cb) => (
                    <div
                      key={cb.id}
                      className="text-sm p-1 hover:bg-white cursor-pointer rounded"
                      onClick={() => onRecenterToCB(cb.id)}
                    >
                      {cb.bond_name} ({cb.issue_date})
                    </div>
                  ))}
                  <button
                    onClick={() => onRecenterToCompany(inv.company_id)}
                    className="mt-2 text-sm text-blue-600 hover:underline"
                  >
                    이 회사 중심으로 보기 →
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

**난이도:** 상
**예상 소요:** 5-7일

---

## 💰 Phase 3: 재무제표 데이터 수집

### 작업 3-1: DB 스키마 생성

**파일:** `alembic/versions/xxx_add_financial_statements.py`

**테이블:**
```sql
CREATE TABLE financial_statements (
  id UUID PRIMARY KEY,
  company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
  fiscal_year INTEGER NOT NULL,  -- 2022, 2023, 2024
  quarter VARCHAR(2),  -- NULL(연간), Q1, Q2, Q3, Q4
  statement_date DATE NOT NULL,

  -- 재무상태표
  cash_and_equivalents BIGINT,        -- 현금및현금성자산
  accounts_receivable BIGINT,         -- 매출채권
  inventory BIGINT,                   -- 재고자산
  current_assets BIGINT,              -- 유동자산
  current_liabilities BIGINT,         -- 유동부채
  total_liabilities BIGINT,           -- 부채총계
  total_equity BIGINT,                -- 자본총계

  -- 손익계산서
  revenue BIGINT,                     -- 매출액
  cost_of_sales BIGINT,               -- 매출원가
  accounts_payable BIGINT,            -- 매입채무

  data_source VARCHAR(50),  -- "annual_report", "quarterly_report"
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(company_id, fiscal_year, quarter)
);

CREATE INDEX idx_financial_company ON financial_statements(company_id);
CREATE INDEX idx_financial_year ON financial_statements(fiscal_year);

CREATE TABLE financial_metrics (
  id UUID PRIMARY KEY,
  company_id UUID REFERENCES companies(id) ON DELETE CASCADE UNIQUE,

  -- 계산된 지표
  cash_amount_billion DECIMAL(10, 2),       -- 현금자산 (억원)
  revenue_cagr DECIMAL(5, 2),               -- 매출 CAGR (%)
  receivables_turnover DECIMAL(10, 2),      -- 매출채권 회전율
  payables_turnover DECIMAL(10, 2),         -- 매입채무 회전율
  inventory_turnover DECIMAL(10, 2),        -- 재고자산 회전율
  debt_ratio DECIMAL(10, 2),                -- 부채비율 (%)
  current_ratio DECIMAL(10, 2),             -- 유동비율 (%)

  -- 메타 정보
  data_quality_score INTEGER,  -- 0-100, 데이터 완전성
  last_updated TIMESTAMP,
  calculation_date TIMESTAMP DEFAULT NOW(),

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

**난이도:** 하
**예상 소요:** 0.5일

### 작업 3-2: 재무제표 XML 파서

**파일:** `scripts/financial_statement_parser.py`

**처리 로직:**

1. **XML 항목명 매핑 테이블**
```python
ACCOUNT_MAPPINGS = {
    "cash": [
        "현금및현금성자산",
        "현금 및 현금성자산",
        "현금및현금성자산총계",
        "Cash and cash equivalents"
    ],
    "accounts_receivable": [
        "매출채권",
        "매출채권 및 기타채권",
        "매출채권과 기타유동채권",
        "Trade receivables"
    ],
    # ... (전체 항목 매핑)
}
```

2. **파싱 함수**
```python
def parse_financial_statement(xml_path: Path) -> Dict:
    """사업보고서/분기보고서 XML에서 재무제표 추출"""
    tree = ET.parse(xml_path)

    # 재무상태표 파싱
    balance_sheet = parse_balance_sheet(tree)

    # 손익계산서 파싱
    income_statement = parse_income_statement(tree)

    return {
        "fiscal_year": extract_fiscal_year(tree),
        "quarter": extract_quarter(tree),
        "statement_date": extract_statement_date(tree),
        **balance_sheet,
        **income_statement
    }

def find_account_value(tree: ET.Element, account_names: List[str]) -> Optional[int]:
    """항목명 리스트에서 매칭되는 첫 번째 값 반환"""
    for name in account_names:
        # XPath로 검색
        for elem in tree.findall(f".//*[contains(text(), '{name}')]"):
            value_elem = elem.find(".//금액") or elem.find(".//amount")
            if value_elem is not None:
                return parse_amount(value_elem.text)
    return None

def parse_amount(text: str) -> int:
    """금액 문자열을 정수로 변환 (쉼표, 괄호 처리)"""
    # "1,234,567" → 1234567
    # "(123)" → -123 (손실)
    if not text:
        return None
    text = text.replace(",", "").replace(" ", "")
    if text.startswith("(") and text.endswith(")"):
        return -int(text[1:-1])
    return int(text)
```

**난이도:** 중
**예상 소요:** 3-4일

### 작업 3-3: 재무 데이터 수집 스크립트

**파일:** `scripts/collect_financial_data.py`

**처리 로직:**
```python
async def collect_financial_data():
    """기존 수집된 사업보고서에서 재무제표 추출"""

    # 1. 회사별로 사업보고서 XML 찾기
    companies = await get_all_companies()

    for company in companies:
        print(f"Processing: {company.name}")

        # 2. 2022~2024 사업보고서 찾기 (매출 CAGR용)
        for year in [2022, 2023, 2024]:
            report = find_annual_report(company.corp_code, year)
            if report:
                data = parse_financial_statement(report.xml_path)
                await save_financial_statement(company.id, data)

        # 3. 최신 분기보고서 찾기 (2025 Q2)
        quarterly = find_latest_quarterly_report(company.corp_code)
        if quarterly:
            data = parse_financial_statement(quarterly.xml_path)
            await save_financial_statement(company.id, data)

async def save_financial_statement(company_id: UUID, data: Dict):
    """재무제표 데이터 저장"""
    stmt = FinancialStatement(
        company_id=company_id,
        fiscal_year=data["fiscal_year"],
        quarter=data.get("quarter"),
        statement_date=data["statement_date"],
        cash_and_equivalents=data.get("cash"),
        revenue=data.get("revenue"),
        # ... 나머지 필드
    )
    db.session.add(stmt)
    await db.session.commit()
```

**난이도:** 중
**예상 소요:** 2일

### 작업 3-4: 재무지표 계산 엔진

**파일:** `app/services/financial_calculator.py`

```python
class FinancialCalculator:
    """재무지표 계산 엔진"""

    async def calculate_all_metrics(self, company_id: UUID) -> FinancialMetrics:
        """회사의 모든 재무지표 계산"""

        # 1. 재무제표 데이터 조회
        statements = await self.get_financial_statements(company_id)

        if not statements:
            return None

        # 2. 각 지표 계산
        metrics = FinancialMetrics(company_id=company_id)

        metrics.cash_amount_billion = self.calc_cash_amount(statements)
        metrics.revenue_cagr = self.calc_revenue_cagr(statements)
        metrics.receivables_turnover = self.calc_receivables_turnover(statements)
        metrics.payables_turnover = self.calc_payables_turnover(statements)
        metrics.inventory_turnover = self.calc_inventory_turnover(statements)
        metrics.debt_ratio = self.calc_debt_ratio(statements)
        metrics.current_ratio = self.calc_current_ratio(statements)

        # 3. 데이터 품질 점수 계산
        metrics.data_quality_score = self.calc_data_quality(metrics)

        return metrics

    def calc_cash_amount(self, statements: List[FinancialStatement]) -> Decimal:
        """현금자산총액 (억원)"""
        latest = self.get_latest_statement(statements)
        if not latest or not latest.cash_and_equivalents:
            return None
        return Decimal(latest.cash_and_equivalents) / 100_000_000  # 억원 변환

    def calc_revenue_cagr(self, statements: List[FinancialStatement]) -> Decimal:
        """매출 CAGR (2022~2024)"""
        # 연간 매출만 필터링
        annual = [s for s in statements if s.quarter is None]
        annual.sort(key=lambda x: x.fiscal_year)

        if len(annual) < 2:
            return None

        first_revenue = annual[0].revenue
        last_revenue = annual[-1].revenue
        years = annual[-1].fiscal_year - annual[0].fiscal_year

        if not first_revenue or not last_revenue or years == 0:
            return None

        cagr = ((last_revenue / first_revenue) ** (1 / years) - 1) * 100
        return round(Decimal(cagr), 2)

    def calc_receivables_turnover(self, statements: List[FinancialStatement]) -> Decimal:
        """매출채권 회전율"""
        latest = self.get_latest_statement(statements)
        if not latest or not latest.accounts_receivable or not latest.revenue:
            return None

        # 연환산 매출 / 평균 매출채권
        annualized_revenue = latest.revenue * (4 if latest.quarter else 1)
        turnover = annualized_revenue / latest.accounts_receivable
        return round(Decimal(turnover), 2)

    def calc_data_quality(self, metrics: FinancialMetrics) -> int:
        """데이터 품질 점수 (0-100)"""
        fields = [
            metrics.cash_amount_billion,
            metrics.revenue_cagr,
            metrics.receivables_turnover,
            metrics.payables_turnover,
            metrics.inventory_turnover,
            metrics.debt_ratio,
            metrics.current_ratio
        ]

        available = sum(1 for f in fields if f is not None)
        return int((available / len(fields)) * 100)
```

**난이도:** 중
**예상 소요:** 2일

### 작업 3-5: 재무지표 API

**파일:** `app/api/endpoints/financials.py`

```python
@router.get("/companies/{company_id}/financials")
async def get_company_financials(
    company_id: UUID,
    recalculate: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """회사 재무지표 조회"""

    # 1. 캐시 확인 (24시간 이내면 캐시 사용)
    if not recalculate:
        cached = await db.get(FinancialMetrics, company_id)
        if cached and (datetime.now() - cached.last_updated).days < 1:
            return {
                "company_id": company_id,
                "metrics": cached.to_dict(),
                "cached": True
            }

    # 2. 재계산
    calculator = FinancialCalculator(db)
    metrics = await calculator.calculate_all_metrics(company_id)

    if not metrics:
        raise HTTPException(404, "재무제표 데이터 없음")

    # 3. 캐시 저장
    await db.merge(metrics)
    await db.commit()

    return {
        "company_id": company_id,
        "metrics": metrics.to_dict(),
        "cached": False
    }

@router.get("/companies/{company_id}/financials/history")
async def get_financial_history(
    company_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """재무제표 시계열 데이터"""

    result = await db.execute(
        select(FinancialStatement)
        .where(FinancialStatement.company_id == company_id)
        .order_by(FinancialStatement.fiscal_year, FinancialStatement.quarter)
    )
    statements = result.scalars().all()

    return {
        "company_id": company_id,
        "statements": [s.to_dict() for s in statements]
    }
```

**난이도:** 하
**예상 소요:** 1일

---

## 🚨 Phase 4: 위험신호 탐지 시스템

### 작업 4-1: 위험 패턴 정의 및 탐지 쿼리

**파일:** `scripts/neo4j_risk_patterns.cypher`

**패턴 1: 자사주 CB 인수**
```cypher
// 임원 또는 대주주가 자사 CB 인수
MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
MATCH (c)-[:ISSUED]->(cb:ConvertibleBond)
MATCH (s:Subscriber)-[:SUBSCRIBED]->(cb)
WHERE s.name CONTAINS o.name OR o.name CONTAINS s.name
RETURN c.name as company,
       o.name as officer,
       s.name as subscriber,
       cb.bond_name as bond,
       'SELF_SUBSCRIPTION' as risk_type,
       80 as risk_score
```

**패턴 2: 순환 투자 구조**
```cypher
// A → B → C → A 형태의 투자
MATCH path = (c1:Company)-[:INVESTED_IN*2..4]->(c1)
WHERE length(path) >= 2
RETURN nodes(path) as companies,
       'CIRCULAR_INVESTMENT' as risk_type,
       95 as risk_score
```

**패턴 3: 임원 과다 겸직**
```cypher
// 한 임원이 5개 이상 회사 겸직
MATCH (o:Officer)-[:WORKS_AT]->(c:Company)
WITH o, COUNT(DISTINCT c) as company_count
WHERE company_count >= 5
RETURN o.name as officer,
       company_count,
       'EXCESSIVE_CONCURRENT_POSITIONS' as risk_type,
       60 as risk_score
```

**패턴 4: CB 과다 발행**
```cypher
// 최근 3년간 자본 대비 50% 이상 CB 발행
MATCH (c:Company)-[:ISSUED]->(cb:ConvertibleBond)
WHERE cb.issue_date >= date() - duration({years: 3})
WITH c, SUM(cb.issue_amount) as total_cb_amount
MATCH (fs:FinancialStatement {company_id: c.id})
WHERE fs.total_equity IS NOT NULL
WITH c, total_cb_amount, fs.total_equity
WHERE total_cb_amount > fs.total_equity * 0.5
RETURN c.name as company,
       total_cb_amount,
       fs.total_equity,
       (total_cb_amount * 100.0 / fs.total_equity) as cb_ratio,
       'EXCESSIVE_CB_ISSUANCE' as risk_type,
       75 as risk_score
```

**패턴 5: 계열사 순환 출자**
```cypher
// 3단계 이상 순환 출자
MATCH path = (c1:Company)-[:HAS_AFFILIATE*3..5]->(c1)
RETURN nodes(path) as companies,
       length(path) as depth,
       'CIRCULAR_AFFILIATE_STRUCTURE' as risk_type,
       85 as risk_score
```

**패턴 6: 동일 투자자 집중**
```cypher
// CB 인수의 70% 이상이 단일 투자자
MATCH (c:Company)-[:ISSUED]->(cb:ConvertibleBond)
MATCH (s:Subscriber)-[sub:SUBSCRIBED]->(cb)
WITH c, s, SUM(sub.subscription_amount) as investor_amount
WITH c,
     COLLECT({subscriber: s.name, amount: investor_amount}) as investors,
     SUM(investor_amount) as total_amount
UNWIND investors as inv
WITH c, inv, total_amount,
     (inv.amount * 100.0 / total_amount) as ratio
WHERE ratio >= 70
RETURN c.name as company,
       inv.subscriber as dominant_investor,
       ratio,
       'INVESTOR_CONCENTRATION' as risk_type,
       55 as risk_score
```

**패턴 7: 재무지표 악화**
```cypher
// 유동비율 100% 미만 + 부채비율 200% 이상
MATCH (c:Company)
MATCH (fm:FinancialMetrics {company_id: c.id})
WHERE fm.current_ratio < 100 AND fm.debt_ratio > 200
RETURN c.name as company,
       fm.current_ratio,
       fm.debt_ratio,
       'FINANCIAL_DETERIORATION' as risk_type,
       70 as risk_score
```

**패턴 8: 관계사 거래 집중**
```cypher
// 매출의 50% 이상이 계열사 거래 (향후 구현)
// 현재 데이터 없음, 추후 관계사 거래 데이터 수집 시 추가
```

**난이도:** 중
**예상 소요:** 2일

### 작업 4-2: 위험 분석 스크립트

**파일:** `scripts/neo4j_risk_analyzer.py`

```python
class RiskAnalyzer:
    """위험 패턴 분석기"""

    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.patterns = self.load_risk_patterns()

    def load_risk_patterns(self) -> List[RiskPattern]:
        """위험 패턴 정의 로드"""
        return [
            RiskPattern(
                name="자사주 CB 인수",
                type="SELF_SUBSCRIPTION",
                query=PATTERN_QUERIES["self_subscription"],
                base_score=80,
                severity="HIGH"
            ),
            # ... 나머지 패턴
        ]

    async def analyze_company_risks(self, company_id: UUID) -> CompanyRiskReport:
        """특정 회사의 모든 위험 패턴 분석"""

        risks_found = []

        for pattern in self.patterns:
            result = await self.check_pattern(company_id, pattern)
            if result:
                risks_found.extend(result)

        # 종합 위험도 계산
        total_score = self.calculate_total_risk(risks_found)
        risk_grade = self.classify_risk_grade(total_score)

        return CompanyRiskReport(
            company_id=company_id,
            risks=risks_found,
            total_score=total_score,
            grade=risk_grade,
            analysis_date=datetime.now()
        )

    async def check_pattern(self, company_id: UUID, pattern: RiskPattern) -> List[RiskSignal]:
        """특정 패턴 검사"""

        async with self.driver.session() as session:
            result = await session.run(
                pattern.query,
                company_id=str(company_id)
            )

            signals = []
            async for record in result:
                signal = RiskSignal(
                    pattern_type=pattern.type,
                    pattern_name=pattern.name,
                    risk_score=record["risk_score"],
                    severity=pattern.severity,
                    details=dict(record),
                    detected_at=datetime.now()
                )
                signals.append(signal)

            return signals

    def calculate_total_risk(self, risks: List[RiskSignal]) -> int:
        """종합 위험도 점수 계산"""

        if not risks:
            return 0

        # 가중 평균 방식
        total = sum(r.risk_score for r in risks)
        return min(int(total / len(risks)), 100)

    def classify_risk_grade(self, score: int) -> str:
        """위험 등급 분류"""
        if score >= 86:
            return "CRITICAL"
        elif score >= 71:
            return "HIGH"
        elif score >= 51:
            return "MEDIUM"
        elif score >= 31:
            return "LOW"
        else:
            return "SAFE"

    async def analyze_all_companies(self):
        """전체 회사 위험도 분석 (배치 작업)"""

        companies = await get_all_companies()

        for company in companies:
            logger.info(f"Analyzing: {company.name}")

            report = await self.analyze_company_risks(company.id)

            # DB에 저장
            await self.save_risk_report(report)

    async def save_risk_report(self, report: CompanyRiskReport):
        """위험 분석 결과 저장"""

        # risk_signals 테이블에 저장
        for risk in report.risks:
            signal = RiskSignal(
                company_id=report.company_id,
                pattern_type=risk.pattern_type,
                risk_score=risk.risk_score,
                severity=risk.severity,
                details=risk.details
            )
            db.session.add(signal)

        # companies 테이블 업데이트
        await db.execute(
            update(Company)
            .where(Company.id == report.company_id)
            .values(
                risk_score=report.total_score,
                risk_grade=report.grade,
                risk_updated_at=datetime.now()
            )
        )

        await db.session.commit()
```

**난이도:** 중
**예상 소요:** 3일

### 작업 4-3: 위험신호 API

**파일:** `app/api/endpoints/risks.py`

```python
@router.get("/companies/{company_id}/risks")
async def get_company_risks(
    company_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """회사 위험신호 조회"""

    # 1. 최신 위험 신호 조회
    result = await db.execute(
        select(RiskSignal)
        .where(RiskSignal.company_id == company_id)
        .order_by(RiskSignal.detected_at.desc())
    )
    signals = result.scalars().all()

    # 2. 회사 위험 등급 조회
    company = await db.get(Company, company_id)

    return {
        "company_id": company_id,
        "company_name": company.name,
        "risk_grade": company.risk_grade,
        "total_score": company.risk_score,
        "signals": [
            {
                "pattern": s.pattern_type,
                "name": s.pattern_name,
                "score": s.risk_score,
                "severity": s.severity,
                "details": s.details,
                "detected_at": s.detected_at
            }
            for s in signals
        ],
        "last_updated": company.risk_updated_at
    }

@router.get("/risks/patterns")
async def get_all_risk_patterns(
    pattern_type: Optional[str] = None,
    severity: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """전체 위험 패턴 조회"""

    query = select(RiskSignal)

    if pattern_type:
        query = query.where(RiskSignal.pattern_type == pattern_type)
    if severity:
        query = query.where(RiskSignal.severity == severity)

    result = await db.execute(query.order_by(RiskSignal.risk_score.desc()).limit(100))
    signals = result.scalars().all()

    return {
        "patterns": [s.to_dict() for s in signals]
    }

@router.get("/risks/alerts")
async def get_risk_alerts(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """사용자 관심 회사 위험 알림"""

    # 사용자 watchlist 조회
    watchlist = await get_user_watchlist(user_id, db)

    alerts = []
    for company_id in watchlist:
        # 최근 24시간 내 위험도 변화 확인
        new_signals = await get_recent_risk_signals(company_id, hours=24)
        if new_signals:
            alerts.append({
                "company_id": company_id,
                "new_signals": new_signals
            })

    return {"alerts": alerts}
```

**난이도:** 하
**예상 소요:** 1일

---

## 🔐 Phase 5: 사용자 인증 및 구독 관리

### 작업 5-1: 사용자 인증 시스템

**파일:** `app/auth/`

**기능:**
- 회원가입/로그인 (JWT)
- OAuth (Google, Kakao)
- 비밀번호 재설정
- 이메일 인증

**난이도:** 중
**예상 소요:** 3일

### 작업 5-2: 구독 플랜 관리

**테이블:**
```sql
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  plan VARCHAR(20),  -- "free", "basic", "pro", "enterprise"
  status VARCHAR(20),  -- "active", "cancelled", "expired"
  quota_used INTEGER DEFAULT 0,
  quota_limit INTEGER,
  started_at TIMESTAMP,
  expires_at TIMESTAMP,
  auto_renew BOOLEAN DEFAULT true
);

CREATE TABLE usage_logs (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  endpoint VARCHAR(100),
  query_type VARCHAR(50),
  timestamp TIMESTAMP DEFAULT NOW()
);
```

**난이도:** 중
**예상 소요:** 2일

### 작업 5-3: 결제 연동

**파일:** `app/payment/iamport.py`

**기능:**
- 아임포트 결제 연동
- 정기 결제 등록
- 결제 완료 Webhook
- 환불 처리

**난이도:** 중
**예상 소요:** 3일

---

## 📊 Phase 6: 대시보드 UI

### 작업 6-1: 회사 상세 페이지

**파일:** `frontend/src/pages/CompanyDetail.tsx`

**섹션:**
1. 헤더: 회사명, 종합 위험도 게이지
2. 탭1 - 재무분석: 7개 지표 카드
3. 탭2 - 위험신호: 발견된 위험 리스트
4. 탭3 - 네트워크: 그래프 시각화

**난이도:** 중
**예상 소요:** 4일

### 작업 6-2: 검색 및 필터

**파일:** `frontend/src/pages/Search.tsx`

**기능:**
- 회사명/티커 검색
- 산업별 필터
- 위험도 필터
- 재무지표 범위 필터

**난이도:** 하
**예상 소요:** 2일

---

## 🚀 Phase 7: 배포 및 운영

### 작업 7-1: 배치 작업 스케줄러

**파일:** `scripts/scheduler.py`

```python
# 매일 00:00 - 위험도 재계산
@scheduler.scheduled_job('cron', hour=0, minute=0)
async def daily_risk_analysis():
    analyzer = RiskAnalyzer()
    await analyzer.analyze_all_companies()

# 매일 01:00 - 재무지표 업데이트
@scheduler.scheduled_job('cron', hour=1, minute=0)
async def daily_financial_update():
    calculator = FinancialCalculator()
    await calculator.update_all_companies()

# 매월 1일 - 최신 분기보고서 수집
@scheduler.scheduled_job('cron', day=1, hour=2, minute=0)
async def monthly_quarterly_report_collection():
    collector = QuarterlyReportCollector()
    await collector.collect_latest()
```

**난이도:** 하
**예상 소요:** 1일

### 작업 7-2: 모니터링 설정

- Sentry (에러 추적)
- Prometheus + Grafana (서버 모니터링)
- Google Analytics (사용자 분석)

**난이도:** 중
**예상 소요:** 2일

---

## 📅 전체 일정 요약

| Phase | 작업 | 난이도 | 소요 | 우선순위 |
|-------|------|--------|------|---------|
| 0 | 그래프 데이터 재설계 | 중 | 4일 | ⭐⭐⭐ |
| 1 | 그래프 데이터 변환 | 중 | 4일 | ⭐⭐⭐ |
| 2 | 인터랙티브 그래프 UI | 상 | 8일 | ⭐⭐⭐ |
| 3 | 재무제표 수집/분석 | 중 | 9일 | ⭐⭐⭐ |
| 4 | 위험신호 탐지 | 중 | 6일 | ⭐⭐⭐ |
| 5 | 인증/구독 관리 | 중 | 8일 | ⭐⭐ |
| 6 | 대시보드 UI | 중 | 6일 | ⭐⭐ |
| 7 | 배포/운영 | 중 | 3일 | ⭐ |

**총 예상 소요: 48일 (약 2개월)**

---

## 🎯 MVP (Minimum Viable Product) 범위

**1차 출시 (4주):**
- Phase 0-2: 인터랙티브 그래프
- Phase 3: 재무제표 (기본 지표만)
- Phase 4: 위험신호 (5개 패턴만)

**2차 확장 (4주):**
- Phase 5: 인증/구독
- Phase 6: 대시보드
- Phase 7: 배포/운영

---

## ✅ 체크리스트

### 개발 전 준비
- [ ] 프론트엔드 프로젝트 생성 (React + Vite)
- [ ] neovis.js 설치 및 테스트
- [ ] Alembic migration 환경 설정
- [ ] 사업보고서 샘플 XML 수집 (테스트용)

### Phase 0-1 완료 조건
- [ ] Officer WORKED_AT 관계 생성 완료
- [ ] Subscriber INVESTED_IN 관계 생성 완료
- [ ] career_count, influence_score 계산 완료
- [ ] 색상 규칙 적용 확인

### Phase 2 완료 조건
- [ ] 임원 클릭 → 경력 패널 표시
- [ ] "경력 회사 보기" → 그래프 확장
- [ ] 경력 회사 클릭 → 중심 전환
- [ ] CB 클릭 → 인수자 패널 표시
- [ ] 인수자 클릭 → 투자 이력 확장
- [ ] 투자 회사 클릭 → 중심 전환

### Phase 3 완료 조건
- [ ] 재무제표 파싱 100개 회사 성공
- [ ] 7개 지표 모두 계산 가능
- [ ] API 응답 1초 이내

### Phase 4 완료 조건
- [ ] 8개 위험 패턴 모두 탐지 가능
- [ ] 위험도 점수 정확도 검증
- [ ] 배치 작업 1000개 회사 분석 완료

---

**작업 시작 명령 대기 중**
