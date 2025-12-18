# Raymontology 배포 가이드

**Railway 환경 배포 완벽 가이드**

---

## 📋 목차

1. [개요](#개요)
2. [사전 준비](#사전-준비)
3. [백엔드 배포](#백엔드-배포)
4. [프론트엔드 배포](#프론트엔드-배포)
5. [데이터베이스 설정](#데이터베이스-설정)
6. [환경 변수 설정](#환경-변수-설정)
7. [모니터링 설정](#모니터링-설정)
8. [트러블슈팅](#트러블슈팅)

---

## 개요

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      Railway Platform                        │
│                                                               │
│  ┌──────────────────────┐  ┌──────────────────────┐         │
│  │   Frontend Service   │  │   Backend Service    │         │
│  │   (React + Vite)     │  │   (FastAPI)          │         │
│  │   Port: $PORT        │  │   Port: 8000         │         │
│  └──────────┬───────────┘  └──────────┬───────────┘         │
│             │                          │                      │
│             └──────────────┬───────────┘                      │
│                            │                                  │
│  ┌─────────────────────────┼──────────────────────┐          │
│  │                         │                       │          │
│  │  ┌──────────┐  ┌───────▼──────┐  ┌──────────┐ │          │
│  │  │PostgreSQL│  │    Redis     │  │  Neo4j   │ │          │
│  │  │(Plugin)  │  │   (Plugin)   │  │ (Plugin) │ │          │
│  │  └──────────┘  └──────────────┘  └──────────┘ │          │
│  │                                                  │          │
│  └──────────────────────────────────────────────────┘          │
│                                                               │
│  ┌──────────────────────────────────────────────┐            │
│  │  Monitoring: Sentry + Prometheus + Logs     │            │
│  └──────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ DART OpenAPI│
                    │ Cloudflare  │
                    │ R2 Storage  │
                    └─────────────┘
```

### 서비스 구성

1. **Frontend**: React + TypeScript + Vite
2. **Backend**: FastAPI + Python 3.11
3. **PostgreSQL**: 관계형 데이터베이스
4. **Redis**: 캐싱 및 세션
5. **Neo4j**: 그래프 데이터베이스
6. **Cloudflare R2**: PDF 스토리지

---

## 사전 준비

### 1. Railway 계정 생성

https://railway.app 접속 및 회원가입

### 2. GitHub 연동

Railway Dashboard → Settings → GitHub 연결

### 3. 필요한 API 키

- **DART API Key**: https://opendart.fss.or.kr/
- **Sentry DSN** (선택): https://sentry.io/
- **Cloudflare R2** (선택): https://developers.cloudflare.com/r2/

---

## 백엔드 배포

### Step 1: Railway 프로젝트 생성

1. Railway Dashboard → New Project
2. Deploy from GitHub repo 선택
3. `raymontology` 저장소 선택
4. Root Directory: `/backend` 설정

### Step 2: 환경 변수 설정

Railway Dashboard → Backend Service → Variables

**필수 환경 변수**:

```bash
# Python
PYTHON_VERSION=3.11

# Environment
ENVIRONMENT=production
DEBUG=false

# PostgreSQL (Railway Plugin에서 자동 설정)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (Railway Plugin에서 자동 설정)
REDIS_URL=${{Redis.REDIS_URL}}

# Neo4j (Railway Plugin에서 자동 설정)
NEO4J_URI=${{Neo4j.NEO4J_URI}}
NEO4J_USER=${{Neo4j.NEO4J_USER}}
NEO4J_PASSWORD=${{Neo4j.NEO4J_PASSWORD}}

# JWT
SECRET_KEY=your-secret-key-here-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=https://your-frontend.railway.app,http://localhost:5173

# DART API
DART_API_KEY=your-dart-api-key

# Sentry (선택)
SENTRY_DSN=your-sentry-dsn

# Cloudflare R2 (선택)
STORAGE_TYPE=r2
S3_BUCKET_NAME=raymontology-disclosures
S3_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=your-r2-access-key
S3_SECRET_ACCESS_KEY=your-r2-secret-key
```

### Step 3: 빌드 설정 확인

Railway는 자동으로 `requirements.txt` 감지 및 설치

**Procfile 없이 자동 실행**:
```bash
# Railway가 자동으로 실행:
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Step 4: 데이터베이스 플러그인 추가

1. **PostgreSQL**:
   - Dashboard → Add Plugin → PostgreSQL
   - 자동으로 `DATABASE_URL` 환경 변수 생성

2. **Redis**:
   - Dashboard → Add Plugin → Redis
   - 자동으로 `REDIS_URL` 환경 변수 생성

3. **Neo4j** (Community Plugin):
   - Dashboard → Add Plugin → Search "Neo4j"
   - 자동으로 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` 생성

### Step 5: 배포 확인

```bash
# 로그 확인
Railway Dashboard → Backend Service → Deployments → View Logs

# 헬스 체크
curl https://your-backend.railway.app/health

# 응답:
{
  "status": "healthy",
  "environment": "production"
}
```

---

## 프론트엔드 배포

### Step 1: Railway 서비스 추가

1. Railway Dashboard → Add New Service
2. Deploy from GitHub repo 선택
3. Root Directory: `/frontend` 설정

### Step 2: 환경 변수 설정

Railway Dashboard → Frontend Service → Variables

```bash
# API URL
VITE_API_URL=https://your-backend.railway.app

# Environment
VITE_ENV=production

# Feature Flags
VITE_ENABLE_DEV_TOOLS=false
```

### Step 3: 빌드 설정

Railway는 `package.json`의 스크립트 자동 실행:

```json
{
  "scripts": {
    "build": "tsc && vite build",
    "start": "vite preview --port $PORT --host 0.0.0.0"
  }
}
```

### Step 4: 배포 확인

```bash
# 프론트엔드 접속
https://your-frontend.railway.app

# 로그인 테스트
https://your-frontend.railway.app/login
```

---

## 데이터베이스 설정

### PostgreSQL 초기 설정

**1. 마이그레이션 실행**:

Railway Dashboard → Backend Service → Settings → Deploy Command:

```bash
# 수동 실행 (Railway Shell)
python -m alembic upgrade head
```

**2. 초기 데이터 로드**:

```bash
# 관리자 계정 생성 등
python scripts/init_db.py
```

### Redis 확인

```python
# Python 셸에서 테스트
import redis
r = redis.from_url(os.getenv('REDIS_URL'))
r.ping()  # True
```

### Neo4j 초기화

```python
# Neo4j 브라우저 접속
https://your-neo4j.railway.app

# Cypher 쿼리 실행
CREATE INDEX company_id IF NOT EXISTS FOR (c:Company) ON (c.id);
```

---

## 환경 변수 설정

### Backend 필수 환경 변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `ENVIRONMENT` | 환경 (production/development) | `production` |
| `DATABASE_URL` | PostgreSQL 연결 URL | Railway 자동 설정 |
| `REDIS_URL` | Redis 연결 URL | Railway 자동 설정 |
| `SECRET_KEY` | JWT 서명 키 (32자 이상) | `your-secret-key...` |
| `DART_API_KEY` | DART OpenAPI 키 | `xxxxxxxx...` |
| `ALLOWED_ORIGINS` | CORS 허용 도메인 | `https://frontend.railway.app` |

### Frontend 필수 환경 변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `VITE_API_URL` | 백엔드 API URL | `https://backend.railway.app` |
| `VITE_ENV` | 환경 | `production` |

### 환경 변수 검증

**Backend**:
```bash
# Railway Shell에서 실행
python -c "from app.config import settings; print(settings.model_dump())"
```

**Frontend**:
```bash
# 브라우저 콘솔에서
console.log(import.meta.env);
```

---

## 모니터링 설정

### 1. Sentry (에러 추적)

**Backend** (`backend/app/core/sentry.py`):
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

def init_sentry():
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
        )
```

Railway 환경 변수:
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

### 2. Prometheus (메트릭)

**자동 활성화** (`backend/app/main.py`):
```python
if settings.environment == "production":
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

**메트릭 확인**:
```bash
curl https://your-backend.railway.app/metrics
```

### 3. 로그 모니터링

**Structured Logging** (자동 활성화):
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "message": "Request completed",
  "extra": {
    "method": "GET",
    "path": "/api/companies/search",
    "duration_ms": 123.45
  }
}
```

**Railway Logs**:
```bash
Railway Dashboard → Service → Logs
```

### 4. 성능 모니터링

**API 엔드포인트**:

```bash
# 메모리 사용량
GET /api/monitoring/metrics/memory

# 성능 메트릭
GET /api/monitoring/metrics/performance

# 데이터베이스 연결 풀
GET /api/monitoring/metrics/database

# 캐시 통계
GET /api/monitoring/metrics/cache

# 활성 알림
GET /api/monitoring/alerts
```

---

## 초기 데이터 로드

### 1. DART 크롤링 시작

**최근 24시간 공시**:
```bash
curl -X POST https://your-backend.railway.app/api/admin/crawl/dart/recent \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hours": 24}'
```

**전체 크롤링** (백그라운드):
```bash
curl -X POST https://your-backend.railway.app/api/admin/crawl/dart/all \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"years": 3, "batch_size": 10}'
```

### 2. 진행 상황 확인

```bash
GET /api/admin/crawl/status/{job_id}

# 응답:
{
  "status": "running",
  "details": {
    "companies_processed": 123,
    "total_companies": 2500,
    "progress_percent": 5
  }
}
```

---

## 트러블슈팅

### 문제 1: 배포 실패 (Build Error)

**증상**: Railway 빌드 실패

**해결**:
1. `requirements.txt` 확인:
```bash
cd backend
pip freeze > requirements.txt
```

2. Python 버전 명시:
```bash
# Railway 환경 변수
PYTHON_VERSION=3.11
```

3. 빌드 로그 확인:
```bash
Railway Dashboard → Service → Deployments → View Logs
```

### 문제 2: 데이터베이스 연결 실패

**증상**: `sqlalchemy.exc.OperationalError`

**해결**:
1. 환경 변수 확인:
```bash
echo $DATABASE_URL
```

2. PostgreSQL 플러그인 재시작:
```bash
Railway Dashboard → PostgreSQL Plugin → Restart
```

3. 연결 풀 설정 조정:
```python
# backend/app/database.py
pool_size=5  # Railway Hobby: 최대 5
max_overflow=10
```

### 문제 3: CORS 에러

**증상**: 프론트엔드에서 API 호출 실패

**해결**:
1. Backend `ALLOWED_ORIGINS` 확인:
```bash
# Railway 환경 변수
ALLOWED_ORIGINS=https://your-frontend.railway.app,http://localhost:5173
```

2. Frontend `VITE_API_URL` 확인:
```bash
# Railway 환경 변수
VITE_API_URL=https://your-backend.railway.app
```

### 문제 4: 메모리 부족 (OOM)

**증상**: Railway 자동 재시작

**해결**:
1. 메모리 사용량 확인:
```bash
GET /api/monitoring/metrics/memory

# 응답:
{
  "process": {
    "rss_mb": 425.5,  # ⚠️ Railway Hobby: 512MB
    "percent": 83.1
  }
}
```

2. 배치 크기 줄이기:
```python
# DART 크롤링
batch_size=5  # 10 → 5
```

3. 캐시 TTL 단축:
```python
# backend/app/utils/cache.py
COMPANY_SEARCH = 15 * 60  # 30분 → 15분
```

### 문제 5: Celery Worker 실패

**증상**: 크롤링 태스크 실행 안 됨

**해결**:
1. Redis 연결 확인:
```python
import redis
r = redis.from_url(os.getenv('REDIS_URL'))
r.ping()
```

2. Celery Worker 로그 확인:
```bash
Railway Dashboard → Celery Worker Service → Logs
```

3. 태스크 재시도:
```bash
POST /api/admin/crawl/dart/recent
```

---

## 성능 최적화

### 1. Database Connection Pool

```python
# backend/app/database.py
pool_size=5  # Railway Hobby 최적
max_overflow=10
pool_recycle=3600  # 1시간
```

### 2. Redis Caching

```python
# backend/app/utils/cache.py
COMPANY_INFO = 24 * 60 * 60  # 24시간
RISK_SCORE = 60 * 60  # 1시간
COMPANY_SEARCH = 30 * 60  # 30분
```

### 3. API Response Compression

```python
# backend/app/main.py
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 4. Frontend Caching

```tsx
// frontend/src/main.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5분
      cacheTime: 10 * 60 * 1000,  // 10분
    },
  },
});
```

---

## 보안 체크리스트

### Backend

- [ ] `SECRET_KEY` 32자 이상 랜덤 문자열
- [ ] `DEBUG=false` (프로덕션)
- [ ] HTTPS 강제 (Railway 자동)
- [ ] CORS 화이트리스트 설정
- [ ] Rate Limiting 활성화
- [ ] SQL Injection 방지 (SQLAlchemy ORM 사용)
- [ ] XSS 방지 (FastAPI 자동)

### Frontend

- [ ] API 키 노출 금지
- [ ] 환경 변수 사용 (`VITE_*`)
- [ ] JWT 토큰 HttpOnly (백엔드 처리)
- [ ] HTTPS 사용
- [ ] 민감 정보 로컬스토리지 암호화

---

## Railway 비용 최적화

### Hobby Plan 제한

- **메모리**: 512MB
- **CPU**: Shared
- **대역폭**: 100GB/월
- **실행 시간**: 제한 없음

### 최적화 전략

1. **메모리**:
   - 배치 크기 조정 (5-10)
   - 스트리밍 처리 활용
   - 가비지 컬렉션 강제 실행

2. **대역폭**:
   - Gzip 압축 (1KB 이상)
   - 이미지 최적화
   - CDN 사용 (Cloudflare)

3. **데이터베이스**:
   - 연결 풀 제한 (pool_size=5)
   - 인덱스 최적화
   - 불필요한 JOIN 제거

---

## 유지보수

### 정기 작업

1. **일일**:
   - 최근 24시간 DART 크롤링
   - 에러 로그 확인
   - 메모리 사용량 모니터링

2. **주간**:
   - 전체 데이터 업데이트
   - 데이터베이스 백업
   - 성능 메트릭 리뷰

3. **월간**:
   - 의존성 업데이트
   - 보안 패치 적용
   - 비용 분석

### 백업 전략

**PostgreSQL**:
```bash
# Railway CLI
railway run pg_dump $DATABASE_URL > backup.sql
```

**Neo4j**:
```bash
# Neo4j 브라우저에서 export
CALL apoc.export.json.all("backup.json")
```

---

## 참고 자료

### 공식 문서

- [Railway 문서](https://docs.railway.app/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [React 문서](https://react.dev/)
- [PostgreSQL 문서](https://www.postgresql.org/docs/)
- [Redis 문서](https://redis.io/docs/)
- [Neo4j 문서](https://neo4j.com/docs/)

### 내부 문서

- `backend/README.md`: 백엔드 개발 가이드
- `backend/PERFORMANCE_OPTIMIZATION.md`: 성능 최적화
- `backend/CRAWLER_README.md`: DART 크롤러
- `backend/NLP_PERFORMANCE_GUIDE.md`: NLP 파싱
- `frontend/FRONTEND_README.md`: 프론트엔드 개발 가이드

---

**Railway 배포 완료! 🚀**
