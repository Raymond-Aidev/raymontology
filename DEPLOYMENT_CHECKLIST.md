# Railway 배포 최종 체크리스트

**빠른 배포 가이드 - 15분 완성**

---

## ✅ 1단계: 로컬 환경 검증 (5분)

### 필수 파일 확인
```bash
# 배포 필수 파일 존재 확인
ls -la railway.json                    # ✓ Root config
ls -la .railwayignore                  # ✓ Ignore file
ls -la backend/railway.json            # ✓ Backend config
ls -la frontend/railway.json           # ✓ Frontend config
ls -la backend/requirements.txt        # ✓ Python dependencies
ls -la frontend/package.json           # ✓ Node dependencies
ls -la backend/scripts/db_migrate.py   # ✓ Migration script
ls -la backend/scripts/create_admin.py # ✓ Admin creation
```

### 환경 변수 템플릿 확인
```bash
# .env.example 파일 확인
cat backend/.env.example
```

**필수 환경 변수 (13개)**:
- `DATABASE_URL` - PostgreSQL 연결
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` - Neo4j 연결
- `REDIS_URL` - Redis 연결
- `SECRET_KEY` - JWT 암호화 (최소 32자)
- `DART_API_KEY` - DART 공시 API
- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT_URL` - PDF 저장소
- `SENTRY_DSN` - 에러 추적 (선택)
- `ENVIRONMENT` - production

### 로컬 빌드 테스트
```bash
# Backend 빌드
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main &

# Frontend 빌드
cd ../frontend
npm install
npm run build

# Health Check
curl http://localhost:8000/health
# 예상: {"status":"healthy"}
```

**체크포인트**:
- [ ] Backend 시작 성공 (`Application startup complete`)
- [ ] Frontend 빌드 성공 (`dist/` 폴더 생성)
- [ ] Health Check 응답 정상

---

## ✅ 2단계: Railway 프로젝트 설정 (3분)

### Railway 계정 및 프로젝트
```bash
# Railway CLI 설치 (선택)
npm install -g @railway/cli

# 로그인
railway login

# 프로젝트 생성
railway init
```

**웹 UI 설정**:
1. https://railway.app → "New Project"
2. "Deploy from GitHub repo" 선택
3. Repository 선택: `raymontology`
4. Root Directory: `/`

### 서비스 추가
프로젝트 대시보드에서 "Add Service" 클릭:

1. **PostgreSQL**
   - "Add Database" → PostgreSQL
   - 플랜: Hobby ($5/월)
   - 자동 생성: `DATABASE_URL`

2. **Redis**
   - "Add Database" → Redis
   - 플랜: Hobby ($5/월)
   - 자동 생성: `REDIS_URL`

3. **Backend Service**
   - "Add Service" → GitHub repo
   - Root Directory: `/backend`
   - 감지: `railway.json`

4. **Frontend Service**
   - "Add Service" → GitHub repo
   - Root Directory: `/frontend`
   - 감지: `railway.json`

**체크포인트**:
- [ ] PostgreSQL 서비스 실행 중
- [ ] Redis 서비스 실행 중
- [ ] Backend 서비스 생성됨
- [ ] Frontend 서비스 생성됨

---

## ✅ 3단계: 외부 서비스 준비 (5분)

### Neo4j Aura (무료)
1. https://console.neo4j.io → "Create Free Instance"
2. Region: `asia-southeast1` (싱가포르)
3. 생성 후 복사:
   ```
   NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=xxxxx
   ```

### Cloudflare R2 (무료 10GB)
1. https://dash.cloudflare.com → "R2"
2. "Create Bucket" → `raymontology-pdfs`
3. "Manage R2 API Tokens" → "Create API Token"
4. 권한: "Object Read & Write"
5. 복사:
   ```
   R2_ACCESS_KEY_ID=xxxxx
   R2_SECRET_ACCESS_KEY=xxxxx
   R2_BUCKET_NAME=raymontology-pdfs
   R2_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com
   ```

### DART API (무료)
1. https://opendart.fss.or.kr → 회원가입
2. "인증키 신청/관리" → API 키 발급
3. 복사:
   ```
   DART_API_KEY=xxxxx
   ```

### Sentry (선택, 무료)
1. https://sentry.io → "Create Project"
2. Platform: "Python (FastAPI)"
3. 복사:
   ```
   SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
   ```

**체크포인트**:
- [ ] Neo4j URI 복사 완료
- [ ] R2 버킷 생성 및 API 키 복사
- [ ] DART API 키 발급
- [ ] Sentry DSN 복사 (선택)

---

## ✅ 4단계: 환경 변수 설정 (2분)

Railway 대시보드 → Backend Service → "Variables" 탭:

```env
# Database (자동 생성됨)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Neo4j (수동 입력)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxxxx

# DART API (수동 입력)
DART_API_KEY=xxxxx

# Cloudflare R2 (수동 입력)
R2_ACCESS_KEY_ID=xxxxx
R2_SECRET_ACCESS_KEY=xxxxx
R2_BUCKET_NAME=raymontology-pdfs
R2_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com

# Security (수동 생성)
SECRET_KEY=your-super-secret-key-min-32-characters-long-change-this

# Environment
ENVIRONMENT=production
```

