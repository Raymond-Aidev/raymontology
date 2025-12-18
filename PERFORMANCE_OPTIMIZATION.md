# Railway 성능 최적화 가이드

Raymontology의 Railway 환경 최적화 전략 및 구현 상세

---

## 📋 최적화 개요

### Railway Hobby Plan 제한사항
- **메모리**: 512MB
- **CPU**: 공유 vCPU
- **Database**: PostgreSQL (연결 제한)
- **Network**: 제한된 대역폭

### 최적화 목표
- 메모리 사용량 < 400MB (80% 이하)
- API 응답 시간 < 200ms (P95 < 1s)
- Database 연결 효율적 관리
- 캐시 히트율 > 80%

---

## 🗄️ 1. Database 연결 풀 최적화

### 설정 (backend/app/database.py:28-52)

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=5,           # Railway Hobby 제한
    max_overflow=10,       # 피크 시 추가 10개 (총 15개)
    pool_recycle=3600,     # 1시간마다 재활용
    pool_timeout=30,       # 30초 타임아웃
    pool_use_lifo=True,    # LIFO 방식 (캐시 효율성)
)
```

### 최적화 포인트

1. **LIFO (Last-In-First-Out) 전략**
   - 최근 사용된 연결을 재사용하여 캐시 효율성 향상
   - Warm connection 활용

2. **TCP Keepalive**
   - 유휴 연결 유지로 재연결 오버헤드 감소
   - Railway 네트워크 안정성 향상

3. **Connection Recycling**
   - 1시간마다 연결 재활용으로 메모리 누수 방지
   - Long-running connection 문제 해결

### 모니터링

```bash
# 연결 풀 상태 확인
curl https://your-app.railway.app/api/monitoring/metrics/database

# 응답 예시
{
  "pool": {
    "size": 5,
    "checked_out": 3,
    "overflow": 2,
    "total_connections": 7
  }
}
```

---

## 🚀 2. Redis 캐싱 전략

### 캐시 TTL 전략 (backend/app/utils/cache.py:22-41)

```python
class CacheTTL:
    COMPANY_INFO = 24 * 60 * 60      # 24시간 (자주 변하지 않음)
    RISK_SCORE = 60 * 60             # 1시간 (정기 업데이트)
    COMPANY_SEARCH = 30 * 60         # 30분 (검색 결과)
    USER_SESSION = 30 * 60           # 30분 (세션)
    RATE_LIMIT = 60                  # 1분 (Rate limiting)
```

### 캐싱 패턴

#### 1. 기업 정보 캐싱

```python
# 조회 시 캐시 우선
cached = await get_cached_company_info(redis, company_id)
if cached:
    return cached

# 캐시 미스 시 DB 조회 후 캐싱
company = await db.get(company_id)
await cache_company_info(redis, company_id, company, CacheTTL.COMPANY_INFO)
```

#### 2. 검색 결과 캐싱

```python
# 검색 파라미터를 해시로 변환
cache_key = make_hash_key("search", {
    "query": "삼성",
    "market": "KOSPI",
    "page": 1
})

# 캐시 조회/저장
results = await get_cached_search_results(redis, search_params)
```

#### 3. 캐시 무효화

```python
# 기업 데이터 업데이트 시 관련 캐시 삭제
await invalidate_company_cache(redis, company_id)
# 삭제되는 패턴:
# - company:{id}
# - risk:{id}
# - disclosure:{id}:*
```

### Redis 연결 풀 최적화

```python
redis_client = await Redis.from_url(
    settings.redis_url,
    max_connections=50,           # 최대 연결 수
    socket_timeout=5,             # 5초 타임아웃
    retry_on_timeout=True,        # 타임아웃 시 재시도
    health_check_interval=30,     # 30초마다 헬스체크
)
```

### 캐시 성능 모니터링

```bash
curl https://your-app.railway.app/api/monitoring/metrics/cache

# 응답 예시
{
  "total_keys": 1234,
  "memory_used_mb": 12.5,
  "hit_rate": 0.85,              # 85% 히트율
  "connected_clients": 5
}
```

---

## ⚡ 3. API 응답 최적화

### Gzip 압축 (main.py:57)

```python
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

- 1KB 이상 응답 자동 압축
- 평균 70-80% 크기 감소
- Railway 대역폭 절약

### 페이지네이션 (backend/app/utils/pagination.py)

```python
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)  # 최대 50개
```

**최적화 전략**:
1. 최대 페이지 크기 제한 (50개)
2. Offset 기반 페이지네이션 (작은 데이터셋)
3. Cursor 기반 페이지네이션 (대용량 데이터셋)

**사용 예시**:

```python
# Offset 기반 (일반 검색)
items, total = await paginate(
    session,
    query,
    PaginationParams(page=1, page_size=20)
)

# Cursor 기반 (대용량)
response = CursorPaginatedResponse.create(
    items=results,
    limit=params.limit,
    cursor_field="id"
)
```

