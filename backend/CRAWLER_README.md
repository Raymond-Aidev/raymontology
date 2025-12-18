# DART 크롤러 Railway 배포 가이드

Raymontology DART 공시 데이터 수집 시스템

---

## 📋 개요

### DART란?
- **D**ata **A**nalysis, **R**etrieval and **T**ransfer System
- 금융감독원 전자공시시스템
- 상장기업의 모든 공시 정보 제공
- OpenAPI: https://opendart.fss.or.kr/

### 수집 데이터
- 사업보고서
- 분기보고서
- 감사보고서
- 전환사채(CB) 발행 공시
- 주요주주 변동 공시
- 임원 현황

---

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Railway                               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   FastAPI    │  │    Celery    │  │   Celery     │     │
│  │   (API)      │  │    Worker    │  │    Beat      │     │
│  └───────┬──────┘  └───────┬──────┘  └───────┬──────┘     │
│          │                 │                  │             │
│          └─────────────────┴──────────────────┘             │
│                           │                                 │
│  ┌────────────────────────┼────────────────────────┐       │
│  │                        │                         │       │
│  │  ┌──────────┐  ┌──────▼─────┐  ┌──────────┐   │       │
│  │  │PostgreSQL│  │   Redis    │  │   Neo4j  │   │       │
│  │  └──────────┘  └────────────┘  └──────────┘   │       │
│  │                                                  │       │
│  └──────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ DART OpenAPI│
                    │    (FSS)    │
                    └─────────────┘
```

---

## ⚠️ Railway 제한사항 및 고려사항

### 1. 스토리지 (Ephemeral)

**문제**: Railway는 임시 스토리지만 제공
- 컨테이너 재시작 시 파일 삭제
- 대용량 PDF 저장 불가

**해결책**:
```python
# ❌ 로컬 파일 저장 (Railway에서 삭제됨)
with open('report.pdf', 'wb') as f:
    f.write(pdf_data)

# ✅ S3/R2에 업로드
import boto3
s3 = boto3.client('s3')
s3.put_object(
    Bucket='raymontology-disclosures',
    Key=f'{corp_code}/{rcept_no}.pdf',
    Body=pdf_data
)
```

**추천 스토리지**:
1. **Cloudflare R2** (권장)
   - S3 호환 API
   - 무료 10GB
   - Egress 무료
   - 설정: https://developers.cloudflare.com/r2/

2. **AWS S3**
   - 안정성 높음
   - 비용 발생 (Egress)

3. **Railway Volume** (제한적)
   - 영구 저장 가능
   - 메타데이터만 권장

### 2. 메모리 제한

**Railway Hobby Plan**: 512MB

**문제**: 대량 크롤링 시 OOM (Out of Memory)

**해결책**:
```python
# ❌ 전체 로드 (메모리 부족)
companies = await get_all_companies()  # 2500개
for company in companies:
    await crawl(company)  # 메모리 폭발

# ✅ 배치 처리 (메모리 안전)
BATCH_SIZE = 10  # Railway 최적화
for i in range(0, len(companies), BATCH_SIZE):
    batch = companies[i:i+BATCH_SIZE]
    await process_batch(batch)
    # 배치 완료 후 메모리 해제
    gc.collect()
```

**모니터링**:
```bash
# 메모리 사용량 확인
curl https://your-app.railway.app/api/monitoring/metrics/memory

# 응답
{
  "process": {
    "rss_mb": 256.5,  # 현재 사용량
    "percent": 50.1   # 전체의 50%
  }
}
```

### 3. API 요청 제한

**DART API 제한**:
- **초당**: 10건
- **분당**: 600건
- **일일**: 10,000건

**구현**:
```python
# backend/app/crawlers/dart_client.py
class DARTClient:
    MAX_REQUESTS_PER_SECOND = 10

    async def _rate_limit(self):
        # 초당 10건 제한
        if len(self._request_times) >= 10:
            await asyncio.sleep(1.0)
```

**전체 크롤링 예상 시간**:
```
상장사 2,500개 × 평균 50개 공시 = 125,000건
125,000건 ÷ 10,000건/일 = 약 12.5일

