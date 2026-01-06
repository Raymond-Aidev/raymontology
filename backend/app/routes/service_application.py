"""
서비스 이용신청 API 라우트
- 사용자: 신청 생성, 조회, 취소
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging
import base64
import uuid as uuid_module

from app.database import get_db
from app.models.users import User
from app.models.service_application import (
    ServiceApplication,
    ApplicationStatus,
    PlanType,
    ENTERPRISE_PLANS
)
from app.schemas.service_application import (
    ServiceApplicationResponse,
    ServiceApplicationListResponse,
    ServiceApplicationCreateResult,
    EnterprisePlanInfo,
    EnterprisePlansResponse,
    PaymentInfoResponse,
    PaymentBankInfo
)
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/service-applications", tags=["service-applications"])

# 허용 파일 타입
ALLOWED_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ============================================================================
# 플랜 정보 조회
# ============================================================================

@router.get("/plans", response_model=EnterprisePlansResponse)
async def get_enterprise_plans():
    """엔터프라이즈 이용 플랜 목록 조회"""
    plans = []
    for plan_type, info in ENTERPRISE_PLANS.items():
        plans.append(EnterprisePlanInfo(
            plan_type=plan_type,
            name_ko=info["name_ko"],
            price=info["price"],
            price_display=f"{info['price']:,}원",
            duration_days=info["duration_days"],
            discount=info.get("discount")
        ))
    return EnterprisePlansResponse(plans=plans)


# ============================================================================
# 사용자 API: 신청 생성
# ============================================================================

@router.post("/", response_model=PaymentInfoResponse)
async def create_service_application(
    applicant_email: str = Form(...),
    plan_type: str = Form(...),
    business_registration_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    서비스 이용신청 생성

    - applicant_email: 신청자 이메일
    - plan_type: 플랜 타입 (1_MONTH, 6_MONTHS, 1_YEAR)
    - business_registration_file: 사업자등록증 파일 (필수, PDF/JPG/PNG, 최대 10MB)
    """
    # 사업자등록증 필수 확인
    if not business_registration_file or not business_registration_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사업자등록증 파일은 필수입니다."
        )
    # 플랜 타입 검증
    if plan_type not in ENTERPRISE_PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 플랜입니다. 가능한 플랜: {list(ENTERPRISE_PLANS.keys())}"
        )

    # 중복 신청 확인 (PENDING 상태인 신청이 있는지)
    existing = await db.execute(
        select(ServiceApplication)
        .where(ServiceApplication.user_id == current_user.id)
        .where(ServiceApplication.status == ApplicationStatus.PENDING.value)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 처리 중인 신청이 있습니다. 기존 신청이 완료된 후 다시 시도해주세요."
        )

    # 파일 처리 (필수)
    # 파일 타입 검증
    if business_registration_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="허용되지 않는 파일 형식입니다. PDF, JPG, PNG만 가능합니다."
        )

    # 파일 크기 검증
    content = await business_registration_file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"파일 크기가 너무 큽니다. 최대 {MAX_FILE_SIZE // (1024 * 1024)}MB까지 가능합니다."
        )

    # Base64 인코딩
    file_content = base64.b64encode(content).decode('utf-8')
    file_name = business_registration_file.filename
    mime_type = business_registration_file.content_type

    # 플랜 정보
    plan_info = ENTERPRISE_PLANS[plan_type]

    # 신청 생성
    application = ServiceApplication(
        user_id=current_user.id,
        applicant_email=applicant_email,
        business_registration_file_content=file_content,
        business_registration_file_name=file_name,
        business_registration_mime_type=mime_type,
        plan_type=plan_type,
        plan_amount=plan_info["price"],
        status=ApplicationStatus.PENDING.value
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    logger.info(f"Service application created: {application.id} by user {current_user.email}")

    # 이메일 발송 (비동기)
    try:
        from app.services.email_service import email_service
        await email_service.send_service_application_email(
            to_email=applicant_email,
            plan_type=plan_type,
            plan_name=plan_info["name_ko"],
            plan_amount=plan_info["price"]
        )
        # 관리자에게도 알림
        await email_service.send_admin_application_notification(
            applicant_email=applicant_email,
            plan_name=plan_info["name_ko"],
            plan_amount=plan_info["price"],
            application_id=str(application.id)
        )
    except Exception as e:
        logger.warning(f"Email sending failed: {e}")
        # 이메일 실패해도 신청은 완료

    return PaymentInfoResponse(
        application_id=application.id,
        plan_type=plan_type,
        plan_name_ko=plan_info["name_ko"],
        plan_amount=plan_info["price"],
        plan_amount_display=f"{plan_info['price']:,}원",
        bank_info=PaymentBankInfo(),
        message="신청이 완료되었습니다. 입금 안내 이메일을 확인해주세요."
    )


# ============================================================================
# 사용자 API: 내 신청 조회
# ============================================================================

@router.get("/my", response_model=ServiceApplicationListResponse)
async def get_my_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """내 서비스 이용신청 목록 조회"""
    result = await db.execute(
        select(ServiceApplication)
        .where(ServiceApplication.user_id == current_user.id)
        .order_by(ServiceApplication.created_at.desc())
    )
    applications = result.scalars().all()

    # 현재 이용권 상태
    current_subscription = None
    if current_user.subscription_tier and current_user.subscription_tier != 'free':
        is_active = True
        if current_user.subscription_expires_at:
            is_active = current_user.subscription_expires_at > datetime.utcnow()

        current_subscription = {
            "status": "ACTIVE" if is_active else "EXPIRED",
            "tier": current_user.subscription_tier,
            "end_date": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None
        }
    else:
        current_subscription = {
            "status": "NONE",
            "tier": "free",
            "end_date": None
        }

    return ServiceApplicationListResponse(
        applications=[
            ServiceApplicationResponse(
                id=app.id,
                applicant_email=app.applicant_email,
                plan_type=app.plan_type,
                plan_name_ko=ENTERPRISE_PLANS.get(app.plan_type, {}).get("name_ko", app.plan_type),
                plan_amount=app.plan_amount,
                status=app.status,
                subscription_start_date=app.subscription_start_date,
                subscription_end_date=app.subscription_end_date,
                created_at=app.created_at,
                updated_at=app.updated_at
            )
            for app in applications
        ],
        current_subscription=current_subscription
    )


# ============================================================================
# 사용자 API: 신청 취소
# ============================================================================

@router.delete("/{application_id}")
async def cancel_application(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """서비스 이용신청 취소 (PENDING 상태에서만 가능)"""
    try:
        app_uuid = uuid_module.UUID(application_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 신청 ID입니다."
        )

    result = await db.execute(
        select(ServiceApplication)
        .where(ServiceApplication.id == app_uuid)
        .where(ServiceApplication.user_id == current_user.id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신청을 찾을 수 없습니다."
        )

    if application.status != ApplicationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 처리된 신청은 취소할 수 없습니다."
        )

    application.status = ApplicationStatus.CANCELLED.value
    application.updated_at = datetime.utcnow()

    await db.commit()

    logger.info(f"Service application cancelled: {application.id} by user {current_user.email}")

    return {"message": "신청이 취소되었습니다."}
