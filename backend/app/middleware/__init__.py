"""
Middleware Module

Railway 최적화 미들웨어:
- StructuredLoggingMiddleware: 구조화된 로깅
- PerformanceLoggingMiddleware: 성능 로깅 (요구사항 패턴)
- PerformanceMonitoringMiddleware: 성능 모니터링 (상세 메트릭)
- RateLimitMiddleware: 요청 제한
- setup_compression: Gzip 압축
"""

from app.middleware.logging import (
    StructuredLoggingMiddleware,
    PerformanceLoggingMiddleware,
    setup_logging
)
from app.middleware.performance import PerformanceMonitoringMiddleware
from app.middleware.rate_limit import RateLimitMiddleware, check_rate_limit_for_user
from app.middleware.compression import setup_compression

__all__ = [
    "StructuredLoggingMiddleware",
    "PerformanceLoggingMiddleware",
    "PerformanceMonitoringMiddleware",
    "setup_logging",
    "RateLimitMiddleware",
    "check_rate_limit_for_user",
    "setup_compression",
]
