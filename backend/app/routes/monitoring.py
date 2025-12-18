"""
Monitoring API Routes

성능 모니터링 및 시스템 상태 조회
"""
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis, check_db_health
from app.middleware.performance import performance_metrics, get_memory_usage
from app.utils.cache import get_cache_stats

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


# ============================================================================
# Health & Status
# ============================================================================

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    종합 헬스 체크

    - 데이터베이스 연결 상태
    - Redis 연결 상태
    - Neo4j 연결 상태
    - 응답 시간
    """
    db_health = await check_db_health()

    return {
        "status": "healthy",
        "databases": db_health,
    }


@router.get("/status")
async def system_status():
    """
    시스템 상태 조회

    - 메모리 사용량
    - CPU 사용률
    - 프로세스 정보
    """
    import psutil
    import os

    try:
        process = psutil.Process()

        # CPU 사용률 (1초 간격)
        cpu_percent = process.cpu_percent(interval=1)

        # 메모리 사용량
        memory = get_memory_usage()

        # 시스템 정보
        system_memory = psutil.virtual_memory()

        return {
            "process": {
                "pid": os.getpid(),
                "cpu_percent": round(cpu_percent, 2),
                "memory_rss_mb": memory.get("rss_mb"),
                "memory_percent": memory.get("percent"),
                "num_threads": process.num_threads(),
            },
            "system": {
                "total_memory_mb": round(system_memory.total / 1024 / 1024, 2),
                "available_memory_mb": round(system_memory.available / 1024 / 1024, 2),
                "memory_percent": round(system_memory.percent, 2),
            },
        }
    except Exception as e:
        return {
            "error": str(e)
        }


# ============================================================================
# Performance Metrics
# ============================================================================

@router.get("/metrics/performance")
async def get_performance_metrics():
    """
    성능 메트릭 조회

    - 엔드포인트별 요청 수
    - 평균 응답 시간
    - P95 응답 시간
    - 에러율
    """
    stats = performance_metrics.get_stats()

    return {
        "endpoints": stats,
        "summary": {
            "total_requests": sum(s["request_count"] for s in stats.values()),
            "total_errors": sum(s["error_count"] for s in stats.values()),
            "avg_response_time_ms": round(
                sum(s["avg_response_time_ms"] * s["request_count"] for s in stats.values()) /
                max(sum(s["request_count"] for s in stats.values()), 1),
                2
            ),
        }
    }


@router.post("/metrics/reset")
async def reset_performance_metrics():
    """성능 메트릭 초기화"""
    performance_metrics.reset()
    return {"message": "Performance metrics reset"}


# ============================================================================
# Cache Statistics
# ============================================================================

@router.get("/metrics/cache")
async def get_cache_metrics(redis: Redis = Depends(get_redis)):
    """
    캐시 통계 조회

    - 전체 키 개수
    - 메모리 사용량
    - 히트율
    - 연결된 클라이언트 수
    """
    if not redis:
        return {"error": "Redis not available"}

    stats = await get_cache_stats(redis)
    return stats


# ============================================================================
# Database Metrics
# ============================================================================

@router.get("/metrics/database")
async def get_database_metrics(db: AsyncSession = Depends(get_db)):
    """
    데이터베이스 메트릭 조회

    - 연결 풀 상태
    - 활성 연결 수
    """
    from app.database import engine

    pool = engine.pool

    return {
        "pool": {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_overflow": pool._max_overflow,
            "total_connections": pool.size() + pool.overflow(),
        },
    }


# ============================================================================
# Slow Queries
# ============================================================================

# 느린 쿼리 로그 (메모리 저장 - 최근 100개)
slow_queries_log = []
MAX_SLOW_QUERIES = 100


def log_slow_query(query_name: str, duration_ms: float, details: dict = None):
    """느린 쿼리 기록"""
    import time

    entry = {
        "timestamp": time.time(),
        "query_name": query_name,
        "duration_ms": duration_ms,
        "details": details or {},
    }

    slow_queries_log.append(entry)

    # 최근 100개만 유지
    if len(slow_queries_log) > MAX_SLOW_QUERIES:
        slow_queries_log.pop(0)


@router.get("/metrics/slow-queries")
async def get_slow_queries():
    """
    느린 쿼리 조회

    Returns:
        최근 느린 쿼리 목록
    """
    return {
        "total": len(slow_queries_log),
        "queries": slow_queries_log[-20:],  # 최근 20개
    }


# ============================================================================
# Memory Profiling
# ============================================================================

@router.get("/metrics/memory")
async def get_memory_metrics():
    """
    메모리 상세 정보

    - RSS (Resident Set Size)
    - VMS (Virtual Memory Size)
    - 메모리 사용률
    """
    import psutil
    import gc

    # 가비지 컬렉션 통계
    gc_stats = {
        "collections": gc.get_count(),
        "threshold": gc.get_threshold(),
    }

    # 메모리 사용량
    memory = get_memory_usage()

    # 시스템 메모리
    system_memory = psutil.virtual_memory()

    return {
        "process": memory,
        "system": {
            "total_mb": round(system_memory.total / 1024 / 1024, 2),
            "available_mb": round(system_memory.available / 1024 / 1024, 2),
            "used_mb": round(system_memory.used / 1024 / 1024, 2),
            "percent": round(system_memory.percent, 2),
        },
        "gc": gc_stats,
    }


# ============================================================================
# API Endpoints Analysis
# ============================================================================

@router.get("/metrics/endpoints")
async def get_endpoint_metrics():
    """
    엔드포인트별 상세 통계

    - 요청 수
    - 평균/최소/최대 응답 시간
    - 에러율
    - 처리량 (requests/min)
    """
    stats = performance_metrics.get_stats()

    # 응답 시간 기준 정렬 (느린 순)
    sorted_endpoints = sorted(
        stats.items(),
        key=lambda x: x[1]["avg_response_time_ms"],
        reverse=True
    )

    return {
        "slowest_endpoints": [
            {
                "endpoint": endpoint,
                **metrics
            }
            for endpoint, metrics in sorted_endpoints[:10]
        ],
        "most_requested_endpoints": sorted(
            [
                {
                    "endpoint": endpoint,
                    **metrics
                }
                for endpoint, metrics in stats.items()
            ],
            key=lambda x: x["request_count"],
            reverse=True
        )[:10],
    }


# ============================================================================
# Alerts & Warnings
# ============================================================================

@router.get("/alerts")
async def get_active_alerts(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    활성 알림 조회

    - 높은 메모리 사용
    - 느린 응답 시간
    - 데이터베이스 연결 문제
    - 높은 에러율
    """
    alerts = []

    # 메모리 체크
    memory = get_memory_usage()
    if memory.get("rss_mb", 0) > 400:  # Railway Hobby: 512MB
        alerts.append({
            "type": "memory",
            "severity": "warning",
            "message": f"High memory usage: {memory.get('rss_mb')}MB",
            "threshold": "400MB",
        })

    # 데이터베이스 체크
    db_health = await check_db_health()
    for db_name, health in db_health.items():
        if health.get("status") != "ok":
            alerts.append({
                "type": "database",
                "severity": "critical",
                "message": f"{db_name} connection failed",
                "error": health.get("error"),
            })
        elif health.get("latency_ms", 0) > 100:
            alerts.append({
                "type": "database",
                "severity": "warning",
                "message": f"{db_name} slow response: {health.get('latency_ms')}ms",
                "threshold": "100ms",
            })

    # 성능 체크
    stats = performance_metrics.get_stats()
    for endpoint, metrics in stats.items():
        if metrics["error_rate"] > 0.05:  # 5% 이상 에러
            alerts.append({
                "type": "error_rate",
                "severity": "warning",
                "message": f"High error rate for {endpoint}: {metrics['error_rate'] * 100:.1f}%",
                "threshold": "5%",
            })

        if metrics["p95_response_time_ms"] > 1000:  # 1초 이상
            alerts.append({
                "type": "slow_response",
                "severity": "warning",
                "message": f"Slow P95 response for {endpoint}: {metrics['p95_response_time_ms']}ms",
                "threshold": "1000ms",
            })

    return {
        "total": len(alerts),
        "alerts": alerts,
    }
