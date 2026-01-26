"""
FinancialSnapshot 모델 - M&A 타겟 분석용 일별 스냅샷
"""
from sqlalchemy import Column, Integer, BigInteger, String, Date, DateTime, Numeric, Index, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from decimal import Decimal

from app.database import Base


class FinancialSnapshot(Base):
    """
    일별 재무 스냅샷 테이블 - M&A 타겟 분석용

    매일 10:00 KST에 생성
    - 전일 종가 (KRX)
    - 발행주식수 (DART/companies)
    - 계산된 시가총액
    - 최신 재무 지표 (분기별 갱신)
    - M&A 타겟 점수
    """
    __tablename__ = "financial_snapshots"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # 스냅샷 일자
    snapshot_date = Column(Date, nullable=False, comment='스냅샷 일자')

    # 주가 데이터 (KRX)
    close_price = Column(Integer, nullable=True, comment='전일 종가')
    market_cap_krx = Column(BigInteger, nullable=True, comment='KRX 제공 시가총액')

    # 발행주식수 (DART/companies)
    shares_outstanding = Column(BigInteger, nullable=True, comment='유통주식수')

    # 계산된 시가총액
    market_cap_calculated = Column(BigInteger, nullable=True, comment='계산된 시가총액 (종가×주식수)')

    # 재무 지표 (분기별 갱신, 최신 값)
    cash_and_equivalents = Column(BigInteger, nullable=True, comment='현금 및 현금성자산')
    short_term_investments = Column(BigInteger, nullable=True, comment='단기금융상품')
    total_liquid_assets = Column(BigInteger, nullable=True, comment='현금성 유동자산 합계')
    tangible_assets = Column(BigInteger, nullable=True, comment='유형자산')
    revenue = Column(BigInteger, nullable=True, comment='매출액')
    operating_profit = Column(BigInteger, nullable=True, comment='영업이익')

    # YoY 증감율 (%)
    tangible_assets_growth = Column(Numeric(10, 2), nullable=True, comment='유형자산 증가율')
    revenue_growth = Column(Numeric(10, 2), nullable=True, comment='매출 증감율')
    operating_profit_growth = Column(Numeric(10, 2), nullable=True, comment='영업이익 증감율')

    # M&A 타겟 점수
    ma_target_score = Column(Numeric(5, 2), nullable=True, comment='M&A 타겟 점수 (0-100)')
    ma_target_grade = Column(String(5), nullable=True, comment='M&A 타겟 등급')
    ma_target_factors = Column(JSONB, nullable=True, comment='M&A 타겟 요소별 점수')

    # 메타
    fiscal_year = Column(Integer, nullable=True, comment='재무데이터 기준 사업연도')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    company = relationship("Company", backref="financial_snapshots")

    # 제약조건 및 인덱스
    __table_args__ = (
        UniqueConstraint('company_id', 'snapshot_date', name='uq_financial_snapshot_company_date'),
        Index('idx_financial_snapshots_date', 'snapshot_date'),
        Index('idx_financial_snapshots_company', 'company_id'),
        Index('idx_financial_snapshots_ma_score', 'ma_target_score'),
    )

    def __repr__(self):
        return f"<FinancialSnapshot(company_id={self.company_id}, date={self.snapshot_date}, score={self.ma_target_score})>"

    def to_dict(self):
        """API 응답용 딕셔너리 변환"""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "close_price": self.close_price,
            "market_cap_krx": self.market_cap_krx,
            "shares_outstanding": self.shares_outstanding,
            "market_cap_calculated": self.market_cap_calculated,
            "cash_and_equivalents": self.cash_and_equivalents,
            "short_term_investments": self.short_term_investments,
            "total_liquid_assets": self.total_liquid_assets,
            "tangible_assets": self.tangible_assets,
            "revenue": self.revenue,
            "operating_profit": self.operating_profit,
            "tangible_assets_growth": float(self.tangible_assets_growth) if self.tangible_assets_growth else None,
            "revenue_growth": float(self.revenue_growth) if self.revenue_growth else None,
            "operating_profit_growth": float(self.operating_profit_growth) if self.operating_profit_growth else None,
            "ma_target_score": float(self.ma_target_score) if self.ma_target_score else None,
            "ma_target_grade": self.ma_target_grade,
            "ma_target_factors": self.ma_target_factors,
            "fiscal_year": self.fiscal_year,
        }

    @staticmethod
    def calculate_grade(score: float) -> str:
        """M&A 타겟 점수에서 등급 계산"""
        if score is None:
            return None
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C+"
        elif score >= 40:
            return "C"
        else:
            return "D"
