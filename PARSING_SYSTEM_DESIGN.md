# DART 데이터 파싱 시스템 보완 설계서

## 1. 현재 상태 분석

### 1.1 DB 현황 (2025-12-09 기준)

| 테이블 | 현재 레코드 | 목표 | 달성률 | 상태 |
|--------|------------|------|--------|------|
| companies | 3,922 | 3,922 | 100% | 완료 |
| officers | 38,125 | ~96,000 | ~40% | 진행중 |
| officer_positions | 240,320 | ~120,000 | 200% | 완료(초과) |
| convertible_bonds | 1,435 | ~1,700 | ~84% | 진행중 |
| cb_subscribers | 8,656 | ~10,000 | ~87% | 진행중 |
| disclosures | 0 | ~228,000 | 0% | 미적재 |
| financial_statements | 0 | ~12,000 | 0% | 미적재 |
| risk_signals | 0 | ~50,000 | 0% | 미적재 |

### 1.2 원시 데이터 현황

```
backend/data/dart/
├── batch_001/ ~ batch_014/   # 14개 배치 폴더
│   └── {corp_code}/          # 회사별 폴더 (예: 00100957)
│       └── {year}/           # 연도별 폴더 (2022~2025)
│           ├── {rcept_no}.zip          # 공시 문서 ZIP
│           └── {rcept_no}_meta.json    # 메타데이터
└── logs/
```

- **총 ZIP 파일**: 228,395개
- **데이터 크기**: 9.2GB
- **회사 수**: 2,859개

### 1.3 기존 파싱 시스템 문제점

1. **단일 스레드 처리**: 병렬 처리 미지원
2. **재시작 어려움**: 체크포인트/상태 저장 없음
3. **에러 복구 취약**: 실패 시 전체 재시작 필요
4. **검증 부재**: 파싱 결과 검증 로직 없음
5. **Neo4j 동기화 분리**: PostgreSQL → Neo4j 동기화가 별도 스크립트

---

## 2. DDD (Domain-Driven Design) 구조

