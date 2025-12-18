# Raymontology Railway 배포 가이드

**단계별 체크리스트와 실전 가이드**

---

## 📋 배포 전 체크리스트

### 로컬 테스트

- [ ] **Docker 환경 실행**
  ```bash
  docker-compose up -d
  # PostgreSQL, Redis, Neo4j 실행 확인
  ```

- [ ] **백엔드 서버 시작**
  ```bash
  cd backend
  python -m venv venv
  source venv/bin/activate  # Windows: venv\Scripts\activate
  pip install -r requirements.txt
  python -m app.main
  ```
  - 예상 출력: `Application startup complete.`
  - 확인: http://localhost:8000/docs

- [ ] **프론트엔드 빌드**
  ```bash
  cd frontend
  npm install
  npm run build
  ```
  - 빌드 성공 확인: `dist/` 폴더 생성
  - 크기 확인: `dist/` < 5MB

- [ ] **API 엔드포인트 테스트**
  ```bash
  # Health Check
  curl http://localhost:8000/health

  # Auth
  curl -X POST http://localhost:8000/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"Test1234!","full_name":"Test User"}'

  # Companies
  curl http://localhost:8000/api/companies/search?query=삼성
  ```

- [ ] **Health Check 작동 확인**
  ```bash
  curl http://localhost:8000/health
  # 예상: {"status":"healthy","environment":"development"}
  ```

### 코드 점검

- [ ] **`.env` 파일 .gitignore 확인**
  ```bash
  cat .gitignore | grep .env
  # 확인: .env, .env.local, .env.*.local
  ```

- [ ] **하드코딩된 URL 제거**
  ```bash
  # Backend 확인
  grep -r "localhost:8000" backend/app/

  # Frontend 확인
  grep -r "localhost:8000" frontend/src/

  # ❌ 발견 시: 환경 변수로 변경
  # ✅ settings.frontend_url 또는 import.meta.env.VITE_API_URL 사용
  ```

- [ ] **requirements.txt 최신화**
  ```bash
  cd backend
  pip freeze > requirements.txt

  # 불필요한 패키지 제거
  # ❌ pkg-resources==0.0.0 (제거)
  ```

- [ ] **package.json 의존성 확인**
  ```bash
  cd frontend
  npm outdated
  npm audit
  npm audit fix
  ```

- [ ] **TypeScript 에러 확인**
  ```bash
  cd frontend
  npm run build
  # 에러 0개 확인
  ```

### Git 준비

- [ ] **모든 변경사항 커밋**
  ```bash
  git status
  git add .
  git commit -m "chore: Railway 배포 준비"
  ```

- [ ] **main 브랜치에 푸시**
  ```bash
  git push origin main
  ```

- [ ] **GitHub 저장소 확인**
  - Repository: Public ✅ (또는 Private with Railway Pro)
  - README.md 존재
  - .gitignore 적용됨

---

## 🚀 Railway 배포 단계

### 1. Railway 계정 생성

1. **https://railway.app** 접속
2. **"Start a New Project"** 클릭
3. **GitHub 계정으로 로그인**
   - "Sign in with GitHub" 클릭
   - Railway 권한 승인
4. **저장소 연동 허용**
   - "Install Railway" on GitHub
   - 저장소 선택: `raymontology`

### 2. 새 프로젝트 생성

1. **"New Project"** 클릭
2. **"Deploy from GitHub repo"** 선택
3. **저장소 선택**: `your-username/raymontology`
4. Railway 자동 감지:
   - ✅ Backend: `backend/` (Python)
   - ✅ Frontend: `frontend/` (Node.js)

**중요**: 각 서비스에 Root Directory 설정
- Backend Service → Settings → Root Directory: `/backend`
- Frontend Service → Settings → Root Directory: `/frontend`

### 3. 데이터베이스 추가

#### PostgreSQL

