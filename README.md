# Raymontology

**Raymond + Ontology** = 관계형 리스크 온톨로지 시스템

팔란티어 온톨로지 기반 금융 시장 리스크 분석 플랫폼

## 핵심 기능

- 🔍 **관계 추적**: 임원, 기업, 펀드 간 복잡한 관계망 시각화
- ⚠️ **리스크 분석**: 정보/권력 비대칭 측정 및 점수화
- 📊 **실시간 모니터링**: DART 공시 자동 수집 및 분석
- 🎯 **투자 보호**: 일반 투자자를 위한 공정한 정보 제공

## 기술 스택

- Backend: FastAPI (Python 3.11)
- Frontend: React + TypeScript
- Database: PostgreSQL 15 (Railway)
- Cache: Redis 7 (Railway)
- Graph DB: Neo4j Aura
- Hosting: Railway

## 로컬 개발

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/raymontology.git
cd raymontology
```

### 2. 데이터베이스 시작
```bash
docker-compose up -d
```

### 3. 백엔드 실행
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

### 4. 프론트엔드 실행
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

접속: http://localhost:5173

## Railway 배포

**빠른 시작**: [QUICK_START.md](QUICK_START.md) - 5분 배포 가이드

### 배포 전 검증
```bash
python3 scripts/verify_deployment.py
```

### 배포 가이드
- **[빠른 시작](QUICK_START.md)**: 5-10분 최소 배포 가이드
- **[배포 체크리스트](DEPLOYMENT_CHECKLIST.md)**: 단계별 상세 체크리스트
- **[상세 배포 가이드](DEPLOYMENT.md)**: 완전한 배포 문서 (500+ 줄)
- **[운영 매뉴얼](OPERATIONS.md)**: 배포 후 일일/주간 운영 가이드

### 필수 단계 요약

1. **Railway 설정**
   - https://railway.app 계정 생성
   - New Project → Deploy from GitHub
   - raymontology 저장소 선택

2. **데이터베이스 추가**
   - PostgreSQL (Railway Hobby)
   - Redis (Railway Hobby)
   - Neo4j Aura (무료, 별도 설정)

3. **환경 변수 (13개)**
   - Backend: DATABASE_URL, REDIS_URL, NEO4J_*, DART_API_KEY, R2_*, SECRET_KEY
   - Frontend: VITE_API_URL

4. **배포 실행**
   ```bash
   git push origin main
   ```

5. **배포 후 초기화**
   ```bash
   railway run python backend/scripts/db_migrate.py create
   railway run python backend/scripts/create_admin.py
   ```

**예상 비용**: 월 $5 (Railway Hobby Plan)

## 아키텍처

```
사용자
  │
  ↓
Frontend (React) ← Railway CDN
  │
  ↓
Backend (FastAPI) ← Railway
  │
  ├→ PostgreSQL (구조화 데이터)
  ├→ Redis (캐시)
  ├→ Neo4j (관계 그래프)
  └→ DART API (공시 수집)
```

## 📚 문서

### 배포 및 운영

- **[빠른 시작](QUICK_START.md)**: 5분 Railway 배포 가이드
- **[배포 체크리스트](DEPLOYMENT_CHECKLIST.md)**: 단계별 배포 체크리스트 (15분)
- **[상세 배포 가이드](DEPLOYMENT.md)**: 완전한 Railway 배포 문서
- **[운영 매뉴얼](OPERATIONS.md)**: 일일/주간/월간 운영 가이드

### 개발 가이드

- **[백엔드 개발 가이드](backend/README.md)**: FastAPI, 데이터베이스, API 개발
- **[프론트엔드 개발 가이드](frontend/FRONTEND_README.md)**: React, TypeScript, 컴포넌트 개발
- **[회사 UI 가이드](frontend/COMPANY_UI_README.md)**: 회사 검색/상세 페이지, Debounce 패턴

### 성능 최적화

- **[성능 최적화 가이드](backend/PERFORMANCE_OPTIMIZATION.md)**: Railway 환경 최적화 (33% 메모리 절감)
- **[NLP 파싱 가이드](backend/NLP_PERFORMANCE_GUIDE.md)**: PDF 파싱 메모리 관리
- **[모니터링 가이드](backend/MONITORING.md)**: Sentry, 로그, 메트릭

### 데이터 수집

- **[DART 크롤러 가이드](backend/CRAWLER_README.md)**: 공시 데이터 자동 수집

### 도구

- **배포 검증**: `python3 scripts/verify_deployment.py`
- **DB 마이그레이션**: `python backend/scripts/db_migrate.py create`
- **관리자 생성**: `python backend/scripts/create_admin.py`

## 라이선스

MIT

## 기여

이슈와 PR을 환영합니다!
