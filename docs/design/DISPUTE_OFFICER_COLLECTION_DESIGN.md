# 경영분쟁 임원 수집 시스템 설계

> **버전**: 1.0 | **작성일**: 2026-02-04 | **상태**: ✅ 구현 완료

---

## 1. 개요

### 1.1 목적

임시주주총회 공시 중 경영분쟁으로 인한 임원 해임/선임 사례를 식별하고, 신규 선임 임원의 정보(이름, 경력)를 수집하여 DB에 적재하는 시스템 구축.

### 1.2 배경

- **기존 시스템**: 사업보고서의 "임원 및 직원 등의 현황" 테이블에서 임원 정보 파싱
- **미수집 영역**: 임시주주총회를 통한 경영분쟁 관련 임원 변동 정보
- **비즈니스 가치**: 경영권 분쟁 리스크 조기 식별, 투자자 알림 서비스

### 1.3 범위

| 항목 | 범위 |
|------|------|
| 기간 | 2022년 1월 ~ 현재 |
| 대상 기업 | LISTED 상태의 KOSPI/KOSDAQ/KONEX 기업 (3,021개) |
| 공시 유형 | 임시주주총회결과, 주주총회소집결의(임시주주총회), 경영권분쟁소송 관련 |
| 수집 데이터 | 신규 선임 임원 이름, 경력, 선임 배경 |

---

## 2. 현황 분석

### 2.1 공시 데이터 현황 (2022년~현재)

| 공시 유형 | 건수 | 비고 |
|----------|------|------|
| 임시주주총회결과 | ~1,564건 | 핵심 파싱 대상 |
| 주주총회소집결의(임시주주총회) | ~1,242건 | 사전 안건 파악용 |
| 경영권분쟁소송 관련 | ~30건 | 직접 태깅 대상 |
| 사외이사선임·해임신고 | 다수 | 보조 데이터 |
| **합계** | **~2,980건** | |

**연도별 추이**:
| 연도 | 임시주주총회 관련 건수 |
|------|---------------------|
| 2022 | 382건 |
| 2023 | 609건 |
| 2024 | 1,158건 |
| 2025 | 831건 |

### 2.2 기존 시스템 분석

**장점 (재사용 가능)**:
- `BaseParser` 클래스: ZIP 추출, 인코딩 처리, 단위 감지
- `OfficerParser` 클래스: 임원 UPSERT, 동일인 식별 (name + birth_date)
- `disclosures` 테이블: 공시 메타데이터 인덱싱 완료

**한계점**:
- 공시 본문(XML) 미저장 (`storage_url`, `storage_key` NULL)
- 임시주주총회 공시 전용 파서 부재
- 경영분쟁 여부 판단 로직 부재

### 2.3 기술적 제약사항

| 제약 | 영향 | 해결책 |
|------|------|--------|
| DART API Rate Limit | 분당 900건 | 배치 처리 + 지연 |
| 공시 본문 형식 다양성 | 파싱 복잡도 증가 | 다중 패턴 매칭 |
| 경영분쟁 판단 주관성 | 오탐/미탐 가능 | 키워드 기반 + 수동 검토 플래그 |

---

## 3. 시스템 아키텍처

### 3.1 전체 흐름

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. Discovery   │────▶│   2. Download   │────▶│   3. Analysis   │
│  (공시 식별)     │     │   (본문 다운로드)  │     │   (분쟁 분류)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌─────────────────────────────────┘
                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   4. Parsing    │────▶│   5. Storage    │────▶│  6. Validation  │
│   (임원 추출)    │     │   (DB 적재)      │     │   (검증)        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 3.2 컴포넌트 구성

```
backend/
├── scripts/
│   ├── parsers/
│   │   ├── base.py                    # (기존) BaseParser
│   │   ├── officer.py                 # (기존) OfficerParser
│   │   └── egm_officer.py             # (신규) EGMOfficerParser
│   │
│   ├── collection/
│   │   └── collect_egm_disclosures.py # (신규) 임시주주총회 공시 수집
│   │
│   └── pipeline/
│       └── run_egm_officer_pipeline.py # (신규) 전체 파이프라인
│
├── app/
│   ├── models/
│   │   ├── dispute_officers.py        # (신규) 분쟁 임원 모델
│   │   └── egm_disclosures.py         # (신규) 임시주주총회 공시 모델
│   │
│   └── api/endpoints/
│       └── dispute_analysis.py        # (신규) 분쟁 분석 API
```

---

## 4. 데이터베이스 스키마 설계

### 4.1 신규 테이블: `egm_disclosures` (임시주주총회 공시)

