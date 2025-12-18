"""
Sentry Error Tracking Integration

프로덕션 환경에서 에러 모니터링 및 성능 추적
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

from app.config import settings


def init_sentry() -> None:
    """
    Sentry SDK 초기화

    프로덕션 환경에서만 활성화
    """
    if not settings.sentry_dsn:
        logging.info("Sentry DSN not configured, skipping initialization")
        return

    if settings.environment != "production":
        logging.info(f"Sentry disabled in {settings.environment} environment")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,

        # 성능 모니터링
        traces_sample_rate=settings.sentry_traces_sample_rate,
        enable_tracing=True,

        # 통합
        integrations=[
            # FastAPI 요청 추적
            FastApiIntegration(
                transaction_style="endpoint",  # /api/companies/{id} 형태
                failed_request_status_codes=[403, *range(500, 599)],
            ),

            # SQLAlchemy 쿼리 추적
            SqlalchemyIntegration(),

            # Redis 명령 추적
            RedisIntegration(),

            # Celery 태스크 추적
            CeleryIntegration(
                monitor_beat_tasks=True,
                exclude_beat_tasks=None,
            ),

            # 로그 통합 (ERROR 이상만)
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],

        # 보안 설정
        send_default_pii=False,  # 개인정보 전송 안함
        attach_stacktrace=True,  # 스택 트레이스 첨부

        # Release 버전 추적
        release=f"raymontology@{settings.environment}",

        # 샘플링 설정
        profiles_sample_rate=0.1,  # 프로파일링 10%만

        # 무시할 에러
        ignore_errors=[
            # HTTP 에러
            "HTTPException",
            # 인증 에러 (의도된 동작)
            "AuthenticationError",
            "PermissionDenied",
            # 클라이언트 에러 (4xx)
            "ValidationError",
        ],

        # 필터링할 URL
        before_send=before_send_filter,
    )

    logging.info(
        "Sentry initialized",
        extra={
            "environment": settings.sentry_environment,
            "traces_sample_rate": settings.sentry_traces_sample_rate,
        }
    )


def before_send_filter(event, hint):
    """
    Sentry 전송 전 이벤트 필터링

    Args:
        event: Sentry 이벤트
        hint: 추가 정보

    Returns:
        event 또는 None (None이면 전송 안함)
    """
    # Health check 요청은 무시
    if event.get("request", {}).get("url", "").endswith("/health"):
        return None

    # /metrics 요청은 무시
    if event.get("request", {}).get("url", "").endswith("/metrics"):
        return None

    # 민감 정보 제거
    if "request" in event:
        # Authorization 헤더 제거
        headers = event["request"].get("headers", {})
        if "Authorization" in headers:
            headers["Authorization"] = "[Filtered]"

        # 쿠키 제거
        if "cookies" in event["request"]:
            event["request"]["cookies"] = "[Filtered]"

    return event


# Context 관리 함수들
def set_user_context(user_id: str, email: str | None = None) -> None:
    """사용자 컨텍스트 설정"""
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
    })


def set_company_context(company_id: str, company_name: str) -> None:
    """기업 컨텍스트 설정"""
    sentry_sdk.set_context("company", {
        "id": company_id,
        "name": company_name,
    })


def set_custom_context(key: str, data: dict) -> None:
    """커스텀 컨텍스트 설정"""
    sentry_sdk.set_context(key, data)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: dict | None = None,
) -> None:
    """
    Breadcrumb 추가 (이벤트 발생 경로 추적)

    Args:
        message: 메시지
        category: 카테고리 (예: "auth", "database", "api")
        level: 레벨 (debug, info, warning, error)
        data: 추가 데이터
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )


def capture_exception_with_context(
    exception: Exception,
    extra: dict | None = None,
) -> str:
    """
    예외를 컨텍스트와 함께 캡처

    Args:
        exception: 예외 객체
        extra: 추가 정보

    Returns:
        Sentry 이벤트 ID
    """
    if extra:
        sentry_sdk.set_context("extra", extra)

    event_id = sentry_sdk.capture_exception(exception)
    return event_id


def capture_message_with_context(
    message: str,
    level: str = "info",
    extra: dict | None = None,
) -> str:
    """
    메시지를 컨텍스트와 함께 캡처

    Args:
        message: 메시지
        level: 레벨 (debug, info, warning, error, fatal)
        extra: 추가 정보

    Returns:
        Sentry 이벤트 ID
    """
    if extra:
        sentry_sdk.set_context("extra", extra)

    event_id = sentry_sdk.capture_message(message, level=level)
    return event_id
