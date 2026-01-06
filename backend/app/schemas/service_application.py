"""
서비스 이용신청 스키마
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime, date
from uuid import UUID


# 플랜 타입
PlanTypeEnum = Literal["1_MONTH", "6_MONTHS", "1_YEAR"]

# 상태 타입
ApplicationStatusEnum = Literal[
    "PENDING",           # 신청완료 (입금대기)
    "PAYMENT_CONFIRMED", # 입금확인
    "APPROVED",          # 승인완료
    "REJECTED",          # 거절
    "CANCELLED"          # 취소
]


# ============================================================
# 플랜 정보
# ============================================================
class EnterprisePlanInfo(BaseModel):
    """엔터프라이즈 플랜 정보"""
    plan_type: PlanTypeEnum
    name_ko: str
    price: int
    price_display: str
    duration_days: int
    discount: Optional[str] = None


class EnterprisePlansResponse(BaseModel):
    """엔터프라이즈 플랜 목록 응답"""
    plans: List[EnterprisePlanInfo]


# ============================================================
# 서비스 이용신청 - 사용자용
# ============================================================
class ServiceApplicationCreate(BaseModel):
    """서비스 이용신청 생성 요청"""
    applicant_email: EmailStr = Field(..., description="신청자 이메일")
    plan_type: PlanTypeEnum = Field(..., description="신청 플랜")
    # 파일은 multipart/form-data로 별도 처리


class ServiceApplicationResponse(BaseModel):
    """서비스 이용신청 응답"""
    id: UUID
    applicant_email: str
    plan_type: str
    plan_name_ko: str
    plan_amount: int
    status: ApplicationStatusEnum
    subscription_start_date: Optional[date] = None
    subscription_end_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceApplicationListResponse(BaseModel):
    """서비스 이용신청 목록 응답 (사용자용)"""
    applications: List[ServiceApplicationResponse]
    current_subscription: Optional[dict] = None  # 현재 이용권 상태


class ServiceApplicationCreateResult(BaseModel):
    """서비스 이용신청 생성 결과"""
    id: UUID
    status: ApplicationStatusEnum
    plan_type: str
    plan_amount: int
    created_at: datetime
    message: str


# ============================================================
# 서비스 이용신청 - 관리자용
# ============================================================
class ServiceApplicationAdminResponse(BaseModel):
    """서비스 이용신청 응답 (관리자용)"""
    id: UUID
    user_id: UUID
    applicant_email: str
    plan_type: str
    plan_name_ko: str
    plan_amount: int
    status: ApplicationStatusEnum
    has_business_registration: bool  # 사업자등록증 첨부 여부
    business_registration_file_name: Optional[str] = None
    admin_memo: Optional[str] = None
    processed_by: Optional[UUID] = None
    processed_at: Optional[datetime] = None
    subscription_start_date: Optional[date] = None
    subscription_end_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceApplicationAdminListResponse(BaseModel):
    """서비스 이용신청 목록 응답 (관리자용)"""
    applications: List[ServiceApplicationAdminResponse]
    total: int
    page: int
    total_pages: int


class ServiceApplicationStatusUpdate(BaseModel):
    """서비스 이용신청 상태 변경 요청"""
    status: Literal["PAYMENT_CONFIRMED", "APPROVED", "REJECTED"]
    admin_memo: Optional[str] = None
    subscription_start_date: Optional[date] = None  # APPROVED 시 필수
    subscription_end_date: Optional[date] = None    # APPROVED 시 필수


class ServiceApplicationStatusUpdateResult(BaseModel):
    """서비스 이용신청 상태 변경 결과"""
    id: UUID
    status: ApplicationStatusEnum
    message: str


# ============================================================
# 입금 정보
# ============================================================
class PaymentBankInfo(BaseModel):
    """입금 계좌 정보"""
    company_name: str = "코넥트"
    business_number: str = "686-19-02309"
    bank_name: str = "카카오뱅크"
    account_number: str = "3333-31-9041159"
    account_holder: str = "코넥트 / 박재준"


class PaymentInfoResponse(BaseModel):
    """입금 안내 응답"""
    application_id: UUID
    plan_type: str
    plan_name_ko: str
    plan_amount: int
    plan_amount_display: str
    bank_info: PaymentBankInfo
    message: str = "신청이 완료되었습니다. 입금 안내 이메일을 확인해주세요."
