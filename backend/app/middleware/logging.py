"""
Structured Logging Middleware
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
import uuid
import json

logger = logging.getLogger("raymontology")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    구조화된 로깅 미들웨어

    모든 HTTP 요청/응답을 JSON 형식으로 로깅
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """
        요청 처리 및 로깅

        Args:
            request: FastAPI Request
            call_next: 다음 미들웨어/라우트

        Returns:
            Response
        """
        # Request ID 생성
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 시작 시간
        start_time = time.time()

        # 요청 정보
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        # 요청 로깅
        logger.info(f"Request started: {json.dumps(log_data)}")

        # 예외 처리
        try:
            response = await call_next(request)

            # 처리 시간
            process_time = time.time() - start_time

            # 응답 정보
            log_data.update({
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
            })

            # 응답 로깅
            if response.status_code >= 400:
                logger.warning(f"Request failed: {json.dumps(log_data)}")
            else:
                logger.info(f"Request completed: {json.dumps(log_data)}")

            # Response Header에 Request ID 추가
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # 에러 로깅
            process_time = time.time() - start_time

            log_data.update({
                "status_code": 500,
                "error": str(e),
                "error_type": type(e).__name__,
                "process_time_ms": round(process_time * 1000, 2),
            })

            logger.error(f"Request error: {json.dumps(log_data)}", exc_info=True)

            raise


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    API 응답 시간 로깅 (요구사항 패턴)

    모든 API 요청의 응답 시간을 측정하고 로깅
    느린 요청 (> 1초)은 경고로 표시
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # 느린 요청 경고 (> 1초)
        if duration > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {duration:.2f}s"
            )
        else:
            logger.info(
                f"{request.method} {request.url.path} "
                f"- {duration:.3f}s"
            )

        # Response 헤더에 시간 추가
        response.headers["X-Process-Time"] = str(duration)

        return response


def setup_logging():
    """
    로깅 설정

    JSON 형식의 구조화된 로그 출력
    """
    # 로거 설정
    logger = logging.getLogger("raymontology")
    logger.setLevel(logging.INFO)

    # 핸들러 설정
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    # 포맷터 설정 (간단한 형식)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # 핸들러 추가
    if not logger.handlers:
        logger.addHandler(handler)

    return logger