```sql
CREATE TABLE egm_disclosures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 공시 메타데이터 (disclosures 테이블 참조)
    disclosure_id VARCHAR(50) NOT NULL,       -- disclosures.rcept_no
    company_id UUID REFERENCES companies(id),
    corp_code VARCHAR(8) NOT NULL,

    -- 임시주주총회 고유 필드
    egm_date DATE,                            -- 주주총회 개최일
    egm_type VARCHAR(50),                     -- 'REGULAR', 'SPECIAL', 'COURT_ORDERED'

    -- 경영분쟁 분류
    is_dispute_related BOOLEAN DEFAULT FALSE, -- 경영분쟁 관련 여부
    dispute_type VARCHAR(100),                -- 'HOSTILE_TAKEOVER', 'MANAGEMENT_CONFLICT', 'SHAREHOLDER_ACTIVISM'
    dispute_keywords JSONB,                   -- 탐지된 키워드 목록

    -- 안건 정보
    agenda_items JSONB,                       -- [{number, title, result, vote_detail}]
    officer_changes JSONB,                    -- [{action, officer_name, position, vote_result}]

    -- 파싱 메타데이터
    raw_content TEXT,                         -- 원문 (디버깅용)
    parse_status VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'PARSED', 'MANUAL_REVIEW', 'FAILED'
    parse_confidence DECIMAL(3,2),            -- 파싱 신뢰도 (0.00~1.00)
    parse_errors JSONB,                       -- 파싱 오류 목록

    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_egm_disclosures_company ON egm_disclosures(company_id);
CREATE INDEX idx_egm_disclosures_dispute ON egm_disclosures(is_dispute_related) WHERE is_dispute_related = TRUE;
CREATE INDEX idx_egm_disclosures_egm_date ON egm_disclosures(egm_date);
CREATE UNIQUE INDEX idx_egm_disclosures_disclosure ON egm_disclosures(disclosure_id);
```

### 4.2 신규 테이블: `dispute_officers` (분쟁 선임 임원)

```sql
CREATE TABLE dispute_officers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 임원 연결 (기존 officers 테이블과 소프트 참조)
    officer_id UUID REFERENCES officers(id),  -- 매칭된 경우
    officer_name VARCHAR(100) NOT NULL,
    birth_date VARCHAR(10),                   -- 'YYYYMM' 형식

    -- 선임 정보
    company_id UUID REFERENCES companies(id),
    position VARCHAR(100),                    -- 선임 직책
    egm_disclosure_id UUID REFERENCES egm_disclosures(id),
    appointment_date DATE,                    -- 선임일

    -- 경력 정보 (공시에서 추출)
    career_from_disclosure TEXT,              -- 공시 원문에서 추출한 경력
    career_parsed JSONB,                      -- 구조화된 경력 [{text, status}]

    -- 분쟁 맥락
    appointment_context VARCHAR(50),          -- 'DISPUTE_NEW', 'DISPUTE_REPLACEMENT', 'REGULAR'
    replaced_officer_name VARCHAR(100),       -- 해임된 전임자 이름
    vote_result VARCHAR(200),                 -- 투표 결과 (찬성/반대 비율)

    -- 검증 상태
    is_verified BOOLEAN DEFAULT FALSE,        -- 수동 검증 완료 여부
    verification_notes TEXT,

    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_dispute_officers_company ON dispute_officers(company_id);
CREATE INDEX idx_dispute_officers_officer ON dispute_officers(officer_id);
CREATE INDEX idx_dispute_officers_context ON dispute_officers(appointment_context);
```

### 4.3 기존 테이블 확장 (선택적)

**officers 테이블 - 신규 컬럼 추가 (선택)**:
```sql
-- 분쟁 선임 여부 플래그 (선택적 확장)
ALTER TABLE officers ADD COLUMN IF NOT EXISTS
    dispute_appointment_count INTEGER DEFAULT 0;

-- 코멘트
COMMENT ON COLUMN officers.dispute_appointment_count IS
    '경영분쟁을 통한 선임 횟수';
```

### 4.4 ER 다이어그램

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│   companies     │◀──────│  egm_disclosures    │───────▶│   disclosures   │
│                 │       │                     │       │   (참조)         │
│  id (PK)        │       │  id (PK)            │       │                 │
│  corp_code      │       │  company_id (FK)    │       │  rcept_no       │
│  name           │       │  disclosure_id      │       │                 │
└─────────────────┘       │  is_dispute_related │       └─────────────────┘
        ▲                 │  agenda_items       │
        │                 │  officer_changes    │
        │                 └─────────────────────┘
        │                           │
        │                           │ 1:N
        │                           ▼
        │                 ┌─────────────────────┐       ┌─────────────────┐
        │                 │  dispute_officers   │───────▶│    officers     │
        │                 │                     │       │   (소프트 참조)  │
        └─────────────────│  company_id (FK)    │       │                 │
                          │  egm_disclosure_id  │       │  id (PK)        │
                          │  officer_name       │       │  name           │
                          │  appointment_context│       │  birth_date     │
                          └─────────────────────┘       └─────────────────┘
