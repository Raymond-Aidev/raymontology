"""
Database Configuration and Session Management

Railway 최적화
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from redis.asyncio import Redis
from neo4j import AsyncGraphDatabase
import logging
from typing import AsyncGenerator

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# SQLAlchemy Base
# ============================================================================

Base = declarative_base()

# ============================================================================
# PostgreSQL (Railway 최적화)
# ============================================================================

# Async Engine (Railway Hobby Plan 최적화)
# AsyncAdaptedQueuePool 사용 (비동기 엔진용)
from sqlalchemy.pool import AsyncAdaptedQueuePool

engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    poolclass=AsyncAdaptedQueuePool,  # 비동기 엔진용 풀 클래스
    pool_size=5,            # Railway Hobby: 최대 5개 권장
    max_overflow=10,        # 피크 시 추가 10개 (총 15개)
    pool_pre_ping=True,     # 연결 유효성 검사
    pool_recycle=3600,      # 1시간마다 연결 재생성
    pool_timeout=30,        # 30초 대기 타임아웃
    pool_use_lifo=True,     # LIFO 방식 (캐시 효율성)
    echo=settings.debug,    # 프로덕션에서는 False
    echo_pool=settings.debug,
    connect_args={
        "server_settings": {
            "application_name": "raymontology",
            "jit": "off",
        },
        "command_timeout": 60,
        "timeout": 10,
    },
)

# Session Factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ============================================================================
# Redis
# ============================================================================

redis_client: Redis = None

# ============================================================================
# Neo4j
# ============================================================================

neo4j_driver = None

# ============================================================================
# Dependency Injection
# ============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency: Database Session

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> Redis:
    """
    FastAPI Dependency: Redis Client
    """
    return redis_client


async def get_neo4j():
    """
    FastAPI Dependency: Neo4j Driver
    """
    return neo4j_driver


# ============================================================================
# Lifecycle Management
# ============================================================================


async def init_db():
    """
    Initialize all database connections

    Called on application startup
    """
    global redis_client, neo4j_driver

    # PostgreSQL - 테이블 생성
    logger.info("Initializing PostgreSQL...")
    async with engine.begin() as conn:
        # 개발 환경에서만 테이블 자동 생성
        # 프로덕션에서는 Alembic 사용
        if settings.debug:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("PostgreSQL tables created (debug mode)")
        else:
            logger.info("PostgreSQL connected (use Alembic for migrations)")

    # Redis (최적화된 연결 풀) - Optional
    if settings.redis_url:
        logger.info("Initializing Redis...")
        try:
            redis_client = await Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                # 연결 풀 최적화
                max_connections=50,  # 최대 연결 수
                socket_connect_timeout=5,
                socket_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 10,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                },
                health_check_interval=30,
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],
            )
            await redis_client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            redis_client = None
    else:
        logger.info("Redis URL not configured. Caching disabled.")
        redis_client = None

    # Neo4j
    logger.info("Initializing Neo4j...")
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=60,
        )
        await neo4j_driver.verify_connectivity()
        logger.info("Neo4j connected successfully")
    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")
        neo4j_driver = None

    logger.info("All databases initialized")


async def close_db():
    """
    Close all database connections

    Called on application shutdown
    """
    global redis_client, neo4j_driver

    logger.info("Closing database connections...")

    # Redis
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

    # Neo4j
    if neo4j_driver:
        await neo4j_driver.close()
        logger.info("Neo4j connection closed")

    # PostgreSQL
    await engine.dispose()
    logger.info("PostgreSQL connection closed")

    logger.info("All database connections closed")


# ============================================================================
# Health Check
# ============================================================================


async def check_db_health() -> dict:
    """
    Check health of all databases

    Returns:
        {
            "postgresql": {"status": "ok", "latency_ms": 12.3},
            "redis": {"status": "ok", "latency_ms": 1.2},
            "neo4j": {"status": "ok", "latency_ms": 5.6}
        }
    """
    import time

    health = {}

    # PostgreSQL
    try:
        start = time.time()
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        latency = (time.time() - start) * 1000
        health["postgresql"] = {"status": "ok", "latency_ms": round(latency, 2)}
    except Exception as e:
        health["postgresql"] = {"status": "error", "error": str(e)}

    # Redis
    if redis_client:
        try:
            start = time.time()
            await redis_client.ping()
            latency = (time.time() - start) * 1000
            health["redis"] = {"status": "ok", "latency_ms": round(latency, 2)}
        except Exception as e:
            health["redis"] = {"status": "error", "error": str(e)}
    else:
        health["redis"] = {"status": "not_initialized"}

    # Neo4j
    if neo4j_driver:
        try:
            start = time.time()
            await neo4j_driver.verify_connectivity()
            latency = (time.time() - start) * 1000
            health["neo4j"] = {"status": "ok", "latency_ms": round(latency, 2)}
        except Exception as e:
            health["neo4j"] = {"status": "error", "error": str(e)}
    else:
        health["neo4j"] = {"status": "not_initialized"}

    return health
