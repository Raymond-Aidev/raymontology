"""
Admin Routes - 관리자 전용 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime, timedelta
import logging
import uuid as uuid_module

from app.database import get_db
from app.models.users import User
from app.models.site_settings import SiteSetting
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================================
# Schemas
# ============================================================================

class SiteSettingUpdate(BaseModel):
    """사이트 설정 업데이트 요청"""
    key: str
    value: str


class SiteSettingResponse(BaseModel):
    """사이트 설정 응답"""
    key: str
    value: str
    updated_at: datetime


class UserListItem(BaseModel):
    """사용자 목록 항목"""
    id: str
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    oauth_provider: Optional[str]
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    created_at: datetime
    last_login: Optional[datetime]


class SubscriptionUpdateRequest(BaseModel):
    """이용권 업데이트 요청"""
    tier: Literal['free', 'light', 'max']  # 2종 플랜: Light 3,000원/월, Max 30,000원/월
    duration_days: Optional[int] = None  # None이면 무기한
    memo: Optional[str] = None  # 부여 사유


class UserListResponse(BaseModel):
    """사용자 목록 응답"""
    users: List[UserListItem]
    total: int


class StatsResponse(BaseModel):
    """통계 응답"""
    total_users: int
    active_users: int
    oauth_users: int
    superusers: int


# ============================================================================
# Helper: Admin Check
# ============================================================================

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """관리자 권한 확인"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user


# ============================================================================
# Site Settings Endpoints
# ============================================================================

@router.get("/settings/{key}", response_model=SiteSettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """사이트 설정 조회 (관리자 전용)"""
    result = await db.execute(
        select(SiteSetting).where(SiteSetting.key == key)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        # 기본값 반환
        return SiteSettingResponse(
            key=key,
            value="",
            updated_at=datetime.utcnow()
        )

    return SiteSettingResponse(
        key=setting.key,
        value=setting.value,
        updated_at=setting.updated_at
    )


@router.put("/settings", response_model=SiteSettingResponse)
async def update_setting(
    data: SiteSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """사이트 설정 업데이트 (관리자 전용)"""
    try:
        result = await db.execute(
            select(SiteSetting).where(SiteSetting.key == data.key)
        )
        setting = result.scalar_one_or_none()

        if setting:
            # 기존 설정 업데이트
            setting.value = data.value
            setting.updated_by = current_user.id
        else:
            # 새 설정 생성
            setting = SiteSetting(
                key=data.key,
                value=data.value,
                updated_by=current_user.id
            )
            db.add(setting)

        await db.commit()
        await db.refresh(setting)

        logger.info(f"Setting '{data.key}' updated by {current_user.email}")

        return SiteSettingResponse(
            key=setting.key,
            value=setting.value,
            updated_at=setting.updated_at
        )
    except Exception as e:
        logger.error(f"Failed to update setting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="설정 업데이트에 실패했습니다."
        )


# ============================================================================
# Public Settings Endpoint (for terms/privacy pages)
# ============================================================================

@router.get("/public/settings/{key}")
async def get_public_setting(
    key: str,
    db: AsyncSession = Depends(get_db)
):
    """공개 사이트 설정 조회 (이용약관, 개인정보처리방침)"""
    if key not in ["terms", "privacy"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="설정을 찾을 수 없습니다."
        )

    result = await db.execute(
        select(SiteSetting).where(SiteSetting.key == key)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        # 기본 내용 반환
        default_content = {
            "terms": "# 이용약관\n\n이용약관 내용이 아직 등록되지 않았습니다.",
            "privacy": "# 개인정보 처리방침\n\n개인정보 처리방침 내용이 아직 등록되지 않았습니다."
        }
        return {"key": key, "value": default_content.get(key, "")}

    return {"key": setting.key, "value": setting.value}


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """사용자 목록 조회 (관리자 전용)"""
    # 전체 수 조회
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar()

    # 사용자 목록 조회
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()

    return UserListResponse(
        users=[
            UserListItem(
                id=str(user.id),
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                oauth_provider=user.oauth_provider,
                subscription_tier=user.subscription_tier or 'free',
                subscription_expires_at=user.subscription_expires_at,
                created_at=user.created_at,
                last_login=user.last_login
            )
            for user in users
        ],
        total=total
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """통계 조회 (관리자 전용)"""
    # 전체 사용자 수
    total_result = await db.execute(select(func.count(User.id)))
    total_users = total_result.scalar()

    # 활성 사용자 수
    active_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_result.scalar()

    # OAuth 사용자 수
    oauth_result = await db.execute(
        select(func.count(User.id)).where(User.oauth_provider.isnot(None))
    )
    oauth_users = oauth_result.scalar()

    # 관리자 수
    superuser_result = await db.execute(
        select(func.count(User.id)).where(User.is_superuser == True)
    )
    superusers = superuser_result.scalar()

    return StatsResponse(
        total_users=total_users,
        active_users=active_users,
        oauth_users=oauth_users,
        superusers=superusers
    )


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """사용자 활성/비활성 토글 (관리자 전용)"""
    try:
        user_uuid = uuid_module.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 사용자 ID 형식입니다."
        )

    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    # 자기 자신은 비활성화 불가
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 계정은 비활성화할 수 없습니다."
        )

    user.is_active = not user.is_active
    await db.commit()

    return {"message": f"사용자 상태가 {'활성화' if user.is_active else '비활성화'}되었습니다."}


@router.patch("/users/{user_id}/subscription")
async def update_user_subscription(
    user_id: str,
    data: SubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """사용자 이용권 업데이트 (관리자 전용)"""
    try:
        user_uuid = uuid_module.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 사용자 ID 형식입니다."
        )

    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    # 이용권 업데이트
    old_tier = user.subscription_tier
    user.subscription_tier = data.tier

    if data.tier == 'free':
        # 무료로 변경 시 만료일 제거
        user.subscription_expires_at = None
    elif data.duration_days is None:
        # 무기한
        user.subscription_expires_at = None
    else:
        # 기간 설정
        user.subscription_expires_at = datetime.utcnow() + timedelta(days=data.duration_days)

    await db.commit()

    tier_names = {
        'free': '무료',
        'light': '라이트',
        'max': '맥스'
    }

    expires_msg = "무기한" if user.subscription_expires_at is None else f"{data.duration_days}일"
    memo_msg = f" (사유: {data.memo})" if data.memo else ""

    logger.info(f"Subscription updated for {user.email}: {old_tier} -> {data.tier} ({expires_msg}) by {current_user.email}{memo_msg}")

    return {
        "message": f"이용권이 {tier_names.get(data.tier, data.tier)} ({expires_msg})으로 설정되었습니다.",
        "subscription_tier": user.subscription_tier,
        "subscription_expires_at": user.subscription_expires_at
    }
