# 시계열 이력 관리 전략 보고서
## Temporal Data Management Strategy for Officers & Convertible Bonds

**작성일**: 2025-11-21
**작성자**: 풀스택 전문 개발자 (20년 경력)
**목적**: 임원 및 전환사채의 다중 재직/발행 이력 관리 방안

---

## 🎯 **핵심 요구사항 분석**

### 비즈니스 시나리오

#### 1. 임원 (Officers) - 복잡한 경력 패턴

**케이스 A: 동일 회사, 다중 임기**
```
예시: 김철수 → 삼성전자
- 2020.01 ~ 2021.12: 상무 (1차 임기)
- 2022.01 ~ 2024.12: 전무 (재선임, 승진)
- 2025.01 ~ 현재: 부사장 (3차 임기)

⚠️ 문제: 현재 설계는 1개 레코드만 저장
→ 최신 상태만 보임 → 경력 변화 추적 불가
```

**케이스 B: 다중 회사, 겸직**
```
예시: 이영희
- 2022.01 ~ 2023.12: A회사 이사
- 2023.01 ~ 현재: B회사 감사 (겸직)
- 2024.01 ~ 현재: C회사 사외이사 (겸직)

⚠️ 문제: current_company_id가 1개만
→ 겸직 정보 누락 → 네트워크 분석 왜곡
```

**케이스 C: 회사 간 이동**
```
예시: 박영수
- 2020.01 ~ 2021.12: SK하이닉스 상무
- 2022.01 ~ 2023.12: 삼성전자 전무 (이직)
- 2024.01 ~ 현재: LG전자 부사장 (재이직)

✅ 필요: 각 재직 기간을 별도 레코드로 저장
→ 이직 패턴 분석 가능
→ 리스크 탐지 (빈번한 이동)
```

#### 2. 전환사채 (Convertible Bonds) - 발행 이력

**케이스 A: 동일 회사, 다중 발행**
```
예시: ABC기업
- 2022.03: 제1회 전환사채 500억 발행
- 2023.06: 제2회 전환사채 300억 발행
- 2024.01: 제3회 전환사채 700억 발행

✅ 필요: 각각 별도 레코드
→ 과도한 CB 발행 패턴 탐지
→ 재무 악화 신호
```

**케이스 B: 인수자가 다른 회사 대표**
```
예시: DEF기업 CB
- 인수자: 김대표 (GHI기업 대표이사)
- 특수관계: is_related_party = TRUE

✅ 필요: 인수자의 다른 회사 관계 추적
→ 순환 투자 구조 탐지
→ 특수관계자 거래 분석
```

#### 3. 공시 날짜 기준 이력

**핵심**: 모든 데이터는 **공시일 기준**으로 저장

```
공시 보고서 A (2023.03.15 제출)
→ 임원: 김철수 (상무, 임기: 2023.01~2025.12)
→ 이 정보는 2023.03.15 기준 사실

공시 보고서 B (2024.03.20 제출)
→ 임원: 김철수 (전무, 임기: 2024.01~2026.12)
→ 승진 사실, 새로운 레코드 필요

⚠️ 만약 하나로 합치면:
- 2023.03.15 ~ 2024.03.20 사이 상태 알 수 없음
- 승진 시점 추적 불가
- 감사/분석 불가능
```

---

## 📐 **데이터베이스 설계 전략**

### 전략 1: 이력 테이블 패턴 (Recommended ⭐)

#### A. Officers - 이력 테이블 분리

**현재 설계 (문제)**:
```sql
CREATE TABLE officers (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    current_company_id UUID,  -- ❌ 1개만
    position VARCHAR(100),     -- ❌ 현재 직책만
    career_history JSONB       -- ❌ 구조화 안됨
);
```