1. 프로젝트 Dashboard에서 **"New"** 클릭
2. **"Database"** → **"Add PostgreSQL"** 선택
3. ✅ 자동 생성됨
4. **Variables** 탭에서 확인:
   ```
   DATABASE_URL=postgresql://postgres:xxxxx@xxxxx.railway.app:5432/railway
   ```
5. Backend Service에서 자동으로 `${{Postgres.DATABASE_URL}}` 사용 가능

#### Redis

1. **"New"** → **"Database"** → **"Add Redis"** 선택
2. ✅ 자동 생성됨
3. **Variables** 탭에서 확인:
   ```
   REDIS_URL=redis://default:xxxxx@xxxxx.railway.app:6379
   ```
4. Backend Service에서 `${{Redis.REDIS_URL}}` 사용 가능

#### Neo4j (외부 서비스)

Railway에서는 Neo4j를 직접 지원하지 않으므로 Neo4j Aura 사용:

1. **https://neo4j.com/cloud/aura/** 접속
2. **"Start Free"** 클릭 (또는 Google/GitHub 로그인)
3. **무료 인스턴스 생성**:
   - Name: `raymontology-prod`
   - Cloud Provider: `Google Cloud` (또는 AWS)
   - Region: `Singapore` (한국에서 가까움)
   - Database: `AuraDB Free` (200k nodes, 4 relationships)
4. **연결 정보 저장** (중요!):
   ```
   URI: neo4j+s://xxxxx.databases.neo4j.io
   Username: neo4j
   Password: xxxxxxxxxx (생성 시 한 번만 표시됨!)
   ```
   - ⚠️ 비밀번호를 안전한 곳에 저장하세요 (1Password, Bitwarden 등)

5. **IP 화이트리스트** (보안):
   - Neo4j Console → Security → Network Access
   - "Add IP Address" → "0.0.0.0/0" (모든 IP 허용, 또는 Railway IP만)

### 4. 환경 변수 설정

#### Backend 서비스 Variables

Railway Dashboard → Backend Service → **Variables** 탭:

```bash
# ============================================================================
# Database (자동 설정됨)
# ============================================================================
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# ============================================================================
# Neo4j (수동 설정 - Neo4j Aura에서 복사)
# ============================================================================
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password_here

# ============================================================================
# DART API (opendart.fss.or.kr에서 발급)
# ============================================================================
DART_API_KEY=your_dart_api_key_here

# ============================================================================
# Security (중요!)
# ============================================================================
SECRET_KEY=your-super-secret-key-minimum-32-characters-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================================================
# Environment
# ============================================================================
ENVIRONMENT=production
DEBUG=false

# ============================================================================
# CORS (프론트엔드 URL)
# ============================================================================
ALLOWED_ORIGINS=https://raymontology.up.railway.app,https://your-custom-domain.com

# ============================================================================
# Sentry (선택사항 - 에러 추적)
# ============================================================================
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx

# ============================================================================
# Storage (선택사항 - Cloudflare R2)
# ============================================================================
STORAGE_TYPE=r2
S3_BUCKET_NAME=raymontology-disclosures
S3_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=your_r2_access_key
S3_SECRET_ACCESS_KEY=your_r2_secret_key
```

**SECRET_KEY 생성 방법**:
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32
```

#### Frontend 서비스 Variables

Railway Dashboard → Frontend Service → **Variables** 탭:

```bash
# API URL (Backend 서비스 URL)
VITE_API_URL=https://raymontology-backend.up.railway.app

# Environment
VITE_ENV=production

