# 모니터링 설정 가이드

Raymontology 프로덕션 환경을 위한 모니터링 및 관찰성(Observability) 설정

---

## 📊 모니터링 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Railway Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Backend    │  │   Frontend   │  │   Worker     │      │
│  │   (FastAPI)  │  │   (React)    │  │   (Celery)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │               │
│         └─────────────────┴──────────────────┘               │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
        ┌───────▼──┐  ┌────▼────┐  ┌──▼──────┐
        │  Sentry  │  │ Railway │  │ Better  │
        │  (Errors)│  │ Metrics │  │ Uptime  │
        └──────────┘  └─────────┘  └─────────┘
```

---

## 🔧 1. Railway 내장 모니터링

Railway는 기본적으로 다음 메트릭을 제공합니다:

### 메트릭

1. **CPU Usage**
   - 서비스별 CPU 사용률
   - 시간대별 그래프
   - 임계값: 80% 이상시 스케일업 고려

2. **Memory Usage**
   - 서비스별 메모리 사용량
   - Railway 무료 플랜: 512MB
   - Railway Pro: 8GB
   - 임계값: 85% 이상시 최적화 필요

3. **Network I/O**
   - 인바운드/아웃바운드 트래픽
   - 대역폭 사용량

4. **Deployment Status**
   - 배포 성공/실패 이력
   - 배포 소요 시간

### 로그

Railway Dashboard에서 실시간 로그 확인:

```bash
# Railway CLI로 로그 스트리밍
railway logs

# 특정 서비스 로그
railway logs --service backend

# 에러 로그만 필터링
railway logs | grep ERROR
```

---

## 🐛 2. Sentry (에러 추적)

### 설치

1. **Sentry 계정 생성**
   - https://sentry.io/signup/
   - 무료 플랜: 5,000 errors/month

2. **프로젝트 생성**
   - Platform: Python (Backend)
   - Name: raymontology-backend

3. **DSN 복사**
   ```
   https://examplePublicKey@o0.ingest.sentry.io/0
   ```

### Backend 설정

`backend/requirements.txt`:
```
sentry-sdk[fastapi]==1.40.0
```

`backend/app/core/config.py`:
```python
class Settings(BaseSettings):
    # ... 기존 설정 ...

    # Sentry
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "production"
    sentry_traces_sample_rate: float = 0.1
```

`backend/app/main.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from app.core.config import settings

# Sentry 초기화
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        # 성능 모니터링
        enable_tracing=True,
        # PII 데이터 제거
        send_default_pii=False,
        # 요청 정보 첨부
        attach_stacktrace=True,
        # Release 트래킹
        release=f"raymontology@{settings.api_version}",
    )
```

### Railway 환경 변수

```bash
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### 사용 예시

```python
from sentry_sdk import capture_exception, capture_message

try:
    # 위험한 작업
    result = await risky_operation()
except Exception as e:
    # 에러를 Sentry로 전송
    capture_exception(e)
    raise

# 커스텀 메시지 전송
capture_message("High risk score detected", level="warning")
```

### Sentry 대시보드

1. **Issues**
   - 에러 발생 횟수
   - 영향받은 사용자 수
   - 스택 트레이스

2. **Performance**
   - API 엔드포인트별 응답 시간
   - 느린 쿼리 탐지
   - N+1 쿼리 감지

3. **Releases**
   - 배포 버전별 에러 추적
   - 새 배포 후 에러 증가 알림

---

## ⏱️ 3. Better Uptime (가동 시간 모니터링)

### 설정

1. **계정 생성**
   - https://betteruptime.com/
   - 무료 플랜: 10 monitors

2. **HTTP Monitor 추가**

   **Backend Health Check**:
   - URL: `https://raymontology-backend.up.railway.app/health`
   - Method: GET
   - Interval: 1 minute
   - Timeout: 30 seconds
   - Expected Status: 200
   - Expected Content: `"status":"healthy"`

   **Frontend Monitor**:
   - URL: `https://raymontology-frontend.up.railway.app/`
   - Method: GET
   - Interval: 3 minutes
   - Timeout: 30 seconds
   - Expected Status: 200