**개선 설계 (이력 관리)**:
```sql
-- 1. 임원 마스터 테이블 (인물 정보)
CREATE TABLE officers (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    birth_year INTEGER,
    education TEXT[],

    -- 네트워크 지표 (집계값)
    total_positions INTEGER DEFAULT 0,
    total_companies INTEGER DEFAULT 0,
    influence_score FLOAT,

    -- 메타데이터
    first_seen_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. 임원 재직 이력 테이블 (시계열)
CREATE TABLE officer_positions (
    id UUID PRIMARY KEY,
    officer_id UUID REFERENCES officers(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,

    -- 재직 정보
    position VARCHAR(100) NOT NULL,
    position_type VARCHAR(50),  -- 사내이사, 사외이사, 감사, 상근, 비상근

    -- 기간 (중요!)
    term_start_date DATE,
    term_end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,

    -- 공시 출처 (추적 가능성)
    source_disclosure_id UUID REFERENCES disclosures(rcept_no),
    source_report_date DATE NOT NULL,  -- 공시일
    source_report_type VARCHAR(100),   -- 보고서 종류

    -- 상세 정보
    appointment_reason TEXT,
    duties TEXT,

    -- 리스크 플래그
    is_related_party BOOLEAN DEFAULT FALSE,
    conflict_of_interest BOOLEAN DEFAULT FALSE,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스
    UNIQUE(officer_id, company_id, term_start_date, source_report_date)
);

-- 인덱스 (성능 최적화)
CREATE INDEX idx_officer_positions_officer_id ON officer_positions(officer_id);
CREATE INDEX idx_officer_positions_company_id ON officer_positions(company_id);
CREATE INDEX idx_officer_positions_dates ON officer_positions(term_start_date, term_end_date);
CREATE INDEX idx_officer_positions_current ON officer_positions(is_current) WHERE is_current = TRUE;
CREATE INDEX idx_officer_positions_source_date ON officer_positions(source_report_date);
```

**데이터 예시**:
```sql
-- officers 테이블
INSERT INTO officers VALUES (
    'uuid-1234',
    '김철수',
    'Kim Chul-soo',
    1970,
    ARRAY['서울대 경영학과', 'Harvard MBA'],
    3,  -- 총 3번 재직
    2,  -- 2개 회사
    0.85,  -- 영향력 점수
    '2020-01-01',  -- 처음 발견
    '2025-11-21',  -- 마지막 갱신
    NOW(),
    NOW()
);

-- officer_positions 테이블
INSERT INTO officer_positions VALUES
-- 1차 재직: 삼성전자 상무
('pos-1', 'uuid-1234', 'samsung-id', '상무', '사내이사',
 '2020-01-01', '2021-12-31', FALSE,
 'disclosure-2020-03', '2020-03-15', '정기주주총회소집공고',
 '신규 선임', '경영관리', FALSE, FALSE, NOW(), NOW()),

-- 2차 재직: 삼성전자 전무 (승진)
('pos-2', 'uuid-1234', 'samsung-id', '전무', '사내이사',
 '2022-01-01', '2024-12-31', FALSE,
 'disclosure-2022-03', '2022-03-20', '정기주주총회소집공고',
 '재선임', '전략기획', FALSE, FALSE, NOW(), NOW()),

-- 3차 재직: 삼성전자 부사장 (현재)
('pos-3', 'uuid-1234', 'samsung-id', '부사장', '사내이사',
 '2025-01-01', NULL, TRUE,
 'disclosure-2025-03', '2025-03-18', '정기주주총회소집공고',
 '재선임', '글로벌영업', FALSE, FALSE, NOW(), NOW());
```

#### B. Convertible Bonds - 발행 이력

**현재 설계**:
```sql
CREATE TABLE convertible_bonds (
    id UUID PRIMARY KEY,
    company_id UUID,
    bond_name VARCHAR(200),
    issue_date DATE,
    issue_amount INTEGER,
    -- ...
    UNIQUE(company_id, bond_name, issue_date)  -- ✅ 이미 다중 발행 지원
);
```
→ **이미 설계가 올바름!** 각 발행마다 별도 레코드

**추가 개선사항**:
```sql
ALTER TABLE convertible_bonds ADD COLUMN series_number INTEGER;
ALTER TABLE convertible_bonds ADD COLUMN source_disclosure_id UUID;
ALTER TABLE convertible_bonds ADD COLUMN source_report_date DATE;

-- 공시 추적 가능
CREATE INDEX idx_cb_source_report ON convertible_bonds(source_report_date);
```

#### C. CB Subscribers - 인수 이력

**현재 설계**:
```sql
CREATE TABLE cb_subscribers (
    id UUID PRIMARY KEY,
    cb_id UUID REFERENCES convertible_bonds(id),
    subscriber_name VARCHAR(200),
    subscription_amount INTEGER,
    is_related_party BOOLEAN,
    -- ...
);
```
→ **문제**: 인수자가 다른 회사 임원인지 추적 불가

