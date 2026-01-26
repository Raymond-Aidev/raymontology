"""
DailyStockPrice 모델 - KRX 일별 종가 데이터
"""
from sqlalchemy import Column, Integer, BigInteger, Date, DateTime, Index, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class DailyStockPrice(Base):
    """
    일별 주가 테이블 - KRX 정보데이터시스템에서 수집

    매일 10:00 KST에 전일 종가 수집
    M&A 타겟 분석을 위한 시가총액 계산에 사용
    """
    __tablename__ = "daily_stock_prices"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # 날짜
    price_date = Column(Date, nullable=False, comment='거래일')

    # 가격 정보 (원 단위)
    close_price = Column(Integer, nullable=False, comment='종가')
    open_price = Column(Integer, nullable=True, comment='시가')
    high_price = Column(Integer, nullable=True, comment='고가')
    low_price = Column(Integer, nullable=True, comment='저가')

    # 거래 정보
    volume = Column(BigInteger, nullable=True, comment='거래량')
    trading_value = Column(BigInteger, nullable=True, comment='거래대금')

    # KRX 제공 데이터
    market_cap = Column(BigInteger, nullable=True, comment='시가총액 (KRX 제공)')
    listed_shares = Column(BigInteger, nullable=True, comment='상장주식수 (KRX 제공)')

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    company = relationship("Company", backref="daily_stock_prices")

    # 제약조건 및 인덱스
    __table_args__ = (
        UniqueConstraint('company_id', 'price_date', name='uq_daily_stock_price_company_date'),
        Index('idx_daily_stock_prices_date', 'price_date'),
        Index('idx_daily_stock_prices_company', 'company_id'),
    )

    def __repr__(self):
        return f"<DailyStockPrice(company_id={self.company_id}, date={self.price_date}, close={self.close_price})>"

    def to_dict(self):
        """API 응답용 딕셔너리 변환"""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "price_date": self.price_date.isoformat() if self.price_date else None,
            "close_price": self.close_price,
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "volume": self.volume,
            "trading_value": self.trading_value,
            "market_cap": self.market_cap,
            "listed_shares": self.listed_shares,
        }
