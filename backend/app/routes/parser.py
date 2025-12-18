"""
Parser Routes

보고서 파싱 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from pathlib import Path

from app.database import get_db
from app.schemas.parsed_report import (
    ParseReportRequest,
    ParseSectionRequest,
    ParsedReportDetail,
    ParsedReportSummary,
    ParsedReportValidation,
    ParsingStatistics,
    ParseJobStatus,
)
from app.models.disclosures import Disclosure, DisclosureParsedData
from app.tasks.parser_tasks import (
    parse_report_task,
    parse_officer_section_task,
    parse_cb_section_task,
)
from app.nlp.report_parser import ReportParser

router = APIRouter(prefix="/api/parser", tags=["parser"])


# ============================================================================
# 파싱 작업
# ============================================================================

@router.post("/parse", response_model=ParseJobStatus, status_code=status.HTTP_201_CREATED)
async def parse_report(
    request: ParseReportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    보고서 파싱 작업 생성

    백그라운드에서 PDF를 파싱하고 구조화된 데이터 추출

    **파이프라인**:
    1. PDF → 텍스트 추출
    2. 텍스트 → 섹션 분할
    3. 섹션 → NER (임원, 전환사채 등)
    4. 구조화된 데이터 저장

    **파싱 대상**:
    - 임원 현황
    - 전환사채 발행 현황
    - 특수관계자 거래
    - 주주 현황
    """
    # 공시 존재 확인
    query = select(Disclosure).where(Disclosure.rcept_no == request.rcept_no)
    result = await db.execute(query)
    disclosure = result.scalar_one_or_none()

    if not disclosure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disclosure not found: {request.rcept_no}"
        )

    # 이미 파싱된 데이터 확인
    parsed_query = select(DisclosureParsedData).where(
        DisclosureParsedData.rcept_no == request.rcept_no
    )
    parsed_result = await db.execute(parsed_query)
    existing_parsed = parsed_result.scalar_one_or_none()

    if existing_parsed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report already parsed: {request.rcept_no}"
        )

    # PDF 파일 경로 (storage_url에서 추출 또는 로컬 경로)
    # TODO: S3에서 다운로드 로직 추가
    pdf_path = disclosure.storage_url or f"./data/dart/{disclosure.corp_code}/temp.pdf"

    # 백그라운드 파싱 작업 생성
    task = parse_report_task.delay(
        rcept_no=request.rcept_no,
        pdf_path=pdf_path,
        company_id=request.company_id or str(disclosure.corp_code),
        use_ocr=request.use_ocr
    )

    return ParseJobStatus(
        job_id=task.id,
        status="pending",
        rcept_no=request.rcept_no,
        company_id=request.company_id,
        progress=0.0,
        created_at=disclosure.crawled_at.isoformat(),
    )


