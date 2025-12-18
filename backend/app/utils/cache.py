"""
Redis Caching Utilities

Railway 환경 최적화된 캐싱 전략
"""
import json
import hashlib
import logging
from typing import Any, Optional, Callable
from functools import wraps
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# ============================================================================
# Cache Manager Class (요구사항 패턴)
# ============================================================================

class CacheManager:
    """
    캐시 관리자 (요구사항 패턴)

    Usage:
        cache = CacheManager()
        result = await cache.get_or_compute(
            "company:123",
            lambda: get_company_from_db(123),
            cache.TTL_COMPANY_INFO
        )
    """

    def __init__(self):
        """초기화 - Redis는 dependency injection으로 전달받음"""
        self.redis = None  # 런타임에 주입

    # TTL 상수
    TTL_COMPANY_INFO = 86400      # 24시간
    TTL_RISK_SCORE = 3600         # 1시간
    TTL_SEARCH_RESULTS = 1800     # 30분

    async def get(self, redis: Redis, key: str) -> Optional[Any]:
        """캐시 조회"""
        if not redis:
            return None

        try:
            value = await redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        redis: Redis,
        key: str,
        value: Any,
        ttl: int
    ):
        """캐시 저장"""
        if not redis:
            return

        try:
            await redis.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")

    async def get_or_compute(
        self,
        redis: Redis,
        key: str,
        compute_fn: Callable,
        ttl: int
    ) -> Any:
        """
        캐시 미스 시 계산

        Usage:
            result = await cache.get_or_compute(
                redis,
                "company:123",
                lambda: get_company_from_db(123),
                cache.TTL_COMPANY_INFO
            )
        """
        # 1. 캐시 확인
        cached = await self.get(redis, key)
        if cached is not None:
            logger.debug(f"Cache hit: {key}")
            return cached

        # 2. 계산
        logger.debug(f"Cache miss: {key}, computing...")
        result = await compute_fn() if callable(compute_fn) else compute_fn

        # 3. 캐시 저장
        if result is not None:
            await self.set(redis, key, result, ttl)

        return result

    async def invalidate(self, redis: Redis, pattern: str):
        """캐시 무효화"""
        if not redis:
            return

        try:
            keys = []
            async for key in redis.scan_iter(match=pattern, count=100):
                keys.append(key)

            if keys:
                await redis.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
        except Exception as e:
            logger.error(f"Cache invalidation error for pattern {pattern}: {e}")


# 싱글톤 인스턴스
cache = CacheManager()


# ============================================================================
# Cache TTL Constants (Railway 최적화)
# ============================================================================

class CacheTTL:
    """캐시 TTL 상수"""
    # 기업 정보
    COMPANY_INFO = 24 * 60 * 60  # 24시간
    COMPANY_SEARCH = 30 * 60  # 30분

    # 리스크 분석
    RISK_SCORE = 60 * 60  # 1시간
    RISK_COMPONENTS = 60 * 60  # 1시간

    # 공시 정보
    DISCLOSURE_LIST = 15 * 60  # 15분
    DISCLOSURE_DETAIL = 60 * 60  # 1시간

    # 인증
    USER_SESSION = 30 * 60  # 30분
    RATE_LIMIT = 60  # 1분

    # 통계
    STATS_DAILY = 24 * 60 * 60  # 24시간
    STATS_HOURLY = 60 * 60  # 1시간


# ============================================================================
# Cache Key Generators
# ============================================================================