# Feature Flags
VITE_ENABLE_DEV_TOOLS=false
```

**중요**: `VITE_API_URL`은 Backend 배포 후 자동 생성된 URL로 업데이트!

### 5. Build & Start 설정 확인

#### Backend

Railway Settings → **Deploy**:
- Build Command: (자동 감지 - 없음)
- Start Command:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

#### Frontend

Railway Settings → **Deploy**:
- Build Command:
  ```bash
  npm run build
  ```
- Start Command:
  ```bash
  npm run start
  ```

**`package.json`에서 확인**:
```json
{
  "scripts": {
    "build": "tsc && vite build",
    "start": "vite preview --port $PORT --host 0.0.0.0"
  }
}
```

### 6. 도메인 설정 (선택사항)

#### Railway 기본 도메인 (무료)

자동 생성됨:
- Backend: `raymontology-backend.up.railway.app`
- Frontend: `raymontology.up.railway.app`

**확인 방법**:
Railway → Service → **Settings** → **Domains**

#### 커스텀 도메인 (선택)

1. **도메인 구매**:
   - 가비아, Cloudflare, Namecheap 등
   - 예: `raymontology.com` ($10-15/년)

2. **Railway에서 추가**:
   - Frontend Service → Settings → **Domains**
   - "Custom Domain" → `raymontology.com` 입력
   - Railway가 CNAME 제공: `raymontology.up.railway.app`

3. **DNS 설정** (도메인 제공업체):
   ```
   Type: CNAME
   Name: @  (또는 raymontology.com)
   Value: raymontology.up.railway.app
   TTL: 3600
   ```

   API용:
   ```
   Type: CNAME
   Name: api
   Value: raymontology-backend.up.railway.app
   TTL: 3600
   ```

4. **SSL 인증서**: Railway가 자동으로 Let's Encrypt 적용 (무료)

5. **Frontend CORS 업데이트**:
   ```bash
   # Backend Variables
   ALLOWED_ORIGINS=https://raymontology.com,https://www.raymontology.com
   ```

### 7. 배포 실행

#### 자동 배포 (권장)

1. **코드 푸시**:
   ```bash
   git add .
   git commit -m "deploy: Railway 배포"
   git push origin main
   ```

2. **Railway 자동 작업**:
   - ✅ GitHub Webhook 감지
   - ✅ 코드 Pull
   - ✅ 의존성 설치
   - ✅ 빌드 실행
   - ✅ 배포
   - ✅ Health Check

3. **배포 진행 상황**:
   - Railway Dashboard → **Deployments** 탭
   - 실시간 로그 확인

#### 수동 배포 (필요 시)

Railway Dashboard → Service → **Deployments** → **Deploy Now**

### 8. 배포 확인

#### Health Check

```bash
# Backend
curl https://raymontology-backend.up.railway.app/health

# 예상 응답:
{
  "status": "healthy",
  "environment": "production"
}
```

#### API 테스트

```bash
# 회원가입
curl -X POST https://raymontology-backend.up.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!",
    "full_name": "Test User"
  }'

# 기업 검색
curl "https://raymontology-backend.up.railway.app/api/companies/search?query=삼성"

# 공시 검색
curl "https://raymontology-backend.up.railway.app/api/disclosures?corp_code=00126380"
```

#### 프론트엔드 접속

브라우저에서:
```
https://raymontology.up.railway.app
```

**확인 사항**:
- [ ] 로그인 페이지 표시
- [ ] API 연결 (회원가입 시도)
- [ ] 기업 검색 작동
- [ ] 반응형 디자인 (모바일)

---

## 🔧 배포 후 작업

### 데이터베이스 마이그레이션

#### Railway CLI 설치

```bash
# npm
npm install -g @railway/cli

# 또는 Homebrew (Mac)
brew install railway
```

#### 마이그레이션 실행

```bash
# Railway 로그인
railway login

# 프로젝트 연결
cd /path/to/raymontology
railway link

# 현재 프로젝트 확인
railway status

# 마이그레이션 실행 (Backend 서비스 선택)
railway run alembic upgrade head

# 또는 직접 환경 변수 사용
railway run python -m alembic upgrade head
```

**Alembic이 없는 경우**:
```bash
# Backend에 추가
cd backend
pip install alembic
alembic init migrations

# 마이그레이션 생성
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 초기 데이터 로드

#### 관리자 계정 생성

