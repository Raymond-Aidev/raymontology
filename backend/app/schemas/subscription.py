"""
Subscription Schemas - 이용권 및 결제 스키마
"""
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime


# 이용권 등급 타입
SubscriptionTierType = Literal['free', 'light', 'max']


class SubscriptionPlanFeature(BaseModel):
    """이용권 플랜 기능"""
    text: str


class SubscriptionPlan(BaseModel):
    """이용권 플랜 정보"""
    tier: SubscriptionTierType
    name: str
    name_ko: str
    price: int
    price_display: str
    features: List[str]


class SubscriptionPlansResponse(BaseModel):
    """이용권 플랜 목록 응답"""
    plans: List[SubscriptionPlan]


class UserSubscriptionStatus(BaseModel):
    """사용자 이용권 상태"""
    tier: SubscriptionTierType
    tier_name: str
    expires_at: Optional[datetime]
    is_active: bool
    days_remaining: Optional[int]


# 결제 관련 스키마
class PaymentCreateRequest(BaseModel):
    """결제 생성 요청"""
    tier: Literal['light', 'max']
    duration_months: int = 1  # 1, 3, 6, 12개월


class PaymentCreateResponse(BaseModel):
    """결제 생성 응답 (PG사로 리다이렉트 전)"""
    order_id: str
    amount: int
    tier: str
    checkout_url: Optional[str] = None  # PG사 결제 페이지 URL
    client_key: Optional[str] = None    # 프론트엔드 SDK용 키


class PaymentVerifyRequest(BaseModel):
    """결제 확인 요청 (PG사에서 리다이렉트 후)"""
    order_id: str
    payment_key: str  # PG사에서 받은 결제 키
    amount: int


class PaymentResult(BaseModel):
    """결제 결과"""
    success: bool
    message: str
    tier: Optional[str] = None
    expires_at: Optional[datetime] = None
    transaction_id: Optional[str] = None


class PaymentHistoryItem(BaseModel):
    """결제 이력 항목"""
    id: str
    tier: str
    tier_name: str
    amount: int
    status: str
    payment_method: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class PaymentHistoryResponse(BaseModel):
    """결제 이력 응답"""
    payments: List[PaymentHistoryItem]
    total: int


# 어드민용 스키마
class AdminSubscriptionGrant(BaseModel):
    """어드민 이용권 부여 요청"""
    tier: Literal['free', 'light', 'max']
    duration_days: Optional[int] = None  # None이면 무기한
    memo: Optional[str] = None  # 부여 사유


class AdminSubscriptionResponse(BaseModel):
    """어드민 이용권 부여 응답"""
    message: str
    user_id: str
    tier: str
    expires_at: Optional[datetime]
