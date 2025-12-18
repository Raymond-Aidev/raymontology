# DART Crawler

한국 전자공시시스템(DART) 공시 데이터 수집 시스템

## 개요

DART OpenAPI를 사용하여 한국 상장사 및 비상장사의 공시 데이터를 자동으로 수집합니다.

## 구성 요소

### 1. DARTClient (`dart_client.py`)

DART OpenAPI 클라이언트

**주요 기능**:
- 기업 코드 목록 조회 (`get_corp_code_list`)
- 공시 목록 조회 (`get_disclosure_list`)
- 공시 문서 다운로드 (`download_document`)
- Rate Limiting (초당 10 요청)
- 비동기 처리 (`async/await`)

**사용 예시**:
```python
async with DARTClient(api_key) as client:
    # 전체 기업 코드 조회
    corp_codes = await client.get_corp_code_list()

    # 특정 기업 공시 조회
    result = await client.get_disclosure_list(
        corp_code="00126380",
        start_date="20240101",
        end_date="20241231"
    )

    # 문서 다운로드
    await client.download_document(
        rcept_no="20240101000001",
        save_path=Path("./data/document.zip")
    )
```

### 2. DARTCrawler (`dart_crawler.py`)

대규모 크롤링 작업 관리

**주요 기능**:
- 전체 기업 공시 수집 (`crawl_all_companies`)
- 최근 N시간 공시 수집 (`crawl_recent`)
- 특정 기업 공시 수집 (`crawl_company`)
- 진행률 표시 (tqdm)
- 에러 핸들링 및 재시도
- 통계 정보 수집

**저장 구조**:
```
/data/dart/
  ├── {corp_code}/
  │   ├── 2024/
  │   │   ├── {rcept_no}.zip          # 공시 문서
  │   │   └── {rcept_no}_meta.json    # 메타데이터
  │   └── 2023/
  │       └── ...
  └── ...
```

**사용 예시**:
```python
crawler = DARTCrawler(
    api_key="your_api_key",
    data_dir=Path("./data/dart")
)

# 최근 3년 전체 크롤링
stats = await crawler.crawl_all_companies(years=3)

# 최근 24시간 크롤링
stats = await crawler.crawl_recent(hours=24)

# 특정 기업 크롤링
count = await crawler.crawl_company(
    corp_code="00126380",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
```

### 3. Background Tasks (`../tasks/crawler_tasks.py`)

Celery 백그라운드 작업

**주요 작업**:
- `crawl_all_companies_task`: 전체 기업 크롤링
- `crawl_recent_task`: 최근 공시 크롤링
- `crawl_company_task`: 특정 기업 크롤링

**특징**:
- 비동기 실행
- 자동 재시도 (최대 3회)
- DB 세션 자동 관리
- 작업 상태 추적 (pending → running → completed/failed)

## Railway 배포 고려사항

### 1. 파일 저장

Railway는 파일 저장 비용이 높으므로 S3/Cloudflare R2 사용 권장:

```python
# TODO: S3 업로드 구현
async def upload_to_s3(file_path: Path, bucket: str, key: str):
    """S3에 파일 업로드"""
    pass

# crawler에서 사용
storage_url = await upload_to_s3(
    file_path=doc_path,
    bucket="raymontology-disclosures",
    key=f"{corp_code}/{year}/{rcept_no}.zip"
)
```

### 2. 메타데이터 저장

메타데이터는 PostgreSQL에 저장:

```sql
-- disclosures 테이블
CREATE TABLE disclosures (
    id UUID PRIMARY KEY,
    rcept_no VARCHAR(14) UNIQUE NOT NULL,
    corp_code VARCHAR(8) NOT NULL,
    storage_url VARCHAR(500),  -- S3 URL
    metadata JSONB,
    crawled_at TIMESTAMP
);
```

### 3. 백그라운드 작업

Celery + Redis로 크롤링 작업 관리:

```bash
# Worker 실행
celery -A app.tasks.celery_app worker --loglevel=info --queue=crawler

# Beat 실행 (스케줄러)
celery -A app.tasks.celery_app beat --loglevel=info
```

## API 엔드포인트

### 공시 조회

```http
GET /api/disclosures?corp_code=00126380&page=1&page_size=20
GET /api/disclosures/{rcept_no}
GET /api/disclosures/stats/overview
```

### 크롤링 작업

```http
POST /api/disclosures/crawl
{
  "job_type": "recent",
  "hours": 24
}

GET /api/disclosures/crawl/jobs
GET /api/disclosures/crawl/jobs/{job_id}
GET /api/disclosures/crawl/stats/overview
```

## Rate Limiting

DART OpenAPI 제한: **초당 10 요청**

크롤러는 자동으로 Rate Limiting을 적용:
- Semaphore로 동시 요청 제한
- 시간 추적으로 초당 요청 수 관리
- 필요 시 자동 대기

## 에러 핸들링

### 재시도 로직

```python
for attempt in range(max_retries):
    try:
        success = await client.download_document(rcept_no, doc_path)
        if success:
            return True
        await asyncio.sleep(retry_delay)
    except Exception as e:
        logger.warning(f"Retry {attempt + 1}/{max_retries}: {e}")
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)

# 최종 실패
stats["failed_downloads"] += 1
```

### 통계 추적

```python
stats = {
    "total_companies": 0,
    "total_disclosures": 0,
    "downloaded_documents": 0,
    "failed_downloads": 0,
    "errors": [
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "error": "Connection timeout"
        }
    ]
}
```

## CLI 사용법

```bash
# 전체 크롤링 (최근 3년)
python -m app.crawlers.dart_crawler \
    --api-key YOUR_API_KEY \
    --years 3 \
    --data-dir ./data/dart

# 최근 24시간 크롤링
python -m app.crawlers.dart_crawler \
    --api-key YOUR_API_KEY \
    --recent-hours 24 \
    --data-dir ./data/dart
```

## 환경 변수

```bash
# .env 파일
DART_API_KEY=your_dart_api_key_here
DART_DATA_DIR=./data/dart
```

## 다음 단계

- [ ] S3/Cloudflare R2 통합
- [ ] 공시 파싱 엔진 (HTML → 구조화된 데이터)
- [ ] 중요 공시 알림 (CB 발행, 대량 거래 등)
- [ ] 온톨로지 연결 (공시 → 회사 → 임원)
- [ ] 대시보드 (크롤링 상태, 통계)
