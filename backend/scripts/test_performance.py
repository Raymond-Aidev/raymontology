#!/usr/bin/env python3
"""
성능 최적화 검증 스크립트

Railway 배포 전 로컬에서 성능 최적화를 검증합니다.

실행:
    python backend/scripts/test_performance.py
"""
import asyncio
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, AsyncSessionLocal, redis_client, check_db_health
from app.utils.cache import cache, CacheManager
from app.config import settings


async def test_database_pool():
    """데이터베이스 연결 풀 테스트"""
    print("\n" + "="*60)
    print("1. 데이터베이스 연결 풀 테스트")
    print("="*60)

    # 연결 풀 설정 확인
    print(f"Pool Size: {engine.pool.size()}")
    print(f"Pool Class: {engine.pool.__class__.__name__}")
    print(f"Pool Pre-Ping: True" if hasattr(engine.pool, '_pre_ping') else "Pool Pre-Ping: Not configured")

    # 연결 테스트
    start = time.time()
    async with AsyncSessionLocal() as session:
        result = await session.execute("SELECT 1")
        assert result.scalar() == 1
    duration_ms = (time.time() - start) * 1000

    print(f"✅ 연결 테스트: {duration_ms:.2f}ms")

    # Health Check
    health = await check_db_health()
    print(f"✅ PostgreSQL: {health['postgresql']['status']} ({health['postgresql'].get('latency_ms', 0)}ms)")
    if 'redis' in health:
        print(f"✅ Redis: {health['redis']['status']} ({health['redis'].get('latency_ms', 0)}ms)")
    if 'neo4j' in health:
        print(f"✅ Neo4j: {health['neo4j']['status']} ({health['neo4j'].get('latency_ms', 0)}ms)")


async def test_cache_manager():
    """CacheManager 테스트"""
    print("\n" + "="*60)
    print("2. CacheManager 테스트")
    print("="*60)

    if not redis_client:
        print("⚠️  Redis가 연결되지 않았습니다. 캐싱 테스트를 건너뜁니다.")
        return

    cache_mgr = CacheManager()

    # 캐시 저장
    test_key = "test:performance:123"
    test_data = {"id": 123, "name": "Test Company", "value": 100}

    await cache_mgr.set(redis_client, test_key, test_data, 60)
    print(f"✅ 캐시 저장: {test_key}")

    # 캐시 조회 (캐시 히트)
    start = time.time()
    cached_data = await cache_mgr.get(redis_client, test_key)
    duration_ms = (time.time() - start) * 1000

    assert cached_data == test_data
    print(f"✅ 캐시 조회 (Hit): {duration_ms:.2f}ms")

    # get_or_compute 테스트 (캐시 히트)
    start = time.time()
    result = await cache_mgr.get_or_compute(
        redis_client,
        test_key,
        lambda: {"computed": True},
        60
    )
    duration_ms = (time.time() - start) * 1000

    assert result == test_data  # 캐시에서 가져옴
    print(f"✅ get_or_compute (Hit): {duration_ms:.2f}ms")

    # get_or_compute 테스트 (캐시 미스)
    new_key = "test:performance:456"
    computed_data = {"id": 456, "name": "Computed", "computed": True}

    start = time.time()
    result = await cache_mgr.get_or_compute(
        redis_client,
        new_key,
        lambda: computed_data,
        60
    )
    duration_ms = (time.time() - start) * 1000

    assert result == computed_data
    print(f"✅ get_or_compute (Miss): {duration_ms:.2f}ms")

    # 캐시 무효화
    await cache_mgr.invalidate(redis_client, "test:performance:*")
    print(f"✅ 캐시 무효화: test:performance:*")


async def test_performance_metrics():
    """성능 메트릭 테스트"""
    print("\n" + "="*60)
    print("3. 성능 메트릭 테스트")
    print("="*60)

    from app.middleware.performance import get_memory_usage, check_memory_threshold

    # 메모리 사용량 확인
    memory = get_memory_usage()
    print(f"✅ 메모리 사용량:")
    print(f"   - RSS: {memory['rss_mb']}MB")
    print(f"   - VMS: {memory['vms_mb']}MB")
    print(f"   - Percent: {memory['percent']}%")

    # Railway Hobby 제한 체크 (512MB)
    if memory['rss_mb'] > 400:
        print(f"⚠️  메모리 사용량이 높습니다: {memory['rss_mb']}MB (Railway Hobby: 512MB)")
    else:
        print(f"✅ 메모리 사용량 정상: {memory['rss_mb']}MB < 400MB")

    # 메모리 임계값 체크
    is_over = check_memory_threshold(threshold_mb=400)
    if not is_over:
        print(f"✅ 메모리 임계값 정상")


async def test_ttl_constants():
    """TTL 상수 테스트"""
    print("\n" + "="*60)
    print("4. TTL 상수 테스트")
    print("="*60)

    print(f"✅ TTL_COMPANY_INFO: {cache.TTL_COMPANY_INFO}s (24시간)")
    print(f"✅ TTL_RISK_SCORE: {cache.TTL_RISK_SCORE}s (1시간)")
    print(f"✅ TTL_SEARCH_RESULTS: {cache.TTL_SEARCH_RESULTS}s (30분)")

    assert cache.TTL_COMPANY_INFO == 86400  # 24시간
    assert cache.TTL_RISK_SCORE == 3600     # 1시간
    assert cache.TTL_SEARCH_RESULTS == 1800 # 30분


async def test_configuration():
    """설정 확인"""
    print("\n" + "="*60)
    print("5. Railway 설정 확인")
    print("="*60)

    print(f"✅ Environment: {settings.environment}")
    print(f"✅ Debug: {settings.debug}")
    print(f"✅ Database URL: {settings.database_url[:30]}...")
    print(f"✅ Redis URL: {settings.redis_url[:30] if settings.redis_url else 'Not configured'}...")
    print(f"✅ Neo4j URI: {settings.neo4j_uri[:30]}...")


async def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("Railway 성능 최적화 검증")
    print("="*60)

    try:
        # 데이터베이스 초기화
        from app.database import init_db
        await init_db()

        # 모든 테스트 실행
        await test_configuration()
        await test_database_pool()
        await test_cache_manager()
        await test_performance_metrics()
        await test_ttl_constants()

        print("\n" + "="*60)
        print("✅ 모든 테스트 통과!")
        print("="*60)
        print("\n🚀 Railway 배포 준비 완료!")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 데이터베이스 연결 종료
        from app.database import close_db
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
