"""
Rate Limiting Middleware (Redis-based)
"""
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from redis.asyncio import Redis
import time
from typing import Optional

from app.database import get_redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis 기반 Rate Limiting 미들웨어

    슬라이딩 윈도우 알고리즘 사용
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

    async def dispatch(self, request: Request, call_next):
        """
        요청 처리 및 Rate Limiting

        Args:
            request: FastAPI Request
            call_next: 다음 미들웨어/라우트

        Returns:
            Response

        Raises:
            HTTPException: 429 (Too Many Requests)
        """
        # Redis 클라이언트
        redis = await get_redis()

        if redis is None:
            # Redis 미사용 시 Rate Limiting 건너뛰기
            return await call_next(request)

        # 클라이언트 식별 (IP 또는 User ID)
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)

        identifier = f"user:{user_id}" if user_id else f"ip:{client_ip}"

        # Rate Limiting 체크
        is_allowed, headers = await self._check_rate_limit(redis, identifier)

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers=headers,
            )

        # 요청 처리
        response = await call_next(request)

        # Rate Limit 헤더 추가
        for key, value in headers.items():
            response.headers[key] = value

        return response

    async def _check_rate_limit(
        self,
        redis: Redis,
        identifier: str
    ) -> tuple[bool, dict]:
        """
        Rate Limit 체크

        Args:
            redis: Redis 클라이언트
            identifier: 클라이언트 식별자

        Returns:
            (허용 여부, 헤더 딕셔너리)
        """
        now = int(time.time())

        # 분당 제한
        minute_key = f"rate_limit:minute:{identifier}:{now // 60}"
        hour_key = f"rate_limit:hour:{identifier}:{now // 3600}"

        # 현재 요청 수
        minute_count = await redis.incr(minute_key)
        hour_count = await redis.incr(hour_key)

        # TTL 설정 (첫 요청일 때만)
        if minute_count == 1:
            await redis.expire(minute_key, 60)
        if hour_count == 1:
            await redis.expire(hour_key, 3600)

        # 제한 확인
        minute_allowed = minute_count <= self.requests_per_minute
        hour_allowed = hour_count <= self.requests_per_hour

        # 헤더 생성
        headers = {
            "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
            "X-RateLimit-Remaining-Minute": str(max(0, self.requests_per_minute - minute_count)),
            "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
            "X-RateLimit-Remaining-Hour": str(max(0, self.requests_per_hour - hour_count)),
        }

        # Retry-After 헤더 (제한 초과 시)
        if not minute_allowed:
            headers["Retry-After"] = "60"
        elif not hour_allowed:
            headers["Retry-After"] = str(3600 - (now % 3600))

        return (minute_allowed and hour_allowed), headers


async def check_rate_limit_for_user(
    user_id: str,
    redis: Redis,
    limit: int = 10,
    window: int = 60
) -> bool:
    """
    특정 사용자의 Rate Limit 체크

    Args:
        user_id: 사용자 ID
        redis: Redis 클라이언트
        limit: 제한 횟수
        window: 시간 창 (초)

    Returns:
        허용 여부
    """
    now = int(time.time())
    key = f"rate_limit:user:{user_id}:{now // window}"

    count = await redis.incr(key)

    if count == 1:
        await redis.expire(key, window)

    return count <= limit