### 2.1 도메인 모델 (Domain Model)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Bounded Contexts                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   Company     │  │   Officer     │  │   Disclosure  │       │
│  │   Context     │  │   Context     │  │   Context     │       │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘       │
│          │                  │                  │                │
│          ▼                  ▼                  ▼                │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  CB/Finance   │  │    Risk       │  │    Graph      │       │
│  │   Context     │  │   Context     │  │   Context     │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 계층 구조 (Layered Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                          │
│         (FastAPI Routes, WebSocket, CLI Commands)               │
├─────────────────────────────────────────────────────────────────┤
│                     Application Layer                           │
│           (Use Cases, Application Services, DTOs)               │
├─────────────────────────────────────────────────────────────────┤
│                      Domain Layer                               │
│    (Entities, Value Objects, Domain Services, Repositories)     │
├─────────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                          │
│  (PostgreSQL, Neo4j, Redis, File System, External APIs)         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 핵심 도메인 엔티티

```python
# Domain Entities (Value Objects & Aggregates)

@dataclass(frozen=True)
class CorpCode:
    """기업 고유번호 Value Object"""
    value: str

    def __post_init__(self):
        if not re.match(r'^\d{8}$', self.value):
            raise ValueError(f"Invalid corp_code: {self.value}")

@dataclass(frozen=True)
class ReceptNo:
    """접수번호 Value Object"""
    value: str

    def __post_init__(self):
        if not re.match(r'^\d{14}$', self.value):
            raise ValueError(f"Invalid rcept_no: {self.value}")

@dataclass
class DisclosureAggregate:
    """공시 Aggregate Root"""
    rcept_no: ReceptNo
    corp_code: CorpCode
    report_type: str
    report_date: date
    file_path: Path

    # Nested entities
    officers: List[OfficerEntity]
    convertible_bonds: List[CBEntity]
    financial_data: Optional[FinancialEntity]

    def validate(self) -> List[ValidationError]:
        errors = []
        # Business rule validations
        return errors
```

---

## 3. 시스템 아키텍처

### 3.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DART 파싱 파이프라인                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│   │  Batch   │───▶│  Parser  │───▶│  Loader  │───▶│  Sync    │            │
│   │ Scanner  │    │  Engine  │    │ (PG)     │    │ (Neo4j)  │            │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘            │
│        │               │               │               │                   │
│        ▼               ▼               ▼               ▼                   │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│   │ State    │    │ Worker   │    │ Bulk     │    │ Graph    │            │
│   │ Manager  │    │ Pool     │    │ Insert   │    │ Builder  │            │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘            │
│        │               │               │               │                   │
│        └───────────────┴───────────────┴───────────────┘                   │
│                              │                                              │
│                              ▼                                              │
│                    ┌──────────────────┐                                    │
│                    │  Progress        │                                    │
│                    │  Monitor         │                                    │
│                    │  (Redis/File)    │                                    │
│                    └──────────────────┘                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 데이터 흐름 (Data Flow)

```
                         원시 데이터
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    1. Batch Scanner                             │
│                                                                 │
│   data/dart/batch_001/ ──┬── /00100957/2024/20240409002052.zip │
│                          │                                      │
│                          └── 메타데이터 수집 및 큐 생성         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    2. Parser Engine                             │
│                                                                 │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │ XML Parser  │     │ Table Parser│     │ NER Parser  │      │
│   │ (임원현황)  │     │ (CB/재무)   │     │ (경력추출)  │      │
│   └─────────────┘     └─────────────┘     └─────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    3. Domain Transformer                        │
│                                                                 │
│   Raw Data ──▶ Value Objects ──▶ Entities ──▶ Aggregates       │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ Validation Layer                                         │  │
│   │ - 데이터 타입 검증                                       │  │
│   │ - 비즈니스 규칙 검증                                     │  │
│   │ - 참조 무결성 검증                                       │  │
│   └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   4A. PostgreSQL Loader │     │   4B. Neo4j Sync        │
│                         │     │                         │
│   - Bulk COPY           │────▶│   - Company Nodes       │
│   - Upsert Logic        │     │   - Officer Nodes       │
│   - Constraint Check    │     │   - Relationship Edges  │
└─────────────────────────┘     └─────────────────────────┘
```

### 3.3 상태 관리 (State Management)

```python
@dataclass
class ParsingState:
    """파싱 작업 상태"""
    job_id: str
    status: JobStatus  # PENDING, RUNNING, PAUSED, COMPLETED, FAILED

    # Progress
    total_files: int
    processed_files: int
    failed_files: int

    # Checkpoints
    last_batch: int
    last_corp_code: str
    last_rcept_no: str

    # Statistics
    records_inserted: Dict[str, int]  # 테이블별 적재 건수
    errors: List[ErrorLog]

    # Timestamps
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
```

---

## 4. API 설계

### 4.1 REST API 엔드포인트

#### 4.1.1 Parsing Jobs API

```yaml
# 파싱 작업 관리

POST /api/v1/parsing/jobs
  Description: 새 파싱 작업 생성
  Request:
    {
      "job_type": "full" | "incremental" | "specific",
      "target": {
        "batches": [1, 2, 3],           # 특정 배치
        "corp_codes": ["00100957"],     # 특정 회사
        "date_range": {
          "start": "2024-01-01",
          "end": "2024-12-31"
        }
      },
      "options": {
        "parallel_workers": 4,
        "batch_size": 100,
        "skip_existing": true,
        "sync_neo4j": true
      }
    }
  Response:
    {
      "job_id": "pj_20241209_001",
      "status": "PENDING",
      "estimated_files": 50000,
      "created_at": "2024-12-09T10:00:00Z"
    }

GET /api/v1/parsing/jobs/{job_id}
  Description: 작업 상태 조회
  Response:
    {
      "job_id": "pj_20241209_001",
      "status": "RUNNING",
      "progress": {
        "total_files": 50000,
        "processed": 25000,
        "failed": 12,
        "percentage": 50.0
      },
      "stats": {
        "officers": 15000,
        "disclosures": 25000,
        "cb": 500
      },
      "checkpoint": {
        "batch": 7,
        "corp_code": "00150000",
        "rcept_no": "20240615001234"
      },
      "errors": [
        {"file": "xxx.zip", "error": "XML parsing failed", "timestamp": "..."}
      ]
    }

POST /api/v1/parsing/jobs/{job_id}/pause
  Description: 작업 일시 중지

POST /api/v1/parsing/jobs/{job_id}/resume
  Description: 중지된 작업 재개

DELETE /api/v1/parsing/jobs/{job_id}
  Description: 작업 취소
```

#### 4.1.2 Data Query API

```yaml
# 파싱된 데이터 조회

GET /api/v1/disclosures
  Description: 공시 목록 조회
  Query Params:
    - corp_code: string
    - report_type: string  # 사업보고서, 반기보고서, etc.
    - start_date: date
    - end_date: date
    - page: int
    - limit: int
  Response:
    {
      "items": [...],
      "total": 228395,
      "page": 1,
      "pages": 2284
    }

GET /api/v1/officers
  Description: 임원 목록 조회
  Query Params:
    - company_id: uuid
    - name: string (검색)
    - position: string
    - as_of_date: date  # 특정 시점 기준
  Response:
    {
      "items": [
        {
          "id": "uuid",
          "name": "홍길동",
          "birth_date": "1970.02",
          "current_position": "대표이사",
          "company": {
            "id": "uuid",
            "name": "삼성전자"
          },
          "positions_history": [
            {
              "company_name": "LG전자",
              "position": "이사",
              "term_start": "2018-03-01",
              "term_end": "2021-02-28"
            }
          ],
          "career_history": [
            {"company": "현대자동차", "position": "부장", "status": "former"}
          ]
        }
      ]
    }

GET /api/v1/convertible-bonds
  Description: 전환사채 목록 조회
  Query Params:
    - company_id: uuid
    - status: string
    - issue_date_from: date
    - issue_date_to: date

GET /api/v1/financial-statements/{company_id}
  Description: 재무제표 조회
  Query Params:
    - fiscal_year: int
    - quarter: string
```

#### 4.1.3 Graph API

```yaml
# Neo4j 그래프 조회

GET /api/v1/graph/company/{company_id}/network
  Description: 회사 중심 관계망 조회
  Query Params:
    - depth: int (1-3)
    - include_officers: bool
    - include_cb: bool
    - include_affiliates: bool
  Response:
    {
      "nodes": [
        {"id": "...", "type": "Company", "name": "삼성전자", ...},
        {"id": "...", "type": "Officer", "name": "홍길동", ...},
        {"id": "...", "type": "CB", "bond_name": "제1회 CB", ...}
      ],
      "edges": [
        {"source": "...", "target": "...", "type": "HAS_OFFICER"},
        {"source": "...", "target": "...", "type": "ISSUED"},
        {"source": "...", "target": "...", "type": "SUBSCRIBED"}
      ]
    }

GET /api/v1/graph/officer/{officer_id}/connections
  Description: 임원 연결망 조회

POST /api/v1/graph/query
  Description: 커스텀 Cypher 쿼리 실행 (관리자 전용)
  Request:
    {
      "cypher": "MATCH (c:Company)-[:ISSUED]->(cb:CB) RETURN c, cb LIMIT 10"
    }
```

#### 4.1.4 Risk Analysis API

```yaml
# 리스크 분석

POST /api/v1/risk/analyze
  Description: 리스크 분석 실행
  Request:
    {
      "company_id": "uuid",
      "analysis_types": ["circular_cb", "insider_trading", "related_party"]
    }
  Response:
    {
      "analysis_id": "ra_001",
      "status": "COMPLETED",
      "signals": [
        {
          "signal_id": "...",
          "pattern_type": "circular_cb",
          "severity": "HIGH",
          "risk_score": 0.85,
          "evidence": [...],
          "description": "특수관계자 CB 순환 투자 패턴 감지"
        }
      ]
    }

GET /api/v1/risk/signals
  Description: 리스크 신호 목록 조회
  Query Params:
    - company_id: uuid
    - severity: string
    - status: string
    - pattern_type: string
```

### 4.2 WebSocket API (실시간 진행 상황)

```yaml
WS /ws/parsing/{job_id}
  Description: 파싱 작업 실시간 모니터링

  # Server → Client Messages
  {
    "type": "progress",
    "data": {
      "processed": 25001,
      "total": 50000,
      "current_file": "20240615001234.zip",
      "speed": "120 files/min"
    }
  }

  {
    "type": "error",
    "data": {
      "file": "xxx.zip",
      "error": "XML parsing failed",
      "recoverable": true
    }
  }

  {
    "type": "completed",
    "data": {
      "total_processed": 50000,
      "stats": {...}
    }
  }
```

---

## 5. 보완된 파싱 시스템 설계

### 5.1 디렉토리 구조

```
backend/
├── app/
│   ├── domain/                      # 도메인 레이어
│   │   ├── entities/
│   │   │   ├── disclosure.py        # 공시 엔티티
│   │   │   ├── officer.py           # 임원 엔티티
│   │   │   └── convertible_bond.py  # CB 엔티티
│   │   ├── value_objects/
│   │   │   ├── corp_code.py
│   │   │   ├── rcept_no.py
│   │   │   └── money.py
│   │   ├── services/
│   │   │   ├── officer_identification.py  # 동일인 식별 도메인 서비스
│   │   │   └── term_calculation.py        # 임기 계산 서비스
│   │   └── repositories/
│   │       ├── officer_repository.py      # 임원 리포지토리 인터페이스
│   │       └── disclosure_repository.py
│   │
│   ├── application/                 # 애플리케이션 레이어
│   │   ├── commands/
│   │   │   ├── parse_batch_command.py
│   │   │   └── sync_neo4j_command.py
│   │   ├── queries/
│   │   │   ├── get_officers_query.py
│   │   │   └── get_company_network_query.py
│   │   └── services/
│   │       ├── parsing_service.py
│   │       ├── risk_analysis_service.py
│   │       └── graph_sync_service.py
│   │
│   ├── infrastructure/              # 인프라 레이어
│   │   ├── persistence/
│   │   │   ├── postgres/
│   │   │   │   ├── officer_repository_impl.py
│   │   │   │   └── bulk_loader.py
│   │   │   └── neo4j/
│   │   │       ├── graph_repository.py
│   │   │       └── cypher_builder.py
│   │   ├── parsing/
│   │   │   ├── xml_parser.py        # XML 파싱 (임원, CB 등)
│   │   │   ├── table_parser.py      # HTML 테이블 파싱
│   │   │   └── career_extractor.py  # NER 기반 경력 추출
│   │   └── state/
│   │       ├── job_state_manager.py  # 작업 상태 관리
│   │       └── checkpoint_store.py   # 체크포인트 저장
│   │
│   └── presentation/                # 프레젠테이션 레이어
│       ├── api/
│       │   ├── parsing_routes.py
│       │   ├── data_routes.py
│       │   └── graph_routes.py
│       └── cli/
│           └── parsing_commands.py
│
├── scripts/
│   ├── parsing/
│   │   ├── run_full_parse.py        # 전체 파싱 실행
│   │   ├── run_incremental.py       # 증분 파싱
│   │   └── resume_job.py            # 중단된 작업 재개
│   └── sync/
│       └── sync_to_neo4j.py         # Neo4j 동기화
│
└── data/
    └── dart/
        └── batch_XXX/
```

### 5.2 핵심 컴포넌트 설계

#### 5.2.1 ParsingOrchestrator (작업 오케스트레이터)

```python
class ParsingOrchestrator:
    """
    파싱 작업 총괄 오케스트레이터

    책임:
    - 작업 생성/관리
    - 병렬 워커 조율
    - 상태 추적 및 복구
    - Neo4j 동기화 트리거
    """

    def __init__(
        self,
        state_manager: JobStateManager,
        worker_pool: WorkerPool,
        pg_loader: BulkLoader,
        neo4j_sync: GraphSyncService,
    ):
        self.state = state_manager
        self.workers = worker_pool
        self.loader = pg_loader
        self.neo4j = neo4j_sync

    async def create_job(self, config: ParsingJobConfig) -> ParsingJob:
        """새 파싱 작업 생성"""
        job = ParsingJob(
            job_id=f"pj_{datetime.now():%Y%m%d_%H%M%S}",
            config=config,
            status=JobStatus.PENDING,
        )
        await self.state.save_job(job)
        return job

    async def execute_job(self, job_id: str):
        """작업 실행"""
        job = await self.state.get_job(job_id)

        try:
            job.status = JobStatus.RUNNING
            await self.state.save_job(job)

            # 1. 파일 목록 수집
            files = await self._collect_files(job.config)
            job.total_files = len(files)

            # 2. 체크포인트에서 재개 (있는 경우)
            checkpoint = await self.state.get_checkpoint(job_id)
            if checkpoint:
                files = self._skip_processed(files, checkpoint)

            # 3. 병렬 파싱 실행
            async for batch_result in self.workers.process_parallel(files):
                # 4. PostgreSQL 적재
                await self.loader.bulk_insert(batch_result)

                # 5. 체크포인트 저장
                await self.state.save_checkpoint(job_id, batch_result.last_file)

                # 6. 진행 상황 업데이트
                job.processed_files += len(batch_result.files)
                await self.state.save_job(job)

            # 7. Neo4j 동기화
            if job.config.sync_neo4j:
                await self.neo4j.sync_incremental(job.config.target)

            job.status = JobStatus.COMPLETED

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            raise
        finally:
            await self.state.save_job(job)
```

#### 5.2.2 BulkLoader (대량 적재기)

```python
class BulkLoader:
    """
    PostgreSQL 대량 데이터 적재기

    특징:
    - COPY 명령어 활용 (INSERT 대비 10x 빠름)
    - 배치 단위 트랜잭션
    - Upsert 지원 (ON CONFLICT)
    """

    async def bulk_insert_officers(
        self,
        officers: List[OfficerEntity],
        batch_size: int = 1000
    ) -> InsertResult:
        """임원 대량 적재"""

        async with self.session.begin():
            # 1. 기존 임원 매칭 (동일인 식별)
            existing_map = await self._fetch_existing_officers(
                [(o.name, o.birth_date) for o in officers]
            )

            # 2. 새 임원 vs 업데이트 분류
            to_insert = []
            to_update = []

            for officer in officers:
                key = (officer.name, officer.birth_date)
                if key in existing_map:
                    officer.id = existing_map[key].id
                    to_update.append(officer)
                else:
                    to_insert.append(officer)

            # 3. COPY를 이용한 대량 삽입
            if to_insert:
                await self._copy_officers(to_insert)

            # 4. 배치 업데이트
            if to_update:
                await self._batch_update_officers(to_update)

        return InsertResult(
            inserted=len(to_insert),
            updated=len(to_update)
        )

    async def _copy_officers(self, officers: List[OfficerEntity]):
        """PostgreSQL COPY 명령어로 대량 삽입"""

        # CSV 형식으로 변환
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        for o in officers:
            writer.writerow([
                str(o.id),
                o.name,
                o.birth_date,
                o.gender,
                o.position,
                json.dumps(o.career_history),
                # ...
            ])

        buffer.seek(0)

        # COPY 실행
        async with self.engine.raw_connection() as conn:
            await conn.copy_from(
                buffer,
                'officers',
                columns=['id', 'name', 'birth_date', 'gender', 'position', 'career_history'],
                sep=','
            )
```

#### 5.2.3 GraphSyncService (Neo4j 동기화)

```python
class GraphSyncService:
    """
    PostgreSQL → Neo4j 그래프 동기화 서비스

    그래프 스키마:
    - (Company) -[:HAS_OFFICER]-> (Officer)
    - (Officer) -[:WORKS_AT {position, term_start, term_end}]-> (Company)
    - (Company) -[:ISSUED]-> (ConvertibleBond)
    - (Subscriber) -[:SUBSCRIBED]-> (ConvertibleBond)
    - (Officer) -[:HAS_CAREER_AT]-> (Company)  # 경력 연결
    """

    async def sync_full(self):
        """전체 동기화"""

        async with self.driver.session() as session:
            # 1. 기존 데이터 삭제 (선택적)
            await session.run("MATCH (n) DETACH DELETE n")

            # 2. 제약조건/인덱스 생성
            await self._create_constraints(session)

            # 3. 노드 생성
            await self._sync_companies(session)
            await self._sync_officers(session)
            await self._sync_convertible_bonds(session)
            await self._sync_subscribers(session)

            # 4. 관계 생성
            await self._create_officer_relationships(session)
            await self._create_cb_relationships(session)
            await self._create_career_relationships(session)

    async def _create_officer_relationships(self, session):
        """임원-회사 관계 생성"""

        # PostgreSQL에서 officer_positions 데이터 가져오기
        async with AsyncSessionLocal() as db:
            positions = await db.execute(
                select(OfficerPosition)
                .options(
                    joinedload(OfficerPosition.officer),
                    joinedload(OfficerPosition.company)
                )
            )

            for pos in positions.scalars():
                await session.run("""
                    MATCH (o:Officer {id: $officer_id})
                    MATCH (c:Company {id: $company_id})
                    MERGE (o)-[r:WORKS_AT]->(c)
                    SET r.position = $position,
                        r.term_start = date($term_start),
                        r.term_end = date($term_end),
                        r.is_current = $is_current
                """, {
                    "officer_id": str(pos.officer_id),
                    "company_id": str(pos.company_id),
                    "position": pos.position,
                    "term_start": pos.term_start_date.isoformat() if pos.term_start_date else None,
                    "term_end": pos.term_end_date.isoformat() if pos.term_end_date else None,
                    "is_current": pos.is_current,
                })
```

### 5.3 에러 처리 및 복구 전략

```python
class ParsingErrorHandler:
    """파싱 에러 처리기"""

    ERROR_CATEGORIES = {
        "xml_parse_error": ErrorCategory.RECOVERABLE,      # 재시도 가능
        "encoding_error": ErrorCategory.RECOVERABLE,       # 인코딩 변환 후 재시도
        "missing_file": ErrorCategory.SKIP,                # 건너뛰기
        "db_constraint": ErrorCategory.INVESTIGATE,        # 조사 필요
        "timeout": ErrorCategory.RETRY_LATER,              # 나중에 재시도
    }

    async def handle_error(
        self,
        error: Exception,
        context: ParsingContext
    ) -> ErrorAction:
        """에러 처리 및 액션 결정"""

        category = self._categorize_error(error)

        if category == ErrorCategory.RECOVERABLE:
            if context.retry_count < 3:
                return ErrorAction.RETRY
            return ErrorAction.SKIP_AND_LOG

        elif category == ErrorCategory.SKIP:
            return ErrorAction.SKIP_AND_LOG

        elif category == ErrorCategory.INVESTIGATE:
            await self._alert_admin(error, context)
            return ErrorAction.PAUSE_JOB

        return ErrorAction.FAIL_JOB

    async def _alert_admin(self, error: Exception, context: ParsingContext):
        """관리자 알림"""
        await self.slack.send_alert(
            f"파싱 에러 발생: {context.file_path}\n"
            f"에러: {str(error)}\n"
            f"조사가 필요합니다."
        )
```

---

## 6. 구현 우선순위

### Phase 1: 핵심 파이프라인 보완 (1주)

1. **체크포인트 시스템 구현**
   - JobStateManager: Redis/File 기반 상태 저장
   - CheckpointStore: 배치/파일 단위 체크포인트

2. **대량 적재 최적화**
   - PostgreSQL COPY 활용
   - 배치 트랜잭션 (1000건 단위)

3. **에러 처리 강화**
   - 에러 카테고리별 처리 전략
   - 실패 파일 로깅 및 재시도 큐

### Phase 2: 미적재 데이터 처리 (1주)

1. **disclosures 테이블 적재** (~228,000건)
   - ZIP 메타데이터 스캔
   - 빠른 메타데이터만 적재 (본문 파싱 없이)

2. **financial_statements 적재** (~12,000건)
   - DART API 호출 또는 XML 파싱
   - 재무제표 주요 항목 추출

### Phase 3: 리스크 엔진 구현 (2주)

1. **risk_signals 생성 로직**
   - 순환 CB 패턴 감지
   - 특수관계자 거래 분석
   - 임원 이동 패턴 분석

2. **Neo4j 그래프 분석 쿼리**
   - 경로 탐색 알고리즘
   - 커뮤니티 감지

### Phase 4: API 및 모니터링 (1주)

1. **REST API 구현**
   - 파싱 작업 관리 API
   - 데이터 조회 API
   - 그래프 쿼리 API

2. **모니터링 대시보드**
   - 파싱 진행 상황 실시간 표시
   - 에러 통계 및 알림

---

## 7. 데이터베이스 스키마 보완

### 7.1 추가 필요 컬럼

```sql
-- officers 테이블 보완
ALTER TABLE officers
ADD COLUMN IF NOT EXISTS normalized_name VARCHAR(100);  -- 정규화된 이름 (검색용)

-- officer_positions 테이블 보완
ALTER TABLE officer_positions
ADD COLUMN IF NOT EXISTS appointment_number INTEGER DEFAULT 1;  -- 재취임 횟수

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_officer_name_birth
ON officers (name, birth_date);

CREATE INDEX IF NOT EXISTS idx_position_date_range
ON officer_positions (company_id, term_start_date, term_end_date);
```

### 7.2 파싱 작업 추적 테이블 (신규)

```sql
CREATE TABLE IF NOT EXISTS parsing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL,  -- full, incremental, specific
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    config JSONB NOT NULL,

    -- Progress
    total_files INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    failed_files INTEGER DEFAULT 0,

    -- Checkpoint
    last_batch INTEGER,
    last_corp_code VARCHAR(8),
    last_rcept_no VARCHAR(14),

    -- Statistics
    records_inserted JSONB DEFAULT '{}',

    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parsing_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES parsing_jobs(id),
    file_path VARCHAR(500) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. Neo4j 그래프 스키마

### 8.1 노드 타입

```cypher
// Company 노드
(:Company {
    id: UUID,
    corp_code: String,
    name: String,
    ticker: String,
    sector: String,
    market: String
})

// Officer 노드
(:Officer {
    id: UUID,
    name: String,
    birth_date: String,
    gender: String
})

// ConvertibleBond 노드
(:ConvertibleBond {
    id: UUID,
    bond_name: String,
    issue_date: Date,
    maturity_date: Date,
    issue_amount: Integer,
    conversion_price: Integer
})

// Subscriber 노드 (CB 인수자)
(:Subscriber {
    id: UUID,
    name: String,
    type: String  // 개인, 법인, 기관투자자 등
})

// Disclosure 노드 (공시)
(:Disclosure {
    rcept_no: String,
    report_type: String,
    report_date: Date
})
```

### 8.2 관계 타입

```cypher
// 임원 관계
(Officer)-[:WORKS_AT {
    position: String,
    term_start: Date,
    term_end: Date,
    is_current: Boolean,
    appointment_number: Integer
}]->(Company)

// 경력 관계 (과거 재직)
(Officer)-[:HAS_CAREER_AT {
    position: String,
    status: String  // former, current
}]->(Company)

// CB 발행 관계
(Company)-[:ISSUED {
    issue_date: Date,
    amount: Integer
}]->(ConvertibleBond)

// CB 인수 관계
(Subscriber)-[:SUBSCRIBED {
    amount: Integer,
    is_related_party: Boolean,
    relationship: String
}]->(ConvertibleBond)

// 특수관계자 관계
(Officer)-[:RELATED_PARTY_OF]->(Company)
(Subscriber)-[:RELATED_PARTY_OF]->(Company)

// 공시 출처 관계
(Officer)-[:DISCLOSED_IN]->(Disclosure)
(ConvertibleBond)-[:DISCLOSED_IN]->(Disclosure)
```

### 8.3 유용한 Cypher 쿼리

```cypher
// 1. 특정 회사의 CB 인수자 중 특수관계자 찾기
MATCH (c:Company {name: $company_name})-[:ISSUED]->(cb:ConvertibleBond)<-[s:SUBSCRIBED]-(sub:Subscriber)
WHERE s.is_related_party = true
RETURN c.name, cb.bond_name, sub.name, s.relationship, s.amount

// 2. 임원의 경력 네트워크 (겸직 회사 포함)
MATCH (o:Officer {name: $officer_name})-[:WORKS_AT|HAS_CAREER_AT]->(c:Company)
RETURN o, c

// 3. 순환 CB 투자 패턴 감지 (A → CB1 → B → CB2 → A)
MATCH path = (c1:Company)-[:ISSUED]->(cb1:ConvertibleBond)<-[:SUBSCRIBED]-(s:Subscriber)
            -[:RELATED_PARTY_OF]->(c2:Company)-[:ISSUED]->(cb2:ConvertibleBond)
            <-[:SUBSCRIBED]-(s2:Subscriber)-[:RELATED_PARTY_OF]->(c1)
WHERE c1 <> c2
RETURN path

// 4. 동일 인물이 재직한 회사들 간 연결
MATCH (o:Officer)-[w1:WORKS_AT]->(c1:Company),
      (o)-[w2:WORKS_AT]->(c2:Company)
WHERE c1 <> c2
RETURN o.name, c1.name, c2.name, w1.position, w2.position
```

---

## 9. 실행 검증 체크리스트

### 파싱 작업 실행 전 필수 확인

```bash
# 1. 현재 DB 상태 확인
PGPASSWORD=dev_password psql -h localhost -U postgres -d raymontology_dev -c "
SELECT 'companies' as tbl, COUNT(*) FROM companies
UNION ALL SELECT 'officers', COUNT(*) FROM officers
UNION ALL SELECT 'disclosures', COUNT(*) FROM disclosures
UNION ALL SELECT 'convertible_bonds', COUNT(*) FROM convertible_bonds
UNION ALL SELECT 'cb_subscribers', COUNT(*) FROM cb_subscribers
UNION ALL SELECT 'financial_statements', COUNT(*) FROM financial_statements
UNION ALL SELECT 'risk_signals', COUNT(*) FROM risk_signals
UNION ALL SELECT 'officer_positions', COUNT(*) FROM officer_positions;
"

# 2. DART 데이터 확인
ls -la /Users/jaejoonpark/raymontology/backend/data/dart/ | head -20
find /Users/jaejoonpark/raymontology/backend/data/dart -name "*.zip" | wc -l

# 3. Neo4j 상태 확인
cypher-shell -u neo4j -p <password> "CALL db.stats.retrieve('GRAPH COUNTS')"
```

### 파싱 작업 실행 후 필수 검증

```bash
# 1. 적재 건수 확인 (증가분 계산)
# 이전 COUNT와 비교

# 2. 데이터 무결성 검증
PGPASSWORD=dev_password psql -h localhost -U postgres -d raymontology_dev -c "
-- 고아 레코드 확인 (FK 무결성)
SELECT COUNT(*) as orphan_officers
FROM officers o
WHERE current_company_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = o.current_company_id);

