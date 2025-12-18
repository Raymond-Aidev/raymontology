"""
Notification Utilities

Slack 및 기타 알림 채널 통합
"""
import httpx
import logging
import time
from typing import Literal
from app.config import settings

logger = logging.getLogger(__name__)

AlertLevel = Literal["info", "warning", "error", "critical"]


async def send_slack_alert(
    message: str,
    level: AlertLevel = "info",
    details: dict | None = None,
) -> bool:
    """
    Slack으로 알림 전송

    Args:
        message: 알림 메시지
        level: 알림 레벨 (info, warning, error, critical)
        details: 추가 세부 정보

    Returns:
        bool: 전송 성공 여부
    """
    if not settings.slack_webhook_url:
        logger.debug("Slack webhook not configured, skipping notification")
        return False

    # 레벨별 색상
    color_map = {
        "info": "#36a64f",      # Green
        "warning": "#ff9900",   # Orange
        "error": "#ff0000",     # Red
        "critical": "#8b0000",  # Dark Red
    }

    # 레벨별 이모지
    emoji_map = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "🔴",
        "critical": "🚨",
    }

    # Slack 메시지 구성
    payload = {
        "attachments": [{
            "color": color_map.get(level, "#808080"),
            "title": f"{emoji_map.get(level, '📢')} Raymontology Alert ({level.upper()})",
            "text": message,
            "fields": [
                {
                    "title": key,
                    "value": str(value),
                    "short": True
                }
                for key, value in (details or {}).items()
            ],
            "footer": "Raymontology Monitoring",
            "footer_icon": "https://railway.app/favicon.ico",
            "ts": int(time.time())
        }]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.slack_webhook_url,
                json=payload
            )
            response.raise_for_status()

        logger.info(
            "Slack alert sent",
            extra={
                "level": level,
                "message": message,
            }
        )
        return True

    except httpx.HTTPError as e:
        logger.error(
            f"Failed to send Slack alert: {e}",
            extra={
                "level": level,
                "message": message,
                "error": str(e),
            }
        )
        return False


async def send_high_risk_alert(
    company_name: str,
    company_id: str,
    risk_score: float,
    warnings: list[str],
) -> None:
    """
    높은 리스크 점수 감지시 알림

    Args:
        company_name: 기업명
        company_id: 기업 ID
        risk_score: 리스크 점수 (0-1)
        warnings: 경고 메시지 리스트
    """
    level: AlertLevel = "critical" if risk_score > 0.9 else "warning"

    message = f"High risk score detected for {company_name}"

    details = {
        "Company ID": company_id,
        "Risk Score": f"{risk_score:.2%}",
        "Warnings Count": len(warnings),
        "Top Warnings": ", ".join(warnings[:3]) if warnings else "None",
    }

    await send_slack_alert(message, level, details)


async def send_crawler_failure_alert(
    corp_code: str,
    error: str,
    retry_count: int,
) -> None:
    """
    크롤러 실패시 알림

    Args:
        corp_code: 기업 코드
        error: 에러 메시지
        retry_count: 재시도 횟수
    """
    message = f"DART crawler failed for company {corp_code}"

    details = {
        "Corp Code": corp_code,
        "Error": error,
        "Retry Count": retry_count,
    }

    await send_slack_alert(message, "error", details)


async def send_database_connection_alert(
    database: str,
    error: str,
) -> None:
    """
    데이터베이스 연결 실패시 알림

    Args:
        database: 데이터베이스 이름 (PostgreSQL, Redis, Neo4j)
        error: 에러 메시지
    """
    message = f"Database connection failed: {database}"

    details = {
        "Database": database,
        "Error": error,
    }

    await send_slack_alert(message, "critical", details)


async def send_api_error_rate_alert(
    endpoint: str,
    error_count: int,
    total_count: int,
    time_window: str,
) -> None:
    """
    API 에러율 임계값 초과시 알림

    Args:
        endpoint: API 엔드포인트
        error_count: 에러 횟수
        total_count: 총 요청 횟수
        time_window: 시간 윈도우 (예: "5 minutes")
    """
    error_rate = (error_count / total_count * 100) if total_count > 0 else 0

    message = f"High error rate detected for {endpoint}"

    details = {
        "Endpoint": endpoint,
        "Error Rate": f"{error_rate:.1f}%",
        "Errors": error_count,
        "Total Requests": total_count,
        "Time Window": time_window,
    }

    await send_slack_alert(message, "error", details)


async def send_deployment_notification(
    version: str,
    environment: str,
    status: Literal["started", "completed", "failed"],
    details: dict | None = None,
) -> None:
    """
    배포 알림

    Args:
        version: 배포 버전
        environment: 환경 (production, staging)
        status: 배포 상태
        details: 추가 정보
    """
    level_map = {
        "started": "info",
        "completed": "info",
        "failed": "error",
    }

    message = f"Deployment {status}: {version} to {environment}"

    await send_slack_alert(
        message,
        level_map.get(status, "info"),  # type: ignore
        details
    )


async def send_custom_alert(
    title: str,
    message: str,
    level: AlertLevel = "info",
    details: dict | None = None,
) -> None:
    """
    커스텀 알림

    Args:
        title: 알림 제목
        message: 메시지
        level: 알림 레벨
        details: 추가 정보
    """
    full_message = f"{title}\n{message}"
    await send_slack_alert(full_message, level, details)


# 이메일 알림 (미구현 - 필요시 구현)
async def send_email_notification(
    to: str,
    subject: str,
    body: str,
) -> bool:
    """
    이메일 알림 전송

    Args:
        to: 수신자 이메일
        subject: 제목
        body: 본문

    Returns:
        bool: 전송 성공 여부
    """
    # TODO: SMTP 설정 및 이메일 전송 구현
    logger.warning("Email notifications not implemented yet")
    return False