```

---

## 5. 파싱 로직 설계

### 5.1 경영분쟁 식별 키워드

**강력 지표 (가중치 3.0)**:
```python
STRONG_DISPUTE_KEYWORDS = [
    '경영권 분쟁', '경영권분쟁', '적대적', '경영권 확보',
    '주주제안', '주주 제안', '소수주주', '반대주주',
    '해임 청구', '해임청구', '직무집행정지',
    '가처분', '소송', '소집허가',
]
```

**중간 지표 (가중치 2.0)**:
```python
MEDIUM_DISPUTE_KEYWORDS = [
    '해임', '퇴임', '사임', '교체',
    '대표이사 변경', '이사회 구성',
    '지배구조', '경영진 교체',
]
```

**약한 지표 (가중치 1.0)**:
```python
WEAK_DISPUTE_KEYWORDS = [
    '임시주주총회', '긴급', '특별',
    '이사 선임', '감사 선임',
]
```

**분쟁 판정 로직**:
```python
def classify_dispute(text: str) -> Tuple[bool, float, str]:
    """
    Returns:
        is_dispute: 분쟁 여부
        confidence: 신뢰도 (0.0~1.0)
        dispute_type: 분쟁 유형
    """
    score = 0.0
    detected_keywords = []

    for kw in STRONG_DISPUTE_KEYWORDS:
        if kw in text:
            score += 3.0
            detected_keywords.append(kw)

    for kw in MEDIUM_DISPUTE_KEYWORDS:
        if kw in text:
            score += 2.0
            detected_keywords.append(kw)

    # 해임 + 선임 조합 = 추가 가중치
    if '해임' in text and '선임' in text:
        score += 2.0

    # 정규화 (최대 10점 기준)
    confidence = min(score / 10.0, 1.0)
    is_dispute = confidence >= 0.3  # 임계값

    # 분쟁 유형 분류
    dispute_type = None
    if is_dispute:
        if any(kw in text for kw in ['적대적', '경영권 확보']):
            dispute_type = 'HOSTILE_TAKEOVER'
        elif any(kw in text for kw in ['주주제안', '소수주주']):
            dispute_type = 'SHAREHOLDER_ACTIVISM'
        else:
            dispute_type = 'MANAGEMENT_CONFLICT'

    return is_dispute, confidence, dispute_type
```

### 5.2 임원 정보 추출 패턴

**안건 파싱 패턴**:
```python
AGENDA_PATTERNS = [
    # 제N호 의안: 이사 OOO 선임의 건
    r'제\s*(\d+)\s*호\s*의안\s*[:：]\s*(.+?)(이사|감사|대표이사)\s+(.+?)\s*(선임|해임)',

    # 의안 N. OOO 이사 선임
    r'의안\s*(\d+)\s*[\.:\s]\s*(.+?)\s*(이사|감사|대표이사)\s*(선임|해임)',

    # - 선임 이사: OOO
    r'[-•]\s*(선임|해임)\s*(이사|감사)\s*[:：]\s*(.+)',
]
```

**경력 추출 패턴**:
```python
CAREER_PATTERNS = [
    # 1. 후보자 경력: ...
    r'후보자\s*경력\s*[:：]\s*(.+?)(?=\n\n|\Z)',

    # 경력사항: ...
    r'경력\s*사항\s*[:：]\s*(.+?)(?=\n\n|\Z)',

    # 주요경력
    r'주요\s*경력\s*[:：]?\s*(.+?)(?=\n\n|\Z)',
]
```

### 5.3 EGMOfficerParser 클래스 설계

```python
class EGMOfficerParser(BaseParser):
    """임시주주총회 공시 임원 파서"""

    def __init__(self, database_url: Optional[str] = None):
        super().__init__(database_url)
        self.dispute_classifier = DisputeClassifier()
        self.officer_extractor = OfficerExtractor()

    async def parse(self, zip_path: Path, meta: Dict) -> Dict[str, Any]:
        """공시 본문 파싱"""
        result = {
            'success': False,
            'is_dispute': False,
            'dispute_confidence': 0.0,
            'agenda_items': [],
            'officer_changes': [],
            'errors': [],
        }

        # XML 추출
        xml_content = self.extract_xml_from_zip(zip_path)
        if not xml_content:
            result['errors'].append('XML extraction failed')
            return result

        # 텍스트 추출
        text = self._clean_xml_text(xml_content)

        # 분쟁 분류
        is_dispute, confidence, dispute_type = self.dispute_classifier.classify(text)
        result['is_dispute'] = is_dispute
        result['dispute_confidence'] = confidence
        result['dispute_type'] = dispute_type

        # 안건 파싱
        result['agenda_items'] = self._parse_agenda(text)

        # 임원 변동 추출
        if is_dispute or self._has_officer_agenda(result['agenda_items']):
            result['officer_changes'] = self._parse_officer_changes(text)

        result['success'] = True
        return result

    def _parse_agenda(self, text: str) -> List[Dict]:
        """안건 목록 파싱"""
        # ... 구현

    def _parse_officer_changes(self, text: str) -> List[Dict]:
        """임원 변동 정보 추출"""
        # ... 구현

    async def save_to_db(self, conn, data: Dict) -> bool:
        """DB 저장"""
        # ... 구현
