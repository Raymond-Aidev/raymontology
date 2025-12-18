"""
Crawler Background Tasks

DART 크롤링 백그라운드 작업
"""
import asyncio
from typing import Dict, Optional
from datetime import datetime
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.tasks.celery_app import celery_app
from app.crawlers.dart_crawler import DARTCrawler
from app.config import settings
from app.database import async_session_maker
from app.models.disclosures import CrawlJob

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """
    데이터베이스 세션을 사용하는 Celery Task

    자동으로 세션 생성/종료
    """
    _db: Optional[AsyncSession] = None

    async def get_db(self) -> AsyncSession:
        """DB 세션 생성"""
        if self._db is None:
            self._db = async_session_maker()
        return self._db

    async def close_db(self):
        """DB 세션 종료"""
        if self._db is not None:
            await self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.crawler_tasks.crawl_all_companies_task",
    max_retries=3,
    default_retry_delay=300  # 5분
)
def crawl_all_companies_task(
    self,
    job_id: str,
    years: int = 3,
    batch_size: int = 10
) -> Dict:
    """
    전체 기업 공시 크롤링 (비동기 래퍼)

    Args:
        job_id: 작업 ID
        years: 수집 기간 (년)
        batch_size: 동시 처리할 기업 수

    Returns:
        통계 정보
    """
    return asyncio.run(
        _crawl_all_companies_async(self, job_id, years, batch_size)
    )


async def _crawl_all_companies_async(
    task: DatabaseTask,
    job_id: str,
    years: int,
    batch_size: int
) -> Dict:
    """전체 기업 공시 크롤링 (비동기)"""
    db = await task.get_db()

    try:
        # 작업 상태 업데이트: running
        job = await db.get(CrawlJob, job_id)
        if job:
            job.status = "running"
            job.started_at = datetime.utcnow()
            await db.commit()

        # 크롤러 생성
        crawler = DARTCrawler(
            api_key=settings.dart_api_key,
            data_dir=settings.dart_data_dir
        )

        # 크롤링 실행
        logger.info(f"Starting full crawl: job_id={job_id}, years={years}")
        stats = await crawler.crawl_all_companies(years=years, batch_size=batch_size)

        # 작업 상태 업데이트: completed
        if job:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.total_companies = stats["total_companies"]
            job.total_disclosures = stats["total_disclosures"]
            job.downloaded_documents = stats["downloaded_documents"]
            job.failed_downloads = stats["failed_downloads"]
            job.errors = stats["errors"]
            await db.commit()

        logger.info(f"Crawl completed: job_id={job_id}, stats={stats}")
        return stats

    except Exception as e:
        logger.error(f"Crawl failed: job_id={job_id}, error={e}")

        # 작업 상태 업데이트: failed
        if job:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            await db.commit()

        # 재시도
        raise task.retry(exc=e)

    finally:
        await task.close_db()


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.crawler_tasks.crawl_recent_task",
    max_retries=3,
    default_retry_delay=60  # 1분
)
def crawl_recent_task(
    self,
    job_id: str,
    hours: int = 24,
    batch_size: int = 10
) -> Dict:
    """
    최근 N시간 공시 크롤링 (비동기 래퍼)

    Args:
        job_id: 작업 ID
        hours: 수집 기간 (시간)
        batch_size: 동시 처리할 기업 수

    Returns:
        통계 정보
    """
    return asyncio.run(
        _crawl_recent_async(self, job_id, hours, batch_size)
    )


async def _crawl_recent_async(
    task: DatabaseTask,
    job_id: str,
    hours: int,
    batch_size: int
) -> Dict:
    """최근 N시간 공시 크롤링 (비동기)"""
    db = await task.get_db()

    try:
        # 작업 상태 업데이트: running
        job = await db.get(CrawlJob, job_id)
        if job:
            job.status = "running"
            job.started_at = datetime.utcnow()
            await db.commit()

        # 크롤러 생성
        crawler = DARTCrawler(
            api_key=settings.dart_api_key,
            data_dir=settings.dart_data_dir
        )

        # 크롤링 실행
        logger.info(f"Starting recent crawl: job_id={job_id}, hours={hours}")
        stats = await crawler.crawl_recent(hours=hours, batch_size=batch_size)

        # 작업 상태 업데이트: completed
        if job:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.total_companies = stats["total_companies"]
            job.total_disclosures = stats["total_disclosures"]
            job.downloaded_documents = stats["downloaded_documents"]
            job.failed_downloads = stats["failed_downloads"]
            job.errors = stats["errors"]
            await db.commit()

        logger.info(f"Recent crawl completed: job_id={job_id}, stats={stats}")
        return stats

    except Exception as e:
        logger.error(f"Recent crawl failed: job_id={job_id}, error={e}")

        # 작업 상태 업데이트: failed
        if job:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            await db.commit()

        # 재시도
        raise task.retry(exc=e)

    finally:
        await task.close_db()


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.crawler_tasks.crawl_company_task",
    max_retries=3,
    default_retry_delay=60  # 1분
)
def crawl_company_task(
    self,
    job_id: str,
    corp_code: str,
    years: int = 3
) -> Dict:
    """
    특정 기업 공시 크롤링 (비동기 래퍼)

    Args:
        job_id: 작업 ID
        corp_code: 기업 고유번호
        years: 수집 기간 (년)

    Returns:
        통계 정보
    """
    return asyncio.run(
        _crawl_company_async(self, job_id, corp_code, years)
    )


async def _crawl_company_async(
    task: DatabaseTask,
    job_id: str,
    corp_code: str,
    years: int
) -> Dict:
    """특정 기업 공시 크롤링 (비동기)"""
    from datetime import timedelta

    db = await task.get_db()

    try:
        # 작업 상태 업데이트: running
        job = await db.get(CrawlJob, job_id)
        if job:
            job.status = "running"
            job.started_at = datetime.utcnow()
            await db.commit()

        # 크롤러 생성
        crawler = DARTCrawler(
            api_key=settings.dart_api_key,
            data_dir=settings.dart_data_dir
        )

        # 날짜 범위
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)

        # 크롤링 실행
        logger.info(f"Starting company crawl: job_id={job_id}, corp_code={corp_code}")
        count = await crawler.crawl_company(corp_code, start_date, end_date)

        stats = {
            "total_companies": 1,
            "total_disclosures": count,
            "downloaded_documents": count,
            "failed_downloads": 0,
            "errors": []
        }

        # 작업 상태 업데이트: completed
        if job:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.total_companies = 1
            job.total_disclosures = count
            job.downloaded_documents = count
            await db.commit()

        logger.info(f"Company crawl completed: job_id={job_id}, count={count}")
        return stats

    except Exception as e:
        logger.error(f"Company crawl failed: job_id={job_id}, error={e}")

        # 작업 상태 업데이트: failed
        if job:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            await db.commit()

        # 재시도
        raise task.retry(exc=e)

    finally:
        await task.close_db()