@router.post("/parse-section", status_code=status.HTTP_201_CREATED)
async def parse_section(
    request: ParseSectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 섹션만 파싱 (경량 작업)

    **섹션 유형**:
    - `officers`: 임원 현황만 추출
    - `convertible_bonds`: 전환사채만 추출
    - `related_parties`: 특수관계자만 추출
    """
    # 공시 존재 확인
    query = select(Disclosure).where(Disclosure.rcept_no == request.rcept_no)
    result = await db.execute(query)
    disclosure = result.scalar_one_or_none()

    if not disclosure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disclosure not found: {request.rcept_no}"
        )

    # PDF 경로
    pdf_path = disclosure.storage_url or f"./data/dart/{disclosure.corp_code}/temp.pdf"
    company_id = str(disclosure.corp_code)

    # 섹션 유형에 따라 작업 선택
    if request.section_type == "officers":
        task = parse_officer_section_task.delay(request.rcept_no, pdf_path, company_id)
    elif request.section_type == "convertible_bonds":
        task = parse_cb_section_task.delay(request.rcept_no, pdf_path, company_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported section type: {request.section_type}"
        )

    return {
        "job_id": task.id,
        "status": "pending",
        "section_type": request.section_type,
        "rcept_no": request.rcept_no,
    }


# ============================================================================
# 파싱 결과 조회
# ============================================================================

@router.get("/parsed/{rcept_no}", response_model=ParsedReportDetail)
async def get_parsed_report(
    rcept_no: str,
    db: AsyncSession = Depends(get_db)
):
    """
    파싱된 보고서 조회

    구조화된 데이터 반환 (임원, CB, 특수관계자 등)
    """
    query = select(DisclosureParsedData).where(
        DisclosureParsedData.rcept_no == rcept_no
    )
    result = await db.execute(query)
    parsed_data = result.scalar_one_or_none()

    if not parsed_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parsed report not found: {rcept_no}"
        )

    # ParsedReportDetail로 변환
    data = parsed_data.parsed_data

    return ParsedReportDetail(
        report_id=data.get("report_id", ""),
        company_id=data.get("company_id", ""),
        rcept_no=rcept_no,
        metadata=data.get("metadata", {}),
        total_pages=data.get("total_pages", 0),
        sections=data.get("sections", {}),
        officers=data.get("officers", []),
        convertible_bonds=data.get("convertible_bonds", []),
        related_parties=data.get("related_parties", []),
        shareholders=data.get("shareholders", []),
        parsed_at=parsed_data.parsed_at.isoformat(),
        parsing_stats=data.get("parsing_stats", {}),
    )


@router.get("/parsed/{rcept_no}/officers")
async def get_parsed_officers(
    rcept_no: str,
    db: AsyncSession = Depends(get_db)
):
    """
    파싱된 임원 정보만 조회
    """
    query = select(DisclosureParsedData).where(
        DisclosureParsedData.rcept_no == rcept_no
    )
    result = await db.execute(query)
    parsed_data = result.scalar_one_or_none()

    if not parsed_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parsed report not found: {rcept_no}"
        )

    officers = parsed_data.parsed_data.get("officers", [])

    return {
        "rcept_no": rcept_no,
        "officers": officers,
        "count": len(officers),
    }


@router.get("/parsed/{rcept_no}/convertible-bonds")
async def get_parsed_convertible_bonds(
    rcept_no: str,
    db: AsyncSession = Depends(get_db)
):
    """
    파싱된 전환사채 정보만 조회
    """
    query = select(DisclosureParsedData).where(
        DisclosureParsedData.rcept_no == rcept_no
    )
    result = await db.execute(query)
    parsed_data = result.scalar_one_or_none()

    if not parsed_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parsed report not found: {rcept_no}"
        )

    cbs = parsed_data.parsed_data.get("convertible_bonds", [])

    return {
        "rcept_no": rcept_no,
        "convertible_bonds": cbs,
        "count": len(cbs),
    }


@router.get("/parsed/{rcept_no}/validate", response_model=ParsedReportValidation)
async def validate_parsed_report(
    rcept_no: str,
    db: AsyncSession = Depends(get_db)
):
    """
    파싱된 데이터 검증

    누락된 필수 필드, 데이터 이상 등 확인
    """
    query = select(DisclosureParsedData).where(
        DisclosureParsedData.rcept_no == rcept_no
    )
    result = await db.execute(query)
    parsed_data = result.scalar_one_or_none()

    if not parsed_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parsed report not found: {rcept_no}"
        )

    # 검증 로직 (간단한 예시)
    errors = []
    warnings = []

    data = parsed_data.parsed_data

    # 필수 섹션 확인
    if not data.get("officers"):
        warnings.append("No officers found")

    # 임원 데이터 검증
    for officer in data.get("officers", []):
        if not officer.get("name"):
            errors.append("Officer missing name")

    is_valid = len(errors) == 0

    return ParsedReportValidation(
        report_id=data.get("report_id", ""),
        errors=errors,
        warnings=warnings,
        is_valid=is_valid,
    )


# ============================================================================
# 통계
# ============================================================================

@router.get("/stats", response_model=ParsingStatistics)
async def get_parsing_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    파싱 통계

    전체 파싱 수, 평균 시간 등
    """
    # 전체 파싱 수
    total_reports = await db.scalar(select(func.count(DisclosureParsedData.id)))

    # 전체 임원 수 (JSONB 쿼리)
    # TODO: JSONB 배열 길이 집계

    # 최근 파싱 시각
    latest_parsed_query = select(func.max(DisclosureParsedData.parsed_at))
    latest_parsed = await db.scalar(latest_parsed_query)

    return ParsingStatistics(
        total_reports=total_reports or 0,
        total_officers=0,  # TODO
        total_cbs=0,  # TODO
        avg_parsing_time=0.0,  # TODO
        success_rate=100.0,  # TODO
        latest_parsed=latest_parsed.isoformat() if latest_parsed else None,
    )
