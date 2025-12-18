# Railway 배포 가이드

Raymontology를 Railway에 배포하기 위한 완전한 가이드

## 📋 배포 전 체크리스트

### 코드 준비

- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] `backend/requirements.txt` 최신화 확인
  ```bash
  cd backend
  pip freeze > requirements.txt
  ```
- [ ] `backend/Procfile` 존재 확인
- [ ] `backend/railway.json` 설정 확인
- [ ] `frontend/railway.json` 설정 확인
- [ ] Health Check 엔드포인트 작동 확인
  ```bash
  # 로컬에서 테스트
  curl http://localhost:8000/health
  ```

### 데이터베이스 마이그레이션

- [ ] Alembic 마이그레이션 파일 생성
  ```bash
  cd backend
  alembic revision --autogenerate -m "description"
  ```
- [ ] 로컬에서 마이그레이션 테스트
  ```bash
  alembic upgrade head
  ```

### 보안

- [ ] 모든 시크릿 키가 `.env`에만 존재하는지 확인
- [ ] `SECRET_KEY` 강력한 랜덤 값으로 생성
  ```python
  import secrets
  print(secrets.token_urlsafe(32))
  ```
- [ ] `ALLOWED_ORIGINS` 프로덕션 도메인으로 설정

---

## 🚀 Railway 설정

### 1. 프로젝트 생성

