"""
서비스 이용신청 모델
- 수동 입금확인 방식의 엔터프라이즈 서비스 이용신청 관리
"""
from sqlalchemy import Column, String, Integer, DateTime, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum


from app.database import Base


class ApplicationStatus(str, enum.Enum):
    """이용신청 상태"""
    PENDING = "PENDING"                    # 신청완료 (입금대기)
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"  # 입금확인
    APPROVED = "APPROVED"                  # 승인완료 (이용권 부여)
    REJECTED = "REJECTED"                  # 거절
    CANCELLED = "CANCELLED"                # 취소


class PlanType(str, enum.Enum):
    """이용신청 플랜 타입"""
    ONE_MONTH = "1_MONTH"      # 1개월 - 300,000원
    SIX_MONTHS = "6_MONTHS"    # 6개월 - 1,500,000원
    ONE_YEAR = "1_YEAR"        # 1년 - 3,000,000원


# 플랜별 금액 및 기간 설정
ENTERPRISE_PLANS = {
    PlanType.ONE_MONTH.value: {
        "name_ko": "1개월",
        "price": 300000,
        "duration_days": 30,
        "discount": None,
    },
    PlanType.SIX_MONTHS.value: {
        "name_ko": "6개월",
        "price": 1500000,
        "duration_days": 180,
        "discount": "17%",
    },
    PlanType.ONE_YEAR.value: {
        "name_ko": "1년",
        "price": 3000000,
        "duration_days": 365,
        "discount": "17%",
    },
}


class ServiceApplication(Base):
    """
    서비스 이용신청 테이블
    수동 입금 확인 방식으로 엔터프라이즈 고객 관리
    """
    __tablename__ = "service_applications"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 신청자 정보
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    applicant_email = Column(String(255), nullable=False)

    # 사업자등록증 파일 (Base64 인코딩)
    business_registration_file_content = Column(Text, nullable=True)  # Base64 데이터
    business_registration_file_name = Column(String(255), nullable=True)
    business_registration_mime_type = Column(String(50), nullable=True)

    # 신청 플랜 및 금액
    plan_type = Column(String(20), nullable=False)  # '1_MONTH', '6_MONTHS', '1_YEAR'
    plan_amount = Column(Integer, nullable=False)   # 금액 (원)

    # 상태 관리
    status = Column(
        String(20),
        default=ApplicationStatus.PENDING.value,
        nullable=False,
        index=True
    )

    # 처리 정보
    admin_memo = Column(Text, nullable=True)
    processed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # 이용권 정보 (승인 시 설정)
    subscription_start_date = Column(Date, nullable=True)
    subscription_end_date = Column(Date, nullable=True)

    # 타임스탬프
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id],
        backref="service_applications"
    )
    processor = relationship(
        "User",
        foreign_keys=[processed_by],
        backref="processed_applications"
    )

    def __repr__(self):
        return (
            f"<ServiceApplication("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"plan_type='{self.plan_type}', "
            f"status='{self.status}'"
            f")>"
        )

    @property
    def plan_info(self) -> dict:
        """플랜 정보 반환"""
        return ENTERPRISE_PLANS.get(self.plan_type, {})

    @property
    def plan_name_ko(self) -> str:
        """플랜 한글명"""
        return self.plan_info.get("name_ko", self.plan_type)

    @property
    def duration_days(self) -> int:
        """플랜 기간 (일)"""
        return self.plan_info.get("duration_days", 30)
