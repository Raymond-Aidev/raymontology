"""
Subscription 모델 - 결제 이력 및 구독 관리
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


class SubscriptionTier(str, enum.Enum):
    """이용권 등급"""
    FREE = "free"
    TRIAL = "trial"  # 회원가입 시 1회 무료 체험
    LIGHT = "light"  # 3,000원/월
    MAX = "max"      # 30,000원/월


class PaymentStatus(str, enum.Enum):
    """결제 상태"""
    PENDING = "pending"      # 결제 대기
    COMPLETED = "completed"  # 결제 완료
    FAILED = "failed"        # 결제 실패
    CANCELLED = "cancelled"  # 결제 취소
    REFUNDED = "refunded"    # 환불


class UserQueryUsage(Base):
    """
    사용자 조회 횟수 추적 테이블
    월별로 조회 횟수를 기록
    """
    __tablename__ = "user_query_usage"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 사용자 정보
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 조회 기간 (YYYY-MM 형식)
    year_month = Column(String(7), nullable=False, index=True)  # 예: '2025-01'

    # 조회 횟수
    query_count = Column(Integer, default=0, nullable=False)    # 회사 상세 조회
    report_count = Column(Integer, default=0, nullable=False)   # 리포트 조회

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Unique constraint: 사용자별 월별 1개 레코드
    __table_args__ = (
        UniqueConstraint('user_id', 'year_month', name='uq_user_query_usage_user_month'),
    )

    # Relationship
    user = relationship("User", backref="query_usage")

    def __repr__(self):
        return f"<UserQueryUsage(user_id={self.user_id}, year_month='{self.year_month}', query_count={self.query_count})>"


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


class CompanyViewHistory(Base):
    """
    사용자 기업 조회 기록 테이블
    조회한 기업 목록을 저장하여 나중에 다시 볼 수 있도록 함
    """
    __tablename__ = "company_view_history"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 사용자 정보
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 기업 정보
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # 조회 당시 정보 스냅샷 (기업 삭제 시에도 표시 가능하도록)
    company_name = Column(String(200), nullable=True)
    ticker = Column(String(20), nullable=True)
    market = Column(String(20), nullable=True)

    # 조회 시간
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 인덱스: 사용자별 최근 조회 순 정렬
    __table_args__ = (
        Index('ix_company_view_history_user_viewed', 'user_id', 'viewed_at'),
    )

    # Relationships
    user = relationship("User", backref="view_history")
    company = relationship("Company", backref="view_history")

    def __repr__(self):
        return f"<CompanyViewHistory(user_id={self.user_id}, company_name='{self.company_name}', viewed_at={self.viewed_at})>"


# 이용권별 조회 제한 설정
SUBSCRIPTION_LIMITS = {
    "free": {
        "monthly_queries": 0,       # 조회 불가 (비로그인은 검색만 가능)
        "monthly_reports": 0,       # 리포트 불가
    },
    "trial": {
        "monthly_queries": 1,       # 회원가입 시 1회 무료 체험
        "monthly_reports": 0,       # 리포트 불가
    },
    "light": {
        "monthly_queries": 30,      # 월 30건 조회
        "monthly_reports": 30,      # 월 30건 리포트
    },
    "max": {
        "monthly_queries": -1,      # 무제한 (-1)
        "monthly_reports": -1,      # 무제한 (-1)
    }
}


# 이용권 플랜 정보 (상수)
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free",
        "name_ko": "무료",
        "price": 0,
        "price_display": "무료",
        "features": [
            "회사 검색",
            "로그인 필요"
        ]
    },
    "trial": {
        "name": "Trial",
        "name_ko": "체험",
        "price": 0,
        "price_display": "무료",
        "features": [
            "회원가입 시 1회 무료 체험",
            "기업 관계도 분석 1회"
        ]
    },
    "light": {
        "name": "Light",
        "name_ko": "라이트",
        "price": 3000,
        "price_display": "3,000원/월",
        "features": [
            "월 30건 조회",
            "리스크 분석 리포트",
            "CB 네트워크 분석",
            "임원 경력 추적"
        ]
    },
    "max": {
        "name": "Max",
        "name_ko": "맥스",
        "price": 30000,
        "price_display": "30,000원/월",
        "features": [
            "무제한 조회",
            "Light 플랜 모든 기능",
            "API 액세스",
            "대량 조회 기능",
            "맞춤 알림 설정",
            "전담 지원"
        ]
    }
}