3. **알림 설정**
   - Email: 즉시 알림
   - Slack: (선택사항) 웹훅 추가
   - SMS: (유료)

4. **Status Page 생성** (선택사항)
   - Public status page
   - Custom domain: `status.yourdomain.com`
   - 사용자에게 장애 상황 투명하게 공개

### 알림 규칙

```yaml
Escalation Policy:
  1. First Alert (0분): Email
  2. Second Alert (5분): Email + Slack
  3. Third Alert (15분): Email + Slack + SMS

Auto-resolve:
  - 3번 연속 성공시 자동 해결
```

---

## 📈 4. Custom Application Metrics

### Prometheus + Grafana (선택사항)

Railway에서 직접 호스팅하기 어려우므로, 외부 서비스 사용 권장:
- **Grafana Cloud**: 무료 플랜 제공
- **Datadog**: 14일 무료 체험

### FastAPI Metrics 수집

`backend/requirements.txt`:
```
prometheus-fastapi-instrumentator==6.1.0
```

`backend/app/main.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(...)

# Prometheus 메트릭 수집
if settings.environment == "production":
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

### 수집 메트릭

- **HTTP Requests**: 총 요청 수, 응답 시간
- **Database Connections**: 연결 풀 사용량
- **Celery Tasks**: 작업 성공/실패율, 대기 시간
- **Custom Business Metrics**:
  ```python
  from prometheus_client import Counter, Histogram

  risk_analysis_counter = Counter(
      'risk_analysis_total',
      'Total risk analyses performed'
  )

  risk_score_histogram = Histogram(
      'risk_score_distribution',
      'Distribution of risk scores'
  )

  # 사용
  risk_analysis_counter.inc()
  risk_score_histogram.observe(0.75)
  ```

---

## 📝 5. Structured Logging

### 설정

`backend/app/core/logging.py`:
```python
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """구조화된 JSON 로깅 설정"""
    logger = logging.getLogger()

    # Railway는 stdout으로 로그 수집
    handler = logging.StreamHandler(sys.stdout)

    # JSON 포맷터
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={
            'asctime': 'timestamp',
            'levelname': 'level',
            'name': 'logger',
        }
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
```

`backend/app/main.py`:
```python
from app.core.logging import setup_logging

# 앱 시작시 로깅 설정
logger = setup_logging()

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting", extra={
        "environment": settings.environment,
        "version": settings.api_version,
    })
```

### 사용 예시

```python
import logging

logger = logging.getLogger(__name__)

# 구조화된 로그
logger.info("Company search performed", extra={
    "query": "삼성",
    "results_count": 15,
    "user_id": user.id,
    "duration_ms": 234,
})

