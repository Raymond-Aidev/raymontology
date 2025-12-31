"""
Stock Price 모델 - 월별 종가 데이터
"""
from sqlalchemy import Column, String, Float, Date, DateTime, Index, ForeignKey, UniqueConstraint, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class StockPrice(Base):
    """
    주가 테이블 - 월별 종가 데이터

    2022년 1월부터 현재까지 매월 말일 종가 저장
    상장사만 대상 (ticker가 있는 companies)
    """
    __tablename__ = "stock_prices"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key - companies 테이블 연결
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # 날짜 정보
    price_date = Column(Date, nullable=False)           # 월말 기준일 (2022-01-31)
    year_month = Column(String(7), nullable=False)      # "2022-01" (조회 편의)

    # 가격 정보 (원 단위)
    close_price = Column(Float, nullable=False)         # 종가
    open_price = Column(Float, nullable=True)           # 시가 (월 시작일)
    high_price = Column(Float, nullable=True)           # 월중 최고가
    low_price = Column(Float, nullable=True)            # 월중 최저가

    # 거래량
    volume = Column(BigInteger, nullable=True)          # 월간 거래량

    # 변동률 (전월 대비)
    change_rate = Column(Float, nullable=True)          # 전월 대비 변동률 (%)

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship
    company = relationship("Company", back_populates="stock_prices")

    # 제약조건 및 인덱스
    __table_args__ = (
        # 동일 기업의 동일 월 데이터는 하나만 존재
        UniqueConstraint('company_id', 'year_month', name='uq_stock_price_company_month'),
        # 조회 최적화 인덱스
        Index('idx_stock_price_company_date', 'company_id', 'price_date'),
        Index('idx_stock_price_year_month', 'year_month'),
    )

    def __repr__(self):
        return f"<StockPrice(company_id={self.company_id}, year_month='{self.year_month}', close={self.close_price})>"

    def to_dict(self):
        """API 응답용 딕셔너리 변환"""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "price_date": self.price_date.isoformat() if self.price_date else None,
            "year_month": self.year_month,
            "close_price": self.close_price,
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "volume": self.volume,
            "change_rate": self.change_rate,
        }