def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    캐시 키 생성

    Args:
        prefix: 키 접두사 (예: "company", "risk")
        *args: 위치 인자
        **kwargs: 키워드 인자

    Returns:
        str: 캐시 키 (예: "company:12345", "search:query=samsung&market=KOSPI")
    """
    parts = [prefix]

    # 위치 인자 추가
    for arg in args:
        if arg is not None:
            parts.append(str(arg))

    # 키워드 인자 추가 (정렬하여 일관성 보장)
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        kwargs_str = "&".join(f"{k}={v}" for k, v in sorted_kwargs if v is not None)
        if kwargs_str:
            parts.append(kwargs_str)

    return ":".join(parts)


def make_hash_key(prefix: str, data: dict) -> str:
    """
    해시 기반 캐시 키 생성 (긴 쿼리 파라미터용)

    Args:
        prefix: 키 접두사
        data: 딕셔너리 데이터

    Returns:
        str: 해시 키 (예: "search:hash:a1b2c3d4")
    """
    # JSON 직렬화 후 해시
    json_str = json.dumps(data, sort_keys=True)
    hash_value = hashlib.md5(json_str.encode()).hexdigest()[:8]
    return f"{prefix}:hash:{hash_value}"


# ============================================================================
# Cache Operations
# ============================================================================

async def get_cached(
    redis: Redis,
    key: str,
    deserializer: Callable = json.loads,
) -> Optional[Any]:
    """
    캐시에서 데이터 가져오기

    Args:
        redis: Redis 클라이언트
        key: 캐시 키
        deserializer: 역직렬화 함수

    Returns:
        캐시된 데이터 또는 None
    """
    if not redis:
        return None

    try:
        data = await redis.get(key)
        if data:
            logger.debug(f"Cache hit: {key}")
            return deserializer(data) if deserializer else data
        else:
            logger.debug(f"Cache miss: {key}")
            return None
    except Exception as e:
        logger.error(f"Cache get error for key {key}: {e}")
        return None


async def set_cached(
    redis: Redis,
    key: str,
    value: Any,
    ttl: int,
    serializer: Callable = json.dumps,
) -> bool:
    """
    캐시에 데이터 저장

    Args:
        redis: Redis 클라이언트
        key: 캐시 키
        value: 저장할 데이터
        ttl: TTL (초)
        serializer: 직렬화 함수

    Returns:
        bool: 성공 여부
    """
    if not redis:
        return False

    try:
        serialized = serializer(value) if serializer else value
        await redis.setex(key, ttl, serialized)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.error(f"Cache set error for key {key}: {e}")
        return False


async def delete_cached(redis: Redis, *keys: str) -> int:
    """
    캐시 삭제

    Args:
        redis: Redis 클라이언트
        *keys: 삭제할 키들

    Returns:
        int: 삭제된 키 개수
    """
    if not redis or not keys:
        return 0

    try:
        deleted = await redis.delete(*keys)
        logger.debug(f"Cache deleted: {deleted} keys")
        return deleted
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        return 0


async def delete_pattern(redis: Redis, pattern: str) -> int:
    """
    패턴에 맞는 캐시 삭제

    Args:
        redis: Redis 클라이언트
        pattern: 패턴 (예: "company:*")

    Returns:
        int: 삭제된 키 개수
    """
    if not redis:
        return 0

    try:
        keys = []
        async for key in redis.scan_iter(match=pattern, count=100):
            keys.append(key)

        if keys:
            deleted = await redis.delete(*keys)
            logger.info(f"Cache pattern deleted: {pattern} ({deleted} keys)")
            return deleted
        return 0
    except Exception as e:
        logger.error(f"Cache pattern delete error for {pattern}: {e}")
        return 0


# ============================================================================
# Cache Decorators
# ============================================================================

def cached(
    ttl: int,
    key_prefix: str,
    key_builder: Optional[Callable] = None,
):
    """
    함수 결과 캐싱 데코레이터

    Args:
        ttl: TTL (초)
        key_prefix: 캐시 키 접두사
        key_builder: 키 생성 함수 (선택사항)

    Usage:
        @cached(ttl=CacheTTL.COMPANY_INFO, key_prefix="company")
        async def get_company(company_id: str, redis: Redis):
            # Redis는 함수 인자로 전달받음
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Redis 클라이언트 찾기
            redis = kwargs.get('redis')
            if not redis:
                # 위치 인자에서 찾기
                for arg in args:
                    if isinstance(arg, Redis):
                        redis = arg
                        break

            # Redis 없으면 캐시 스킵
            if not redis:
                return await func(*args, **kwargs)

            # 캐시 키 생성
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # 기본 키 생성 (첫 번째 인자 사용)
                first_arg = args[0] if args else None
                cache_key = make_cache_key(key_prefix, first_arg)

            # 캐시 조회
            cached_data = await get_cached(redis, cache_key)
            if cached_data is not None:
                return cached_data

            # 함수 실행
            result = await func(*args, **kwargs)

            # 캐시 저장
            if result is not None:
                await set_cached(redis, cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# ============================================================================
# Specialized Cache Functions
# ============================================================================

async def cache_company_info(
    redis: Redis,
    company_id: str,
    data: dict,
) -> bool:
    """기업 기본정보 캐싱"""
    key = make_cache_key("company", company_id)
    return await set_cached(redis, key, data, CacheTTL.COMPANY_INFO)


async def get_cached_company_info(
    redis: Redis,
    company_id: str,
) -> Optional[dict]:
    """캐시된 기업 정보 조회"""
    key = make_cache_key("company", company_id)
    return await get_cached(redis, key)


async def cache_risk_score(
    redis: Redis,
    company_id: str,
    risk_data: dict,
) -> bool:
    """리스크 점수 캐싱"""
    key = make_cache_key("risk", company_id)
    return await set_cached(redis, key, risk_data, CacheTTL.RISK_SCORE)


async def get_cached_risk_score(
    redis: Redis,
    company_id: str,
) -> Optional[dict]:
    """캐시된 리스크 점수 조회"""
    key = make_cache_key("risk", company_id)
    return await get_cached(redis, key)


async def cache_search_results(
    redis: Redis,
    search_params: dict,
    results: dict,
) -> bool:
    """검색 결과 캐싱"""
    key = make_hash_key("search", search_params)
    return await set_cached(redis, key, results, CacheTTL.COMPANY_SEARCH)


async def get_cached_search_results(
    redis: Redis,
    search_params: dict,
) -> Optional[dict]:
    """캐시된 검색 결과 조회"""
    key = make_hash_key("search", search_params)
    return await get_cached(redis, key)


async def invalidate_company_cache(
    redis: Redis,
    company_id: str,
) -> int:
    """
    기업 관련 모든 캐시 무효화

    Returns:
        int: 삭제된 캐시 개수
    """
    patterns = [
        f"company:{company_id}",
        f"risk:{company_id}",
        f"disclosure:{company_id}:*",
    ]

    total_deleted = 0
    for pattern in patterns:
        deleted = await delete_pattern(redis, pattern)
        total_deleted += deleted

    logger.info(f"Invalidated {total_deleted} cache entries for company {company_id}")
    return total_deleted


# ============================================================================
# Cache Statistics
# ============================================================================

async def get_cache_stats(redis: Redis) -> dict:
    """
    캐시 통계 조회

    Returns:
        dict: {
            "total_keys": 1234,
            "memory_used_mb": 12.5,
            "hit_rate": 0.85,
        }
    """
    if not redis:
        return {}

    try:
        info = await redis.info("stats")
        memory_info = await redis.info("memory")

        return {
            "total_keys": await redis.dbsize(),
            "memory_used_mb": round(memory_info.get("used_memory", 0) / 1024 / 1024, 2),
            "hit_rate": round(
                info.get("keyspace_hits", 0) /
                max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1),
                3
            ),
            "connected_clients": info.get("connected_clients", 0),
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {}


# ============================================================================
# Cache Warming (선택사항)
# ============================================================================

async def warm_cache(redis: Redis, popular_company_ids: list[str]):
    """
    인기 기업 캐시 워밍 (앱 시작시 실행)

    Args:
        redis: Redis 클라이언트
        popular_company_ids: 인기 기업 ID 리스트
    """
    logger.info(f"Warming cache for {len(popular_company_ids)} companies...")

    # TODO: 실제 데이터 로드 로직 구현
    # 여기서는 플레이스홀더만 제공

    logger.info("Cache warming completed")