1. [Railway.app](https://railway.app) 로그인
2. "New Project" 클릭
3. "Deploy from GitHub repo" 선택
4. `raymontology` 저장소 선택

### 2. 서비스 추가

#### Backend (FastAPI)

1. "New Service" → "Empty Service"
2. Settings:
   - **Name**: `raymontology-backend`
   - **Root Directory**: `/backend`
   - **Start Command**: (자동 감지 - Procfile 사용)
   - **Port**: `8000`

#### Frontend (React + Vite)

1. "New Service" → "Empty Service"
2. Settings:
   - **Name**: `raymontology-frontend`
   - **Root Directory**: `/frontend`
   - **Build Command**: `npm run build`
   - **Start Command**: `npm run preview`
   - **Port**: `5173`

#### PostgreSQL

1. "New" → "Database" → "Add PostgreSQL"
2. 자동으로 `DATABASE_URL` 환경 변수 생성됨

#### Redis

1. "New" → "Database" → "Add Redis"
2. 자동으로 `REDIS_URL` 환경 변수 생성됨

### 3. 환경 변수 설정

Backend 서비스에서 "Variables" 탭:

```bash
# Database (자동 생성)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Neo4j (수동 추가 - Railway에서 Neo4j를 지원하지 않으므로 외부 서비스 사용)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Security
SECRET_KEY=your_super_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# DART API
DART_API_KEY=your_dart_api_key

# Environment
ENVIRONMENT=production
DEBUG=false
FRONTEND_URL=https://raymontology-frontend.up.railway.app

# CORS
ALLOWED_ORIGINS=https://raymontology-frontend.up.railway.app,https://yourdomain.com
```

Frontend 서비스에서 "Variables" 탭:

```bash
VITE_API_URL=https://raymontology-backend.up.railway.app
```

### 4. 도메인 연결 (선택 사항)

1. Backend 서비스 → Settings → Networking → "Generate Domain"
2. 또는 커스텀 도메인 추가:
   - "Custom Domain" 클릭
   - `api.yourdomain.com` 입력
   - DNS CNAME 레코드 추가

3. Frontend 서비스 → Settings → Networking → "Generate Domain"
4. 커스텀 도메인: `yourdomain.com`

---

## ✅ 배포 후 체크리스트

### Health Check

- [ ] Backend Health Check
  ```bash
  curl https://raymontology-backend.up.railway.app/health
  ```

  예상 응답:
  ```json
  {
    "status": "healthy",
    "environment": "production"
  }
  ```

- [ ] Frontend 접속 확인
  ```
  https://raymontology-frontend.up.railway.app
  ```

### API 테스트

- [ ] 로그인 테스트
  ```bash
  curl -X POST https://raymontology-backend.up.railway.app/api/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test@example.com&password=testpass"
  ```

- [ ] 기업 검색 테스트
  ```bash
  curl https://raymontology-backend.up.railway.app/api/companies/search?query=삼성
  ```

### 데이터베이스

- [ ] 마이그레이션 실행 확인
  ```bash
  # Railway CLI 사용
  railway run alembic upgrade head
  ```

- [ ] 테이블 생성 확인
  ```bash
  # Railway Dashboard → PostgreSQL → Query
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public';
  ```

### 로그 확인

- [ ] Backend 로그 확인
  - Railway Dashboard → Backend 서비스 → Logs
  - 에러 없이 시작되는지 확인

- [ ] Frontend 로그 확인
  - Railway Dashboard → Frontend 서비스 → Logs
  - 빌드 성공 확인

### 성능

- [ ] 응답 시간 측정
  ```bash
  time curl https://raymontology-backend.up.railway.app/health
  ```

- [ ] 메모리 사용량 확인
  - Railway Dashboard → Metrics

---

## 🔧 문제 해결

### 일반적인 문제

#### 1. 데이터베이스 연결 실패

**증상**: `could not connect to server`

**해결**:
1. `DATABASE_URL` 환경 변수 확인
2. PostgreSQL 서비스 실행 중인지 확인
3. Railway 네트워크 설정 확인

#### 2. CORS 에러

**증상**: `Access to fetch at ... has been blocked by CORS policy`

**해결**:
1. `ALLOWED_ORIGINS` 환경 변수 확인
2. Frontend URL이 정확한지 확인
3. Backend 재배포

#### 3. Static 파일 404

**증상**: Frontend에서 JS/CSS 파일 로드 실패

**해결**:
1. Build 명령어 확인: `npm run build`
2. Start 명령어 확인: `npm run preview`
3. `vite.config.ts`에서 `base` 경로 확인

#### 4. 메모리 부족

**증상**: `MemoryError` 또는 서비스 재시작

**해결**:
1. Railway 플랜 업그레이드
2. Worker 프로세스 수 줄이기 (Procfile)
3. 메모리 효율적인 코드로 최적화

#### 5. 환경 변수 적용 안 됨

**증상**: 변경한 환경 변수가 반영되지 않음

**해결**:
1. 서비스 재배포 (Redeploy)
2. Railway Dashboard에서 환경 변수 재확인

---

## 📊 모니터링

### Railway 내장 모니터링

1. **Metrics**:
   - CPU 사용량
   - 메모리 사용량
   - 네트워크 I/O

2. **Logs**:
   - Real-time logs
   - 에러 로그 필터링
   - 로그 다운로드

### 외부 모니터링 (선택)

#### Sentry (에러 추적)

1. [Sentry.io](https://sentry.io) 계정 생성
2. Python 프로젝트 생성
3. DSN 복사
4. Backend에 Sentry 설정:
   ```python
   # backend/app/main.py
   import sentry_sdk

   if settings.environment == "production":
       sentry_sdk.init(
           dsn="your_sentry_dsn",
           environment="production",
       )
   ```
5. 환경 변수 추가:
   ```
   SENTRY_DSN=your_sentry_dsn
   ```

#### Better Uptime (가동 시간 모니터링)

1. [Better Uptime](https://betteruptime.com) 계정 생성
2. HTTP Monitor 추가:
   - URL: `https://raymontology-backend.up.railway.app/health`
   - Interval: 1분
3. 알림 설정 (이메일, Slack)

---

## 🔄 CI/CD

### GitHub Actions (선택)

`.github/workflows/deploy.yml`:

```yaml
name: Deploy to Railway

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Railway
        run: echo "Railway auto-deploys on push to main"
```

### Railway 자동 배포

Railway는 기본적으로 **자동 배포**가 활성화되어 있습니다:
- `main` 브랜치에 푸시하면 자동으로 배포됨
- Pull Request 생성 시 Preview 환경 자동 생성 (선택 사항)

---

## 💡 최적화 팁

### 1. 빌드 캐싱

Railway는 자동으로 의존성을 캐싱합니다:
- Python: `requirements.txt` 변경 시에만 재설치
- Node: `package-lock.json` 변경 시에만 재설치

### 2. 메모리 최적화

**Procfile**:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
```

Worker 수를 줄여 메모리 사용량 감소

### 3. Celery Worker 분리

크롤링/파싱 작업이 많은 경우:

1. Worker 서비스 추가
2. Procfile:
   ```
   worker: celery -A app.tasks.celery_app worker --loglevel=info
   ```
3. Redis 공유

### 4. CDN 사용

Static 파일을 Cloudflare나 AWS CloudFront에 업로드하여 속도 향상

---

## 📚 추가 리소스

- [Railway 공식 문서](https://docs.railway.app)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
- [Vite 프로덕션 빌드](https://vitejs.dev/guide/build.html)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Don%27t_Do_This)

---

## 🆘 지원

문제가 발생하면:

1. Railway Community Forum
2. GitHub Issues
3. Railway Discord

**배포 성공을 기원합니다! 🚀**
