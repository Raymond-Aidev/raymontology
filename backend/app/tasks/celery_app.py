"""
Celery Application

백그라운드 작업 처리
"""
from celery import Celery
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Celery 앱 생성
celery_app = Celery(
    "raymontology",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.crawler_tasks"]
)

# Celery 설정
celery_app.conf.update(
    # 작업 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,

    # 결과 저장
    result_expires=3600,  # 1시간 후 결과 삭제
    result_backend_transport_options={
        "master_name": "mymaster"
    } if settings.environment == "production" else {},

    # Worker 설정
    worker_prefetch_multiplier=1,  # 한 번에 하나의 작업만
    worker_max_tasks_per_child=100,  # 100개 작업 후 Worker 재시작
    worker_disable_rate_limits=False,

    # 재시도 설정
    task_acks_late=True,  # 작업 완료 후 ACK
    task_reject_on_worker_lost=True,  # Worker 손실 시 재시도

    # 브로커 설정
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,

    # 결과 저장 설정
    result_persistent=True,

    # 작업 라우팅
    task_routes={
        "app.tasks.crawler_tasks.*": {"queue": "crawler"},
    },

    # 비트 스케줄러 (주기적 작업)
    beat_schedule={
        # 매일 새벽 2시 전체 크롤링
        "crawl-daily": {
            "task": "app.tasks.crawler_tasks.crawl_recent_task",
            "schedule": 86400.0,  # 24시간
            "kwargs": {"hours": 24},
        },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    """디버그 작업"""
    logger.info(f"Request: {self.request!r}")
    return {"status": "ok"}