**개선 설계**:
```sql
-- CB 인수자 테이블 개선
CREATE TABLE cb_subscribers (
    id UUID PRIMARY KEY,
    cb_id UUID REFERENCES convertible_bonds(id) ON DELETE CASCADE,

    -- 인수자 정보
    subscriber_name VARCHAR(200) NOT NULL,
    subscriber_type VARCHAR(50),  -- 개인, 법인, 기관투자자

    -- ⭐ 인수자가 임원인 경우 연결
    subscriber_officer_id UUID REFERENCES officers(id),  -- NULL 가능

    -- ⭐ 인수자가 회사인 경우 연결
    subscriber_company_id UUID REFERENCES companies(id),  -- NULL 가능

    -- 투자 정보
    subscription_amount INTEGER,
    subscription_ratio FLOAT,
    subscription_date DATE,

    -- 관계 정보
    is_related_party BOOLEAN DEFAULT FALSE,
    relationship_desc VARCHAR(200),
    relationship_type VARCHAR(50),  -- 계열사, 최대주주, 임원, 가족 등

    -- 공시 출처
    source_disclosure_id UUID,
    source_report_date DATE,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_subscribers_officer ON cb_subscribers(subscriber_officer_id);
CREATE INDEX idx_subscribers_company ON cb_subscribers(subscriber_company_id);
CREATE INDEX idx_subscribers_related ON cb_subscribers(is_related_party) WHERE is_related_party = TRUE;
```

**데이터 예시**:
```sql
-- 케이스 1: 인수자가 다른 회사 대표
INSERT INTO cb_subscribers VALUES (
    'sub-001',
    'cb-abc-2024',  -- ABC기업 2024년 CB
    '김대표',
    '개인',
    'officer-kim',  -- ⭐ 임원 테이블과 연결
    NULL,
    100000000,  -- 1억
    5.0,
    '2024-01-15',
    TRUE,  -- 특수관계자
    'DEF기업 대표이사',
    '임원',
    'disclosure-2024-01',
    '2024-01-20',
    NOW()
);

-- 케이스 2: 인수자가 계열사
INSERT INTO cb_subscribers VALUES (
    'sub-002',
    'cb-abc-2024',
    'GHI기업',
    '법인',
    NULL,
    'company-ghi',  -- ⭐ 회사 테이블과 연결
    500000000,  -- 5억
    25.0,
    '2024-01-15',
    TRUE,
    '계열사',
    '계열사',
    'disclosure-2024-01',
    '2024-01-20',
    NOW()
);
```

---

### 전략 2: Neo4j 그래프 구조 개선

#### A. Officer Career Path (경력 그래프)

**현재 구조 (문제)**:
```cypher
(Officer)-[:WORKS_AT]->(Company)
// 1개 관계만 → 현재 재직만 표현
```

**개선 구조 (시계열)**:
```cypher
// 1. 각 재직 기간마다 별도 관계
(Officer:Officer {id: "uuid-kim"})
  -[:HELD_POSITION {
      position: "상무",
      term_start: date("2020-01-01"),
      term_end: date("2021-12-31"),
      is_current: false,
      source_report_date: date("2020-03-15"),
      appointment_reason: "신규 선임"
  }]->(Company:Company {id: "samsung"})

(Officer:Officer {id: "uuid-kim"})
  -[:HELD_POSITION {
      position: "전무",
      term_start: date("2022-01-01"),
      term_end: date("2024-12-31"),
      is_current: false,
      source_report_date: date("2022-03-20")
  }]->(Company:Company {id: "samsung"})

(Officer:Officer {id: "uuid-kim"})
  -[:HOLDS_POSITION {  // 현재 재직은 다른 타입
      position: "부사장",
      term_start: date("2025-01-01"),
      term_end: null,
      is_current: true,
      source_report_date: date("2025-03-18")
  }]->(Company:Company {id: "samsung"})

// 2. 겸직 표현 (동시에 여러 회사)
(Officer:Officer {id: "uuid-lee"})
  -[:HOLDS_POSITION {
      position: "이사",
      term_start: date("2022-01-01"),
      is_current: true
  }]->(Company:Company {id: "company-a"})

(Officer:Officer {id: "uuid-lee"})
  -[:HOLDS_POSITION {
      position: "감사",
      term_start: date("2023-01-01"),
      is_current: true
  }]->(Company:Company {id: "company-b"})
```

**쿼리 예시 - 경력 이동 추적**:
```cypher
// 김철수의 전체 경력 (시계열 순)
MATCH (o:Officer {id: "uuid-kim"})-[r:HELD_POSITION|HOLDS_POSITION]->(c:Company)
RETURN o.name, c.name, r.position, r.term_start, r.term_end, r.is_current
ORDER BY r.term_start

// 2년 이내 3번 이상 이직한 임원 (리스크 패턴)
MATCH (o:Officer)-[r:HELD_POSITION]->(c:Company)
WHERE r.term_start >= date("2023-01-01")
WITH o, COUNT(DISTINCT c) as company_count
WHERE company_count >= 3
RETURN o.name, company_count
ORDER BY company_count DESC
```

#### B. CB Investment Network (투자 네트워크)