logger.error("DART API error", extra={
    "corp_code": "00126380",
    "status_code": 500,
    "retry_count": 3,
}, exc_info=True)
```

---

## 🔔 6. 알림 채널 설정

### Slack Integration

1. **Slack Webhook 생성**
   ```
   https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```

2. **Backend에서 Slack 알림**

   `backend/app/utils/notifications.py`:
   ```python
   import httpx
   from app.core.config import settings

   async def send_slack_alert(message: str, level: str = "info"):
       """Slack으로 알림 전송"""
       if not settings.slack_webhook_url:
           return

       color = {
           "info": "#36a64f",
           "warning": "#ff9900",
           "error": "#ff0000",
       }.get(level, "#808080")

       payload = {
           "attachments": [{
               "color": color,
               "title": f"Raymontology Alert ({level.upper()})",
               "text": message,
               "ts": int(time.time())
           }]
       }

       async with httpx.AsyncClient() as client:
           await client.post(settings.slack_webhook_url, json=payload)
   ```

3. **사용 예시**
   ```python
   # 높은 리스크 점수 감지시
   if risk_score > 0.8:
       await send_slack_alert(
           f"High risk score detected: {company.name} ({risk_score:.2f})",
           level="warning"
       )
   ```

---

## 🎯 7. 모니터링 대시보드 구성

### 권장 메트릭

#### 시스템 건강도
- ✅ HTTP 5xx 에러율 < 0.1%
- ✅ 평균 응답 시간 < 200ms
- ✅ 가동 시간 > 99.9%
- ✅ CPU 사용률 < 70%
- ✅ 메모리 사용률 < 85%

#### 비즈니스 메트릭
- 📊 일일 활성 사용자 (DAU)
- 📊 기업 검색 횟수
- 📊 리스크 분석 실행 횟수
- 📊 DART 크롤링 성공률
- 📊 평균 리스크 점수

#### 데이터베이스
- 🗄️ PostgreSQL 연결 풀 사용률
- 🗄️ 느린 쿼리 (> 1s)
- 🗄️ 데이터베이스 크기
- 🗄️ Redis 메모리 사용량

---

## 🚨 8. Alert Rules

### Critical Alerts (즉시 대응)

```yaml
Rules:
  - name: Service Down
    condition: HTTP health check fails 3 times
    action: Email + Slack + SMS
    threshold: 3 minutes

  - name: High Error Rate
    condition: 5xx errors > 1% in 5 minutes
    action: Email + Slack
    threshold: 5 minutes

  - name: Database Connection Failed
    condition: Cannot connect to PostgreSQL
    action: Email + Slack
    threshold: 1 minute
```

### Warning Alerts (모니터링)

```yaml
Rules:
  - name: High CPU Usage
    condition: CPU > 80% for 10 minutes
    action: Slack
    threshold: 10 minutes

  - name: High Memory Usage
    condition: Memory > 85% for 5 minutes
    action: Slack
    threshold: 5 minutes

  - name: Slow API Response
    condition: P95 latency > 1s
    action: Slack
    threshold: 5 minutes
```

---

## 📋 9. 체크리스트

### 초기 설정

- [ ] Sentry 프로젝트 생성 및 DSN 설정
- [ ] Better Uptime 모니터 추가
- [ ] Slack 웹훅 설정
- [ ] Railway 알림 설정 (Email)
- [ ] 구조화된 로깅 활성화

### 주간 점검

- [ ] Sentry 이슈 리뷰
- [ ] Better Uptime 가동 시간 확인
- [ ] Railway 리소스 사용량 확인
- [ ] 느린 API 엔드포인트 최적화
- [ ] 에러 로그 분석

### 월간 점검

- [ ] 알림 규칙 재검토
- [ ] 성능 트렌드 분석
- [ ] 데이터베이스 인덱스 최적화
- [ ] 비용 분석 (Railway, Sentry 플랜)
- [ ] 보안 업데이트 확인

---

## 🛠️ 10. 트러블슈팅

### 로그 수집 안됨

**원인**: Railway 로그가 표시되지 않음

**해결**:
1. stdout으로 로그 출력 확인
2. Railway Dashboard → Logs → 필터 확인
3. `print()` 대신 `logging` 사용

### Sentry 이벤트 전송 안됨

**원인**: DSN 설정 오류

**해결**:
1. `SENTRY_DSN` 환경 변수 확인
2. Sentry 프로젝트 상태 확인
3. 네트워크 연결 확인

### 메트릭 수집 안됨

**원인**: Prometheus instrumentator 미설정

**해결**:
1. `prometheus-fastapi-instrumentator` 설치 확인
2. `/metrics` 엔드포인트 접근 가능 확인
3. Railway 방화벽 설정 확인

---

## 📚 추가 리소스

- [Sentry FastAPI Integration](https://docs.sentry.io/platforms/python/guides/fastapi/)
- [Better Uptime Docs](https://docs.betteruptime.com/)
- [Railway Observability](https://docs.railway.app/reference/observability)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)

---

**모니터링은 프로덕션 운영의 핵심입니다. 적극적으로 활용하세요! 📊**
