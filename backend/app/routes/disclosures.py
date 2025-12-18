"""
Disclosure Routes

공시 데이터 조회 및 크롤링 작업 관리
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
import uuid
from datetime import datetime

from app.database import get_db
from app.schemas.disclosure import (
    DisclosureSearchParams,
    DisclosureListResponse,
    DisclosureResponse,
    CrawlJobCreateParams,
    CrawlJobResponse,
    CrawlJobListResponse,
    DisclosureStatistics,
    CrawlJobStatistics
)
from app.models.disclosures import Disclosure, CrawlJob
from app.tasks.crawler_tasks import (
    crawl_all_companies_task,
    crawl_recent_task,
    crawl_company_task
)

router = APIRouter(prefix="/api/disclosures", tags=["disclosures"])


# ============================================================================
# 공시 조회
# ============================================================================

@router.get("", response_model=DisclosureListResponse)
async def search_disclosures(
    corp_code: Optional[str] = Query(None, description="기업 코드 (8자리)"),
    stock_code: Optional[str] = Query(None, description="종목 코드 (6자리)"),
    report_nm: Optional[str] = Query(None, description="보고서명 (부분 일치)"),
    start_date: Optional[str] = Query(None, description="시작일 (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="종료일 (YYYYMMDD)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db)
):
    """
    공시 검색

    **검색 필터**:
    - corp_code: 기업 코드로 필터링
    - stock_code: 종목 코드로 필터링
    - report_nm: 보고서명으로 검색 (PostgreSQL trigram 사용)
    - start_date, end_date: 날짜 범위 필터링

    **페이지네이션**:
    - page: 페이지 번호 (1부터 시작)
    - page_size: 페이지당 항목 수 (최대 100)
    """
    query = select(Disclosure)

    # 필터 적용
    if corp_code:
        query = query.where(Disclosure.corp_code == corp_code)
    if stock_code:
        query = query.where(Disclosure.stock_code == stock_code)
    if report_nm:
        query = query.where(Disclosure.report_nm.ilike(f"%{report_nm}%"))
    if start_date:
        query = query.where(Disclosure.rcept_dt >= start_date)
    if end_date:
        query = query.where(Disclosure.rcept_dt <= end_date)

    # 정렬: 최근 공시 우선
    query = query.order_by(desc(Disclosure.rcept_dt))

    # 총 개수
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 페이지네이션
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # 실행
    result = await db.execute(query)
    disclosures = result.scalars().all()

    return DisclosureListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            DisclosureResponse(
                id=d.id,
                rcept_no=d.rcept_no,
                corp_code=d.corp_code,
                corp_name=d.corp_name,
                stock_code=d.stock_code,
                report_nm=d.report_nm,
                rcept_dt=d.rcept_dt,
                flr_nm=d.flr_nm,
                rm=d.rm,
                storage_url=d.storage_url,
                crawled_at=d.crawled_at.isoformat(),
                metadata=d.metadata
            )
            for d in disclosures
        ]
    )


@router.get("/{rcept_no}", response_model=DisclosureResponse)
async def get_disclosure(
    rcept_no: str,
    db: AsyncSession = Depends(get_db)
):
    """
    공시 상세 조회

    접수번호로 특정 공시 조회
    """
    query = select(Disclosure).where(Disclosure.rcept_no == rcept_no)
    result = await db.execute(query)
    disclosure = result.scalar_one_or_none()

    if not disclosure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disclosure not found: {rcept_no}"
        )

    return DisclosureResponse(
        id=disclosure.id,
        rcept_no=disclosure.rcept_no,
        corp_code=disclosure.corp_code,
        corp_name=disclosure.corp_name,
        stock_code=disclosure.stock_code,
        report_nm=disclosure.report_nm,
        rcept_dt=disclosure.rcept_dt,
        flr_nm=disclosure.flr_nm,
        rm=disclosure.rm,
        storage_url=disclosure.storage_url,
        crawled_at=disclosure.crawled_at.isoformat(),
        metadata=disclosure.metadata
    )


@router.get("/stats/overview", response_model=DisclosureStatistics)
async def get_disclosure_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    공시 통계

    전체 공시 수, 기업 수, 최근 크롤링 시각 등
    """
    # 전체 공시 수
    total_disclosures = await db.scalar(select(func.count(Disclosure.id)))

    # 전체 기업 수
    total_companies = await db.scalar(
        select(func.count(func.distinct(Disclosure.corp_code)))
    )

    # 최근 크롤링 시각
    latest_crawl_query = select(func.max(Disclosure.crawled_at))
    latest_crawl = await db.scalar(latest_crawl_query)

    return DisclosureStatistics(
        total_disclosures=total_disclosures or 0,
        total_companies=total_companies or 0,
        latest_crawl=latest_crawl.isoformat() if latest_crawl else None
    )


# ============================================================================
# 크롤링 작업 관리
# ============================================================================

