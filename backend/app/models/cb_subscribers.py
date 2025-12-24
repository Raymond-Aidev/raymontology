"""
CB 인수자 모델

전환사채 발행 대상자(인수자) 정보
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, Date, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class CBSubscriber(Base):
    """
    전환사채 인수자 테이블

    CB를 인수하는 개인/법인 정보 및 발행 회사와의 관계
    """
    __tablename__ = "cb_subscribers"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # CB 정보 (FK)
    cb_id = Column(UUID(as_uuid=True), ForeignKey('convertible_bonds.id', ondelete='CASCADE'), nullable=False, index=True)

    # 인수자 정보
    subscriber_name = Column(String(500), nullable=False, index=True, comment="인수자명")
    subscriber_type = Column(String(50), nullable=True, comment="인수자 유형")

    # 인수 정보
    subscription_amount = Column(Float, nullable=True, comment="인수 금액 (원)")
    subscription_quantity = Column(Float, nullable=True, comment="인수 수량")

    # 관계 정보 (DB 컬럼명과 일치)
    relationship_to_company = Column(String(200), nullable=True, comment="회사와의 관계")
    is_related_party = Column(String(10), nullable=True, comment="특수관계자 여부")
    selection_rationale = Column(String, nullable=True, comment="선정 사유")
    transaction_history = Column(String, nullable=True, comment="거래 내역")
    notes = Column(String, nullable=True, comment="비고")

    # 법인/단체 기본정보 (인수대상자)
    representative_name = Column(String(200), nullable=True, comment="대표이사(대표조합원) 성명")
    representative_share = Column(Float, nullable=True, comment="대표이사 지분율(%)")
    gp_name = Column(String(200), nullable=True, comment="업무집행자(업무집행조합원) 성명")
    gp_share = Column(Float, nullable=True, comment="업무집행자 지분율(%)")
    largest_shareholder_name = Column(String(200), nullable=True, comment="최대주주(최대출자자) 성명")
    largest_shareholder_share = Column(Float, nullable=True, comment="최대주주 지분율(%)")

    # 출처 정보
    source_disclosure_id = Column(String(20), nullable=True, comment="출처 공시 ID")
    source_date = Column(String(8), nullable=True, comment="출처 날짜")
    source_report_date = Column(Date, nullable=True, comment="보고서 날짜", index=True)

    # FK to related entities
    subscriber_officer_id = Column(UUID(as_uuid=True), ForeignKey('officers.id', ondelete='SET NULL'), nullable=True, index=True)
    subscriber_company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='SET NULL'), nullable=True, index=True)

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    convertible_bond = relationship("ConvertibleBond", back_populates="subscribers")

    # 인덱스 및 제약조건
    __table_args__ = (
        # 유니크 제약조건: 동일 CB에 동일 인수자는 1건만 존재
        UniqueConstraint('cb_id', 'subscriber_name', name='uq_cb_subscriber'),
        # 인덱스
        Index('idx_cb_subscribers_cb_id', 'cb_id'),
        Index('idx_cb_subscribers_name', 'subscriber_name'),
        Index('idx_cb_subscribers_related', 'is_related_party'),
        Index('idx_cb_subscribers_source', 'source_disclosure_id'),
    )

    def __repr__(self):
        return f"<CBSubscriber(subscriber_name='{self.subscriber_name}', amount={self.subscription_amount})>"