### 불필요한 JOIN 제거

**비효율적**:
```python
# ❌ N+1 쿼리 문제
companies = await session.execute(select(Company))
for company in companies:
    risk = await session.execute(select(Risk).where(Risk.company_id == company.id))
```

**효율적**:
```python
# ✅ JOIN 사용
query = (
    select(Company, Risk)
    .join(Risk, Company.id == Risk.company_id)
    .options(selectinload(Company.officers))  # Eager loading
)
```

### 응답 크기 최적화

```python
# 필요한 필드만 선택
query = select(
    Company.id,
    Company.name,
    Company.ticker,
    # ... 필요한 필드만
)

# 불필요한 관계 로딩 방지
query = query.options(
    noload(Company.disclosures),  # 큰 관계는 로드하지 않음
    lazyload(Company.officers)
)
```

---

## 💾 4. 메모리 관리 최적화

### 파일 스트리밍 (backend/app/utils/streaming.py)

#### 대용량 파일 처리

```python
# ❌ 메모리에 전체 로드 (512MB 파일 = OOM)
with open(large_file, 'rb') as f:
    content = f.read()  # 전체 메모리 로드

# ✅ 스트리밍 처리
async def stream_file(file_path: Path):
    async with aiofiles.open(file_path, 'rb') as f:
        while chunk := await f.read(CHUNK_SIZE_MEDIUM):
            yield chunk

return StreamingResponse(stream_file(pdf_path))
```

#### 청크 크기 최적화

```python
CHUNK_SIZE_SMALL = 8 * 1024      # 8KB (작은 파일)
CHUNK_SIZE_MEDIUM = 64 * 1024    # 64KB (중간 파일)
CHUNK_SIZE_LARGE = 512 * 1024    # 512KB (큰 파일)
```

### 배치 처리

```python
# 1000개 기업 분석 시
results = await process_in_batches(
    companies,
    batch_size=get_optimal_batch_size(
        total_items=len(companies),
        item_size_mb=0.1,  # 기업당 100KB
        max_memory_mb=100  # 최대 100MB 사용
    ),
    process_func=analyze_company
)
```

**최적 배치 크기 계산**:
- 전체 항목 < 100: batch_size = 10
- 전체 항목 < 1000: batch_size = 50
- 전체 항목 >= 1000: batch_size = 100
- 메모리 기반: max_memory_mb / item_size_mb

### 메모리 임계값 모니터링

```python
# 400MB 이상 경고 (Railway Hobby: 512MB)
if check_memory_threshold(threshold_mb=400):
    logger.warning("Memory usage exceeds threshold")
    # 가비지 컬렉션 강제 실행
    import gc
    gc.collect()
```

---

## 📊 5. 성능 모니터링

### 실시간 모니터링 (backend/app/middleware/performance.py)

#### 응답 시간 추적

```python
class PerformanceMonitoringMiddleware:
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # 응답 헤더 추가
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        # 느린 요청 경고 (1초 이상)
        if duration_ms > 1000:
            logger.warning(f"Slow request: {request.url.path}")
```

#### 메모리 사용량 추적

```python
# 요청 전후 메모리 변화 측정
memory_before = process.memory_info().rss / 1024 / 1024
# ... 요청 처리 ...
memory_after = process.memory_info().rss / 1024 / 1024
memory_delta = memory_after - memory_before

# 50MB 이상 증가 시 경고
if memory_delta > 50:
    logger.warning(f"High memory usage: {memory_delta:.2f}MB")
```

### 모니터링 API 엔드포인트

#### 1. 종합 헬스 체크

```bash
curl https://your-app.railway.app/api/monitoring/health

# 응답
{
  "status": "healthy",
  "databases": {
    "postgresql": {"status": "ok", "latency_ms": 12.3},
    "redis": {"status": "ok", "latency_ms": 1.2},
    "neo4j": {"status": "ok", "latency_ms": 5.6}
  }
}
```

#### 2. 성능 메트릭

```bash
curl https://your-app.railway.app/api/monitoring/metrics/performance

# 응답
{
  "endpoints": {
    "/api/companies/search": {
      "request_count": 1234,
      "avg_response_time_ms": 125.5,
      "p95_response_time_ms": 450.2,
      "error_count": 5,
      "error_rate": 0.004
    }
  }
}
```

#### 3. 메모리 상태

```bash
curl https://your-app.railway.app/api/monitoring/metrics/memory

# 응답
{
  "process": {
    "rss_mb": 256.5,
    "vms_mb": 512.3,
    "percent": 50.1
  },
  "system": {
    "total_mb": 512,
    "available_mb": 255.5,
    "used_mb": 256.5,
    "percent": 50.1
  }
}
```

#### 4. 느린 쿼리