@router.post("/crawl", response_model=CrawlJobResponse, status_code=status.HTTP_201_CREATED)
async def create_crawl_job(
    params: CrawlJobCreateParams,
    db: AsyncSession = Depends(get_db)
):
    """
    크롤링 작업 생성

    **작업 유형**:
    - `full`: 전체 기업 크롤링 (years 파라미터 사용)
    - `recent`: 최근 N시간 크롤링 (hours 파라미터 사용)
    - `company`: 특정 기업 크롤링 (corp_code 파라미터 사용)

    백그라운드에서 Celery 작업으로 실행됩니다.
    """
    # 작업 레코드 생성
    job = CrawlJob(
        id=str(uuid.uuid4()),
        job_type=params.job_type,
        status="pending",
        parameters={
            "years": params.years,
            "hours": params.hours,
            "corp_code": params.corp_code
        }
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Celery 작업 시작
    if params.job_type == "full":
        task = crawl_all_companies_task.delay(
            job_id=job.id,
            years=params.years
        )
    elif params.job_type == "recent":
        task = crawl_recent_task.delay(
            job_id=job.id,
            hours=params.hours
        )
    elif params.job_type == "company":
        if not params.corp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="corp_code is required for company crawl"
            )
        task = crawl_company_task.delay(
            job_id=job.id,
            corp_code=params.corp_code,
            years=params.years
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job_type: {params.job_type}"
        )

    # Task ID 저장
    job.task_id = task.id
    await db.commit()

    return CrawlJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        parameters=job.parameters,
        total_companies=job.total_companies,
        total_disclosures=job.total_disclosures,
        downloaded_documents=job.downloaded_documents,
        failed_downloads=job.failed_downloads,
        errors=job.errors,
        error_message=job.error_message,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        created_at=job.created_at.isoformat(),
        task_id=job.task_id
    )


@router.get("/crawl/jobs", response_model=CrawlJobListResponse)
async def list_crawl_jobs(
    job_type: Optional[str] = Query(None, description="작업 유형"),
    status: Optional[str] = Query(None, description="작업 상태"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db)
):
    """
    크롤링 작업 목록 조회

    최근 작업부터 표시
    """
    query = select(CrawlJob)

    # 필터 적용
    if job_type:
        query = query.where(CrawlJob.job_type == job_type)
    if status:
        query = query.where(CrawlJob.status == status)

    # 정렬: 최근 작업 우선
    query = query.order_by(desc(CrawlJob.created_at))

    # 총 개수
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 페이지네이션
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # 실행
    result = await db.execute(query)
    jobs = result.scalars().all()

    return CrawlJobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            CrawlJobResponse(
                id=j.id,
                job_type=j.job_type,
                status=j.status,
                parameters=j.parameters,
                total_companies=j.total_companies,
                total_disclosures=j.total_disclosures,
                downloaded_documents=j.downloaded_documents,
                failed_downloads=j.failed_downloads,
                errors=j.errors,
                error_message=j.error_message,
                started_at=j.started_at.isoformat() if j.started_at else None,
                completed_at=j.completed_at.isoformat() if j.completed_at else None,
                created_at=j.created_at.isoformat(),
                task_id=j.task_id
            )
            for j in jobs
        ]
    )


@router.get("/crawl/jobs/{job_id}", response_model=CrawlJobResponse)
async def get_crawl_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    크롤링 작업 상세 조회

    작업 진행 상태 및 결과 확인
    """
    job = await db.get(CrawlJob, job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crawl job not found: {job_id}"
        )

    return CrawlJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        parameters=job.parameters,
        total_companies=job.total_companies,
        total_disclosures=job.total_disclosures,
        downloaded_documents=job.downloaded_documents,
        failed_downloads=job.failed_downloads,
        errors=job.errors,
        error_message=job.error_message,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        created_at=job.created_at.isoformat(),
        task_id=job.task_id
    )


@router.get("/crawl/stats/overview", response_model=CrawlJobStatistics)
async def get_crawl_job_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    크롤링 작업 통계

    전체 작업 수, 상태별 개수 등
    """
    # 전체 작업 수
    total_jobs = await db.scalar(select(func.count(CrawlJob.id)))

    # 상태별 개수
    pending_jobs = await db.scalar(
        select(func.count(CrawlJob.id)).where(CrawlJob.status == "pending")
    )
    running_jobs = await db.scalar(
        select(func.count(CrawlJob.id)).where(CrawlJob.status == "running")
    )
    completed_jobs = await db.scalar(
        select(func.count(CrawlJob.id)).where(CrawlJob.status == "completed")
    )
    failed_jobs = await db.scalar(
        select(func.count(CrawlJob.id)).where(CrawlJob.status == "failed")
    )

    # 최근 작업
    latest_job_query = select(CrawlJob).order_by(desc(CrawlJob.created_at)).limit(1)
    result = await db.execute(latest_job_query)
    latest_job = result.scalar_one_or_none()

    return CrawlJobStatistics(
        total_jobs=total_jobs or 0,
        pending_jobs=pending_jobs or 0,
        running_jobs=running_jobs or 0,
        completed_jobs=completed_jobs or 0,
        failed_jobs=failed_jobs or 0,
        latest_job=CrawlJobResponse(
            id=latest_job.id,
            job_type=latest_job.job_type,
            status=latest_job.status,
            parameters=latest_job.parameters,
            total_companies=latest_job.total_companies,
            total_disclosures=latest_job.total_disclosures,
            downloaded_documents=latest_job.downloaded_documents,
            failed_downloads=latest_job.failed_downloads,
            errors=latest_job.errors,
            error_message=latest_job.error_message,
            started_at=latest_job.started_at.isoformat() if latest_job.started_at else None,
            completed_at=latest_job.completed_at.isoformat() if latest_job.completed_at else None,
            created_at=latest_job.created_at.isoformat(),
            task_id=latest_job.task_id
        ) if latest_job else None
    )