**현재 구조**:
```cypher
(Subscriber)-[:SUBSCRIBED]->(ConvertibleBond)-[:ISSUED_BY]->(Company)
```

**개선 구조 (관계 연결)**:
```cypher
// 1. 인수자 노드 분리
(Person:Person {id: "uuid-kim", name: "김대표"})
  -[:IS_OFFICER_OF {
      company_id: "company-def",
      position: "대표이사",
      is_current: true
  }]->(Company:Company {id: "company-def"})

// 2. CB 인수 관계
(Person:Person {id: "uuid-kim"})
  -[:INVESTED_IN_CB {
      cb_id: "cb-abc-2024",
      amount: 100000000,
      ratio: 5.0,
      date: date("2024-01-15"),
      is_related_party: true,
      relationship: "타사 대표이사"
  }]->(ConvertibleBond:CB {id: "cb-abc-2024"})

(ConvertibleBond:CB {id: "cb-abc-2024"})
  -[:ISSUED_BY]->(Company:Company {id: "company-abc"})

// 3. 순환 투자 구조 탐지 가능
// ABC기업 → CB → 김대표 → DEF기업 → CB → 박이사 → ABC기업
```

**쿼리 예시 - 순환 투자 탐지**:
```cypher
// 3-hop 이내 순환 투자
MATCH path = (c1:Company)-[:ISSUED_BY*..3]-(c2:Company)
WHERE c1.id = c2.id AND length(path) > 1
RETURN path, length(path) as cycle_length
ORDER BY cycle_length
```

---

### 전략 3: 공시 출처 추적 (Audit Trail)

#### A. Disclosures 테이블 강화

```sql
CREATE TABLE disclosures (
    rcept_no VARCHAR(20) PRIMARY KEY,  -- 접수번호
    corp_code VARCHAR(8) NOT NULL,
    company_id UUID REFERENCES companies(id),

    -- 공시 정보
    report_nm VARCHAR(200) NOT NULL,
    rcept_dt VARCHAR(8) NOT NULL,  -- YYYYMMDD
    flr_nm VARCHAR(200),  -- 제출인

    -- 분류
    report_type VARCHAR(100),

    -- 파일 정보
    xml_url TEXT,
    pdf_url TEXT,
    html_url TEXT,

    -- 파싱 상태
    is_parsed BOOLEAN DEFAULT FALSE,
    parsed_at TIMESTAMP,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW()
);

-- 파싱된 데이터 (구조화)
CREATE TABLE disclosure_parsed_data (
    id UUID PRIMARY KEY,
    rcept_no VARCHAR(20) REFERENCES disclosures(rcept_no),

    -- 파싱 섹션
    section_type VARCHAR(100),  -- officers, cb, affiliates, financials

    -- 데이터 (JSONB)
    parsed_data JSONB NOT NULL,

    -- 메타데이터
    parsed_at TIMESTAMP DEFAULT NOW(),
    parser_version VARCHAR(20)
);

-- 인덱스
CREATE INDEX idx_disclosures_date ON disclosures(rcept_dt);
CREATE INDEX idx_disclosures_company ON disclosures(company_id);
CREATE INDEX idx_parsed_section ON disclosure_parsed_data(section_type);
CREATE INDEX idx_parsed_data_jsonb ON disclosure_parsed_data USING GIN (parsed_data);
```

#### B. 데이터 연결 (Foreign Keys)

```sql
-- officer_positions 테이블
ALTER TABLE officer_positions
ADD COLUMN source_disclosure_id VARCHAR(20) REFERENCES disclosures(rcept_no);

-- convertible_bonds 테이블
ALTER TABLE convertible_bonds
ADD COLUMN source_disclosure_id VARCHAR(20) REFERENCES disclosures(rcept_no);

-- cb_subscribers 테이블
ALTER TABLE cb_subscribers
ADD COLUMN source_disclosure_id VARCHAR(20) REFERENCES disclosures(rcept_no);

-- affiliates 테이블
ALTER TABLE affiliates
ADD COLUMN source_disclosure_id VARCHAR(20) REFERENCES disclosures(rcept_no);
```

**장점**:
1. **추적 가능성**: 모든 데이터를 원본 공시로 역추적 가능
2. **검증 가능성**: 공시 원문과 비교하여 데이터 정확성 확인
3. **감사 대응**: 규제 기관 요청 시 근거 자료 제시

---

## 🔄 **데이터 흐름 및 처리 로직**

### Flow 1: 공시 수집 → 파싱 → 저장

