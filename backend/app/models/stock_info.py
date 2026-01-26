"""
StockInfo 모델 - DART 발행주식수 이력
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Index, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class StockInfo(Base):
    """
    발행주식수 이력 테이블 - DART stockTotqySttus API에서 수집

    사업연도별 발행주식수 정보 저장
    시가총액 계산에 사용 (종가 × 유통주식수)
    """
    __tablename__ = "stock_info"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # 기준 연도
    fiscal_year = Column(Integer, nullable=False, comment='사업연도')
    report_code = Column(String(10), nullable=True, comment='보고서 코드 (11011: 사업보고서)')

    # 주식 수
    common_shares = Column(BigInteger, nullable=True, comment='보통주 발행주식총수')
    preferred_shares = Column(BigInteger, nullable=True, comment='우선주 발행주식총수')
    total_shares = Column(BigInteger, nullable=True, comment='발행주식총수')
    treasury_shares = Column(BigInteger, nullable=True, comment='자기주식수')
    outstanding_shares = Column(BigInteger, nullable=True, comment='유통주식수 (발행-자기주식)')

    # 메타데이터
    data_source = Column(String(50), nullable=True, default='DART', comment='데이터 소스')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship
    company = relationship("Company", backref="stock_infos")

    # 제약조건 및 인덱스
    __table_args__ = (
        UniqueConstraint('company_id', 'fiscal_year', name='uq_stock_info_company_year'),
        Index('idx_stock_info_company', 'company_id'),
    )

    def __repr__(self):
        return f"<StockInfo(company_id={self.company_id}, year={self.fiscal_year}, outstanding={self.outstanding_shares})>"

    def to_dict(self):
        """API 응답용 딕셔너리 변환"""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "fiscal_year": self.fiscal_year,
            "report_code": self.report_code,
            "common_shares": self.common_shares,
            "preferred_shares": self.preferred_shares,
            "total_shares": self.total_shares,
            "treasury_shares": self.treasury_shares,
            "outstanding_shares": self.outstanding_shares,
            "data_source": self.data_source,
        }
