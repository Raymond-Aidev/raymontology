"""
Redis 캐시 서비스
- Redis 연결 실패 시 자동 fallback (캐시 없이 동작)
- 프로덕션 안정성을 위한 graceful degradation
"""
import json
import logging
from typing import Any, Optional, Callable, TypeVar
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Redis 클라이언트 (lazy initialization)
_redis_client = None
_redis_available = None


def get_redis_client():
    """Redis 클라이언트 반환 (연결 실패 시 None)"""
    global _redis_client, _redis_available

    if _redis_available is False:
        return None

    if _redis_client is None:
        try:
            from app.config import settings
            if not settings.redis_url:
                logger.info("Redis URL not configured, cache disabled")
                _redis_available = False
                return None

            import redis
            logger.info(f"Connecting to Redis: {settings.redis_url[:30]}...")
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # 연결 테스트
            _redis_client.ping()
            _redis_available = True
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed, cache disabled: {e}")
            _redis_available = False
            _redis_client = None

    return _redis_client


class CacheService:
    """
    캐시 서비스 (Redis with fallback)

    Usage:
        cache = CacheService()

        # 직접 사용
        cache.set("key", {"data": "value"}, ttl=300)
        data = cache.get("key")

        # 데코레이터 사용
        @cache.cached(ttl=300)
        def get_company(company_id: str):
            return db.query(Company).filter(Company.id == company_id).first()
    """

    DEFAULT_TTL = 300  # 5분

    @property
    def client(self):
        return get_redis_client()

    @property
    def available(self) -> bool:
        return self.client is not None

    def _make_key(self, key: str, prefix: str = "raymontology") -> str:
        """캐시 키 생성"""
        return f"{prefix}:{key}"

    def get(self, key: str, default: Any = None) -> Any:
        """캐시에서 값 조회"""
        if not self.available:
            return default

        try:
            cache_key = self._make_key(key)
            value = self.client.get(cache_key)
            if value is None:
                return default
            return json.loads(value)
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return default

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """캐시에 값 저장"""
        if not self.available:
            return False

        try:
            cache_key = self._make_key(key)
            ttl = ttl or self.DEFAULT_TTL
            self.client.setex(cache_key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if not self.available:
            return False

        try:
            cache_key = self._make_key(key)
            self.client.delete(cache_key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """패턴에 매칭되는 모든 키 삭제"""
        if not self.available:
            return 0

        try:
            cache_pattern = self._make_key(pattern)
            keys = self.client.keys(cache_pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete_pattern failed for {pattern}: {e}")
            return 0

    def cached(
        self,
        ttl: int = None,
        key_prefix: str = None,
        key_builder: Callable = None,
    ):
        """
        캐시 데코레이터

        Args:
            ttl: 캐시 유효 시간 (초)
            key_prefix: 캐시 키 접두사
            key_builder: 커스텀 키 생성 함수

        Example:
            @cache.cached(ttl=600, key_prefix="company")
            def get_company(company_id: str):
                return db.query(Company).filter_by(id=company_id).first()
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                # 캐시 비활성화 시 원본 함수 실행
                if not self.available:
                    return func(*args, **kwargs)

                # 캐시 키 생성
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    prefix = key_prefix or func.__name__
                    key_parts = [prefix]
                    key_parts.extend(str(a) for a in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    raw_key = ":".join(key_parts)
                    # 긴 키는 해시
                    if len(raw_key) > 200:
                        cache_key = f"{prefix}:{hashlib.md5(raw_key.encode()).hexdigest()}"
                    else:
                        cache_key = raw_key

                # 캐시 조회
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value

                # 캐시 미스 - 원본 함수 실행
                logger.debug(f"Cache miss: {cache_key}")
                result = func(*args, **kwargs)

                # 결과 캐싱 (None이 아닌 경우만)
                if result is not None:
                    self.set(cache_key, result, ttl)

                return result

            # 캐시 무효화 헬퍼 메서드 추가
            wrapper.invalidate = lambda *args, **kwargs: self.delete(
                key_builder(*args, **kwargs) if key_builder
                else f"{key_prefix or func.__name__}:{':'.join(str(a) for a in args)}"
            )

            return wrapper
        return decorator


# 싱글톤 인스턴스
cache = CacheService()
