# Raymontology 5분 배포 가이드

**가장 빠른 Railway 배포 방법**

---

## 🚀 빠른 시작 (5-10분)

### 1️⃣ Railway 프로젝트 생성 (1분)
```bash
# https://railway.app 접속 → "New Project"
# "Deploy from GitHub repo" → raymontology 선택
```

### 2️⃣ 데이터베이스 추가 (1분)
```bash
# Railway 대시보드에서:
# "Add Service" → PostgreSQL (Hobby $5/월)
# "Add Service" → Redis (Hobby $5/월)
```

### 3️⃣ 외부 서비스 준비 (2분)

**Neo4j Aura** (무료):
```bash
# https://console.neo4j.io → "Create Free Instance"
# 복사: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
```

**Cloudflare R2** (무료 10GB):
```bash
# https://dash.cloudflare.com → R2 → "Create Bucket"
# 복사: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_ENDPOINT_URL
```

**DART API** (무료):
```bash
# https://opendart.fss.or.kr → 회원가입 → API 키 발급
# 복사: DART_API_KEY
```

### 4️⃣ 환경 변수 설정 (2분)

**Backend Service → Variables**:
```env
# 자동 생성
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# 수동 입력 (위에서 복사한 값)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxxxx
DART_API_KEY=xxxxx
R2_ACCESS_KEY_ID=xxxxx
R2_SECRET_ACCESS_KEY=xxxxx
R2_BUCKET_NAME=raymontology-pdfs
R2_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com

# SECRET_KEY 생성
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

ENVIRONMENT=production
```

**Frontend Service → Variables**:
```env
VITE_API_URL=https://backend-production-xxxx.up.railway.app
VITE_APP_NAME=Raymontology
VITE_APP_VERSION=1.0.0
```

### 5️⃣ 배포 실행 (자동, 3-5분)
```bash
git push origin main
# Railway가 자동으로 배포 시작
```

### 6️⃣ 배포 후 초기화 (1분)
```bash
# Railway CLI 설치
npm install -g @railway/cli
railway login

# DB 마이그레이션
railway run python backend/scripts/db_migrate.py create

# 관리자 계정 생성
railway run python backend/scripts/create_admin.py
# Email: admin@raymontology.com
# Password: Admin1234!
```

### 7️⃣ 검증 (1분)
```bash
# Health Check
curl https://backend-production-xxxx.up.railway.app/health

# Frontend 접속
open https://frontend-production-xxxx.up.railway.app
```

---

## ✅ 완료!

**서비스 URL**:
- Frontend: https://frontend-production-xxxx.up.railway.app
- Backend API: https://backend-production-xxxx.up.railway.app
- API Docs: https://backend-production-xxxx.up.railway.app/docs

**관리자 계정**:
- Email: `admin@raymontology.com`
- Password: `Admin1234!` (즉시 변경 필요!)

**총 비용**: 월 $5 (Railway Hobby)

---

## 📚 다음 단계

1. **관리자 비밀번호 변경**
   - Frontend 로그인 → 프로필 → 비밀번호 변경

2. **모니터링 설정**
   - Railway 대시보드 → Metrics 확인
   - Sentry 연동 (선택): https://sentry.io

3. **커스텀 도메인 연결** (선택)
   - Railway → Settings → Domains
   - DNS CNAME 레코드 추가

4. **운영 가이드 확인**
   - `OPERATIONS.md` - 일일/주간 체크리스트
   - `DEPLOYMENT.md` - 상세 배포 문서
   - `DEPLOYMENT_CHECKLIST.md` - 단계별 체크리스트

---

## 🚨 문제 해결

### Backend 배포 실패
```bash
railway logs --service backend
# 환경 변수 13개 모두 설정되었는지 확인
```

### Frontend 빌드 실패
```bash
railway logs --service frontend
# VITE_API_URL이 올바른 Backend URL인지 확인
```

### Database 연결 실패
```bash
railway status --service postgres
# PostgreSQL 서비스가 실행 중인지 확인
```

### OOM (메모리 부족)
```yaml
# backend/app/database.py
pool_size: 5  # 이미 최적화됨
max_overflow: 10

# Railway Pro 업그레이드 고려 ($20/월, 8GB)
```

---

## 💡 유용한 명령어

```bash
# Railway CLI 기본 명령어
railway login                    # 로그인
railway status                   # 서비스 상태
railway logs --service backend   # 백엔드 로그
railway logs --service frontend  # 프론트엔드 로그
railway run <command>            # 명령어 실행
railway link                     # 프로젝트 연결

# 데이터베이스 관리
railway run python backend/scripts/db_migrate.py create  # 테이블 생성
railway run python backend/scripts/db_migrate.py drop    # 테이블 삭제
railway run python backend/scripts/db_migrate.py reset   # 리셋

# 관리자 관리
railway run python backend/scripts/create_admin.py       # 관리자 생성
```

---

**작성일**: 2025-11-15
**소요 시간**: 5-10분 (외부 서비스 가입 포함)
**대상**: Railway 처음 사용자
