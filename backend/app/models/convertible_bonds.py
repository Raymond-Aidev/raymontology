"""
Convertible Bond (전환사채) 모델

회사가 발행한 전환사채 정보를 저장
"""
from sqlalchemy import Column, String, Float, DateTime, Date, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class ConvertibleBond(Base):
    """
    전환사채 테이블

    회사가 발행한 전환사채(CB) 정보
    """
    __tablename__ = "convertible_bonds"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 발행 회사
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True, comment="발행 회사 ID")

    # 채권 정보
    bond_name = Column(String(200), nullable=True, comment="채권명")
    bond_type = Column(String(50), nullable=True, index=True, comment="채권 유형")

    # 발행 정보
    issue_date = Column(Date, nullable=True, index=True, comment="발행일")
    maturity_date = Column(Date, nullable=True, index=True, comment="만기일")
    issue_amount = Column(Float, nullable=True, comment="발행금액 (원)")
    interest_rate = Column(Float, nullable=True, comment="이자율 (%)")

    # 전환 정보
    conversion_price = Column(Float, nullable=True, comment="전환가액 (원)")
    conversion_ratio = Column(Float, nullable=True, comment="전환비율 (%)")
    conversion_start_date = Column(Date, nullable=True, comment="전환 시작일")
    conversion_end_date = Column(Date, nullable=True, comment="전환 종료일")

    # 상환 정보
    redemption_price = Column(Float, nullable=True, comment="상환가액")
    early_redemption_date = Column(Date, nullable=True, comment="조기상환일")
    outstanding_amount = Column(Float, nullable=True, comment="미상환잔액")
    converted_amount = Column(Float, nullable=True, comment="전환된 금액")
    redeemed_amount = Column(Float, nullable=True, comment="상환된 금액")

    # 상태
    status = Column(String(20), nullable=True, index=True, comment="상태")

    # 공시 원본 정보
    source_disclosure_id = Column(String(36), nullable=True, comment="원본 공시 ID")
    source_date = Column(String(8), nullable=True, index=True, comment="공시 날짜 (YYYYMMDD)")
    ontology_object_id = Column(String(50), nullable=True, unique=True, index=True, comment="온톨로지 객체 ID")

    # 추가 속성 (유연한 확장을 위해)
    properties = Column(JSONB, default={}, comment="추가 정보 (JSON)")

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 자금사용 목적
    use_of_proceeds = Column(Text, nullable=True, comment="자금사용 목적")

    # Relationships
    company = relationship("Company", foreign_keys=[company_id])
    subscribers = relationship("CBSubscriber", back_populates="convertible_bond", cascade="all, delete-orphan")

    # 인덱스
    __table_args__ = (
        # 중복 방지
        Index('idx_unique_cb', 'company_id', 'bond_name', 'issue_date', unique=True),
    )

    def __repr__(self):
        return f"<ConvertibleBond(id={self.id}, company={self.company_id}, name='{self.bond_name}')>"
