# NLP Module - 사업보고서 자동 파싱 시스템

DART 사업보고서 PDF에서 구조화된 데이터를 자동으로 추출하는 NLP 파이프라인

## 개요

사업보고서를 자동으로 파싱하여 임원 정보, 전환사채 발행 현황, 특수관계자 거래 등을 추출합니다.

**Railway 최적화**:
- CPU 기반 파싱 (GPU 불필요)
- 메모리 효율적 처리
- 비동기 작업 지원

## 아키텍처

```
PDF 파일
    ↓
[1. PDF Extractor]
    ↓ (텍스트)
[2. Section Parser]
    ↓ (섹션별 텍스트)
[3. NER Extractor]
    ↓ (개체명)
[4. Report Parser]
    ↓
구조화된 데이터
```

## 구성 요소

### 1. PDF Extractor (`pdf_extractor.py`)

PDF에서 텍스트 추출

**기능**:
- PyMuPDF (fitz)를 사용한 고속 텍스트 추출
- 선택적 OCR 지원 (Tesseract)
- 테이블 추출 (Camelot)
- 이미지 추출

**사용 예시**:
```python
from app.nlp.pdf_extractor import PDFExtractor

extractor = PDFExtractor(use_ocr=False)
result = await extractor.extract_text(pdf_path)

print(f"페이지 수: {result['total_pages']}")
print(f"텍스트 길이: {len(result['full_text'])}")
```

**Railway 최적화**:
- OCR 기본 비활성화 (메모리 절약)
- 페이지별 스트리밍 처리
- 최소 의존성 (PyMuPDF만 필수)

### 2. Section Parser (`section_parser.py`)

텍스트를 섹션별로 분할

**추출 섹션**:
- 회사의 개요
- 사업의 내용
- 재무에 관한 사항
- **임원 및 직원 현황** ⭐
- **전환사채 발행 현황** ⭐
- **특수관계자 거래** ⭐
- 주주 현황
- 배당 정책

**사용 예시**:
```python
from app.nlp.section_parser import SectionParser

parser = SectionParser()
sections = await parser.parse_sections(full_text)

# 특정 섹션 추출
officer_section = await parser.extract_officer_section(full_text)
cb_section = await parser.extract_cb_section(full_text)
```

**파싱 전략**:
- 정규표현식 기반 (빠르고 안정적)
- 다양한 포맷 지원 (로마자, 숫자, 한글)
- 테이블 블록 감지

### 3. NER Extractor (`ner_extractor.py`)

개체명 추출 (Named Entity Recognition)

**추출 대상**:

#### 임원 정보
```python
{
    "name": "홍길동",
    "position": "대표이사",
    "term_start": "2023-03-01",
    "term_end": "2026-02-28",
    "responsibilities": "경영 총괄"
}
```

#### 전환사채 (CB)
```python
{
    "issue_date": "2023-01-01",
    "maturity_date": "2025-01-01",
    "amount": 10000000000,  # 원 단위
    "conversion_price": 5000,
    "holder": "투자조합1호",
    "conversion_rate": 100.0
}
```

#### 특수관계자
```python
{
    "name": "계열사A",
    "relationship": "계열사",
    "transaction_amount": 5000000000
}
```

**사용 예시**:
```python
from app.nlp.ner_extractor import NERExtractor

extractor = NERExtractor()

# 임원 추출
officers = await extractor.extract_officers(officer_section)

# 전환사채 추출
cbs = await extractor.extract_convertible_bonds(cb_section)

# 특수관계자 추출
parties = await extractor.extract_related_parties(related_party_section)
```

**추출 방법**:
- 정규표현식 패턴 매칭 (CPU 효율적)
- 테이블 파싱 (라인 기반)
- 문맥 기반 정보 추출
- 향후 KoBERT 추가 가능

### 4. Report Parser (`report_parser.py`)

통합 파싱 파이프라인

**주요 클래스**:

#### `ParsedReport`
파싱된 보고서 데이터를 담는 클래스
```python
class ParsedReport:
    report_id: str
    company_id: str
    rcept_no: str

    # 원시 데이터
    full_text: str
    metadata: Dict
    total_pages: int

    # 섹션
    sections: Dict[str, str]

    # 추출된 개체
    officers: List[Dict]
    convertible_bonds: List[Dict]
    related_parties: List[Dict]

    # 통계
    parsing_stats: Dict
```

#### `ReportParser`
메인 파서 클래스
```python
parser = ReportParser(use_ocr=False)

# 전체 파싱
report = await parser.parse_report(
    pdf_path=Path("report.pdf"),
    company_id="550e8400-...",
    rcept_no="20240101000001"
)

# 경량 파싱 (임원만)
officers = await parser.parse_officer_section_only(
    pdf_path=Path("report.pdf"),
    company_id="550e8400-..."
)

# 경량 파싱 (CB만)
cbs = await parser.parse_cb_section_only(
    pdf_path=Path("report.pdf"),
    company_id="550e8400-..."
)
```

## API 엔드포인트

### 파싱 작업 생성

```http
POST /api/parser/parse
{
  "rcept_no": "20240101000001",
  "company_id": "550e8400-...",
  "use_ocr": false,
  "extract_tables": false
}

Response: 201 Created
{
  "job_id": "celery-task-id",
  "status": "pending",
  "rcept_no": "20240101000001"
}
```