```python
# 1. 공시 크롤링
disclosure = fetch_dart_disclosure(rcept_no="20240115001234")

# 2. DB 저장
disclosure_record = Disclosure(
    rcept_no="20240115001234",
    corp_code="00126380",
    report_nm="주주총회소집공고",
    rcept_dt="20240115",
    # ...
)
db.add(disclosure_record)
db.commit()

# 3. 공시 파싱 (임원 정보 추출)
parsed_officers = parse_officer_section(disclosure.xml_content)
# 결과: [
#   {"name": "김철수", "position": "부사장", "term_start": "2025-01-01", ...},
#   {"name": "이영희", "position": "감사", "term_start": "2025-01-01", ...}
# ]

# 4. officer_positions에 저장 (각각 별도 레코드)
for officer_data in parsed_officers:
    # 4-1. 임원 마스터 확인/생성
    officer = db.query(Officer).filter_by(name=officer_data["name"]).first()
    if not officer:
        officer = Officer(
            id=uuid.uuid4(),
            name=officer_data["name"],
            first_seen_at=datetime.now()
        )
        db.add(officer)

    # 4-2. 재직 이력 추가 (⭐ 항상 새 레코드)
    position = OfficerPosition(
        id=uuid.uuid4(),
        officer_id=officer.id,
        company_id=company.id,
        position=officer_data["position"],
        term_start_date=officer_data["term_start"],
        term_end_date=officer_data.get("term_end"),
        is_current=(officer_data.get("term_end") is None),
        source_disclosure_id="20240115001234",  # ⭐ 출처 추적
        source_report_date=date(2024, 1, 15),
        created_at=datetime.now()
    )
    db.add(position)

    # 4-3. 기존 재직 is_current 업데이트
    if officer_data.get("term_end") is None:
        # 새로운 재직이 current라면, 이전 재직은 종료 처리
        db.query(OfficerPosition)\
            .filter_by(officer_id=officer.id, company_id=company.id, is_current=True)\
            .filter(OfficerPosition.id != position.id)\
            .update({"is_current": False, "term_end_date": date(2024, 12, 31)})

db.commit()
```

### Flow 2: 중복 방지 로직 (CRITICAL)

**문제**: 같은 공시를 2번 파싱하면 중복 데이터 생성

**해결책**: UNIQUE 제약 + UPSERT

```sql
-- UNIQUE 제약 추가
ALTER TABLE officer_positions
ADD CONSTRAINT unique_officer_position
UNIQUE (officer_id, company_id, term_start_date, source_disclosure_id);

-- PostgreSQL UPSERT
INSERT INTO officer_positions (
    id, officer_id, company_id, position, term_start_date,
    source_disclosure_id, source_report_date, created_at
)
VALUES (
    uuid_generate_v4(), 'officer-uuid', 'company-uuid', '부사장', '2025-01-01',
    '20240115001234', '2024-01-15', NOW()
)
ON CONFLICT (officer_id, company_id, term_start_date, source_disclosure_id)
DO UPDATE SET
    position = EXCLUDED.position,
    updated_at = NOW();
```

**Python (SQLAlchemy)**:
```python
from sqlalchemy.dialects.postgresql import insert

stmt = insert(OfficerPosition).values(
    id=uuid.uuid4(),
    officer_id=officer.id,
    company_id=company.id,
    position="부사장",
    term_start_date=date(2025, 1, 1),
    source_disclosure_id="20240115001234",
    source_report_date=date(2024, 1, 15)
)

# ON CONFLICT DO UPDATE
stmt = stmt.on_conflict_do_update(
    index_elements=['officer_id', 'company_id', 'term_start_date', 'source_disclosure_id'],
    set_={
        'position': stmt.excluded.position,
        'updated_at': datetime.now()
    }
)

db.execute(stmt)
db.commit()
```

### Flow 3: 겸직 처리 (동시에 여러 회사)

```python
# 공시 A: ABC기업 임원 현황 (2024-03-15)
# "이영희, 감사, 임기: 2024-01-01 ~ 2025-12-31"

# 공시 B: DEF기업 임원 현황 (2024-03-20)
# "이영희, 사외이사, 임기: 2024-01-01 ~ 2025-12-31"

# 처리 결과:
# officer_positions 테이블
# | officer_id  | company_id | position   | term_start | is_current |
# |-------------|------------|------------|------------|------------|
# | lee-uuid    | abc-id     | 감사       | 2024-01-01 | TRUE       |
# | lee-uuid    | def-id     | 사외이사   | 2024-01-01 | TRUE       |

# ✅ 2개 레코드 → 겸직 정상 표현
# ✅ Neo4j에서 쿼리:
# MATCH (o:Officer {id: "lee-uuid"})-[r:HOLDS_POSITION]->(c:Company)
# WHERE r.is_current = true
# RETURN c.name, r.position
# // 결과: ABC기업-감사, DEF기업-사외이사
```

