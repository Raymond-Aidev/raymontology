"""
Usage Service - 조회 횟수 추적 및 제한 체크
"""
from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.users import User
from app.models.subscriptions import UserQueryUsage, SUBSCRIPTION_LIMITS


def get_current_year_month() -> str:
    """현재 년-월을 'YYYY-MM' 형식으로 반환"""
    return datetime.now().strftime("%Y-%m")


async def get_user_usage(
    db: AsyncSession,
    user_id: UUID
) -> Tuple[int, int, int, int]:
    """
    사용자의 현재 월 조회 횟수 및 제한을 반환

    Returns:
        (query_count, query_limit, report_count, report_limit)
        limit이 -1이면 무제한
    """
    year_month = get_current_year_month()

    # 사용자 정보 조회 (tier 확인)
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        return (0, 0, 0, 0)

    # 이용권 만료 체크
    tier = user.subscription_tier or "free"
    if user.subscription_expires_at and user.subscription_expires_at < datetime.now(user.subscription_expires_at.tzinfo):
        tier = "free"

    # 제한 조회
    limits = SUBSCRIPTION_LIMITS.get(tier, SUBSCRIPTION_LIMITS["free"])
    query_limit = limits["monthly_queries"]
    report_limit = limits["monthly_reports"]

    # 현재 월 사용량 조회
    usage_result = await db.execute(
        select(UserQueryUsage).where(
            UserQueryUsage.user_id == user_id,
            UserQueryUsage.year_month == year_month
        )
    )
    usage = usage_result.scalar_one_or_none()

    query_count = usage.query_count if usage else 0
    report_count = usage.report_count if usage else 0

    return (query_count, query_limit, report_count, report_limit)


async def check_query_limit(
    db: AsyncSession,
    user_id: UUID,
    query_type: str = "query"  # "query" or "report"
) -> Tuple[bool, str, int, int]:
    """
    조회 제한 체크

    Args:
        db: DB 세션
        user_id: 사용자 ID
        query_type: "query" (회사 조회) 또는 "report" (리포트 조회)

    Returns:
        (allowed, message, current_count, limit)
        limit이 -1이면 무제한
    """
    query_count, query_limit, report_count, report_limit = await get_user_usage(db, user_id)

    if query_type == "query":
        current = query_count
        limit = query_limit
    else:
        current = report_count
        limit = report_limit

    # 무제한인 경우
    if limit == -1:
        return (True, "무제한", current, limit)

    # 제한 체크
    if current >= limit:
        remaining = 0
        message = f"월 조회 한도 {limit}건을 모두 사용했습니다. 이용권을 업그레이드하세요."
        return (False, message, current, limit)

    remaining = limit - current
    message = f"남은 조회 횟수: {remaining}건"
    return (True, message, current, limit)


async def increment_usage(
    db: AsyncSession,
    user_id: UUID,
    query_type: str = "query"  # "query" or "report"
) -> bool:
    """
    조회 횟수 증가

    Returns:
        성공 여부
    """
    year_month = get_current_year_month()

    # Upsert: 없으면 생성, 있으면 증가
    if query_type == "query":
        stmt = insert(UserQueryUsage).values(
            user_id=user_id,
            year_month=year_month,
            query_count=1,
            report_count=0
        ).on_conflict_do_update(
            index_elements=['user_id', 'year_month'],
            set_={'query_count': UserQueryUsage.query_count + 1}
        )
    else:
        stmt = insert(UserQueryUsage).values(
            user_id=user_id,
            year_month=year_month,
            query_count=0,
            report_count=1
        ).on_conflict_do_update(
            index_elements=['user_id', 'year_month'],
            set_={'report_count': UserQueryUsage.report_count + 1}
        )

    try:
        await db.execute(stmt)
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        print(f"Failed to increment usage: {e}")
        return False


async def get_usage_stats(
    db: AsyncSession,
    user_id: UUID
) -> dict:
    """
    사용자 조회 현황 통계 반환
    """
    query_count, query_limit, report_count, report_limit = await get_user_usage(db, user_id)

    return {
        "query": {
            "used": query_count,
            "limit": query_limit,
            "remaining": query_limit - query_count if query_limit != -1 else -1,
            "unlimited": query_limit == -1
        },
        "report": {
            "used": report_count,
            "limit": report_limit,
            "remaining": report_limit - report_count if report_limit != -1 else -1,
            "unlimited": report_limit == -1
        },
        "year_month": get_current_year_month()
    }
