"""
Company 모델
"""
from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Company(Base):
    """
    기업 테이블

    상장사, 비상장사 모두 포함
    """
    __tablename__ = "companies"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 기본 정보
    corp_code = Column(String(8), unique=True, nullable=True, index=True)  # DART 기업 고유번호
    ticker = Column(String(20), unique=True, nullable=True, index=True)  # 상장사만
    name = Column(String(200), nullable=False, index=True)
    name_en = Column(String(200), nullable=True)
    business_number = Column(String(20), unique=True, nullable=True)

    # 분류
    sector = Column(String(100), nullable=True, index=True)
    industry = Column(String(100), nullable=True)
    market = Column(String(20), nullable=True, index=True)  # KOSPI, KOSDAQ, KONEX
    listing_status = Column(String(20), nullable=True, default='LISTED')  # LISTED, UNLISTED, ETF

    # 재무 지표
    market_cap = Column(Float, nullable=True)  # 시가총액
    revenue = Column(Float, nullable=True)  # 매출
    net_income = Column(Float, nullable=True)  # 순이익
    total_assets = Column(Float, nullable=True)  # 총자산

    # 리스크 지표
    ownership_concentration = Column(Float, nullable=True)  # 소유 집중도 (0~1)
    affiliate_transaction_ratio = Column(Float, nullable=True)  # 특수관계자 거래 비율
    cb_issuance_count = Column(Float, default=0)  # CB 발행 횟수

    # 온톨로지 연결
    ontology_object_id = Column(String(50), unique=True, nullable=True, index=True)

    # 추가 속성 (유연성)
    properties = Column(JSONB, default={})

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    disclosures = relationship("Disclosure", back_populates="company")

    # 인덱스
    __table_args__ = (
        Index('idx_company_name_trigram', 'name', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'}),
        Index('idx_company_ticker', 'ticker'),
        Index('idx_company_market_sector', 'market', 'sector'),
    )

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}', ticker='{self.ticker}')>"