**SECRET_KEY 생성**:
```bash
# Python 방법
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL 방법
openssl rand -base64 32
```

Frontend Service → "Variables" 탭:
```env
VITE_API_URL=https://backend-production-xxxx.up.railway.app
VITE_APP_NAME=Raymontology
VITE_APP_VERSION=1.0.0
```

**체크포인트**:
- [ ] Backend 환경 변수 13개 설정
- [ ] Frontend 환경 변수 3개 설정
- [ ] SECRET_KEY 32자 이상

---

## ✅ 5단계: 배포 실행 (자동)

Railway는 GitHub push 시 자동 배포됩니다.

### 배포 트리거
```bash
git add .
git commit -m "feat: Railway production deployment"
git push origin main
```

### 배포 모니터링
Railway 대시보드 → 각 서비스 → "Deployments" 탭

**Backend 배포 로그 확인**:
```
Building...
Running build command: pip install -r requirements.txt
...
Deployment successful
```

**Frontend 배포 로그 확인**:
```
Building...
Running build command: npm install && npm run build
...
Deployment successful
```

**예상 배포 시간**:
- Backend: 3-5분
- Frontend: 2-3분
- Total: 5-8분

**체크포인트**:
- [ ] Backend 배포 성공
- [ ] Frontend 배포 성공
- [ ] 서비스 URL 생성됨

---

## ✅ 6단계: 배포 후 초기화 (3분)

### 데이터베이스 마이그레이션
```bash
# Railway CLI 사용
railway run python backend/scripts/db_migrate.py create

# 또는 웹 UI: Backend Service → "Run a Command"
python backend/scripts/db_migrate.py create
```

**예상 출력**:
```
🔧 데이터베이스 마이그레이션 시작...
✅ 데이터베이스 테이블 생성 완료!

생성된 테이블:
  - users
  - companies
  - disclosures
  - risk_scores
```

### 관리자 계정 생성
```bash
railway run python backend/scripts/create_admin.py
```

**예상 출력**:
```
✅ 관리자 계정 생성 완료!
   Email: admin@raymontology.com
   Password: Admin1234!

⚠️  보안을 위해 비밀번호를 즉시 변경하세요!
```

