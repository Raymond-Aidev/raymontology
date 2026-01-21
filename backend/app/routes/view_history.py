"""
View History Routes - 조회 기록 관련 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

from app.database import get_db
from app.core.security import get_current_user
from app.models.users import User
from app.models.subscriptions import CompanyViewHistory


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


router = APIRouter(prefix="/api/companies", tags=["view-history"])

# Note: This router is registered directly in main.py without additional prefix


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
    count_query = select(func.count()).select_from(CompanyViewHistory).where(
        CompanyViewHistory.user_id == current_user.id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

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


# 공용 함수: 조회 기록 저장
async def save_view_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    company_id: str,
    company_name: str | None = None,
    ticker: str | None = None,
    market: str | None = None
):
    """
    조회 기록 저장 (중복 시 viewed_at 업데이트)

    Args:
        db: 데이터베이스 세션
        user_id: 사용자 UUID
        company_id: 회사 UUID (문자열)
        company_name: 회사명 (옵션)
        ticker: 티커 (옵션)
        market: 시장 (옵션)
    """
    try:
        company_uuid = uuid.UUID(company_id) if isinstance(company_id, str) else company_id

        # 기존 기록 확인
        existing_query = select(CompanyViewHistory).where(
            CompanyViewHistory.user_id == user_id,
            CompanyViewHistory.company_id == company_uuid
        )
        existing_result = await db.execute(existing_query)
        existing_record = existing_result.scalar_one_or_none()

        if existing_record:
            # 기존 기록 업데이트
            existing_record.viewed_at = datetime.now()
            if company_name:
                existing_record.company_name = company_name
            if ticker:
                existing_record.ticker = ticker
            if market:
                existing_record.market = market
        else:
            # 새 기록 생성
            view_record = CompanyViewHistory(
                user_id=user_id,
                company_id=company_uuid,
                company_name=company_name,
                ticker=ticker,
                market=market,
            )
            db.add(view_record)

        await db.commit()
    except Exception as e:
        await db.rollback()
        # 조회 기록 저장 실패해도 조회는 성공으로 처리
        import logging
        logging.getLogger(__name__).warning(f"Failed to save view history: {e}")
