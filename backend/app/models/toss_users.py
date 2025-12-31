"""
토스 로그인 사용자 모델 (앱인토스용)
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class TossUser(Base):
    """
    토스 로그인 사용자 테이블
    앱인토스에서 토스 로그인한 사용자 정보
    """
    __tablename__ = "toss_users"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 토스 사용자 식별자 (토스 API에서 제공)
    toss_user_key = Column(String(100), unique=True, nullable=False, index=True)

    # 사용자 정보 (암호화된 상태로 저장)
    name = Column(String(100), nullable=True)  # 복호화된 이름
    phone = Column(String(20), nullable=True)  # 복호화된 전화번호
    email = Column(String(255), nullable=True)  # 복호화된 이메일

    # 이용권 (credits)
    credits = Column(Integer, default=0, nullable=False)

    # 토큰 정보
    access_token = Column(Text, nullable=True)  # 암호화 저장 권장
    refresh_token = Column(Text, nullable=True)  # 암호화 저장 권장
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # 상태
    is_active = Column(Boolean, default=True, nullable=False)

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    transactions = relationship("CreditTransaction", back_populates="user", lazy="dynamic")
    report_views = relationship("ReportView", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<TossUser(id={self.id}, toss_user_key='{self.toss_user_key}', credits={self.credits})>"


class CreditTransaction(Base):
    """
    이용권 거래 내역 테이블
    이용권 구매, 사용, 환불 등 모든 거래 기록
    """
    __tablename__ = "credit_transactions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 사용자 참조
    user_id = Column(UUID(as_uuid=True), ForeignKey("toss_users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 거래 유형
    transaction_type = Column(String(20), nullable=False)  # 'purchase', 'use', 'refund', 'bonus'

    # 금액
    amount = Column(Integer, nullable=False)  # 양수: 충전/환불, 음수: 사용
    balance_after = Column(Integer, nullable=False)  # 거래 후 잔액

    # 결제 정보 (구매 시)
    product_id = Column(String(50), nullable=True)  # 상품 ID (report_1, report_10, report_30)
    order_id = Column(String(100), nullable=True, index=True)  # 토스 인앱결제 주문 ID
    payment_amount = Column(Integer, nullable=True)  # 결제 금액 (원)
    payment_method = Column(String(30), nullable=True)  # 결제 수단 (toss_iap, in_app_purchase, etc)
    receipt_data = Column(Text, nullable=True)  # 영수증 데이터

    # 사용 정보 (리포트 조회 시)
    company_id = Column(String(20), nullable=True)  # 조회한 기업 코드
    company_name = Column(String(200), nullable=True)  # 조회한 기업명

    # 메타데이터
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    user = relationship("TossUser", back_populates="transactions")

    __table_args__ = (
        Index('ix_credit_transactions_user_type', 'user_id', 'transaction_type'),
        Index('ix_credit_transactions_created', 'created_at'),
    )

    def __repr__(self):
        return f"<CreditTransaction(id={self.id}, type='{self.transaction_type}', amount={self.amount})>"


class ReportView(Base):
    """
    리포트 조회 기록 테이블
    동일 기업 재조회 시 이용권 중복 차감 방지
    """
    __tablename__ = "report_views"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 사용자 참조
    user_id = Column(UUID(as_uuid=True), ForeignKey("toss_users.id", ondelete="CASCADE"), nullable=False)

    # 기업 정보
    company_id = Column(String(20), nullable=False)  # corp_code
    company_name = Column(String(200), nullable=True)

    # 메타데이터
    first_viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_viewed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    view_count = Column(Integer, default=1, nullable=False)

    # Relationship
    user = relationship("TossUser", back_populates="report_views")

    __table_args__ = (
        # 사용자-기업 조합 유니크 (중복 차감 방지)
        Index('ix_report_views_user_company', 'user_id', 'company_id', unique=True),
    )

    def __repr__(self):
        return f"<ReportView(user_id={self.user_id}, company_id='{self.company_id}')>"


class CreditProduct(Base):
    """
    이용권 상품 테이블
    """
    __tablename__ = "credit_products"

    # Primary Key
    id = Column(String(50), primary_key=True)  # report_1, report_10, report_30

    # 상품 정보
    name = Column(String(100), nullable=False)  # 리포트 1건, 리포트 10건
    credits = Column(Integer, nullable=False)  # 충전되는 이용권 수
    price = Column(Integer, nullable=False)  # 가격 (원)

    # 표시 정보
    badge = Column(String(20), nullable=True)  # 추천, 최저가
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # 플랫폼별 상품 ID
    toss_sku = Column(String(100), nullable=True)  # 토스 인앱결제 SKU
    apple_product_id = Column(String(100), nullable=True)
    google_product_id = Column(String(100), nullable=True)

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<CreditProduct(id='{self.id}', name='{self.name}', price={self.price})>"
