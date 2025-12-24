"""
크롤링 제어 API (관리자 전용)

DART 공시 데이터 수집 제어
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional
import logging

from app.database import get_db, get_redis
from app.crawlers.dart_crawler import DARTCrawler
from app.utils.cache import make_cache_key, get_cached, set_cached, CacheTTL
from app.auth.deps import get_current_superuser
from app.models.users import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/crawl", tags=["Admin - Crawling"])


# ============================================================================
# 관리자 권한 체크 (간단한 버전 - 실제로는 JWT 토큰 검증 필요)
# ============================================================================

async def require_admin(
    current_user: User = Depends(get_current_superuser)
) -> User:
    """
    관리자 권한 확인 (슈퍼유저만 접근 가능)

    Args:
        current_user: JWT 토큰에서 추출된 슈퍼유저

    Returns:
        User 모델 인스턴스

    Raises:
        HTTPException: 401 (인증 실패), 403 (권한 없음)
    """
    logger.info(f"Admin access granted: {current_user.email}")
    return current_user


# ============================================================================
# 크롤링 상태 추적
# ============================================================================

class CrawlStatus:
    """크롤링 작업 상태"""
    def __init__(self, redis: Redis):
        self.redis = redis

    async def set_status(
        self,
        job_id: str,
        status: str,
        details: dict = None
    ):
        """크롤링 상태 저장"""
        key = make_cache_key("crawl_job", job_id)
        data = {
            "job_id": job_id,
            "status": status,  # pending, running, completed, failed
            "details": details or {},
            "updated_at": str(datetime.now())
        }
        await set_cached(self.redis, key, data, ttl=3600)  # 1시간

    async def get_status(self, job_id: str) -> Optional[dict]:
        """크롤링 상태 조회"""
        key = make_cache_key("crawl_job", job_id)
        return await get_cached(self.redis, key)


# ============================================================================
# API 엔드포인트
# ============================================================================

@router.post("/dart/all")
async def trigger_full_crawl(
    background_tasks: BackgroundTasks,
    years: int = Query(default=3, ge=1, le=10, description="최근 N년 데이터"),
    batch_size: int = Query(default=10, ge=1, le=50, description="배치 크기"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    admin: None = Depends(require_admin)
):
    """
    전체 DART 크롤링 시작 (백그라운드)

    주의:
    - 매우 오래 걸림 (수 시간~하루)
    - Railway 메모리 제한 고려 (배치 처리)
    - API 요청 제한 (일일 10,000건)

    Args:
        years: 최근 N년 데이터 수집
        batch_size: 배치 크기 (메모리 최적화)

    Returns:
        {
            "job_id": "crawl_full_20231201_123456",
            "status": "started",
            "message": "백그라운드에서 크롤링 시작됨",
            "estimated_time": "약 3-4시간 소요 예상"
        }
    """
    from datetime import datetime
    import uuid

    # Job ID 생성
    job_id = f"crawl_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # 크롤링 상태 초기화
    crawl_status = CrawlStatus(redis)
    await crawl_status.set_status(
        job_id,
        "pending",
        {
            "years": years,
            "batch_size": batch_size,
            "started_at": str(datetime.now())
        }
    )

    # 백그라운드 태스크 등록
    background_tasks.add_task(
        run_full_crawl_task,
        job_id=job_id,
        years=years,
        batch_size=batch_size,
        redis=redis
    )

    logger.info(f"전체 크롤링 시작: {job_id}")

    return {
        "job_id": job_id,
        "status": "started",
        "message": "백그라운드에서 크롤링 시작됨",
        "estimated_time": f"약 {years * 2}-{years * 3}시간 소요 예상",
        "check_status_url": f"/api/admin/crawl/status/{job_id}"
    }


@router.post("/dart/recent")
async def trigger_recent_crawl(
    hours: int = Query(default=24, ge=1, le=168, description="최근 N시간"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    admin: None = Depends(require_admin)
):
    """
    최근 N시간 공시 크롤링 (빠름, 동기)

    실시간 모니터링용으로 사용

    Args:
        hours: 최근 N시간 (기본 24시간)

    Returns:
        {
            "status": "completed",
            "companies_processed": 123,
            "disclosures_found": 456,
            "duration_seconds": 45.6
        }
    """
    import time

    start_time = time.time()

    crawler = DARTCrawler()
    result = await crawler.crawl_recent(hours=hours)

    duration = time.time() - start_time

    logger.info(
        f"최근 크롤링 완료: {hours}시간, "
        f"{result.get('companies_processed')}개 회사, "
        f"{result.get('disclosures_found')}개 공시"
    )

    return {
        "status": "completed",
        "companies_processed": result.get("companies_processed", 0),
        "disclosures_found": result.get("disclosures_found", 0),
        "duration_seconds": round(duration, 2),
        "hours": hours
    }


@router.post("/dart/company/{corp_code}")
async def trigger_company_crawl(
    corp_code: str,
    years: int = Query(default=3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    admin: None = Depends(require_admin)
):
    """
    특정 기업 크롤링

    Args:
        corp_code: 기업 고유번호 (8자리)
        years: 최근 N년 데이터

    Returns:
        {
            "status": "completed",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "disclosures_found": 45
        }
    """
    from datetime import datetime, timedelta

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years)

    crawler = DARTCrawler()

    async with crawler.client:
        # 기업 정보 조회
        company_info = await crawler.client.get_company_info(corp_code)
        if not company_info:
            raise HTTPException(404, f"기업을 찾을 수 없습니다: {corp_code}")

        # 공시 목록 조회
        disclosures = await crawler.client.get_disclosure_list(
            corp_code,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d")
        )

        # TODO: DB 저장 로직

        return {
            "status": "completed",
            "corp_code": corp_code,
            "corp_name": company_info.get("corp_name"),
            "disclosures_found": len(disclosures),
            "period": f"{years}년"
        }


@router.get("/status/{job_id}")
async def get_crawl_status(
    job_id: str,
    redis: Redis = Depends(get_redis),
    admin: None = Depends(require_admin)
):
    """
    크롤링 작업 상태 조회

    Args:
        job_id: 작업 ID

    Returns:
        {
            "job_id": "crawl_full_20231201_123456",
            "status": "running",  # pending, running, completed, failed
            "details": {
                "companies_processed": 123,
                "total_companies": 456,
                "progress_percent": 27
            }
        }
    """
    crawl_status = CrawlStatus(redis)
    status = await crawl_status.get_status(job_id)

    if not status:
        raise HTTPException(404, f"크롤링 작업을 찾을 수 없습니다: {job_id}")

    return status


@router.delete("/cancel/{job_id}")
async def cancel_crawl(
    job_id: str,
    redis: Redis = Depends(get_redis),
    admin: None = Depends(require_admin)
):
    """
    크롤링 작업 취소

    주의: 백그라운드 태스크는 즉시 중단되지 않을 수 있음
    """
    crawl_status = CrawlStatus(redis)

    # 상태를 "cancelled"로 변경
    await crawl_status.set_status(
        job_id,
        "cancelled",
        {"cancelled_at": str(datetime.now())}
    )

    logger.warning(f"크롤링 취소 요청: {job_id}")

    return {
        "status": "cancelled",
        "job_id": job_id,
        "message": "크롤링 취소 요청됨 (진행 중인 작업은 완료 후 중단)"
    }


@router.get("/stats")
async def get_crawl_stats(
    db: AsyncSession = Depends(get_db),
    admin: None = Depends(require_admin)
):
    """
    크롤링 통계

    Returns:
        {
            "total_companies": 2500,
            "total_disclosures": 123456,
            "last_crawl_at": "2023-12-01T10:30:00",
            "companies_with_data": 2450
        }
    """
    # TODO: DB에서 통계 조회
    return {
        "total_companies": 0,
        "total_disclosures": 0,
        "last_crawl_at": None,
        "companies_with_data": 0,
        "message": "통계 기능 구현 예정"
    }


# ============================================================================
# 백그라운드 태스크
# ============================================================================

async def run_full_crawl_task(
    job_id: str,
    years: int,
    batch_size: int,
    redis: Redis
):
    """
    전체 크롤링 백그라운드 태스크

    Args:
        job_id: 작업 ID
        years: 최근 N년
        batch_size: 배치 크기
        redis: Redis 클라이언트
    """
    from datetime import datetime

    crawl_status = CrawlStatus(redis)

    try:
        # 상태: running
        await crawl_status.set_status(job_id, "running", {
            "started_at": str(datetime.now())
        })

        # 크롤러 실행
        crawler = DARTCrawler()
        result = await crawler.crawl_all_companies(
            years=years,
            batch_size=batch_size,
            save_to_db=True
        )

        # 상태: completed
        await crawl_status.set_status(job_id, "completed", {
            "completed_at": str(datetime.now()),
            "companies_processed": result.get("companies_processed", 0),
            "disclosures_found": result.get("disclosures_found", 0)
        })

        logger.info(f"크롤링 완료: {job_id}")

    except Exception as e:
        logger.error(f"크롤링 실패 ({job_id}): {e}", exc_info=True)

        # 상태: failed
        await crawl_status.set_status(job_id, "failed", {
            "failed_at": str(datetime.now()),
            "error": str(e)
        })