```

---

## 6. 단계별 수행 계획

### Phase 1: 인프라 구축 (1주)

| 단계 | 작업 | 산출물 | 위험도 |
|------|------|--------|--------|
| 1.1 | DB 마이그레이션 스크립트 작성 | `alembic/versions/xxx_add_egm_tables.py` | 낮음 |
| 1.2 | SQLAlchemy 모델 생성 | `app/models/egm_disclosures.py`, `dispute_officers.py` | 낮음 |
| 1.3 | 테스트 데이터 생성 | 샘플 공시 10건 수동 파싱 | 낮음 |

**서비스 영향**: 없음 (신규 테이블 추가만)

### Phase 2: 공시 수집 (1주)

| 단계 | 작업 | 산출물 | 위험도 |
|------|------|--------|--------|
| 2.1 | DART API 연동 모듈 확장 | `collect_egm_disclosures.py` | 낮음 |
| 2.2 | 임시주주총회 공시 목록 수집 | `egm_disclosures` ~2,980건 메타데이터 | 낮음 |
| 2.3 | 공시 본문(ZIP) 다운로드 | `data/dart/egm/` 디렉토리 | 중간 (API 제한) |

**Rate Limit 대응**:
```python
# 일일 처리량: 900 req/min × 60 min × 8 hr = 432,000건
# 실제 필요: ~3,000건 → 약 5분 소요
```

### Phase 3: 파서 개발 (2주)

| 단계 | 작업 | 산출물 | 위험도 |
|------|------|--------|--------|
| 3.1 | 경영분쟁 분류기 개발 | `DisputeClassifier` 클래스 | 중간 |
| 3.2 | 안건 파서 개발 | 정규식 패턴 + 테스트 케이스 | 중간 |
| 3.3 | 임원 추출기 개발 | `OfficerExtractor` 클래스 | 높음 |
| 3.4 | EGMOfficerParser 통합 | 전체 파이프라인 연결 | 중간 |

**검증 전략**:
- 수동 라벨링 데이터 50건으로 정확도 측정
- 목표: 분쟁 분류 정확도 85%+, 임원 추출 정확도 90%+

### Phase 4: 파이프라인 통합 (1주)

| 단계 | 작업 | 산출물 | 위험도 |
|------|------|--------|--------|
| 4.1 | 전체 파이프라인 스크립트 작성 | `run_egm_officer_pipeline.py` | 낮음 |
| 4.2 | 기존 officers 테이블 연계 | 동일인 매칭 로직 | 중간 |
| 4.3 | 배치 실행 테스트 | 전체 데이터 처리 | 중간 |

### Phase 5: 검증 및 배포 (1주)

| 단계 | 작업 | 산출물 | 위험도 |
|------|------|--------|--------|
| 5.1 | 데이터 품질 검증 | 검증 보고서 | 낮음 |
| 5.2 | 수동 검토 대상 목록 생성 | `parse_status='MANUAL_REVIEW'` 목록 | 낮음 |
| 5.3 | 프로덕션 배포 | Railway 배포 | 낮음 |
| 5.4 | 문서 업데이트 | SCHEMA_REGISTRY.md, DATA_STATUS.md | 낮음 |

---

## 7. 서비스 안전성 보장

### 7.1 격리 전략

| 구분 | 기존 시스템 | 신규 시스템 |
|------|------------|------------|
| 테이블 | officers, officer_positions | egm_disclosures, dispute_officers |
| 파서 | OfficerParser | EGMOfficerParser |
| 데이터 소스 | 사업보고서 | 임시주주총회 공시 |

**핵심 원칙**: 신규 테이블에만 데이터 적재, 기존 테이블은 읽기 전용 참조

### 7.2 롤백 계획

```sql
-- 완전 롤백 (신규 테이블 삭제)
DROP TABLE IF EXISTS dispute_officers CASCADE;
DROP TABLE IF EXISTS egm_disclosures CASCADE;