---

## 📊 **프론트엔드 활용 방안**

### 1. Company Detail Page - Officers Tab

**UI 설계**:
```typescript
interface OfficerTimelineItem {
    id: string;
    officer_name: string;
    position: string;
    term_start_date: string;
    term_end_date: string | null;
    is_current: boolean;
    source_report_date: string;
}

// API 호출
const fetchOfficerHistory = async (companyId: string) => {
    const response = await api.get(`/api/companies/${companyId}/officer-history`);
    // 응답: [
    //   { name: "김철수", positions: [
    //       { position: "상무", term: "2020-2021", is_current: false },
    //       { position: "전무", term: "2022-2024", is_current: false },
    //       { position: "부사장", term: "2025-현재", is_current: true }
    //   ]},
    //   ...
    // ]
    return response.data;
};
```

**화면 레이아웃**:
```
┌─────────────────────────────────────────────────────────┐
│ 임원 현황 (Officers)                                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 김철수                                    영향력: ★★★★☆ │
│ ├─ 2020.01 ~ 2021.12: 상무 (사내이사)                   │
│ ├─ 2022.01 ~ 2024.12: 전무 (사내이사)                   │
│ └─ 2025.01 ~ 현재: 부사장 (사내이사) [현재 재직]         │
│                                                          │
│ 이영희                                    영향력: ★★★☆☆ │
│ ├─ 2024.01 ~ 현재: ABC기업 감사 [겸직]                  │
│ └─ 2024.01 ~ 현재: DEF기업 사외이사 [겸직]              │
│                                                          │
│ ⚠️ 리스크 신호:                                         │
│ • 이영희: 겸직 2곳 (리스크 중간)                         │
│ • 김철수: 동일 회사 3차 연임 (장기 재직)                │
└─────────────────────────────────────────────────────────┘
```

### 2. Officer Detail Page - Career Timeline

**시계열 그래프**:
```
김철수의 경력

2020 ──┬── 삼성전자 상무
       │
2021 ──┤
       │
2022 ──┼── 삼성전자 전무 (승진)
       │
2023 ──┤
       │
2024 ──┤
       │
2025 ──┼── 삼성전자 부사장 (현재)
       │
       └──

리스크 분석:
✅ 안정적 경력 (1개 회사, 3차 승진)
✅ 장기 재직 (5년+)
⚠️ 외부 경험 부족
```

### 3. Network Graph - Relationship Visualization

**그래프 시각화**:
```
        [김대표]
           │
           │ 대표이사
           ↓
        [DEF기업]
           │
           │ CB 인수 (1억, 5%)
           ↓
    [ABC기업 2024 CB]
           │
           │ 발행사
           ↓
        [ABC기업] ← [박이사] (사외이사)

⚠️ 순환 투자 리스크:
• 김대표(DEF기업 대표) → ABC기업 CB 인수
• ABC기업 사외이사 박이사 → DEF기업 주주
```

### 4. API 엔드포인트 설계

