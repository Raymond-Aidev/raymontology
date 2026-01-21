"""
Company Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from redis.asyncio import Redis
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.database import get_db, get_redis
from app.schemas.company import (
    CompanySearchParams,
    CompanySearchResult,
    CompanyDetail,
)
from app.services.company_service import CompanyService
from app.core.security import get_current_user
from app.models.users import User
from app.models.subscriptions import CompanyViewHistory
from app.services.usage_service import check_query_limit, increment_usage


# 조회 기록 응답 스키마
class ViewHistoryItem(BaseModel):
    id: str
    company_id: str
    company_name: str | None
    ticker: str | None
    market: str | None
    viewed_at: datetime

    class Config:
        from_attributes = True


class ViewHistoryResponse(BaseModel):
    items: List[ViewHistoryItem]
    total: int
    page: int
    page_size: int

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
    current_user: User = Depends(get_current_user),
):
    """
    회사 상세 정보 조회 (로그인 필요, 조회 횟수 차감)

    **경로 파라미터:**
    - `company_id`: 회사 UUID

    **응답:**
    - 회사 상세 정보 (재무 지표, 리스크 지표, 온톨로지 연결 등)

    **예시:**
    ```
    GET /api/companies/550e8400-e29b-41d4-a716-446655440000
    ```

    **에러:**
    - `401`: 로그인 필요
    - `403`: 조회 한도 초과
    - `404`: 회사를 찾을 수 없음
    """
    # 조회 제한 체크
    allowed, message, current_count, limit = await check_query_limit(db, current_user.id, "query")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": message,
                "code": "QUERY_LIMIT_EXCEEDED",
                "used": current_count,
                "limit": limit
            }
        )

    # 서비스 호출
    service = CompanyService(db=db, redis=redis)
    company = await service.get_company_by_id(company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found"
        )

    # 조회 횟수 증가
    await increment_usage(db, current_user.id, "query")

    # 조회 기록 저장
    await save_view_history(db, current_user.id, company)

    return company


@router.get("/ticker/{ticker}", response_model=CompanyDetail)
async def get_company_by_ticker(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    """
    티커로 회사 조회 (로그인 필요, 조회 횟수 차감)

    **경로 파라미터:**
    - `ticker`: 종목 코드 (예: 005930)

    **응답:**
    - 회사 상세 정보

    **예시:**
    ```
    GET /api/companies/ticker/005930
    ```

    **에러:**
    - `401`: 로그인 필요
    - `403`: 조회 한도 초과
    - `404`: 회사를 찾을 수 없음
    """
    # 조회 제한 체크
    allowed, message, current_count, limit = await check_query_limit(db, current_user.id, "query")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": message,
                "code": "QUERY_LIMIT_EXCEEDED",
                "used": current_count,
                "limit": limit
            }
        )

    # 서비스 호출
    service = CompanyService(db=db, redis=redis)
    company = await service.get_company_by_ticker(ticker)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker {ticker} not found"
        )

    # 조회 횟수 증가
    await increment_usage(db, current_user.id, "query")

    # 조회 기록 저장
    await save_view_history(db, current_user.id, company)

    return company


async def save_view_history(db: AsyncSession, user_id: uuid.UUID, company: CompanyDetail):
    """조회 기록 저장"""
    try:
        view_record = CompanyViewHistory(
            user_id=user_id,
            company_id=uuid.UUID(company.id),
            company_name=company.name,
            ticker=company.ticker,
            market=company.market,
        )
        db.add(view_record)
        await db.commit()
    except Exception as e:
        await db.rollback()
        # 조회 기록 저장 실패해도 조회는 성공으로 처리
        print(f"Failed to save view history: {e}")


@router.get("/view-history/list", response_model=ViewHistoryResponse)
async def get_view_history(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    조회한 기업 목록 조회 (유료 회원 전용)

    **파라미터:**
    - `page`: 페이지 번호 (1부터 시작)
    - `page_size`: 페이지당 항목 수 (최대 100)

    **응답:**
    - `items`: 조회 기록 리스트
    - `total`: 전체 조회 기록 수
    - `page`: 현재 페이지
    - `page_size`: 페이지 크기

    **에러:**
    - `401`: 로그인 필요
    - `403`: 유료 회원 전용 (구독 필요)
    """
    from datetime import timedelta

    tier = current_user.subscription_tier or "free"
    now = datetime.now(current_user.created_at.tzinfo) if current_user.created_at and current_user.created_at.tzinfo else datetime.now()

    # trial 만료 체크 (가입 후 30일)
    if tier == "trial":
        created_at = current_user.created_at
        if created_at:
            trial_expires = created_at + timedelta(days=30)
            if now > trial_expires:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "유료회원 전용메뉴입니다",
                        "code": "TRIAL_EXPIRED"
                    }
                )

    # free 회원 차단
    if tier == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "유료회원 전용메뉴입니다",
                "code": "FREE_USER"
            }
        )

    # 유료 구독 만료 체크
    if tier in ["light", "max"]:
        if current_user.subscription_expires_at:
            expires_at = current_user.subscription_expires_at
            if now > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "유료이용 기간이 아닙니다",
                        "code": "SUBSCRIPTION_EXPIRED"
                    }
                )

    # 조회 기록 가져오기
    offset = (page - 1) * page_size

    # 전체 개수 조회
    count_query = select(CompanyViewHistory).where(
        CompanyViewHistory.user_id == current_user.id
    )
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    # 페이지네이션된 결과 조회
    query = (
        select(CompanyViewHistory)
        .where(CompanyViewHistory.user_id == current_user.id)
        .order_by(desc(CompanyViewHistory.viewed_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    records = result.scalars().all()

    items = [
        ViewHistoryItem(
            id=str(record.id),
            company_id=str(record.company_id),
            company_name=record.company_name,
            ticker=record.ticker,
            market=record.market,
            viewed_at=record.viewed_at,
        )
        for record in records
    ]

    return ViewHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