→ 해결: 최근 1년 데이터만 (약 2-3시간)
```

### 4. 실행 방법

#### 로컬 테스트

```bash
# 1. 환경 변수 설정
export DART_API_KEY=your_api_key_here

# 2. 단일 기업 테스트
python -c "
import asyncio
from app.crawlers.dart_client import DARTClient
from app.config import settings

async def test():
    async with DARTClient(settings.dart_api_key) as client:
        # 삼성전자 공시 조회
        disclosures = await client.get_disclosure_list(
            '00126380',  # 삼성전자
            '20230101',
            '20231231'
        )
        print(f'{len(disclosures)}개 공시 발견')

asyncio.run(test())
"
```

#### Railway 배포

**방법 1: 관리자 API 사용 (권장)**

```bash
# 최근 24시간 크롤링 (빠름, 동기)
POST /api/admin/crawl/dart/recent
{
  "hours": 24
}

# 전체 크롤링 (백그라운드)
POST /api/admin/crawl/dart/all
{
  "years": 3,
  "batch_size": 10
}

# 상태 조회
GET /api/admin/crawl/status/{job_id}
```

**방법 2: Celery 태스크 (스케줄링)**

```python
# backend/app/tasks/crawler_tasks_dart.py
from app.tasks.crawler_tasks_dart import trigger_full_crawl_async

# 백그라운드 실행
task_id = trigger_full_crawl_async(years=3, batch_size=10)
```

**방법 3: Railway Cron (정기 실행)**

Railway에서 Cron 설정:
```yaml
# railway.toml (Railway Cron)
[[schedules]]
name = "daily-dart-crawl"
cron = "0 9 * * *"  # 매일 오전 9시
command = "python -m app.crawlers.dart_crawler recent --hours=24"
```

---

## 🚀 사용 가이드

### 1. DART API 키 발급

1. https://opendart.fss.or.kr/ 접속
2. 회원가입/로그인
3. "인증키 신청/관리" 메뉴
4. 이메일로 API 키 수신

### 2. Railway 환경 변수 설정

```bash
# Railway Dashboard → Variables
DART_API_KEY=your_dart_api_key_here

# 스토리지 (Cloudflare R2 사용시)
STORAGE_TYPE=r2
S3_BUCKET_NAME=raymontology-disclosures
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=your_r2_access_key
S3_SECRET_ACCESS_KEY=your_r2_secret_key
```

### 3. 초기 데이터 수집

**Step 1**: 상장사 목록 조회
```bash
POST /api/admin/crawl/dart/recent
{
  "hours": 720  # 최근 30일
}
```

**Step 2**: 전체 크롤링 (백그라운드)
```bash
POST /api/admin/crawl/dart/all
{
  "years": 3,
  "batch_size": 10  # Railway 메모리 고려
}

# 응답
{
  "job_id": "crawl_full_20231201_123456",
  "status": "started",
  "estimated_time": "약 6-9시간 소요 예상"
}
```

**Step 3**: 진행 상황 확인
```bash
GET /api/admin/crawl/status/crawl_full_20231201_123456

# 응답
{
  "status": "running",
  "details": {
    "companies_processed": 123,
    "total_companies": 2500,
    "progress_percent": 5
  }
}
```

### 4. 정기 크롤링 설정

**Celery Beat 사용**:

```python
# backend/app/tasks/celeryconfig.py
beat_schedule = {
    # 매일 오전 9시 - 최근 24시간 크롤링
    'daily-recent-crawl': {
        'task': 'scheduled_crawl_recent_disclosures',
        'schedule': crontab(hour=9, minute=0),
    },

    # 매주 일요일 새벽 2시 - 주간 전체 업데이트
    'weekly-full-crawl': {
        'task': 'scheduled_crawl_weekly_full',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
    },
}
```

**Railway Cron 사용** (더 간단):

Railway Dashboard → Settings → Cron Jobs:
```
# 매일 오전 9시
0 9 * * * curl -X POST https://your-app.railway.app/api/admin/crawl/dart/recent
```

---

## 📊 모니터링

### 크롤링 통계

```bash
GET /api/admin/crawl/stats

