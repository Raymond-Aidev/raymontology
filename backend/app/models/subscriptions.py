"""
Subscription 모델 - 결제 이력 및 구독 관리
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


class SubscriptionTier(str, enum.Enum):
    """이용권 등급"""
    FREE = "free"
    LIGHT = "light"  # 3,000원/월
    MAX = "max"      # 30,000원/월


class PaymentStatus(str, enum.Enum):
    """결제 상태"""
    PENDING = "pending"      # 결제 대기
    COMPLETED = "completed"  # 결제 완료
    FAILED = "failed"        # 결제 실패
    CANCELLED = "cancelled"  # 결제 취소
    REFUNDED = "refunded"    # 환불


class SubscriptionPayment(Base):
    """
    결제 이력 테이블
    """
    __tablename__ = "subscription_payments"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 사용자 정보
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 이용권 정보
    tier = Column(String(20), nullable=False)  # 'light' or 'max'
    amount = Column(Integer, nullable=False)   # 결제 금액 (원)
    duration_days = Column(Integer, default=30, nullable=False)  # 이용 기간 (일)

    # 결제 정보
    payment_method = Column(String(50), nullable=True)  # 'card', 'bank_transfer', 'admin_grant' 등
    pg_provider = Column(String(50), nullable=True)     # 'tosspayments', 'portone', 'nice' 등
    pg_transaction_id = Column(String(255), nullable=True, index=True)  # PG사 거래 ID
    pg_order_id = Column(String(255), nullable=True, index=True)        # 주문 ID

    # 상태
    status = Column(String(20), default=PaymentStatus.PENDING.value, nullable=False)

    # 메모 (관리자 수동 부여 시 사유 등)
    memo = Column(String(500), nullable=True)

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 결제 완료 시간

    # Relationship
    user = relationship("User", backref="subscription_payments")

    def __repr__(self):
        return f"<SubscriptionPayment(id={self.id}, user_id={self.user_id}, tier='{self.tier}', amount={self.amount}, status='{self.status}')>"


# 이용권 플랜 정보 (상수)
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free",
        "name_ko": "무료",
        "price": 0,
        "price_display": "무료",
        "features": [
            "기본 리스크 조회",
            "회사 검색",
            "월 10회 상세 리포트"
        ]
    },
    "light": {
        "name": "Light",
        "name_ko": "라이트",
        "price": 3000,
        "price_display": "3,000원/월",
        "features": [
            "무제한 리스크 조회",
            "CB 네트워크 분석",
            "임원 경력 추적",
            "월 100회 상세 리포트",
            "이메일 알림"
        ]
    },
    "max": {
        "name": "Max",
        "name_ko": "맥스",
        "price": 30000,
        "price_display": "30,000원/월",
        "features": [
            "Light 플랜 모든 기능",
            "무제한 상세 리포트",
            "API 액세스",
            "대량 조회 기능",
            "맞춤 알림 설정",
            "전담 지원"
        ]
    }
}
