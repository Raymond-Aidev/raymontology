"""
Financial Ratios 모델 - 재무건전성 평가 시스템

25개 재무비율을 6개 카테고리로 분류하여 종합 건전성 점수 산출
- 안정성 (Stability): 6개
- 수익성 (Profitability): 6개
- 성장성 (Growth): 4개
- 활동성 (Activity): 4개
- 현금흐름 (Cash Flow): 3개
- 레버리지 (Leverage): 4개
"""
from sqlalchemy import Column, String, BigInteger, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class FinancialRatios(Base):
    """
    재무비율 분석 결과 테이블

    financial_details 원본 데이터를 기반으로 25개 재무비율 계산.
    성장성 지표는 전기(fiscal_year - 1) 데이터 필요.
    """
    __tablename__ = "financial_ratios"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    financial_detail_id = Column(UUID(as_uuid=True), ForeignKey('financial_details.id', ondelete='SET NULL'), nullable=True)

    # Period information
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer, nullable=True)  # NULL=연간, 1-4=분기
    calculation_date = Column(DateTime(timezone=True), server_default=func.now())

    # ═══════════════════════════════════════════════════════════════
    # 안정성 지표 (Stability) - 6개
    # ═══════════════════════════════════════════════════════════════
    current_ratio = Column(Numeric(10, 2), nullable=True)           # 유동비율 (%)
    quick_ratio = Column(Numeric(10, 2), nullable=True)             # 당좌비율 (%)
    debt_ratio = Column(Numeric(10, 2), nullable=True)              # 부채비율 (%)
    equity_ratio = Column(Numeric(10, 2), nullable=True)            # 자기자본비율 (%)
    debt_dependency = Column(Numeric(10, 2), nullable=True)         # 차입금의존도 (%)
    non_current_ratio = Column(Numeric(10, 2), nullable=True)       # 비유동비율 (%)

    # ═══════════════════════════════════════════════════════════════
    # 수익성 지표 (Profitability) - 6개 + EBITDA
    # ═══════════════════════════════════════════════════════════════
    operating_margin = Column(Numeric(10, 2), nullable=True)        # 매출액영업이익률 (%)
    net_profit_margin = Column(Numeric(10, 2), nullable=True)       # 매출액순이익률 (%)
    roa = Column(Numeric(10, 2), nullable=True)                     # 총자산순이익률 (%)
    roe = Column(Numeric(10, 2), nullable=True)                     # 자기자본순이익률 (%)
    gross_margin = Column(Numeric(10, 2), nullable=True)            # 매출총이익률 (%)
    ebitda_margin = Column(Numeric(10, 2), nullable=True)           # EBITDA마진 (%)
    ebitda = Column(BigInteger, nullable=True)                      # EBITDA (절대값)

    # ═══════════════════════════════════════════════════════════════
    # 성장성 지표 (Growth) - 4개 ⭐전기 데이터 필요
    # ═══════════════════════════════════════════════════════════════
    revenue_growth = Column(Numeric(10, 2), nullable=True)          # 매출액증가율 (%)
    operating_income_growth = Column(Numeric(10, 2), nullable=True) # 영업이익증가율 (%)
    net_income_growth = Column(Numeric(10, 2), nullable=True)       # 순이익증가율 (%)
    total_assets_growth = Column(Numeric(10, 2), nullable=True)     # 총자산증가율 (%)
    growth_data_available = Column(Boolean, default=False)          # 전기 데이터 유무

    # ═══════════════════════════════════════════════════════════════
    # 활동성 지표 (Activity) - 4개 + 회수/보유기간
    # ═══════════════════════════════════════════════════════════════
    asset_turnover = Column(Numeric(10, 2), nullable=True)          # 총자산회전율 (회)
    receivables_turnover = Column(Numeric(10, 2), nullable=True)    # 매출채권회전율 (회)
    inventory_turnover = Column(Numeric(10, 2), nullable=True)      # 재고자산회전율 (회)
    payables_turnover = Column(Numeric(10, 2), nullable=True)       # 매입채무회전율 (회)
    receivables_days = Column(Numeric(10, 2), nullable=True)        # 매출채권회수기간 (일)
    inventory_days = Column(Numeric(10, 2), nullable=True)          # 재고자산보유기간 (일)
    payables_days = Column(Numeric(10, 2), nullable=True)           # 매입채무지급기간 (일)
    cash_conversion_cycle = Column(Numeric(10, 2), nullable=True)   # 현금전환주기 (일)

    # ═══════════════════════════════════════════════════════════════
    # 현금흐름 지표 (Cash Flow) - 3개 + FCF 마진
    # ═══════════════════════════════════════════════════════════════
    ocf_ratio = Column(Numeric(10, 2), nullable=True)               # 영업현금흐름비율 (%)
    ocf_interest_coverage = Column(Numeric(10, 2), nullable=True)   # 현금흐름이자보상배율 (배)
    free_cash_flow = Column(BigInteger, nullable=True)              # 잉여현금흐름 (원)
    fcf_margin = Column(Numeric(10, 2), nullable=True)              # FCF마진 (%)

    # ═══════════════════════════════════════════════════════════════
    # 레버리지 지표 (Leverage) - 4개 + 절대값
    # ═══════════════════════════════════════════════════════════════
    interest_coverage = Column(Numeric(10, 2), nullable=True)       # 이자보상배율 (배)
    ebitda_interest_coverage = Column(Numeric(10, 2), nullable=True)  # EBITDA이자보상배율 (배)
    net_debt_to_ebitda = Column(Numeric(10, 2), nullable=True)      # 순차입금/EBITDA (배)
    financial_expense_ratio = Column(Numeric(10, 2), nullable=True) # 금융비용부담률 (%)
    total_borrowings = Column(BigInteger, nullable=True)            # 총차입금 (원)
    net_debt = Column(BigInteger, nullable=True)                    # 순차입금 (원)

    # ═══════════════════════════════════════════════════════════════
    # 연속 적자/흑자 정보
    # ═══════════════════════════════════════════════════════════════
    consecutive_loss_quarters = Column(Integer, default=0)          # 연속 적자 분기 수
    consecutive_profit_quarters = Column(Integer, default=0)        # 연속 흑자 분기 수
    is_loss_making = Column(Boolean, default=False)                 # 당기 적자 여부

    # ═══════════════════════════════════════════════════════════════
    # 카테고리별 점수 (0-100)
    # ═══════════════════════════════════════════════════════════════
    stability_score = Column(Numeric(5, 2), nullable=True)          # 안정성 점수
    profitability_score = Column(Numeric(5, 2), nullable=True)      # 수익성 점수
    growth_score = Column(Numeric(5, 2), nullable=True)             # 성장성 점수
    activity_score = Column(Numeric(5, 2), nullable=True)           # 활동성 점수
    cashflow_score = Column(Numeric(5, 2), nullable=True)           # 현금흐름 점수
    leverage_score = Column(Numeric(5, 2), nullable=True)           # 레버리지 점수

    # ═══════════════════════════════════════════════════════════════
    # 종합 평가
    # ═══════════════════════════════════════════════════════════════
    financial_health_score = Column(Numeric(5, 2), nullable=True)   # 종합 건전성 점수 (0-100)
    financial_health_grade = Column(String(5), nullable=True)       # 등급 (A++, A+, A, A-, B+, B, B-, C+, C)
    financial_risk_level = Column(String(20), nullable=True)        # 위험 수준 (LOW, MEDIUM, HIGH, CRITICAL)

    # ═══════════════════════════════════════════════════════════════
    # 메타데이터
    # ═══════════════════════════════════════════════════════════════
    data_completeness = Column(Numeric(5, 2), nullable=True)        # 데이터 완성도 (0-1)
    calculation_notes = Column(Text, nullable=True)                 # 계산 비고
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    company = relationship("Company", back_populates="financial_ratios")
    financial_detail = relationship("FinancialDetails", foreign_keys=[financial_detail_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('company_id', 'fiscal_year', 'fiscal_quarter', name='uq_financial_ratios'),
        Index('idx_fr_company', 'company_id'),
        Index('idx_fr_year', 'fiscal_year'),
        Index('idx_fr_quarter', 'fiscal_quarter'),
        Index('idx_fr_health_score', 'financial_health_score'),
        Index('idx_fr_grade', 'financial_health_grade'),
        Index('idx_fr_risk_level', 'financial_risk_level'),
    )

    def __repr__(self):
        return f"<FinancialRatios(company_id={self.company_id}, year={self.fiscal_year}, score={self.financial_health_score}, grade={self.financial_health_grade})>"

    def to_dict(self):
        """API 응답용 딕셔너리 변환"""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "calculation_date": self.calculation_date.isoformat() if self.calculation_date else None,

            # 안정성 지표
            "stability": {
                "current_ratio": float(self.current_ratio) if self.current_ratio else None,
                "quick_ratio": float(self.quick_ratio) if self.quick_ratio else None,
                "debt_ratio": float(self.debt_ratio) if self.debt_ratio else None,
                "equity_ratio": float(self.equity_ratio) if self.equity_ratio else None,
                "debt_dependency": float(self.debt_dependency) if self.debt_dependency else None,
                "non_current_ratio": float(self.non_current_ratio) if self.non_current_ratio else None,
                "score": float(self.stability_score) if self.stability_score else None,
            },

            # 수익성 지표
            "profitability": {
                "operating_margin": float(self.operating_margin) if self.operating_margin else None,
                "net_profit_margin": float(self.net_profit_margin) if self.net_profit_margin else None,
                "roa": float(self.roa) if self.roa else None,
                "roe": float(self.roe) if self.roe else None,
                "gross_margin": float(self.gross_margin) if self.gross_margin else None,
                "ebitda_margin": float(self.ebitda_margin) if self.ebitda_margin else None,
                "ebitda": self.ebitda,
                "score": float(self.profitability_score) if self.profitability_score else None,
            },

            # 성장성 지표
            "growth": {
                "revenue_growth": float(self.revenue_growth) if self.revenue_growth else None,
                "operating_income_growth": float(self.operating_income_growth) if self.operating_income_growth else None,
                "net_income_growth": float(self.net_income_growth) if self.net_income_growth else None,
                "total_assets_growth": float(self.total_assets_growth) if self.total_assets_growth else None,
                "data_available": self.growth_data_available,
                "score": float(self.growth_score) if self.growth_score else None,
            },

            # 활동성 지표
            "activity": {
                "asset_turnover": float(self.asset_turnover) if self.asset_turnover else None,
                "receivables_turnover": float(self.receivables_turnover) if self.receivables_turnover else None,
                "inventory_turnover": float(self.inventory_turnover) if self.inventory_turnover else None,
                "payables_turnover": float(self.payables_turnover) if self.payables_turnover else None,
                "receivables_days": float(self.receivables_days) if self.receivables_days else None,
                "inventory_days": float(self.inventory_days) if self.inventory_days else None,
                "payables_days": float(self.payables_days) if self.payables_days else None,
                "cash_conversion_cycle": float(self.cash_conversion_cycle) if self.cash_conversion_cycle else None,
                "score": float(self.activity_score) if self.activity_score else None,
            },

            # 현금흐름 지표
            "cashflow": {
                "ocf_ratio": float(self.ocf_ratio) if self.ocf_ratio else None,
                "ocf_interest_coverage": float(self.ocf_interest_coverage) if self.ocf_interest_coverage else None,
                "free_cash_flow": self.free_cash_flow,
                "fcf_margin": float(self.fcf_margin) if self.fcf_margin else None,
                "score": float(self.cashflow_score) if self.cashflow_score else None,
            },

            # 레버리지 지표
            "leverage": {
                "interest_coverage": float(self.interest_coverage) if self.interest_coverage else None,
                "ebitda_interest_coverage": float(self.ebitda_interest_coverage) if self.ebitda_interest_coverage else None,
                "net_debt_to_ebitda": float(self.net_debt_to_ebitda) if self.net_debt_to_ebitda else None,
                "financial_expense_ratio": float(self.financial_expense_ratio) if self.financial_expense_ratio else None,
                "total_borrowings": self.total_borrowings,
                "net_debt": self.net_debt,
                "score": float(self.leverage_score) if self.leverage_score else None,
            },

            # 연속 적자/흑자
            "consecutive_status": {
                "loss_quarters": self.consecutive_loss_quarters or 0,
                "profit_quarters": self.consecutive_profit_quarters or 0,
                "is_loss_making": self.is_loss_making,
            },

            # 종합 평가
            "financial_health_score": float(self.financial_health_score) if self.financial_health_score else None,
            "financial_health_grade": self.financial_health_grade,
            "financial_risk_level": self.financial_risk_level,

            # 메타데이터
            "data_completeness": float(self.data_completeness) if self.data_completeness else None,
            "calculation_notes": self.calculation_notes,
        }

    def to_summary_dict(self):
        """랭킹/목록용 요약 딕셔너리"""
        return {
            "company_id": str(self.company_id),
            "fiscal_year": self.fiscal_year,
            "financial_health_score": float(self.financial_health_score) if self.financial_health_score else None,
            "financial_health_grade": self.financial_health_grade,
            "financial_risk_level": self.financial_risk_level,
            "stability_score": float(self.stability_score) if self.stability_score else None,
            "profitability_score": float(self.profitability_score) if self.profitability_score else None,
            "growth_score": float(self.growth_score) if self.growth_score else None,
            "roe": float(self.roe) if self.roe else None,
            "debt_ratio": float(self.debt_ratio) if self.debt_ratio else None,
            "revenue_growth": float(self.revenue_growth) if self.revenue_growth else None,
            "growth_data_available": self.growth_data_available,
        }
