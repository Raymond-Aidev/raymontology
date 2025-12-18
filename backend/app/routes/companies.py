"""
Company Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Optional
import uuid

from app.database import get_db, get_redis
from app.schemas.company import (
    CompanySearchParams,
    CompanySearchResult,
    CompanyDetail,
)
from app.services.company_service import CompanyService

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/search", response_model=CompanySearchResult)
async def search_companies(
    q: Optional[str] = Query(None, description="검색어 (회사명, 티커)"),
    market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ, KONEX)"),
    sector: Optional[str] = Query(None, description="섹터"),
    min_market_cap: Optional[float] = Query(None, description="최소 시가총액"),
    max_market_cap: Optional[float] = Query(None, description="최대 시가총액"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="최소 리스크 점수"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    sort_by: str = Query("market_cap", description="정렬 기준 (market_cap, name, ownership_concentration)"),
    sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    """
    회사 검색

    **검색 옵션:**
    - `q`: 회사명 또는 티커로 검색 (부분 일치)
    - `market`: 시장 필터 (KOSPI, KOSDAQ, KONEX)
    - `sector`: 섹터 필터
    - `min_market_cap`, `max_market_cap`: 시가총액 범위
    - `min_risk_score`: 최소 리스크 점수 (0.0 ~ 1.0)

    **정렬:**
    - `sort_by`: market_cap, name, ownership_concentration 등
    - `sort_order`: asc (오름차순), desc (내림차순)

    **페이징:**
    - `page`: 페이지 번호 (1부터 시작)
    - `page_size`: 페이지당 항목 수 (최대 100)

    **응답:**
    - `total`: 전체 검색 결과 수
    - `items`: 현재 페이지 항목 리스트
    - `has_next`: 다음 페이지 존재 여부

    **예시:**
    ```
    GET /api/companies/search?q=삼성&market=KOSPI&page=1&page_size=20
    ```
    """
    # 검색 파라미터 생성
    params = CompanySearchParams(
        q=q,
        market=market,
        sector=sector,
        min_market_cap=min_market_cap,
        max_market_cap=max_market_cap,
        min_risk_score=min_risk_score,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # 서비스 호출
    service = CompanyService(db=db, redis=redis)
    result = await service.search_companies(params)

    return result


@router.get("/{company_id}", response_model=CompanyDetail)
async def get_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    """
    회사 상세 정보 조회

    **경로 파라미터:**
    - `company_id`: 회사 UUID

    **응답:**
    - 회사 상세 정보 (재무 지표, 리스크 지표, 온톨로지 연결 등)

    **예시:**
    ```
    GET /api/companies/550e8400-e29b-41d4-a716-446655440000
    ```

    **에러:**
    - `404`: 회사를 찾을 수 없음
    """
    # 서비스 호출
    service = CompanyService(db=db, redis=redis)
    company = await service.get_company_by_id(company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found"
        )

    return company


@router.get("/ticker/{ticker}", response_model=CompanyDetail)
async def get_company_by_ticker(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    """
    티커로 회사 조회

    **경로 파라미터:**
    - `ticker`: 종목 코드 (예: 005930)

    **응답:**
    - 회사 상세 정보

    **예시:**
    ```
    GET /api/companies/ticker/005930
    ```

    **에러:**
    - `404`: 회사를 찾을 수 없음
    """
    # 서비스 호출
    service = CompanyService(db=db, redis=redis)
    company = await service.get_company_by_ticker(ticker)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker {ticker} not found"
        )

    return company