```bash
railway run python scripts/create_admin.py
```

**`scripts/create_admin.py`** (생성):
```python
import asyncio
from app.core.security import get_password_hash
from app.database import AsyncSessionLocal, init_db
from app.models import User

async def create_admin():
    await init_db()

    async with AsyncSessionLocal() as session:
        # 관리자 계정 확인
        admin = await session.execute(
            select(User).where(User.email == "admin@raymontology.com")
        )
        if admin.scalar_one_or_none():
            print("Admin already exists")
            return

        # 생성
        admin_user = User(
            email="admin@raymontology.com",
            hashed_password=get_password_hash("Admin1234!"),
            full_name="Administrator",
            is_superuser=True,
        )
        session.add(admin_user)
        await session.commit()
        print("Admin created successfully!")

asyncio.run(create_admin())
```

#### DART 크롤링 시작

```bash
# 최근 24시간 공시
curl -X POST https://raymontology-backend.up.railway.app/api/admin/crawl/dart/recent \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hours": 24}'
```

### 모니터링 설정

#### Railway 기본 모니터링

1. **Dashboard → Metrics**:
   - CPU 사용량
   - 메모리 사용량
   - 네트워크 I/O
   - Disk 사용량

2. **Alerts 설정** (Pro Plan):
   - CPU > 80% → Email/Slack 알림
   - Memory > 400MB (512MB의 80%)
   - 서비스 다운 → 즉시 알림

#### Sentry 에러 추적

1. **https://sentry.io** 가입 (무료)
2. 프로젝트 생성: `raymontology`
3. DSN 복사:
   ```
   https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
   ```
4. Railway Variables에 추가:
   ```bash
   SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
   ```

#### Uptime 모니터링 (UptimeRobot)

1. **https://uptimerobot.com** 가입 (무료)
2. Monitor 추가:
   - Type: HTTP(s)
   - URL: `https://raymontology.up.railway.app`
   - Interval: 5분
3. Alert Contacts: 이메일, Slack

### 백업 설정

#### PostgreSQL 백업 (Railway 자동)

Railway는 자동으로 데이터베이스 백업:
- Frequency: 매일
- Retention: 7일 (Hobby), 30일 (Pro)

**수동 백업**:
```bash
# Railway CLI로 백업
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# 복원
railway run psql $DATABASE_URL < backup_20240115.sql
```

#### Neo4j Aura 백업

Neo4j Aura는 자동 백업:
- Frequency: 매일
- Retention: 7일

**수동 백업**:
```cypher
// Neo4j Browser에서 실행
CALL apoc.export.json.all("backup.json", {})
```

#### 환경 변수 백업

**중요!** 환경 변수를 안전한 곳에 저장:

1. **1Password / Bitwarden**:
   - Secure Note 생성: "Raymontology Railway Env"
   - 모든 환경 변수 복사

2. **로컬 파일** (암호화):
   ```bash
   # .env.production.backup (절대 Git에 커밋 금지!)
   cp .env.railway .env.production.backup

   # GPG 암호화
   gpg -c .env.production.backup
   # → .env.production.backup.gpg 생성
   ```

---

## 🚨 트러블슈팅

### 배포 실패 시

#### 증상: Build Failed

**로그 확인**:
```
Railway → Service → Deployments → Failed Deployment → View Logs
```

**일반적인 원인**:

1. **의존성 설치 실패**:
   ```bash
   # requirements.txt 확인
   # 불필요한 패키지 제거
   # 버전 충돌 해결
   ```

2. **빌드 명령어 오류**:
   ```bash
   # Frontend package.json 확인
   "build": "tsc && vite build"  # TypeScript 에러 확인
   ```

3. **환경 변수 누락**:
   ```bash
   # Variables 탭에서 필수 변수 확인
   VITE_API_URL=...
   DATABASE_URL=...
   ```

#### 증상: 503 Service Unavailable

**원인**: Health Check 실패

**해결**:

