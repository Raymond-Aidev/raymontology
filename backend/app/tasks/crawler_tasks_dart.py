"""
DART 크롤러 Celery 태스크

Railway 환경 최적화:
- 메모리 효율적 배치 처리
- 재시도 로직
- 진행 상황 추적
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from app.tasks.celery_app import celery_app
from app.crawlers.dart_crawler import DARTCrawler
from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Celery 태스크
# ============================================================================

@celery_app.task(
    bind=True,
    name="crawl_dart_all_companies",
    max_retries=3,
    default_retry_delay=300  # 5분
)
def crawl_dart_all_companies(
    self,
    years: int = 3,
    batch_size: int = 10,
    save_to_db: bool = True
):
    """
    전체 상장사 DART 크롤링 (Celery 태스크)

    Args:
        years: 최근 N년 데이터
        batch_size: 배치 크기 (메모리 최적화)
        save_to_db: DB 저장 여부

    Returns:
        {
            "status": "completed",
            "companies_processed": 123,
            "disclosures_found": 456,
            "duration_seconds": 12345
        }
    """
    import time

    start_time = time.time()

    logger.info(
        f"DART 전체 크롤링 시작 (task_id: {self.request.id})",
        extra={
            "years": years,
            "batch_size": batch_size
        }
    )

    try:
        # 비동기 크롤러 실행
        crawler = DARTCrawler()
        result = asyncio.run(
            crawler.crawl_all_companies(
                years=years,
                batch_size=batch_size,
                save_to_db=save_to_db
            )
        )

        duration = time.time() - start_time

        logger.info(
            f"DART 크롤링 완료 (task_id: {self.request.id})",
            extra={
                "companies_processed": result.get("companies_processed"),
                "disclosures_found": result.get("disclosures_found"),
                "duration_seconds": round(duration, 2)
            }
        )

        return {
            "status": "completed",
            "companies_processed": result.get("companies_processed", 0),
            "disclosures_found": result.get("disclosures_found", 0),
            "duration_seconds": round(duration, 2),
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(
            f"DART 크롤링 실패 (task_id: {self.request.id}): {e}",
            exc_info=True
        )

        # 재시도
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="crawl_dart_recent",
    max_retries=3
)
def crawl_dart_recent(self, hours: int = 24):
    """
    최근 N시간 공시 크롤링 (Celery 태스크)

    실시간 모니터링용

    Args:
        hours: 최근 N시간

    Returns:
        {
            "status": "completed",
            "disclosures_found": 45
        }
    """
    logger.info(f"최근 {hours}시간 DART 크롤링 시작")

    try:
        crawler = DARTCrawler()
        result = asyncio.run(crawler.crawl_recent(hours=hours))

        logger.info(
            f"최근 크롤링 완료: {result.get('disclosures_found')}개 공시"
        )

        return result

    except Exception as e:
        logger.error(f"최근 크롤링 실패: {e}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="crawl_dart_company",
    max_retries=3
)
def crawl_dart_company(
    self,
    corp_code: str,
    years: int = 3
):
    """
    특정 기업 크롤링 (Celery 태스크)

    Args:
        corp_code: 기업 고유번호 (8자리)
        years: 최근 N년 데이터

    Returns:
        {
            "status": "completed",
            "corp_code": "00126380",
            "disclosures_found": 45
        }
    """
    logger.info(f"기업 크롤링 시작: {corp_code}")

    try:
        from datetime import datetime, timedelta
        from app.crawlers.dart_client import DARTClient

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)

        async def _crawl():
            async with DARTClient(settings.dart_api_key) as client:
                # 공시 목록 조회
                disclosures = await client.get_disclosure_list(
                    corp_code,
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d")
                )

                # TODO: DB 저장 로직

                return {
                    "status": "completed",
                    "corp_code": corp_code,
                    "disclosures_found": len(disclosures)
                }

        result = asyncio.run(_crawl())

        logger.info(
            f"기업 크롤링 완료: {corp_code} ({result['disclosures_found']}개)"
        )

        return result

    except Exception as e:
        logger.error(f"기업 크롤링 실패 ({corp_code}): {e}", exc_info=True)
        raise self.retry(exc=e)


# ============================================================================
# 스케줄 태스크 (Celery Beat)
# ============================================================================

@celery_app.task(name="scheduled_crawl_recent_disclosures")
def scheduled_crawl_recent_disclosures():
    """
    정기 크롤링: 최근 24시간 공시

    Celery Beat 스케줄:
        - 매일 오전 9시
        - 또는 1시간마다
    """
    logger.info("정기 크롤링 시작: 최근 24시간")

    # crawl_dart_recent 태스크 호출
    crawl_dart_recent.delay(hours=24)


@celery_app.task(name="scheduled_crawl_weekly_full")
def scheduled_crawl_weekly_full():
    """
    정기 크롤링: 주간 전체 업데이트

    Celery Beat 스케줄:
        - 매주 일요일 새벽 2시
    """
    logger.info("정기 크롤링 시작: 주간 전체")

    # crawl_dart_all_companies 태스크 호출 (최근 1년)
    crawl_dart_all_companies.delay(years=1, batch_size=20)


# ============================================================================
# 유틸리티 함수
# ============================================================================

def trigger_full_crawl_async(years: int = 3, batch_size: int = 10):
    """
    비동기 전체 크롤링 시작

    Returns:
        task_id: Celery 태스크 ID
    """
    task = crawl_dart_all_companies.delay(
        years=years,
        batch_size=batch_size
    )

    logger.info(f"DART 크롤링 태스크 시작: {task.id}")

    return task.id


def trigger_recent_crawl_async(hours: int = 24):
    """
    비동기 최근 크롤링 시작

    Returns:
        task_id: Celery 태스크 ID
    """
    task = crawl_dart_recent.delay(hours=hours)

    logger.info(f"최근 크롤링 태스크 시작: {task.id}")

    return task.id


def get_task_status(task_id: str) -> dict:
    """
    태스크 상태 조회

    Args:
        task_id: Celery 태스크 ID

    Returns:
        {
            "task_id": "...",
            "status": "PENDING|STARTED|SUCCESS|FAILURE|RETRY",
            "result": {...},
            "info": {...}
        }
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None,
        "info": result.info
    }


def cancel_task(task_id: str):
    """
    태스크 취소

    Args:
        task_id: Celery 태스크 ID
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)
    result.revoke(terminate=True)

    logger.warning(f"태스크 취소: {task_id}")