### 특정 섹션만 파싱

```http
POST /api/parser/parse-section
{
  "rcept_no": "20240101000001",
  "section_type": "officers"  // or "convertible_bonds"
}
```

### 파싱 결과 조회

```http
GET /api/parser/parsed/{rcept_no}

Response: 200 OK
{
  "report_id": "uuid",
  "company_id": "uuid",
  "officers": [...],
  "convertible_bonds": [...],
  "related_parties": [...],
  "parsing_stats": {...}
}
```

### 임원만 조회

```http
GET /api/parser/parsed/{rcept_no}/officers
```

### 전환사채만 조회

```http
GET /api/parser/parsed/{rcept_no}/convertible-bonds
```

### 검증

```http
GET /api/parser/parsed/{rcept_no}/validate

Response:
{
  "errors": [],
  "warnings": ["No officers found"],
  "is_valid": true
}
```

## 백그라운드 작업

Celery로 비동기 파싱 처리

### 작업 종류

1. **`parse_report_task`**: 전체 파싱
2. **`parse_officer_section_task`**: 임원만 파싱
3. **`parse_cb_section_task`**: CB만 파싱
4. **`batch_parse_reports_task`**: 배치 파싱

### 실행 흐름

```python
# 1. API 요청
POST /api/parser/parse

# 2. Celery 작업 생성
task = parse_report_task.delay(rcept_no, pdf_path, company_id)

# 3. 백그라운드에서 파싱 실행
# - PDF 다운로드 (S3)
# - 텍스트 추출
# - 섹션 분할
# - NER 추출

# 4. 결과 저장
# - DisclosureParsedData 테이블에 저장
# - JSONB 형식으로 구조화된 데이터 저장

# 5. 결과 조회
GET /api/parser/parsed/{rcept_no}
```

## 데이터 흐름

```
Disclosure (disclosures 테이블)
    ↓
PDF 파일 (S3/R2)
    ↓
[파싱 작업]
    ↓
DisclosureParsedData (disclosure_parsed_data 테이블)
    ↓
API 응답
```

## 성능 최적화

### Railway 배포 고려사항

1. **메모리 효율**
   - OCR 기본 비활성화
   - 페이지별 스트리밍 처리
   - 대용량 PDF 분할 처리

2. **CPU 최적화**
   - 정규표현식 기반 (GPU 불필요)
   - 비동기 처리
   - 배치 작업 큐잉

3. **의존성 최소화**
   ```txt
   PyMuPDF (필수)
   pytesseract (선택)
   camelot-py (선택)
   ```

### 파싱 시간

- 소형 보고서 (50페이지): ~5초
- 중형 보고서 (200페이지): ~15초
- 대형 보고서 (500페이지): ~30초

*OCR 비활성화 기준

## 에러 핸들링

### 재시도 로직

Celery 작업에 자동 재시도 설정:
```python
@celery_app.task(max_retries=3, default_retry_delay=60)
def parse_report_task(...):
    try:
        # 파싱 실행
        ...
    except Exception as e:
        # 재시도
        raise task.retry(exc=e)
```

### 검증

```python
validation = await parser.validate_parsed_data(report)

if validation["errors"]:
    # 에러 처리
    logger.error(f"Parsing errors: {validation['errors']}")

if validation["warnings"]:
    # 경고 로그
    logger.warning(f"Parsing warnings: {validation['warnings']}")
```

## 확장 가능성

### 1. KoBERT 추가

```python
# TODO: KoBERT로 고급 NER
from transformers import AutoTokenizer, AutoModelForTokenClassification

class BERTNERExtractor:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("monologg/kobert")
        self.model = AutoModelForTokenClassification.from_pretrained(...)

    async def extract_entities(self, text: str):
        # BERT 기반 개체명 추출
        ...
```

### 2. 테이블 파싱 강화

```python
# TODO: Camelot + 휴리스틱으로 복잡한 테이블 파싱
tables = await extractor.extract_tables(pdf_path)
parsed_tables = await table_parser.parse_financial_tables(tables)
```

### 3. 문서 분류

```python
# TODO: 보고서 유형 자동 분류
report_type = await classifier.classify_report(text)
# "사업보고서", "반기보고서", "분기보고서" 등
```

## 테스트

```python
# tests/test_nlp/test_report_parser.py
import pytest
from pathlib import Path
from app.nlp.report_parser import ReportParser

@pytest.mark.asyncio
async def test_parse_report():
    parser = ReportParser()

    report = await parser.parse_report(
        pdf_path=Path("tests/fixtures/sample_report.pdf"),
        company_id="test-company-id",
        rcept_no="20240101000001"
    )

    assert report.total_pages > 0
    assert len(report.officers) > 0
    assert report.parsing_stats["extraction_time"] > 0
```

## 다음 단계

- [ ] KoBERT 통합 (선택적 사용)
- [ ] 테이블 파싱 강화
- [ ] 문서 분류 기능
- [ ] 실시간 파싱 진행률 표시
- [ ] 파싱 품질 메트릭 추적
- [ ] A/B 테스트 (정규표현식 vs BERT)
