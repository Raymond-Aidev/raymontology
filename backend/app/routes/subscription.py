"""
Subscription Routes - 이용권 및 결제 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import uuid
import logging

from app.database import get_db
from app.models.users import User
from app.models.subscriptions import (
    SubscriptionPayment,
    PaymentStatus,
    SUBSCRIPTION_PLANS
)
from app.schemas.subscription import (
    SubscriptionPlansResponse,
    SubscriptionPlan,
    UserSubscriptionStatus,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentVerifyRequest,
    PaymentResult,
    PaymentHistoryResponse,
    PaymentHistoryItem
)
from app.core.security import get_current_user
from app.services.payment_service import get_payment_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


# ============================================================================
# 이용권 플랜 조회
# ============================================================================

@router.get("/plans", response_model=SubscriptionPlansResponse)
async def get_plans():
    """
    이용권 플랜 목록 조회
    인증 불필요 - 모든 사용자가 조회 가능
    """
    plans = [
        SubscriptionPlan(
            tier=tier,
            name=info["name"],
            name_ko=info["name_ko"],
            price=info["price"],
            price_display=info["price_display"],
            features=info["features"]
        )
        for tier, info in SUBSCRIPTION_PLANS.items()
    ]
    return SubscriptionPlansResponse(plans=plans)


@router.get("/status", response_model=UserSubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user)
):
    """
    현재 사용자의 이용권 상태 조회
    """
    tier = current_user.subscription_tier or "free"
    expires_at = current_user.subscription_expires_at

    # 만료 여부 확인
    is_active = True
    days_remaining = None

    if tier != "free" and expires_at:
        now = datetime.utcnow()
        if expires_at.tzinfo:
            now = datetime.now(expires_at.tzinfo)

        if expires_at < now:
            is_active = False
            days_remaining = 0
        else:
            days_remaining = (expires_at - now).days

    tier_name = SUBSCRIPTION_PLANS.get(tier, {}).get("name_ko", "무료")

    return UserSubscriptionStatus(
        tier=tier,
        tier_name=tier_name,
        expires_at=expires_at,
        is_active=is_active,
        days_remaining=days_remaining
    )


# ============================================================================
# 결제 처리
# ============================================================================

@router.post("/checkout", response_model=PaymentCreateResponse)
async def create_checkout(
    request: PaymentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    결제 요청 생성
    PG사 결제창 호출을 위한 정보 반환
    """
    tier = request.tier
    duration_months = request.duration_months

    if tier not in ["light", "max"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 이용권입니다."
        )

    plan = SUBSCRIPTION_PLANS[tier]
    amount = plan["price"] * duration_months

    # 주문 ID 생성
    order_id = f"sub_{current_user.id}_{uuid.uuid4().hex[:8]}"

    # 결제 이력 생성 (PENDING 상태)
    payment = SubscriptionPayment(
        user_id=current_user.id,
        tier=tier,
        amount=amount,
        duration_days=duration_months * 30,
        pg_order_id=order_id,
        status=PaymentStatus.PENDING.value
    )
    db.add(payment)
    await db.commit()

    # PG사 결제 요청 생성
    payment_service = get_payment_service()
    checkout_info = await payment_service.create_payment(
        order_id=order_id,
        amount=amount,
        order_name=f"RaymondsRisk {plan['name_ko']} {duration_months}개월",
        customer_email=current_user.email,
        customer_name=current_user.full_name or current_user.username,
        success_url=f"{settings.frontend_url}/payment/success",
        fail_url=f"{settings.frontend_url}/payment/fail"
    )

    return PaymentCreateResponse(
        order_id=order_id,
        amount=amount,
        tier=tier,
        checkout_url=checkout_info.get("checkout_url"),
        client_key=checkout_info.get("client_key")
    )


@router.post("/verify", response_model=PaymentResult)
async def verify_payment(
    request: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    결제 승인/확인
    PG사에서 리다이렉트 후 호출
    """
    # 결제 이력 조회
    result = await db.execute(
        select(SubscriptionPayment).where(
            SubscriptionPayment.pg_order_id == request.order_id,
            SubscriptionPayment.user_id == current_user.id
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="결제 정보를 찾을 수 없습니다."
        )

    if payment.status == PaymentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 처리된 결제입니다."
        )

    # 금액 검증
    if payment.amount != request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="결제 금액이 일치하지 않습니다."
        )

    # PG사 결제 승인
    payment_service = get_payment_service()
    verify_result = await payment_service.verify_payment(
        payment_key=request.payment_key,
        order_id=request.order_id,
        amount=request.amount
    )

    if not verify_result.success:
        payment.status = PaymentStatus.FAILED.value
        await db.commit()
        return PaymentResult(
            success=False,
            message=verify_result.message
        )

    # 결제 성공 처리
    payment.status = PaymentStatus.COMPLETED.value
    payment.pg_transaction_id = verify_result.transaction_id
    payment.completed_at = datetime.utcnow()

    # 사용자 이용권 업데이트
    user = await db.get(User, current_user.id)
    user.subscription_tier = payment.tier

    # 만료일 계산 (기존 만료일이 미래면 그 이후로, 아니면 지금부터)
    now = datetime.utcnow()
    if user.subscription_expires_at and user.subscription_expires_at > now:
        base_date = user.subscription_expires_at
    else:
        base_date = now

    user.subscription_expires_at = base_date + timedelta(days=payment.duration_days)

    await db.commit()

    logger.info(f"Payment completed: user={current_user.email}, tier={payment.tier}, amount={payment.amount}")

    return PaymentResult(
        success=True,
        message="결제가 완료되었습니다.",
        tier=payment.tier,
        expires_at=user.subscription_expires_at,
        transaction_id=verify_result.transaction_id
    )


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    결제 이력 조회
    """
    result = await db.execute(
        select(SubscriptionPayment)
        .where(SubscriptionPayment.user_id == current_user.id)
        .order_by(SubscriptionPayment.created_at.desc())
        .limit(50)
    )
    payments = result.scalars().all()

    items = [
        PaymentHistoryItem(
            id=str(p.id),
            tier=p.tier,
            tier_name=SUBSCRIPTION_PLANS.get(p.tier, {}).get("name_ko", p.tier),
            amount=p.amount,
            status=p.status,
            payment_method=p.payment_method,
            created_at=p.created_at,
            completed_at=p.completed_at
        )
        for p in payments
    ]

    return PaymentHistoryResponse(
        payments=items,
        total=len(items)
    )


# ============================================================================
# 웹훅 (PG사 콜백)
# ============================================================================

@router.post("/webhook/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    PG사 웹훅 수신
    결제 상태 변경 알림 처리
    """
    payload = await request.json()
    signature = request.headers.get("X-Webhook-Signature")

    logger.info(f"Webhook received from {provider}: {payload}")

    payment_service = get_payment_service()
    result = await payment_service.handle_webhook(payload, signature)

    if result.success and result.transaction_id:
        # 결제 상태 업데이트
        stmt = select(SubscriptionPayment).where(
            SubscriptionPayment.pg_transaction_id == result.transaction_id
        )
        db_result = await db.execute(stmt)
        payment = db_result.scalar_one_or_none()

        if payment and result.data:
            new_status = result.data.get("status")
            if new_status:
                payment.status = new_status
                await db.commit()
                logger.info(f"Payment status updated: {payment.id} -> {new_status}")

    return {"status": "ok"}
