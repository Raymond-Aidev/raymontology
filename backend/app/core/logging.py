"""
Structured Logging Configuration

Railway 환경에 최적화된 JSON 로깅
"""
import logging
import sys
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from app.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """커스텀 JSON 포맷터"""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        """로그 레코드에 커스텀 필드 추가"""
        super().add_fields(log_record, record, message_dict)

        # 환경 정보 추가
        log_record['environment'] = settings.environment
        log_record['service'] = 'raymontology-backend'

        # 레벨명 소문자로
        if log_record.get('level'):
            log_record['level'] = log_record['level'].lower()


def setup_logging() -> logging.Logger:
    """
    구조화된 JSON 로깅 설정

    Returns:
        Logger: 설정된 루트 로거
    """
    # 루트 로거 가져오기
    logger = logging.getLogger()

    # 기존 핸들러 제거
    logger.handlers.clear()

    # Railway는 stdout으로 로그 수집
    handler = logging.StreamHandler(sys.stdout)

    # JSON 포맷터 설정
    if settings.environment == "production":
        formatter = CustomJsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
            rename_fields={
                'asctime': 'timestamp',
                'levelname': 'level',
                'name': 'logger',
            },
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    else:
        # 개발 환경에서는 일반 텍스트
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # 로그 레벨 설정
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 써드파티 로거 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logger


# 모듈 로드시 로거 설정
logger = setup_logging()


# 편의 함수들
def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: str | None = None,
) -> None:
    """API 요청 로깅"""
    logger.info(
        "API request",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
        }
    )


def log_database_query(
    query_type: str,
    table: str,
    duration_ms: float,
    rows_affected: int = 0,
) -> None:
    """데이터베이스 쿼리 로깅"""
    logger.debug(
        "Database query",
        extra={
            "query_type": query_type,
            "table": table,
            "duration_ms": round(duration_ms, 2),
            "rows_affected": rows_affected,
        }
    )


def log_external_api_call(
    service: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    success: bool = True,
) -> None:
    """외부 API 호출 로깅"""
    level = logging.INFO if success else logging.ERROR
    logger.log(
        level,
        f"External API call: {service}",
        extra={
            "service": service,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "success": success,
        }
    )


def log_task_execution(
    task_name: str,
    status: str,
    duration_ms: float,
    error: str | None = None,
) -> None:
    """Celery 태스크 실행 로깅"""
    level = logging.INFO if status == "success" else logging.ERROR
    logger.log(
        level,
        f"Task execution: {task_name}",
        extra={
            "task_name": task_name,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "error": error,
        }
    )
