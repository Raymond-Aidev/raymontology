"""
Disclosure Schemas

공시 데이터 스키마
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============================================================================
# Request Schemas
# ============================================================================

class DisclosureSearchParams(BaseModel):
    """공시 검색 파라미터"""
    corp_code: Optional[str] = Field(None, description="기업 코드 (8자리)")
    stock_code: Optional[str] = Field(None, description="종목 코드 (6자리)")
    report_nm: Optional[str] = Field(None, description="보고서명 (부분 일치)")
    start_date: Optional[str] = Field(None, description="시작일 (YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="종료일 (YYYYMMDD)")
    page: int = Field(1, ge=1, description="페이지 번호")
    page_size: int = Field(20, ge=1, le=100, description="페이지 크기")


class CrawlJobCreateParams(BaseModel):
    """크롤링 작업 생성 파라미터"""
    job_type: str = Field(..., description="작업 유형 (full, recent, company)")
    years: Optional[int] = Field(3, ge=1, le=10, description="전체 크롤링 기간 (년)")
    hours: Optional[int] = Field(24, ge=1, le=168, description="최근 크롤링 기간 (시간)")
    corp_code: Optional[str] = Field(None, description="특정 기업 크롤링 (8자리)")


# ============================================================================
# Response Schemas
# ============================================================================

class DisclosureResponse(BaseModel):
    """공시 응답"""
    id: str
    rcept_no: str = Field(..., description="접수번호")
    corp_code: str = Field(..., description="기업 코드")
    corp_name: str = Field(..., description="회사명")
    stock_code: Optional[str] = Field(None, description="종목 코드")
    report_nm: str = Field(..., description="보고서명")
    rcept_dt: str = Field(..., description="접수일자 (YYYYMMDD)")
    flr_nm: Optional[str] = Field(None, description="공시 제출인명")
    rm: Optional[str] = Field(None, description="비고")
    storage_url: Optional[str] = Field(None, description="문서 URL")
    crawled_at: str = Field(..., description="크롤링 시각 (ISO 8601)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")

    class Config:
        from_attributes = True


class DisclosureListResponse(BaseModel):
    """공시 목록 응답"""
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")
    items: List[DisclosureResponse] = Field(..., description="공시 목록")


class DisclosureParsedDataResponse(BaseModel):
    """파싱된 공시 데이터 응답"""
    id: str
    rcept_no: str
    parsed_data: Dict[str, Any] = Field(..., description="파싱된 데이터")
    parsed_at: str = Field(..., description="파싱 시각 (ISO 8601)")
    parser_version: Optional[str] = Field(None, description="파서 버전")
    sections_count: int = Field(0, description="섹션 수")
    tables_count: int = Field(0, description="테이블 수")

    class Config:
        from_attributes = True


class CrawlJobResponse(BaseModel):
    """크롤링 작업 응답"""
    id: str
    job_type: str = Field(..., description="작업 유형")
    status: str = Field(..., description="작업 상태 (pending, running, completed, failed)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="작업 파라미터")
    total_companies: int = Field(0, description="전체 기업 수")
    total_disclosures: int = Field(0, description="전체 공시 수")
    downloaded_documents: int = Field(0, description="다운로드 문서 수")
    failed_downloads: int = Field(0, description="실패 다운로드 수")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="에러 목록")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    started_at: Optional[str] = Field(None, description="시작 시각 (ISO 8601)")
    completed_at: Optional[str] = Field(None, description="완료 시각 (ISO 8601)")
    created_at: str = Field(..., description="생성 시각 (ISO 8601)")
    task_id: Optional[str] = Field(None, description="Celery 태스크 ID")

    class Config:
        from_attributes = True


class CrawlJobListResponse(BaseModel):
    """크롤링 작업 목록 응답"""
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")
    items: List[CrawlJobResponse] = Field(..., description="작업 목록")


# ============================================================================
# Statistics
# ============================================================================

class DisclosureStatistics(BaseModel):
    """공시 통계"""
    total_disclosures: int = Field(0, description="전체 공시 수")
    total_companies: int = Field(0, description="전체 기업 수")
    latest_crawl: Optional[str] = Field(None, description="최근 크롤링 시각 (ISO 8601)")
    disclosures_by_date: Dict[str, int] = Field(default_factory=dict, description="날짜별 공시 수")
    top_companies: List[Dict[str, Any]] = Field(default_factory=list, description="상위 공시 기업")


class CrawlJobStatistics(BaseModel):
    """크롤링 작업 통계"""
    total_jobs: int = Field(0, description="전체 작업 수")
    pending_jobs: int = Field(0, description="대기 중 작업 수")
    running_jobs: int = Field(0, description="실행 중 작업 수")
    completed_jobs: int = Field(0, description="완료된 작업 수")
    failed_jobs: int = Field(0, description="실패한 작업 수")
    latest_job: Optional[CrawlJobResponse] = Field(None, description="최근 작업")