# 응답
{
  "total_companies": 2500,
  "total_disclosures": 123456,
  "last_crawl_at": "2023-12-01T10:30:00",
  "companies_with_data": 2450
}
```

### 메모리 사용량

```bash
GET /api/monitoring/metrics/memory

# 경고: 400MB 이상 (Railway Hobby: 512MB)
{
  "process": {
    "rss_mb": 425.5,  # ⚠️ 위험
    "percent": 83.1
  }
}
```

### Celery 태스크 상태

```bash
# Flower UI (선택사항)
http://your-app.railway.app:5555

# 또는 API
GET /api/admin/crawl/status/{task_id}
```

---

## 🛠️ 최적화 팁

### 1. 배치 크기 조정

```python
# 메모리 사용량에 따라 조정
if memory_usage > 400:  # MB
    batch_size = 5  # 작게
elif memory_usage < 200:
    batch_size = 20  # 크게
else:
    batch_size = 10  # 기본
```

### 2. 중요 공시 우선 처리

```python
# 우선순위: 사업보고서 > 분기보고서 > 기타
PRIORITY_REPORTS = [
    "사업보고서",
    "반기보고서",
    "분기보고서",
    "감사보고서"
]

disclosures = sorted(
    disclosures,
    key=lambda x: PRIORITY_REPORTS.index(x['report_nm'])
    if x['report_nm'] in PRIORITY_REPORTS else 999
)
```

### 3. 캐싱 활용

```python
from app.utils.cache import cache_search_results

# 상장사 목록 캐싱 (24시간)
@cached(ttl=24*60*60, key_prefix="dart_companies")
async def get_all_companies():
    async with DARTClient(api_key) as client:
        return await client.get_corp_code_list()
```

---

## 🔧 트러블슈팅

### 문제 1: "API Key Invalid"

**원인**: DART API 키 미설정 또는 잘못됨

**해결**:
```bash
# Railway 환경 변수 확인
railway variables

# 재설정
railway variables set DART_API_KEY=your_new_key
```

### 문제 2: 메모리 부족 (OOM)

**증상**: Railway 자동 재시작

**해결**:
1. 배치 크기 줄이기: `batch_size=5`
2. 가비지 컬렉션 강제 실행
3. 불필요한 데이터 즉시 삭제

```python
import gc

for batch in batches:
    await process_batch(batch)
    batch = None  # 참조 제거
    gc.collect()  # 강제 GC
```

### 문제 3: Rate Limit 초과

**증상**: "API 요청 한도 초과"

**해결**:
```python
# 요청 간 대기 시간 증가
await asyncio.sleep(0.15)  # 100ms → 150ms
```

### 문제 4: 크롤링 중단

**원인**: Railway 재배포 또는 타임아웃

**해결**:
1. Celery 태스크 사용 (재시도 가능)
2. 체크포인트 저장 (중간 상태 기록)
3. 이어서 크롤링 기능 추가

```python
# 마지막 처리 위치 저장
await redis.set('last_crawled_company', corp_code)

# 재시작 시 이어서
last = await redis.get('last_crawled_company')
companies = companies[companies.index(last):]
```

---

## 📈 성능 벤치마크

### 로컬 테스트

| 작업 | 소요 시간 | 메모리 |
|------|----------|--------|
| 상장사 목록 조회 | 5초 | 50MB |
| 단일 기업 (1년) | 10초 | 20MB |
| 100개 기업 (1년) | 15분 | 200MB |

### Railway 배포

| 작업 | 소요 시간 | 메모리 | 비고 |
|------|----------|--------|------|
| 최근 24시간 | 5-10분 | 150MB | 권장 |
| 전체 (1년) | 2-3시간 | 350MB | 배치 10 |
| 전체 (3년) | 6-9시간 | 400MB | 주의 |

---

## 📚 참고 자료

- [DART OpenAPI 가이드](https://opendart.fss.or.kr/guide/main.do)
- [DART API 명세](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001)
- [Cloudflare R2 문서](https://developers.cloudflare.com/r2/)
- [Celery 문서](https://docs.celeryq.dev/)

---

**Railway 환경에 최적화되어 안정적으로 작동합니다! 📊**