1. **Health Check 경로 확인**:
   ```python
   # backend/app/main.py
   @app.get("/health")
   async def health_check():
       return {"status": "healthy"}
   ```

2. **PORT 환경 변수 사용**:
   ```python
   # ❌ 하드코딩
   uvicorn.run(app, host="0.0.0.0", port=8000)

   # ✅ $PORT 사용
   port = int(os.getenv("PORT", 8000))
   uvicorn.run(app, host="0.0.0.0", port=port)
   ```

3. **서버 시작 로그 확인**:
   ```bash
   Railway → Service → Logs → Runtime Logs

   # 예상 로그:
   "Application startup complete."
   "Uvicorn running on http://0.0.0.0:xxxx"
   ```

#### 증상: Database Connection Failed

**에러**:
```
asyncpg.exceptions.InvalidCatalogNameError: database "railway" does not exist
```

**해결**:

1. **DATABASE_URL 확인**:
   ```bash
   # Variables 탭
   DATABASE_URL=postgresql://postgres:...@...railway.app:5432/railway
   ```

2. **asyncpg 설치 확인**:
   ```bash
   # requirements.txt
   asyncpg==0.29.0
   sqlalchemy[asyncio]==2.0.23
   ```

3. **데이터베이스 재시작**:
   ```bash
   Railway → PostgreSQL → Settings → Restart
   ```

#### 증상: CORS Error (Frontend → Backend)

**에러**:
```
Access to fetch at 'https://backend.railway.app' from origin 'https://frontend.railway.app'
has been blocked by CORS policy
```

**해결**:

1. **Backend ALLOWED_ORIGINS 확인**:
   ```bash
   # Backend Variables
   ALLOWED_ORIGINS=https://raymontology.up.railway.app,https://your-domain.com
   ```

2. **Frontend API URL 확인**:
   ```bash
   # Frontend Variables
   VITE_API_URL=https://raymontology-backend.up.railway.app
   ```