```python
# FastAPI 엔드포인트

@router.get("/companies/{company_id}/officer-history")
async def get_officer_history(company_id: str, db: AsyncSession = Depends(get_db)):
    """
    회사의 임원 이력 조회 (시계열)

    응답:
    {
        "company_id": "uuid",
        "company_name": "삼성전자",
        "officers": [
            {
                "officer_id": "uuid",
                "officer_name": "김철수",
                "positions": [
                    {
                        "position": "상무",
                        "term_start": "2020-01-01",
                        "term_end": "2021-12-31",
                        "is_current": false,
                        "duration_months": 24,
                        "source_report_date": "2020-03-15"
                    },
                    // ...
                ]
            }
        ]
    }
    """
    query = select(OfficerPosition)\
        .options(selectinload(OfficerPosition.officer))\
        .where(OfficerPosition.company_id == company_id)\
        .order_by(OfficerPosition.term_start_date.desc())

    result = await db.execute(query)
    positions = result.scalars().all()

    # 그룹화 (officer_id별)
    officer_groups = {}
    for pos in positions:
        if pos.officer_id not in officer_groups:
            officer_groups[pos.officer_id] = []
        officer_groups[pos.officer_id].append(pos)

    # 응답 구성
    officers = []
    for officer_id, position_list in officer_groups.items():
        officers.append({
            "officer_id": str(officer_id),
            "officer_name": position_list[0].officer.name,
            "positions": [
                {
                    "position": pos.position,
                    "term_start": pos.term_start_date.isoformat(),
                    "term_end": pos.term_end_date.isoformat() if pos.term_end_date else None,
                    "is_current": pos.is_current,
                    "source_report_date": pos.source_report_date.isoformat()
                }
                for pos in position_list
            ]
        })

    return {
        "company_id": company_id,
        "officers": officers
    }

@router.get("/officers/{officer_id}/career-path")
async def get_officer_career_path(officer_id: str, db: AsyncSession = Depends(get_db)):
    """
    임원의 전체 경력 경로 (모든 회사)

    응답:
    {
        "officer_id": "uuid",
        "officer_name": "이영희",
        "career_timeline": [
            {
                "company_id": "uuid",
                "company_name": "ABC기업",
                "position": "감사",
                "term_start": "2024-01-01",
                "is_current": true
            },
            {
                "company_id": "uuid",
                "company_name": "DEF기업",
                "position": "사외이사",
                "term_start": "2024-01-01",
                "is_current": true
            }
        ],
        "risk_indicators": {
            "concurrent_positions": 2,  // 겸직 수
            "job_changes": 0,           // 이직 횟수
            "average_tenure_years": 1.5
        }
    }
    """
    pass

@router.get("/cb/{cb_id}/subscribers-network")
async def get_cb_subscribers_network(cb_id: str, db: AsyncSession = Depends(get_db)):
    """
    CB 인수자 네트워크 (임원/계열사 관계)

    응답:
    {
        "cb_id": "uuid",
        "bond_name": "ABC기업 제1회 전환사채",
        "subscribers": [
            {
                "subscriber_id": "uuid",
                "subscriber_name": "김대표",
                "is_officer": true,
                "officer_company": "DEF기업",
                "officer_position": "대표이사",
                "subscription_amount": 100000000,
                "is_related_party": true,
                "relationship_type": "타사 임원"
            }
        ],
        "risk_signals": [
            {
                "type": "CROSS_COMPANY_INVESTMENT",
                "severity": "HIGH",
                "description": "타사 대표이사의 CB 인수 (특수관계자)"
            }
        ]
    }
    """
    pass
```

---

## 🎯 **리스크 탐지 활용**

### 1. 임원 이동 패턴 리스크

```sql
-- 2년 이내 3회 이상 이직한 임원
SELECT
    o.id,
    o.name,
    COUNT(DISTINCT op.company_id) as company_count,
    ARRAY_AGG(DISTINCT c.name ORDER BY c.name) as companies,
    MIN(op.term_start_date) as first_position,
    MAX(op.term_end_date) as last_position
FROM officers o
JOIN officer_positions op ON o.id = op.officer_id
JOIN companies c ON op.company_id = c.id
WHERE op.term_start_date >= CURRENT_DATE - INTERVAL '2 years'
GROUP BY o.id, o.name
HAVING COUNT(DISTINCT op.company_id) >= 3
ORDER BY company_count DESC;
```

### 2. 겸직 리스크

```sql
-- 현재 3개 이상 회사에서 재직 중인 임원
SELECT
    o.id,
    o.name,
    COUNT(*) as concurrent_positions,
    ARRAY_AGG(c.name || ' (' || op.position || ')') as positions
FROM officers o
JOIN officer_positions op ON o.id = op.officer_id
JOIN companies c ON op.company_id = c.id
WHERE op.is_current = TRUE
GROUP BY o.id, o.name
HAVING COUNT(*) >= 3
ORDER BY concurrent_positions DESC;
```

### 3. CB 인수 - 특수관계자 리스크

```sql
-- CB 인수자가 다른 회사 임원인 케이스
SELECT
    cb.id as cb_id,
    c_issuer.name as issuing_company,
    cb.bond_name,
    cb.issue_amount,
    sub.subscriber_name,
    c_officer.name as officer_company,
    op.position as officer_position,
    sub.subscription_amount,
    sub.subscription_ratio
FROM cb_subscribers sub
JOIN convertible_bonds cb ON sub.cb_id = cb.id
JOIN companies c_issuer ON cb.company_id = c_issuer.id
LEFT JOIN officers o ON sub.subscriber_officer_id = o.id
LEFT JOIN officer_positions op ON o.id = op.officer_id AND op.is_current = TRUE
LEFT JOIN companies c_officer ON op.company_id = c_officer.id
WHERE sub.subscriber_officer_id IS NOT NULL
  AND c_issuer.id != c_officer.id  -- 다른 회사 임원
ORDER BY sub.subscription_amount DESC;
```

### 4. 순환 투자 구조 (Neo4j)

