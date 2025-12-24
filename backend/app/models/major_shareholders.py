"""
대주주 모델

기업의 대주주 현황 정보
"""
from sqlalchemy import Column, String, BigInteger, Numeric, Boolean, Date, Integer, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class MajorShareholder(Base):
    """
    대주주 테이블

    기업의 주요 주주 정보 (사업보고서 기준)
    """
    __tablename__ = "major_shareholders"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 회사 정보 (FK)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)

    # 주주 정보
    shareholder_name = Column(String(200), nullable=False, comment="주주명")
    shareholder_name_normalized = Column(String(200), nullable=True, comment="정규화된 주주명")
    shareholder_type = Column(String(30), nullable=True, comment="주주 유형 (개인/법인)")

    # 지분 정보
    share_count = Column(BigInteger, nullable=True, comment="보유 주식 수")
    share_ratio = Column(Numeric(10, 4), nullable=True, comment="지분율(%)")

    # 주주 특성
    is_largest_shareholder = Column(Boolean, default=False, comment="최대주주 여부")
    is_related_party = Column(Boolean, default=False, comment="특수관계인 여부")

    # 보고 기준
    report_date = Column(Date, nullable=True, comment="기준일")
    report_year = Column(Integer, nullable=True, comment="보고 연도")
    report_quarter = Column(Integer, nullable=True, comment="보고 분기")

    # 변동 정보
    change_reason = Column(String(500), nullable=True, comment="변동 사유")
    previous_share_ratio = Column(Numeric(10, 4), nullable=True, comment="이전 지분율(%)")

    # 출처 정보
    source_rcept_no = Column(String(20), nullable=True, comment="출처 공시 번호")

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", backref="major_shareholders")

    # 인덱스 및 제약조건
    __table_args__ = (
        # 유니크 제약조건: 동일 회사, 동일 주주, 동일 보고기간은 1건만 존재
        UniqueConstraint('company_id', 'shareholder_name', 'report_year', 'report_quarter', name='uq_major_shareholder'),
        # 인덱스
        Index('idx_shareholder_company', 'company_id'),
        Index('idx_shareholder_name', 'shareholder_name_normalized'),
        Index('idx_shareholder_report', 'report_date'),
        Index('idx_shareholder_year_quarter', 'report_year', 'report_quarter'),
    )

    def __repr__(self):
        return f"<MajorShareholder(name='{self.shareholder_name}', ratio={self.share_ratio}%)>"