3. **CORS 미들웨어 확인**:
   ```python
   # backend/app/main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=settings.allowed_origins,  # 환경 변수에서 로드
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

#### 증상: OOM (Out of Memory)

**에러**:
```
Process exited with code 137 (OOM)
```

**해결**:

1. **메모리 사용량 확인**:
   ```bash
   GET /api/monitoring/metrics/memory

   # 응답:
   {"process": {"rss_mb": 480, "percent": 93}}  # ⚠️ 위험!
   ```

2. **배치 크기 줄이기**:
   ```python
   # DART 크롤링
   batch_size = 5  # 10 → 5로 감소
   ```

3. **Railway Pro로 업그레이드**:
   - Hobby: 512MB
   - Pro: 8GB

#### 증상: Neo4j Connection Timeout

**에러**:
```
neo4j.exceptions.ServiceUnavailable: Failed to establish connection
```

**해결**:

1. **NEO4J_URI 확인**:
   ```bash
   # neo4j:// → neo4j+s:// (SSL 필수)
   NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
   ```

2. **비밀번호 확인**:
   ```bash
   NEO4J_PASSWORD=correct-password-here
   ```

3. **IP 화이트리스트**:
   - Neo4j Console → Network Access
   - "0.0.0.0/0" 추가 (모든 IP 허용)

---

## 💰 비용 관리

### 예상 비용

#### 초기 단계 (0-100 사용자)

| 서비스 | 플랜 | 비용 |
|--------|------|------|
| Railway | Hobby (512MB RAM, $5 크레딧/월) | $5/월 |
| Neo4j Aura | Free (200k nodes) | $0 |
| Cloudflare R2 | Free (10GB 저장, Egress 무료) | $0 |
| **총계** | | **$5/월** |

#### 성장 단계 (100-1000 사용자)

| 서비스 | 플랜 | 비용 |
|--------|------|------|
| Railway | Pro (8GB RAM, 우선 지원) | $20/월 |
| Neo4j Aura | Professional (1M nodes) | $65/월 |
| Cloudflare R2 | 50GB 저장 | $1/월 |
| Sentry | Team (100k events) | $26/월 |
| **총계** | | **$112/월** |

#### 대규모 (1000+ 사용자)

| 서비스 | 플랜 | 비용 |
|--------|------|------|
| Railway | Custom | $200+/월 |
| Neo4j Aura | Enterprise | $300+/월 |
| Cloudflare R2 | 500GB+ | $10+/월 |
| **총계** | | **$510+/월** |

### 비용 절감 팁

1. **Railway Hobby 최대 활용**:
   - 메모리 최적화 (배치 크기 조정)
   - 불필요한 서비스 비활성화
   - 캐싱 적극 활용

2. **Cloudflare R2 사용**:
   - S3 대비 Egress 무료 (비용 80% 절감)
   - 10GB까지 무료

3. **Neo4j Aura Free 최대 활용**:
   - 200k nodes까지 무료
   - 중요 데이터만 저장

4. **모니터링 무료 도구**:
   - UptimeRobot (무료)
   - Sentry Developer (무료, 5k events)

### 예산 알림 설정

**Railway**:
1. Dashboard → Account → Billing
2. "Usage Alerts" 설정:
   - $5 초과 시 이메일
   - $10 초과 시 서비스 중지

**Neo4j**:
1. Console → Billing
2. "Budget Alerts" 설정

---

## 📊 모니터링 대시보드

### Railway Metrics

**대시보드 접속**:
```
Railway → Project → Metrics
```

**주요 지표**:
- **CPU**: < 50% (정상), > 80% (경고)
- **메모리**: < 400MB (정상), > 450MB (위험)
- **네트워크**: 요청/분, 에러율
- **Disk**: 사용량 (GB)

### Sentry 대시보드

**에러 추적**:
```
Sentry → Projects → raymontology
```

**주요 지표**:
- **Error Rate**: < 1% (정상)
- **Performance**: P95 < 500ms
- **Issues**: 0개 (목표)

### Custom 모니터링

**API 엔드포인트**:
```bash
# 메모리
GET /api/monitoring/metrics/memory

# 성능
GET /api/monitoring/metrics/performance

# 데이터베이스
GET /api/monitoring/metrics/database

