# Raymontology Backend

FastAPI 기반 백엔드 API 서버

## 기술 스택

- FastAPI 0.104+
- SQLAlchemy 2.0 (ORM)
- Alembic (마이그레이션)
- PostgreSQL 15
- Redis 7
- Neo4j (그래프 DB)
- Pydantic v2 (검증)

## 로컬 개발

### 1. 가상 환경 설정
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정
```

### 4. 데이터베이스 마이그레이션
```bash
alembic upgrade head
```

### 5. 서버 실행
```bash
# 개발 모드 (자동 리로드)
uvicorn app.main:app --reload --port 8000

# 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API 문서: http://localhost:8000/docs

## 프로젝트 구조

```
backend/
├── app/
│   ├── main.py              # FastAPI 앱 엔트리포인트
│   ├── config.py            # 설정 관리
│   ├── database.py          # DB 연결 설정
│   ├── models/              # SQLAlchemy 모델
│   ├── schemas/             # Pydantic 스키마
│   ├── routes/              # API 엔드포인트
│   ├── services/            # 비즈니스 로직
│   ├── repositories/        # 데이터 접근 계층
│   ├── middleware/          # 미들웨어
│   ├── auth/                # 인증/인가
│   └── utils/               # 유틸리티 함수
├── tests/                   # 테스트 코드
├── scripts/                 # 유틸리티 스크립트
├── alembic/                 # DB 마이그레이션
├── requirements.txt         # Python 의존성
└── Procfile                 # Railway 실행 명령
```

## API 엔드포인트

### 인증
- POST `/api/auth/register` - 회원가입
- POST `/api/auth/login` - 로그인
- POST `/api/auth/refresh` - 토큰 갱신

### 엔티티
- GET `/api/entities` - 엔티티 목록
- POST `/api/entities` - 엔티티 생성
- GET `/api/entities/{id}` - 엔티티 조회
- GET `/api/entities/{id}/relationships` - 관계 조회

### 리스크
- GET `/api/risks` - 리스크 목록
- GET `/api/risks/{id}` - 리스크 상세
- POST `/api/risks/analyze` - 리스크 분석

### 공시
- GET `/api/disclosures` - 공시 목록
- GET `/api/disclosures/{id}` - 공시 상세

## 테스트

```bash
# 전체 테스트
pytest

# 커버리지 포함
pytest --cov=app tests/

# 특정 테스트
pytest tests/test_auth.py
```

## Railway 배포

### 환경 변수 설정
Railway 대시보드에서 다음 변수 설정:

```
DATABASE_URL=postgresql://...  # Railway가 자동 설정
REDIS_URL=redis://...          # Railway가 자동 설정
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
DART_API_KEY=...
SECRET_KEY=...                  # openssl rand -hex 32
```

### 배포 명령
```bash
git push origin main
```

Railway가 자동으로 빌드 및 배포합니다.

## 개발 가이드

### 새 엔드포인트 추가

1. `schemas/` - Pydantic 스키마 정의
2. `models/` - SQLAlchemy 모델 정의
3. `repositories/` - DB 쿼리 로직
4. `services/` - 비즈니스 로직
5. `routes/` - API 엔드포인트
6. `tests/` - 테스트 작성

### 코드 스타일
```bash
# 포맷팅
black app/
isort app/

# 린팅
flake8 app/
mypy app/
```

## 라이선스

MIT License