```bash
curl https://your-app.railway.app/api/monitoring/metrics/slow-queries

# 응답
{
  "total": 5,
  "queries": [
    {
      "timestamp": 1699999999,
      "query_name": "get_companies_with_risk",
      "duration_ms": 1250.5,
      "details": {}
    }
  ]
}
```

#### 5. 활성 알림

```bash
curl https://your-app.railway.app/api/monitoring/alerts

# 응답
{
  "total": 2,
  "alerts": [
    {
      "type": "memory",
      "severity": "warning",
      "message": "High memory usage: 425MB",
      "threshold": "400MB"
    },
    {
      "type": "slow_response",
      "severity": "warning",
      "message": "Slow P95 response for /api/companies/search: 1250ms",
      "threshold": "1000ms"
    }
  ]
}
```

---

## 🎯 성능 목표 및 벤치마크

### API 응답 시간

| 엔드포인트 | 목표 (P50) | 목표 (P95) | 임계값 |
|----------|-----------|-----------|--------|
| GET /api/companies/{id} | 50ms | 200ms | 500ms |
| GET /api/companies/search | 100ms | 300ms | 1000ms |
| POST /api/risk/analyze | 200ms | 1000ms | 3000ms |
| GET /api/disclosures | 150ms | 500ms | 1500ms |

### 메모리 사용량

| 상태 | 사용량 | 조치 |
|------|--------|------|
| 정상 | < 300MB | 없음 |
| 주의 | 300-400MB | 모니터링 강화 |
| 경고 | 400-450MB | 가비지 컬렉션 |
| 위험 | > 450MB | 재시작 고려 |

### 캐시 성능

| 메트릭 | 목표 | 최소 |
|--------|------|------|
| 히트율 | > 80% | 70% |
| 메모리 사용량 | < 50MB | < 100MB |
| 평균 응답 시간 | < 5ms | < 10ms |

### Database 연결

| 메트릭 | 목표 | 최대 |
|--------|------|------|
| 활성 연결 | 3-5개 | 10개 |
| 대기 시간 | < 10ms | < 100ms |
| 쿼리 시간 | < 50ms | < 500ms |

---

## 🔧 최적화 체크리스트

### 배포 전

- [ ] Database 연결 풀 설정 확인 (pool_size=5)
- [ ] Redis 연결 설정 확인 (max_connections=50)
- [ ] Gzip 압축 활성화
- [ ] 페이지네이션 최대 크기 제한 (50)
- [ ] 성능 모니터링 미들웨어 활성화

### 배포 후

- [ ] 헬스 체크 확인
- [ ] 초기 메모리 사용량 < 200MB
- [ ] API 응답 시간 측정
- [ ] 캐시 히트율 확인
- [ ] 느린 쿼리 모니터링

### 주기적 점검 (일일)

- [ ] 메모리 사용량 트렌드
- [ ] API 에러율 < 1%
- [ ] P95 응답 시간 < 1s
- [ ] 캐시 히트율 > 70%
- [ ] Database 연결 풀 상태

---

## 📈 성능 개선 예시

### Before 최적화

```
메모리 사용량: 480MB (94%)
API 응답 시간 (P95): 2.5s
캐시 히트율: 30%
Database 연결: 20개 (오버플로우)
에러율: 5%
```

### After 최적화

```
메모리 사용량: 320MB (62%)
API 응답 시간 (P95): 450ms
캐시 히트율: 85%
Database 연결: 5-7개
에러율: 0.5%
```

### 개선율

- 메모리: **33% 감소** ✅
- 응답 시간: **82% 개선** ✅
- 캐시 효율: **183% 증가** ✅
- 에러율: **90% 감소** ✅

---

## 🚨 트러블슈팅

### 메모리 부족 (OOM)

**증상**: Railway에서 자동 재시작

**원인**:
- 대용량 파일을 메모리에 전체 로드
- 캐시 무제한 증가
- 메모리 누수

**해결**:
1. 파일 스트리밍 사용
2. 캐시 TTL 및 maxmemory 설정
3. 가비지 컬렉션 강제 실행
4. 배치 크기 줄이기

### 느린 API 응답

**증상**: P95 > 1s

**원인**:
- N+1 쿼리 문제
- 캐시 미스
- 불필요한 JOIN

**해결**:
1. 쿼리 프로파일링
2. Eager loading 사용
3. 캐시 전략 개선
4. 인덱스 추가

### Database 연결 부족

**증상**: "Too many connections"

**원인**:
- 연결 풀 크기 부족
- 연결 누수
- 트랜잭션 미종료

**해결**:
1. 연결 풀 크기 조정
2. 연결 자동 반환 확인
3. 트랜잭션 timeout 설정
4. 연결 모니터링

---

**Railway 환경에서 최적의 성능을 발휘하도록 구성되었습니다! 🚀**