-- 중복 레코드 확인
SELECT name, birth_date, COUNT(*) as cnt
FROM officers
GROUP BY name, birth_date
HAVING COUNT(*) > 1;
"

# 3. Neo4j 동기화 검증
cypher-shell -u neo4j -p <password> "
MATCH (c:Company) RETURN COUNT(c) as companies;
MATCH (o:Officer) RETURN COUNT(o) as officers;
MATCH ()-[r:WORKS_AT]->() RETURN COUNT(r) as works_at_rels;
"
```

---

## 10. 결론

이 설계서는 기존 Raymontology 프로젝트의 파싱 시스템을 DDD 원칙에 따라 재구성하고,
API 중심의 확장 가능한 아키텍처로 보완합니다.

**핵심 개선 사항:**
1. 체크포인트/상태 관리로 안정적인 대량 처리
2. PostgreSQL COPY를 활용한 고성능 적재
3. 실시간 진행 모니터링
4. Neo4j 자동 동기화
5. DDD 기반 계층 분리로 유지보수성 향상

**주의 사항 (CLAUDE.md 준수):**
- 모든 파싱 작업은 포그라운드에서 실행
- 작업 전/후 DB COUNT 필수 확인
- PostgreSQL 데이터 삭제 절대 금지
- Neo4j는 PostgreSQL 기반으로 재생성 가능

---

*작성일: 2025-12-09*
*작성자: System Architect Agent*
