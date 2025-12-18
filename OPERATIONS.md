# Raymontology 운영 가이드

**Railway 배포 후 일상 운영 매뉴얼**

---

## 📋 목차

1. [일일 체크리스트](#일일-체크리스트)
2. [주간 작업](#주간-작업)
3. [월간 작업](#월간-작업)
4. [모니터링](#모니터링)
5. [백업 및 복구](#백업-및-복구)
6. [긴급 대응](#긴급-대응)
7. [성능 튜닝](#성능-튜닝)

---

## 📅 일일 체크리스트

### 매일 오전 (10분)

- [ ] **서비스 상태 확인**
  ```bash
  # Health Check
  curl https://raymontology-backend.up.railway.app/health

  # 예상: {"status":"healthy","environment":"production"}
  ```

- [ ] **Railway Dashboard 확인**
  - CPU 사용률 < 70%
  - 메모리 사용률 < 80% (< 410MB)
  - 에러 로그 0건

- [ ] **Sentry 에러 확인**
  - Sentry Dashboard → Issues
  - 새 에러 0건
  - 진행 중인 이슈 처리

- [ ] **데이터베이스 상태**
  ```bash
  # API로 확인
  curl https://raymontology-backend.up.railway.app/api/monitoring/metrics/database

  # 연결 풀 상태 확인
  # pool_usage < 80%
  ```

### 매일 오후 (5분)

- [ ] **사용자 피드백 확인**
  - 이메일
  - GitHub Issues
  - Discord/Slack

- [ ] **성능 메트릭 확인**
  ```bash
  curl https://raymontology-backend.up.railway.app/api/monitoring/metrics/performance

  # API 응답 시간 P95 < 500ms
  ```

---

## 🗓️ 주간 작업

### 매주 월요일 (30분)

- [ ] **로그 분석**
  - Railway → Logs → 지난 7일
  - 에러 패턴 분석
  - 느린 쿼리 확인

- [ ] **성능 리포트**
  ```bash
  # 메모리 사용 추세
  Railway Dashboard → Metrics → Memory (7 days)

  # CPU 사용 추세
  Railway Dashboard → Metrics → CPU (7 days)
  ```

- [ ] **보안 업데이트**
  ```bash
  # Backend 의존성 확인
  cd backend
  pip list --outdated

  # 보안 취약점 확인
  pip-audit

  # Frontend 의존성 확인
  cd frontend
  npm outdated
  npm audit
  ```

- [ ] **DART 크롤링 상태**
  ```bash
  # 최근 크롤링 작업 확인
  GET /api/admin/crawl/stats

  # 실패한 작업 확인
  GET /api/admin/crawl/jobs?status=failed
  ```

### 매주 일요일 (1시간)

- [ ] **데이터베이스 백업**
  ```bash
  # PostgreSQL 백업
  railway run pg_dump $DATABASE_URL > backups/db_$(date +%Y%m%d).sql

  # 압축
  gzip backups/db_$(date +%Y%m%d).sql

  # S3 업로드 (선택)
  aws s3 cp backups/db_$(date +%Y%m%d).sql.gz s3://raymontology-backups/
  ```

- [ ] **데이터베이스 최적화**
  ```sql
  -- PostgreSQL 통계 업데이트
  ANALYZE;

  -- 인덱스 재구성 (필요시)
  REINDEX DATABASE railway;

  -- 불필요한 데이터 정리
  VACUUM ANALYZE;
  ```

- [ ] **캐시 정리**
  ```bash
  # Redis 메모리 확인
  redis-cli INFO memory

  # 만료된 키 정리 (자동이지만 확인)
  redis-cli INFO stats | grep expired
  ```

---

## 📊 월간 작업

### 매월 1일 (2시간)

- [ ] **비용 분석**
  ```
  Railway Dashboard → Billing
  - 이번 달 사용량
  - 예상 비용
  - 최적화 기회 찾기
  ```

- [ ] **사용자 통계**
  ```sql
  -- 신규 가입자
  SELECT COUNT(*) FROM users
  WHERE created_at >= DATE_TRUNC('month', NOW());

  -- 활성 사용자 (MAU)
  SELECT COUNT(DISTINCT user_id) FROM sessions
  WHERE created_at >= NOW() - INTERVAL '30 days';

  -- 검색 횟수
  SELECT COUNT(*) FROM search_logs
  WHERE created_at >= DATE_TRUNC('month', NOW());
  ```

- [ ] **성능 리뷰**
  ```
  - P95 응답 시간 추세
  - 에러율 추세
  - 메모리 사용량 추세
  - 데이터베이스 쿼리 성능
  ```

- [ ] **보안 감사**
  ```bash
  # 의존성 업데이트
  cd backend
  pip install --upgrade pip
  pip install -U -r requirements.txt

  cd frontend
  npm update

  # 보안 패치 확인
  npm audit fix
  ```

- [ ] **데이터베이스 증분 백업**
  ```bash
  # 전체 백업 (월 1회)
  railway run pg_dump -Fc $DATABASE_URL > backups/monthly_$(date +%Y%m).dump

  # Neo4j 백업
  # Neo4j Aura Console → Backups → Create Snapshot
  ```

---

## 🔍 모니터링

### Railway Metrics

**Dashboard 위치**: Railway → Project → Metrics

**주요 지표**:

| 지표 | 정상 | 경고 | 위험 |
|------|------|------|------|
| CPU | < 50% | 50-80% | > 80% |
| 메모리 | < 350MB | 350-450MB | > 450MB |
| 디스크 | < 70% | 70-90% | > 90% |
| 네트워크 | < 1Gbps | 1-5Gbps | > 5Gbps |

**알림 설정** (Pro Plan):
```
Railway → Settings → Notifications
- CPU > 80% → Slack/Email
- Memory > 450MB → Slack/Email
- Service Down → SMS (긴급)
```

### Custom API Monitoring

**엔드포인트**:

```bash
# 전체 헬스 체크
GET /api/monitoring/health
{
  "status": "healthy",
  "database": "ok",
  "redis": "ok",
  "neo4j": "ok"
}

# 메모리 사용량
GET /api/monitoring/metrics/memory
{
  "process": {
    "rss_mb": 320.5,
    "percent": 62.6
  },
  "system": {
    "total_mb": 512,
    "available_mb": 191.5
  }
}

# 성능 메트릭
GET /api/monitoring/metrics/performance
{
  "api_calls": {
    "total": 12345,
    "errors": 12,
    "avg_response_time_ms": 123.45
  }
}

# 데이터베이스
GET /api/monitoring/metrics/database
{
  "pool": {
    "size": 5,
    "checked_out": 2,
    "overflow": 0
  }
}
```

### Sentry 에러 추적

**Dashboard**: https://sentry.io/organizations/raymontology

**주요 지표**:
- **Error Rate**: < 1%
- **Crash-Free Sessions**: > 99.9%
- **Issues**: 0개 (미해결)

**알림**:
- 새 에러 발생 → Slack
- 에러 급증 (10/분) → Email
- Critical 에러 → SMS

### UptimeRobot

**Dashboard**: https://uptimerobot.com

**모니터링**:
- Frontend: https://raymontology.up.railway.app
- Backend API: https://raymontology-backend.up.railway.app/health
- 간격: 5분
- 알림: 2회 연속 실패 시 Email

---

## 💾 백업 및 복구

### 자동 백업

#### PostgreSQL (Railway 자동)

```
빈도: 매일 자동
보관: 7일 (Hobby), 30일 (Pro)
복구: Railway Dashboard → Database → Backups
```

#### 수동 백업 스크립트

```bash
#!/bin/bash
# backups/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"

# PostgreSQL
echo "Backing up PostgreSQL..."
railway run pg_dump $DATABASE_URL > $BACKUP_DIR/postgres_$DATE.sql
gzip $BACKUP_DIR/postgres_$DATE.sql

# S3 업로드 (선택)
if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    aws s3 cp $BACKUP_DIR/postgres_$DATE.sql.gz s3://raymontology-backups/postgres/
    echo "Uploaded to S3"
fi

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "postgres_*.sql.gz" -mtime +7 -delete

echo "Backup complete: $BACKUP_DIR/postgres_$DATE.sql.gz"
```

### 복구 절차

#### PostgreSQL 복구

```bash
# 1. 백업 파일 압축 해제
gunzip backups/postgres_20240115.sql.gz

# 2. Railway 데이터베이스에 복구
railway run psql $DATABASE_URL < backups/postgres_20240115.sql

# 3. 확인
railway run psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
```

#### Neo4j 복구

```
1. Neo4j Aura Console → Backups
2. 복구할 스냅샷 선택
3. "Restore" 클릭
4. 확인 (5-10분 소요)
```

#### Redis 복구

Redis는 캐시 용도이므로 복구 불필요 (재생성됨)

---

## 🚨 긴급 대응

### 서비스 다운 (5xx 에러)

**증상**: Health Check 실패, 503 Service Unavailable

**대응 순서**:

1. **Railway 로그 확인**:
   ```
   Railway → Service → Logs → Runtime
   ```

2. **서비스 재시작**:
   ```
   Railway → Service → Settings → Restart
   ```

3. **환경 변수 확인**:
   ```
   Railway → Variables
   - DATABASE_URL
   - REDIS_URL
   - NEO4J_URI
   ```

4. **롤백** (필요시):
   ```
   Railway → Deployments → Previous Deployment → Redeploy
   ```

### 데이터베이스 연결 실패

**증상**: `asyncpg.exceptions.InvalidCatalogNameError`

**대응**:

1. **PostgreSQL 상태 확인**:
   ```
   Railway → PostgreSQL → Metrics
   ```

2. **연결 풀 리셋**:
   ```bash
   # Backend 재시작
   Railway → Backend → Restart
   ```

3. **PostgreSQL 재시작** (최후 수단):
   ```
   Railway → PostgreSQL → Settings → Restart
   ```

### 메모리 부족 (OOM)

**증상**: Process exited with code 137

**즉시 대응**:

1. **서비스 재시작**
2. **배치 크기 줄이기**:
   ```python
   # backend/app/tasks/crawler_tasks_dart.py
   batch_size = 5  # 10 → 5
   ```
3. **메모리 프로파일링**:
   ```bash
   GET /api/monitoring/metrics/memory
   ```

**장기 대책**:
- Railway Pro 업그레이드 (512MB → 8GB)
- 메모리 최적화 (캐시 TTL 단축, 스트리밍 처리)

### DART 크롤링 실패

**증상**: `DART_API_KEY invalid`

**대응**:

1. **API 키 확인**:
   ```
   Railway → Backend → Variables → DART_API_KEY
   ```

2. **API 할당량 확인**:
   ```
   DART OpenAPI → 마이페이지 → 사용량
   ```

3. **재시작**:
   ```bash
   # 크롤링 재시작
   POST /api/admin/crawl/dart/recent
   ```

### Neo4j 연결 끊김

**증상**: `ServiceUnavailable: Connection lost`

**대응**:

1. **Neo4j Aura 상태**:
   ```
   Neo4j Aura Console → Instance → Status
   ```

2. **IP 화이트리스트**:
   ```
   Neo4j Console → Network Access
   - 0.0.0.0/0 추가 (또는 Railway IP)
   ```

3. **재연결**:
   ```bash
   # Backend 재시작
   Railway → Backend → Restart
   ```

---

## ⚡ 성능 튜닝

### 데이터베이스 최적화

#### 인덱스 추가

```sql
-- 자주 검색되는 컬럼
CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_companies_ticker ON companies(ticker);
CREATE INDEX idx_disclosures_corp_code ON disclosures(corp_code);
CREATE INDEX idx_disclosures_rcept_dt ON disclosures(rcept_dt);

-- 복합 인덱스
CREATE INDEX idx_disclosures_corp_rcept
ON disclosures(corp_code, rcept_dt DESC);
```

#### 쿼리 최적화

```sql
-- 느린 쿼리 찾기
SELECT
    query,
    calls,
    mean_exec_time,
    total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Redis 캐싱 전략

**TTL 최적화**:

```python
# backend/app/utils/cache.py

# 자주 변하지 않는 데이터
COMPANY_INFO = 24 * 60 * 60  # 24시간

# 자주 변하는 데이터
RISK_SCORE = 60 * 60  # 1시간

# 검색 결과
COMPANY_SEARCH = 30 * 60  # 30분
```

**캐시 Hit Rate 확인**:

```bash
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses

# Hit Rate = hits / (hits + misses)
# 목표: > 80%
```

### API 응답 최적화

**Pagination**:

```python
# 큰 결과셋은 페이지네이션
page_size = 20  # 기본
max_page_size = 100  # 최대
```

**Gzip 압축**:

```python
# backend/app/main.py
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 1KB 이상 자동 압축
# 대역폭 50-70% 절감
```

**JOIN 최적화**:

```python
# ❌ N+1 쿼리 문제
companies = session.query(Company).all()
for company in companies:
    risk_score = company.risk_score  # 추가 쿼리!

# ✅ Eager Loading
companies = session.query(Company)\
    .options(joinedload(Company.risk_score))\
    .all()
```

### Frontend 최적화

**React Query 캐싱**:

```tsx
// frontend/src/main.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5분
      gcTime: 10 * 60 * 1000,     // 10분
    },
  },
});
```

**Code Splitting**:

```tsx
// Lazy loading
const CompanyDetail = lazy(() => import('./pages/CompanyDetail'));

// Route-based splitting
<Route path="/company/:id" element={
  <Suspense fallback={<Loading />}>
    <CompanyDetail />
  </Suspense>
} />
```

**이미지 최적화**:

```
- WebP 형식 사용
- Lazy Loading
- Responsive Images
- CDN (Cloudflare)
```

---

## 📈 성장 대비

### 1,000 사용자 달성 시

**인프라**:
- [ ] Railway Pro 업그레이드 ($20/월)
- [ ] Neo4j Aura Professional ($65/월)
- [ ] Cloudflare CDN 설정

**데이터베이스**:
- [ ] Read Replica 추가
- [ ] Connection Pool 증가 (5 → 20)
- [ ] 인덱스 최적화

**모니터링**:
- [ ] APM 도구 (DataDog, New Relic)
- [ ] 실시간 알림 (PagerDuty)

### 10,000 사용자 달성 시

**아키텍처**:
- [ ] 마이크로서비스 분리
- [ ] Message Queue (RabbitMQ, Kafka)
- [ ] 멀티 리전 배포

**데이터베이스**:
- [ ] Sharding
- [ ] Caching Layer (Redis Cluster)
- [ ] 전문 DBA 고용

---

## ✅ 운영 체크리스트

### 일일
- [ ] Health Check
- [ ] 에러 로그 확인
- [ ] 메모리/CPU 확인

### 주간
- [ ] 성능 리포트
- [ ] 보안 업데이트
- [ ] 데이터베이스 백업

### 월간
- [ ] 비용 분석
- [ ] 사용자 통계
- [ ] 전체 백업

### 분기
- [ ] 인프라 리뷰
- [ ] 보안 감사
- [ ] 재해 복구 테스트

---

**안정적인 서비스 운영을 위해 체크리스트를 준수하세요! 📊**