```cypher
// 3-hop 이내 순환 투자 탐지
MATCH path = (c1:Company)-[:ISSUED_CB]->(:CB)<-[:INVESTED_IN]-(p:Person)
                         -[:IS_OFFICER_OF]->(c2:Company)-[:ISSUED_CB]->(:CB)
                         <-[:INVESTED_IN]-(p2:Person)-[:IS_OFFICER_OF]->(c1)
WHERE c1.id <> c2.id
RETURN
    c1.name as company_a,
    p.name as investor_1,
    c2.name as company_b,
    p2.name as investor_2,
    length(path) as cycle_length
ORDER BY cycle_length
LIMIT 50
```

---

## 📈 **마이그레이션 계획**

### Phase 1: 스키마 변경 (즉시)

```sql
-- 1. 새 테이블 생성
CREATE TABLE officer_positions (...);
CREATE TABLE officer_career_summary (...);

-- 2. 기존 데이터 마이그레이션
INSERT INTO officer_positions (
    id, officer_id, company_id, position,
    term_start_date, term_end_date, is_current,
    created_at
)
SELECT
    uuid_generate_v4(),
    id as officer_id,
    current_company_id as company_id,
    position,
    COALESCE(
        (career_history->0->>'from')::DATE,
        CURRENT_DATE - INTERVAL '1 year'
    ) as term_start_date,
    CASE
        WHEN (career_history->0->>'to')::TEXT = 'present' THEN NULL
        ELSE (career_history->0->>'to')::DATE
    END as term_end_date,
    TRUE as is_current,
    created_at
FROM officers
WHERE current_company_id IS NOT NULL;

-- 3. 외래키 추가
ALTER TABLE officer_positions
ADD CONSTRAINT fk_officer FOREIGN KEY (officer_id) REFERENCES officers(id);

ALTER TABLE officer_positions
ADD CONSTRAINT fk_company FOREIGN KEY (company_id) REFERENCES companies(id);
```

### Phase 2: 공시 재파싱 (1주일)

```bash
# 2022-2025 공시 재파싱
python3 scripts/reparse_disclosures.py \
    --start-date 2022-01-01 \
    --end-date 2025-06-30 \
    --types "주주총회,임원현황,전환사채발행"
```

### Phase 3: Neo4j 동기화 (1주일)

```bash
# PostgreSQL → Neo4j 동기화
python3 scripts/sync_officer_positions_to_neo4j.py
python3 scripts/sync_cb_network_to_neo4j.py
```

---

## ✅ **체크리스트**

### 데이터베이스

- [ ] `officer_positions` 테이블 생성
- [ ] UNIQUE 제약 추가
- [ ] 인덱스 생성
- [ ] 외래키 설정
- [ ] `cb_subscribers` 개선 (officer_id, company_id 추가)
- [ ] 공시 출처 컬럼 추가 (모든 테이블)

### 백엔드

- [ ] UPSERT 로직 구현
- [ ] API 엔드포인트 추가 (`officer-history`, `career-path`)
- [ ] Neo4j 동기화 스크립트
- [ ] 중복 방지 로직
- [ ] 리스크 탐지 쿼리 업데이트

### 프론트엔드

- [ ] Officer 타임라인 컴포넌트
- [ ] Career Path 시각화
- [ ] 겸직 표시 UI
- [ ] 네트워크 그래프 업데이트
- [ ] 리스크 신호 표시

### 테스트

- [ ] 동일 회사 다중 임기 테스트
- [ ] 겸직 케이스 테스트
- [ ] 회사 이동 추적 테스트
- [ ] CB 인수자-임원 연결 테스트
- [ ] 순환 투자 탐지 테스트

---

## 🎯 **결론**

### 핵심 원칙

1. **절대 합치지 마라** (Never Merge)
   - 각 재직 기간 = 별도 레코드
   - 각 CB 발행 = 별도 레코드
   - 각 인수 = 별도 레코드

2. **공시일 기록 필수** (Always Track Source)
   - `source_disclosure_id`
   - `source_report_date`
   - 추적 가능성 확보

3. **시계열 우선** (Temporal First)
   - `term_start_date`, `term_end_date` 필수
   - `is_current` 플래그로 현재 상태 표시
   - 이력 조회 시 날짜 정렬

### 비즈니스 가치

1. **관계형 리스크 탐지**
   - 순환 투자 구조
   - 특수관계자 거래
   - 임원 이동 패턴

2. **시계열 분석**
   - 경력 변화 추적
   - CB 발행 빈도 분석
   - 트렌드 파악

3. **감사 대응**
   - 모든 데이터를 공시로 역추적
   - 데이터 정합성 검증
   - 규제 리포팅

---

**작성일**: 2025-11-21
**다음 단계**: 승인 후 구현 시작
**예상 기간**: 2주