### Neo4j 초기 인덱스 생성
Neo4j Browser (https://console.neo4j.io) → Query:
```cypher
// Company 노드 인덱스
CREATE INDEX company_corp_code IF NOT EXISTS FOR (c:Company) ON (c.corp_code);
CREATE INDEX company_corp_name IF NOT EXISTS FOR (c:Company) ON (c.corp_name);

// Person 노드 인덱스
CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name);

// 인덱스 확인
SHOW INDEXES;
```

**체크포인트**:
- [ ] 데이터베이스 테이블 생성 완료
- [ ] 관리자 계정 생성 완료
- [ ] Neo4j 인덱스 생성 완료

---

## ✅ 7단계: 배포 검증 (3분)

### Health Check
```bash
# Backend Health
curl https://backend-production-xxxx.up.railway.app/health

# 예상 응답
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "neo4j": "connected"
}
```

### API 테스트
```bash
# 1. 회원가입
curl -X POST https://backend-production-xxxx.up.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@test.com",
    "password": "Test1234!",
    "full_name": "Test User"
  }'

# 2. 로그인
curl -X POST https://backend-production-xxxx.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test@test.com",
    "password": "Test1234!"
  }'

# 3. 회사 검색
curl "https://backend-production-xxxx.up.railway.app/api/companies/search?query=삼성"
```

### Frontend 접속
1. Frontend URL 접속: https://frontend-production-xxxx.up.railway.app
2. 로그인 페이지 확인
3. 관리자 계정으로 로그인:
   - Email: `admin@raymontology.com`
   - Password: `Admin1234!`
4. 대시보드 확인

**체크포인트**:
- [ ] Backend Health Check 성공
- [ ] API 엔드포인트 응답 정상
- [ ] Frontend 접속 가능
- [ ] 관리자 로그인 성공

---

## ✅ 8단계: 모니터링 설정 (선택)

### Railway 모니터링
각 서비스 → "Metrics" 탭:
- CPU Usage < 70%
- Memory Usage < 80% (512MB 제한)
- Network Traffic 정상

### Sentry 에러 추적
1. Sentry 프로젝트 접속
2. "Issues" 탭에서 에러 없음 확인
3. Alert 설정: "Project Settings" → "Alerts"

### UptimeRobot (무료)
1. https://uptimerobot.com → "Add New Monitor"
2. Monitor Type: "HTTP(s)"
3. URL: `https://backend-production-xxxx.up.railway.app/health`
4. Interval: 5분
5. Alert Contacts: 이메일 추가

**체크포인트**:
- [ ] Railway 메트릭 정상
- [ ] Sentry 에러 없음
- [ ] UptimeRobot 모니터링 시작

---

## ✅ 9단계: 커스텀 도메인 설정 (선택)

### Railway에서 도메인 추가
Backend Service → "Settings" → "Domains":
1. "Generate Domain" → `api.yourdomain.com`
2. DNS 레코드 추가:
   ```
   Type: CNAME
   Name: api
   Value: backend-production-xxxx.up.railway.app
   ```

Frontend Service → "Settings" → "Domains":
1. "Generate Domain" → `yourdomain.com`
2. DNS 레코드 추가:
   ```
   Type: CNAME
   Name: @
   Value: frontend-production-xxxx.up.railway.app
   ```

### SSL 인증서 (자동)
Railway는 Let's Encrypt SSL을 자동 발급합니다 (2-5분 소요).

**체크포인트**:
- [ ] 커스텀 도메인 추가
- [ ] DNS 레코드 설정
- [ ] SSL 인증서 발급 완료

---

## ✅ 10단계: 최종 검증

### 전체 시스템 테스트
```bash
# 1. Backend Health
curl https://api.yourdomain.com/health

# 2. Frontend 접속
open https://yourdomain.com

# 3. E2E 테스트
# - 회원가입
# - 로그인
# - 회사 검색
# - 리스크 점수 조회
# - 관계 그래프 확인
```

### 성능 벤치마크
```bash
# API 응답 시간
ab -n 100 -c 10 https://api.yourdomain.com/health

# 예상 결과:
# - 평균 응답: < 200ms
# - 99% 응답: < 500ms
```

### 보안 체크
- [ ] HTTPS 활성화 확인
- [ ] 관리자 비밀번호 변경
- [ ] SECRET_KEY 무작위 생성 확인
- [ ] 환경 변수 노출 없음
- [ ] CORS 설정 확인

**체크포인트**:
- [ ] 전체 시스템 정상 작동
- [ ] 성능 기준 충족
- [ ] 보안 체크 완료

---

## 🎉 배포 완료!

**서비스 URL**:
- Frontend: https://frontend-production-xxxx.up.railway.app
- Backend: https://backend-production-xxxx.up.railway.app
- API Docs: https://backend-production-xxxx.up.railway.app/docs

**다음 단계**:
1. `OPERATIONS.md` 참고 - 일일/주간/월간 운영 가이드
2. `DEPLOYMENT.md` 참고 - 상세 배포 문서
3. 모니터링 대시보드 설정
4. 사용자 초대 및 온보딩

---

## 🚨 문제 해결

### Backend 배포 실패
```bash
# 로그 확인
railway logs --service backend

# 일반적인 원인:
# 1. requirements.txt 누락 패키지
# 2. 환경 변수 미설정
# 3. DATABASE_URL 연결 실패
```

**해결 방법**:
1. `backend/requirements.txt` 확인
2. Railway 환경 변수 13개 모두 설정 확인
3. PostgreSQL 서비스 실행 상태 확인

### Frontend 빌드 실패
```bash
# 로그 확인
railway logs --service frontend

# 일반적인 원인:
# 1. TypeScript 타입 에러
# 2. VITE_API_URL 미설정
# 3. npm install 실패
```

**해결 방법**:
1. 로컬에서 `npm run build` 테스트
2. `VITE_API_URL` 환경 변수 확인
3. `package.json` dependencies 확인

### Database 연결 실패
```bash
# PostgreSQL 상태 확인
railway status --service postgres

# 연결 테스트
railway run --service backend python -c "
from sqlalchemy import create_engine
engine = create_engine('$DATABASE_URL')
conn = engine.connect()
print('Connected!')
"
```

### Memory Limit 초과 (OOM)
Railway Hobby: 512MB 제한

**해결 방법**:
1. `backend/app/database.py`: `pool_size=5` 확인
2. PDF 처리: Streaming 사용 (`backend/app/nlp/pdf_utils.py`)
3. DART Crawler: `batch_size=5` 설정
4. Railway Pro 업그레이드 ($20/월, 8GB)

---

## 📊 예상 비용

### Railway Hobby Plan
- **월 $5** (512MB RAM, 500GB 대역폭)
- PostgreSQL: 포함
- Redis: 포함
- 2개 서비스 (Backend + Frontend)

### 외부 서비스 (무료)
- Neo4j Aura: 무료 (200k 노드, 400k 관계)
- Cloudflare R2: 무료 (10GB 저장, 10M 요청/월)
- DART API: 무료 (10,000 요청/일)
- Sentry: 무료 (5,000 에러/월)

**총 예상 비용**: **월 $5**

---

## 📚 참고 문서

- `DEPLOYMENT.md` - 상세 배포 가이드
- `OPERATIONS.md` - 운영 매뉴얼
- `backend/PERFORMANCE_OPTIMIZATION.md` - 성능 최적화
- `frontend/FRONTEND_README.md` - 프론트엔드 가이드
- Railway 공식 문서: https://docs.railway.app

---

**작성일**: 2025-11-15
**버전**: 1.0.0
**대상**: Railway Hobby Plan (512MB)