# 캐시
GET /api/monitoring/metrics/cache
```

---

## 🎯 다음 단계

### 배포 완료 후

#### 1주차: 안정화

- [ ] 에러 로그 매일 확인
- [ ] 성능 모니터링
- [ ] 사용자 피드백 수집
- [ ] 핫픽스 준비

#### 1개월: 최적화

- [ ] 데이터베이스 인덱스 최적화
- [ ] 캐시 전략 개선
- [ ] API 응답 시간 단축 (< 200ms)
- [ ] 메모리 사용량 감소

#### 3개월: 성장

- [ ] 사용자 1000명 달성
- [ ] Railway Pro 업그레이드 검토
- [ ] CDN 설정 (Cloudflare)
- [ ] A/B 테스트 시작

#### 6개월: 확장

- [ ] 마이크로서비스 분리 검토
- [ ] Kubernetes 마이그레이션 검토
- [ ] 멀티 리전 배포
- [ ] 자동 스케일링

### 마케팅

- [ ] Product Hunt 런칭
- [ ] GitHub Stars 모으기
- [ ] 블로그 포스트 작성
- [ ] 유튜브 데모 영상
- [ ] LinkedIn, Twitter 홍보

### 기능 로드맵

- [ ] 실시간 알림 (WebSocket)
- [ ] 모바일 앱 (React Native)
- [ ] API 공개 (REST + GraphQL)
- [ ] AI 리스크 예측

---

## 📚 참고 자료

### Railway 문서

- [Railway Docs](https://docs.railway.app/)
- [Deploy Guide](https://docs.railway.app/deploy/deployments)
- [Environment Variables](https://docs.railway.app/develop/variables)
- [Database](https://docs.railway.app/databases/postgresql)

### Neo4j Aura

- [Getting Started](https://neo4j.com/docs/aura/)
- [Connection Guide](https://neo4j.com/docs/aura/platform/connection-details/)

### 모니터링

- [Sentry Python](https://docs.sentry.io/platforms/python/)
- [UptimeRobot](https://uptimerobot.com/api/)

### 내부 문서

- `DEPLOYMENT_GUIDE.md`: 전체 배포 가이드
- `backend/PERFORMANCE_OPTIMIZATION.md`: 성능 최적화
- `frontend/FRONTEND_README.md`: 프론트엔드 가이드

---

## ✅ 최종 체크리스트

### 배포 전

- [ ] 로컬 테스트 완료
- [ ] 코드 점검 완료
- [ ] Git 푸시 완료

### 배포 중

- [ ] Railway 프로젝트 생성
- [ ] 데이터베이스 추가 (PostgreSQL, Redis, Neo4j)
- [ ] 환경 변수 설정 (Backend 13개, Frontend 3개)
- [ ] 빌드 & 배포 성공

### 배포 후

- [ ] Health Check 확인
- [ ] API 테스트 완료
- [ ] 프론트엔드 접속 확인
- [ ] 데이터베이스 마이그레이션
- [ ] 모니터링 설정
- [ ] 백업 설정

### 운영

- [ ] 에러 로그 확인 (매일)
- [ ] 성능 모니터링 (주간)
- [ ] 비용 확인 (월간)
- [ ] 사용자 피드백 수집

---

---

## 📱 Android WebView 앱 배포

### 앱 프로젝트 위치

```
/android/  # Android Studio 프로젝트
```

### 빌드 및 배포 단계

#### 1. 개발 환경 설정

1. **Android Studio 설치** (Hedgehog 2023.1.1 이상)
2. **프로젝트 열기**: File > Open > `android/` 폴더 선택
3. **Gradle Sync** 실행

#### 2. WebApp URL 설정

`android/app/build.gradle.kts`:
```kotlin
buildConfigField("String", "WEBAPP_URL", "\"https://raymontology.com\"")
```

#### 3. 서명 키 생성

```bash
cd android
mkdir -p keystore
keytool -genkey -v -keystore keystore/raymontology.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias raymontology
```

#### 4. 릴리스 빌드

```bash
# APK (AppIntos용)
./gradlew assembleRelease

# AAB (Google Play Store용)
./gradlew bundleRelease
```

**빌드 결과물**:
- APK: `app/build/outputs/apk/release/app-release.apk`
- AAB: `app/build/outputs/bundle/release/app-release.aab`

### 앱 스토어 제출

#### AppIntos 제출

1. APK 파일 업로드
2. 앱 정보 입력:
   - 앱 이름: Raymontology
   - 카테고리: 금융/비즈니스
   - 설명, 스크린샷

#### Google Play Store 제출

1. **Play Console 계정** 생성 ($25 일회성)
2. **앱 등록**: 내부 테스트 트랙에 AAB 업로드
3. **스토어 정보**:
   - 앱 이름: Raymontology - 기업 관계 네트워크 분석
   - 카테고리: 금융
   - 스크린샷 (최소 2장, 1080x1920)
   - Feature Graphic (1024x500)
4. **데이터 안전 양식** 작성
5. **콘텐츠 등급** 설정
6. **프로덕션 출시**

### 필수 자산

| 자산 | 규격 | 용도 |
|------|------|------|
| 앱 아이콘 | 512x512 PNG | 스토어/런처 |
| Feature Graphic | 1024x500 PNG | Play Store |
| 스크린샷 (폰) | 1080x1920 (2-8장) | 스토어 |

자세한 내용: `android/README.md` 참고

---

**축하합니다! Raymontology가 Railway에 성공적으로 배포되었습니다! 🎉**

다음: [운영 가이드](OPERATIONS.md) (TODO)