-- 데이터만 삭제 (스키마 유지)
TRUNCATE dispute_officers, egm_disclosures;
```

### 7.3 모니터링

```python
# 파이프라인 실행 시 pipeline_runs 테이블에 기록
{
    "pipeline_type": "egm_officer",
    "status": "completed",
    "companies_processed": 2980,
    "dispute_detected": 150,
    "officers_extracted": 320,
    "manual_review_count": 45,
}
```

---

## 8. 예상 결과

### 8.1 데이터 규모

| 항목 | 예상 수량 |
|------|----------|
| 수집 공시 | ~2,980건 |
| 경영분쟁 판정 | ~300건 (10%) |
| 신규 추출 임원 | ~500명 |
| 수동 검토 필요 | ~100건 |

### 8.2 활용 방안

1. **RaymondsRisk 통합**: 경영분쟁 리스크 점수 반영
2. **알림 서비스**: 특정 기업의 경영분쟁 공시 실시간 알림
3. **관계도 확장**: 분쟁 임원의 네트워크 분석
4. **RaymondsIndex 영향**: 지배구조 불안정성 지표로 활용

---

## 9. 파일 경로 정리

```
backend/
├── alembic/versions/
│   └── 2026_02_xx_add_egm_tables.py      # 마이그레이션
│
├── app/models/
│   ├── egm_disclosures.py                 # 임시주주총회 공시 모델
│   └── dispute_officers.py                # 분쟁 임원 모델
│
├── scripts/
│   ├── parsers/
│   │   └── egm_officer.py                 # EGMOfficerParser
│   │
│   ├── collection/
│   │   └── collect_egm_disclosures.py     # 공시 수집
│   │
│   └── pipeline/
│       └── run_egm_officer_pipeline.py    # 통합 파이프라인
│
└── data/dart/egm/                         # 다운로드 공시 저장
    ├── 2022/
    ├── 2023/
    ├── 2024/
    └── 2025/
```

---

## 10. 다음 단계

1. **설계 리뷰 승인** 후 Phase 1 착수
2. **우선순위**: 경영분쟁 분류 정확도가 핵심 성공 요인
3. **의존성**: DART_API_KEY 환경변수 확인 필요

---

*문서 작성: Claude | 마지막 업데이트: 2026-02-04*

---

## 11. 구현 완료 현황 (2026-02-04)

### 완료된 파일

| 단계 | 파일 | 상태 |
|------|------|------|
| **Phase 1.1** | `app/models/egm_disclosures.py` | ✅ 완료 |
| | `app/models/dispute_officers.py` | ✅ 완료 |
| | `app/models/__init__.py` (수정) | ✅ 완료 |
| **Phase 1.2** | `alembic/versions/20260204_add_egm_disclosures_tables.py` | ✅ 완료 |
| **Phase 2** | `scripts/collection/collect_egm_disclosures.py` | ✅ 완료 |
| **Phase 3** | `scripts/parsers/egm_officer.py` | ✅ 완료 |
| **Phase 4** | `scripts/pipeline/run_egm_officer_pipeline.py` | ✅ 완료 |
| **Phase 5** | `scripts/SCHEMA_REGISTRY.md` (업데이트) | ✅ 완료 |

### 다음 실행 단계

마이그레이션 및 파이프라인 실행:

```bash
cd backend
source .venv/bin/activate

# 1. 마이그레이션 실행 (테이블 생성)
alembic upgrade head

# 2. 파이프라인 테스트 (샘플 10건)
python -m scripts.pipeline.run_egm_officer_pipeline --limit 10 --dry-run

# 3. 전체 파이프라인 실행 (2022년~현재)
python -m scripts.pipeline.run_egm_officer_pipeline

# 4. 특정 연도만 실행
python -m scripts.pipeline.run_egm_officer_pipeline --year 2024

# 5. 특정 단계부터 재시작
python -m scripts.pipeline.run_egm_officer_pipeline --start-from parse
```

### 서비스 영향

- **기존 서비스**: 영향 없음 (신규 테이블만 추가)
- **롤백**: 마이그레이션 롤백으로 완전 복구 가능 (`alembic downgrade -1`)
