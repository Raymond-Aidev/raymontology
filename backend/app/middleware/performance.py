"""
Performance Monitoring Middleware

Railway 환경 최적화: 응답 시간, 메모리, 느린 쿼리 추적
"""
import time
import logging
import psutil
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import log_api_request

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    성능 모니터링 미들웨어

    - API 응답 시간 측정
    - 메모리 사용량 추적
    - 느린 API 경고
    - 응답 시간 헤더 추가
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold: float = 1.0,  # 1초
        enable_memory_tracking: bool = True,
    ):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.enable_memory_tracking = enable_memory_tracking
        self.process = psutil.Process()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리"""
        # 시작 시간
        start_time = time.time()

        # 메모리 사용량 (시작)
        memory_before = None
        if self.enable_memory_tracking:
            try:
                memory_before = self.process.memory_info().rss / 1024 / 1024  # MB
            except:
                pass

        # 요청 처리
        response = await call_next(request)

        # 종료 시간
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # 메모리 사용량 (종료)
        memory_delta = None
        if self.enable_memory_tracking and memory_before is not None:
            try:
                memory_after = self.process.memory_info().rss / 1024 / 1024
                memory_delta = memory_after - memory_before
            except:
                pass

        # 응답 헤더 추가
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        if memory_delta is not None:
            response.headers["X-Memory-Delta"] = f"{memory_delta:.2f}MB"

        # 로깅
        log_api_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=getattr(request.state, "user_id", None),
        )

        # 느린 요청 경고
        if duration_ms > self.slow_request_threshold * 1000:
            logger.warning(
                f"Slow request detected",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "threshold_ms": self.slow_request_threshold * 1000,
                }
            )

        # 메모리 증가 경고 (50MB 이상)
        if memory_delta and memory_delta > 50:
            logger.warning(
                f"High memory usage detected",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "memory_delta_mb": round(memory_delta, 2),
                }
            )

        return response


class QueryPerformanceTracker:
    """
    데이터베이스 쿼리 성능 추적

    Usage:
        async with QueryPerformanceTracker("get_companies"):
            result = await session.execute(query)
    """

    def __init__(
        self,
        query_name: str,
        slow_query_threshold: float = 0.5,  # 500ms
    ):
        self.query_name = query_name
        self.slow_query_threshold = slow_query_threshold
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            duration_ms = duration * 1000

            # 느린 쿼리 로깅
            if duration_ms > self.slow_query_threshold * 1000:
                logger.warning(
                    f"Slow query detected: {self.query_name}",
                    extra={
                        "query_name": self.query_name,
                        "duration_ms": round(duration_ms, 2),
                        "threshold_ms": self.slow_query_threshold * 1000,
                    }
                )
            else:
                logger.debug(
                    f"Query executed: {self.query_name}",
                    extra={
                        "query_name": self.query_name,
                        "duration_ms": round(duration_ms, 2),
                    }
                )


# ============================================================================
# Performance Metrics Collector
# ============================================================================

class PerformanceMetrics:
    """성능 메트릭 수집"""

    def __init__(self):
        self.request_counts = {}
        self.response_times = {}
        self.error_counts = {}

    def record_request(
        self,
        endpoint: str,
        duration_ms: float,
        status_code: int,
    ):
        """요청 기록"""
        # 요청 카운트
        self.request_counts[endpoint] = self.request_counts.get(endpoint, 0) + 1

        # 응답 시간 (이동 평균)
        if endpoint not in self.response_times:
            self.response_times[endpoint] = []
        self.response_times[endpoint].append(duration_ms)

        # 최근 100개만 유지 (메모리 최적화)
        if len(self.response_times[endpoint]) > 100:
            self.response_times[endpoint] = self.response_times[endpoint][-100:]

        # 에러 카운트
        if status_code >= 400:
            self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1

    def get_stats(self) -> dict:
        """통계 조회"""
        stats = {}

        for endpoint in self.request_counts.keys():
            response_times = self.response_times.get(endpoint, [])
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                p95_time = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 1 else avg_time
            else:
                avg_time = 0
                p95_time = 0

            stats[endpoint] = {
                "request_count": self.request_counts.get(endpoint, 0),
                "avg_response_time_ms": round(avg_time, 2),
                "p95_response_time_ms": round(p95_time, 2),
                "error_count": self.error_counts.get(endpoint, 0),
                "error_rate": round(
                    self.error_counts.get(endpoint, 0) / max(self.request_counts.get(endpoint, 1), 1),
                    3
                ),
            }

        return stats

    def reset(self):
        """메트릭 초기화"""
        self.request_counts.clear()
        self.response_times.clear()
        self.error_counts.clear()


# 전역 메트릭 인스턴스
performance_metrics = PerformanceMetrics()


# ============================================================================
# Memory Profiling Utilities
# ============================================================================

def get_memory_usage() -> dict:
    """
    현재 메모리 사용량 조회

    Returns:
        {
            "rss_mb": 123.4,  # Resident Set Size
            "vms_mb": 456.7,  # Virtual Memory Size
            "percent": 12.3,  # 시스템 메모리 사용률
        }
    """
    try:
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2),
        }
    except Exception as e:
        logger.error(f"Failed to get memory usage: {e}")
        return {}


def check_memory_threshold(threshold_mb: int = 400) -> bool:
    """
    메모리 임계값 확인

    Args:
        threshold_mb: 임계값 (MB)

    Returns:
        bool: 임계값 초과 여부
    """
    memory = get_memory_usage()
    rss_mb = memory.get("rss_mb", 0)

    if rss_mb > threshold_mb:
        logger.warning(
            f"Memory usage exceeds threshold",
            extra={
                "rss_mb": rss_mb,
                "threshold_mb": threshold_mb,
            }
        )
        return True

    return False


# ============================================================================
# Response Size Optimization
# ============================================================================

class ResponseSizeTracker:
    """응답 크기 추적"""

    @staticmethod
    def estimate_size(data: any) -> int:
        """
        데이터 크기 추정 (바이트)

        Args:
            data: 응답 데이터

        Returns:
            int: 바이트 크기
        """
        import sys
        import json

        try:
            if isinstance(data, (dict, list)):
                # JSON 직렬화 후 크기 측정
                json_str = json.dumps(data)
                return len(json_str.encode('utf-8'))
            else:
                # 파이썬 객체 크기
                return sys.getsizeof(data)
        except:
            return 0

    @staticmethod
    def should_compress(size_bytes: int, threshold_bytes: int = 1000) -> bool:
        """
        압축 필요 여부 확인

        Args:
            size_bytes: 데이터 크기
            threshold_bytes: 압축 임계값 (기본 1KB)

        Returns:
            bool: 압축 필요 여부
        """
        return size_bytes > threshold_bytes
