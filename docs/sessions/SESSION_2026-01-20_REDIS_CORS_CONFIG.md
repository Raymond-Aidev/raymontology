# 세션 기록: Redis 연결 및 CORS 설정 (2026-01-20)

## 세션 요약

Railway 프로덕션 환경에서 Redis 캐시 연결 문제 해결 및 CORS 보안 설정 완료.

---

## 해결된 문제들

### 1. Redis 연결 오류 (Error 22 - EINVAL)

**원인**: `socket_keepalive_options`에 숫자 키 사용 (Linux 전용 옵션이 macOS/Railway 환경에서 호환 안 됨)

**해결**: `database.py`에서 Redis 연결 파라미터 단순화
```python
# 제거된 옵션들:
# - socket_keepalive_options (Linux 전용)
# - max_connections
# - health_check_interval
# - retry_on_error

# 최종 연결 코드:
redis_client = await Redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)
```

### 2. Docker 빌드 캐시 문제

**원인**: Railway가 Docker 레이어 캐시 사용으로 새 코드 미반영

**해결**: `requirements.txt`에 캐시 버스트 주석 추가
```
# Cache bust: 2026-01-20
```

### 3. Python 로깅 버퍼링

**원인**: Railway 환경에서 Python 로깅 출력 지연

**해결**: `print(flush=True)` 사용 후 정상 작동 확인, 디버그 코드 제거

### 4. Neo4j 경고 메시지

**해결**: 사용자가 `NEO4J_URI`, `NEO4J_PASSWORD` 환경변수 비움

### 5. Toss 콜백 자격증명 경고

**해결**: 사용자가 `TOSS_CALLBACK_CREDENTIALS` 환경변수 설정 (정식 출시 완료)

### 6. CORS 보안 설정

**해결**: `CORS_ALLOW_ALL=false` 환경변수 설정

**허용 도메인** (config.py에 하드코딩):
- https://www.konnect-ai.net
- https://konnect-ai.net
- https://raymondsindex.konnect-ai.net

추가 도메인 필요시: `ALLOWED_ORIGINS_STR` 환경변수 사용

---

## 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/database.py` | Redis 연결 파라미터 단순화 |
| `backend/requirements.txt` | 캐시 버스트 주석 추가 |
| `backend/app/services/cache_service.py` | Redis 연결 파라미터 단순화 |

---

## Railway 환경변수 설정

| 변수 | 값 | 비고 |
|------|-----|------|
| `REDIS_URL` | `redis://default:xxx@crossover.proxy.rlwy.net:24985` | Public URL 사용 |
| `NEO4J_URI` | (비움) | 사용 안 함 |
| `NEO4J_PASSWORD` | (비움) | 사용 안 함 |
| `TOSS_CALLBACK_CREDENTIALS` | (설정됨) | 정식 출시용 |
| `CORS_ALLOW_ALL` | `false` | 보안 강화 |

---

## 학습 사항

1. **Redis 연결**: Railway/macOS 환경에서는 Linux 전용 소켓 옵션 사용 금지
2. **Docker 캐시**: 코드 변경 미반영 시 requirements.txt 수정으로 캐시 버스트
3. **Railway Private Network**: 같은 프로젝트 내 서비스도 DNS 해석 실패 가능 → Public URL 사용
4. **CORS 설정**: `config.py`에 환경별 기본 도메인 정의됨, 환경변수로 오버라이드 가능

---

## 현재 상태

- Redis: 연결됨 (캐시 활성화)
- PostgreSQL: 정상
- Neo4j: 비활성화 (환경변수 비움)
- CORS: 프로덕션 도메인만 허용
- 앱인토스: 정식 출시 완료
