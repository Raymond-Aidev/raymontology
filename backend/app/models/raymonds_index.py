"""
RaymondsIndex 모델 - 자본 배분 효율성 지수
"""
from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey, UniqueConstraint, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class RaymondsIndex(Base):
    """
    RaymondsIndex v2.1 계산 결과 테이블

    자본 배분 효율성을 측정하는 종합 지수로,
    4개의 Sub-Index로 구성됨:
    - CEI: Capital Efficiency Index (20%) - 자본 효율성
      → 자산회전율(25%) + 유형자산효율성(20%) + 현금수익률(20%) + ROIC(25%) + 추세(10%)
    - RII: Reinvestment Intensity Index (35%) ⭐ 핵심 - 재투자 강도
      → CAPEX강도(30%) + 투자괴리율(30%) + 재투자율(25%) + 지속성(15%)
    - CGI: Cash Governance Index (25%) ⭐ 핵심 - 현금 거버넌스
      → 현금활용도(20%) + 자금조달효율성(25%) + 주주환원균형(20%) + 현금적정성(15%) + 부채건전성(20%)
    - MAI: Momentum Alignment Index (20%) - 모멘텀 정합성
      → 매출-투자동조성(30%) + 이익품질(25%) + 투자지속성(20%) + 성장투자비율(15%) + FCF추세(10%)

    v2.1 주요 변경 (v2.0 대비):
    - 투자괴리율: 현금 CAGR - CAPEX 성장률 (v2.0: 재투자율 기반)
    - 재투자율: CAPEX / OCF (v2.0: CAPEX / 영업이익)
    - 등급 기준 완화 (A+: 90→88, A: 85→80, etc.)
    - 신규 지표: 유형자산효율성, 현금수익률, 부채건전성, 성장투자비율

    특별 규칙:
    - 현금-유형자산 비율 > 30:1 → 최대 B-
    - 조달자금 전환율 < 30% → 최대 B-
    - 단기금융상품비율 > 65% + CAPEX 감소 → 최대 B
    - 위 조건 2개 이상 해당 → 최대 C+
    """
    __tablename__ = "raymonds_index"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)

    # Calculation metadata
    calculation_date = Column(Date, nullable=False, server_default=func.current_date())
    fiscal_year = Column(Integer, nullable=False)

    # ═══════════════════════════════════════════════════════════════
    # 종합 점수
    # ═══════════════════════════════════════════════════════════════
    total_score = Column(Numeric(5, 2), nullable=False)  # 0-100
    grade = Column(String(5), nullable=False)            # A+, A, B, C, D

    # ═══════════════════════════════════════════════════════════════
    # Sub-Index 점수 (각 0-100)
    # ═══════════════════════════════════════════════════════════════
    cei_score = Column(Numeric(5, 2), nullable=True)     # Capital Efficiency Index (20%)
    rii_score = Column(Numeric(5, 2), nullable=True)     # Reinvestment Intensity Index (35%) ⭐
    cgi_score = Column(Numeric(5, 2), nullable=True)     # Cash Governance Index (25%)
    mai_score = Column(Numeric(5, 2), nullable=True)     # Momentum Alignment Index (20%)

    # ═══════════════════════════════════════════════════════════════
    # 핵심 지표 (기존)
    # ═══════════════════════════════════════════════════════════════
    investment_gap = Column(Numeric(6, 2), nullable=True)     # 투자괴리율 (%) = Cash CAGR - CAPEX Growth
    cash_cagr = Column(Numeric(6, 2), nullable=True)          # 현금 증가율 CAGR (%)
    capex_growth = Column(Numeric(6, 2), nullable=True)       # CAPEX 증가율 (%)
    idle_cash_ratio = Column(Numeric(5, 2), nullable=True)    # 유휴현금비율 (%)
    asset_turnover = Column(Numeric(5, 3), nullable=True)     # 자산회전율 (회)
    reinvestment_rate = Column(Numeric(5, 2), nullable=True)  # 재투자율 (%)
    shareholder_return = Column(Numeric(5, 2), nullable=True) # 주주환원율 (%)

    # ═══════════════════════════════════════════════════════════════
    # v4.0 기존 지표
    # ═══════════════════════════════════════════════════════════════
    cash_tangible_ratio = Column(Numeric(10, 2), nullable=True)    # 현금-유형자산 증가비율 (X:1)
    fundraising_utilization = Column(Numeric(5, 2), nullable=True) # 조달자금 투자전환율 (%)
    short_term_ratio = Column(Numeric(5, 2), nullable=True)        # 단기금융상품 비율 (%)
    capex_trend = Column(String(20), nullable=True)                # CAPEX 추세 (increasing/stable/decreasing)
    roic = Column(Numeric(6, 2), nullable=True)                    # 투하자본수익률 ROIC (%)
    capex_cv = Column(Numeric(5, 3), nullable=True)                # CAPEX 변동계수 (투자 지속성)
    violation_count = Column(Integer, default=0)                   # 특별규칙 위반 개수

    # ═══════════════════════════════════════════════════════════════
    # v2.0/v2.1 지표
    # ═══════════════════════════════════════════════════════════════
    investment_gap_v2 = Column(Numeric(6, 2), nullable=True)       # 투자괴리율 v2 (레거시: 초기2년 - 최근2년 재투자율)
    investment_gap_v21 = Column(Numeric(6, 2), nullable=True)      # 투자괴리율 v2.1 ⭐핵심 (현금 CAGR - CAPEX 성장률)
    rd_intensity = Column(Numeric(5, 2), nullable=True)            # R&D 강도 - 미사용 (데이터 없음)
    ebitda = Column(Numeric(20, 0), nullable=True)                 # EBITDA
    debt_to_ebitda = Column(Numeric(6, 2), nullable=True)          # 부채/EBITDA (CGI용)
    cash_utilization = Column(Numeric(5, 2), nullable=True)        # 현금 활용도 (%)
    industry_sector = Column(String(50), nullable=True)            # 업종 분류
    weight_adjustment = Column(JSONB, nullable=True)               # 업종별 가중치 조정 내역

    # ═══════════════════════════════════════════════════════════════
    # v2.1 신규 지표
    # ═══════════════════════════════════════════════════════════════
    tangible_efficiency = Column(Numeric(6, 3), nullable=True)     # 유형자산 효율성 (매출/유형자산)
    cash_yield = Column(Numeric(6, 2), nullable=True)              # 현금 수익률 (영업이익/총현금 %)
    growth_investment_ratio = Column(Numeric(5, 2), nullable=True) # 성장 투자 비율 (성장CAPEX/총CAPEX %)

    # ═══════════════════════════════════════════════════════════════
    # 위험 신호 (JSONB 배열)
    # ═══════════════════════════════════════════════════════════════
    red_flags = Column(JSONB, default=list)      # 위험 신호 배열
    yellow_flags = Column(JSONB, default=list)   # 주의 신호 배열

    # ═══════════════════════════════════════════════════════════════
    # 해석
    # ═══════════════════════════════════════════════════════════════
    verdict = Column(String(200), nullable=True)       # 한 줄 요약
    key_risk = Column(Text, nullable=True)             # 핵심 리스크 설명
    recommendation = Column(Text, nullable=True)       # 투자자 권고
    watch_trigger = Column(Text, nullable=True)        # 재검토 시점

    # ═══════════════════════════════════════════════════════════════
    # 메타데이터
    # ═══════════════════════════════════════════════════════════════
    data_quality_score = Column(Numeric(3, 2), nullable=True)  # 데이터 품질 점수 (0-1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    company = relationship("Company", back_populates="raymonds_indices")

    # Constraints
    __table_args__ = (
        UniqueConstraint('company_id', 'fiscal_year', name='uq_raymonds_index'),
        Index('idx_ri_company', 'company_id'),
        Index('idx_ri_year', 'fiscal_year'),
        Index('idx_ri_score', 'total_score'),
        Index('idx_ri_grade', 'grade'),
        Index('idx_ri_investment_gap', 'investment_gap'),
    )

    def __repr__(self):
        return f"<RaymondsIndex(company_id={self.company_id}, year={self.fiscal_year}, score={self.total_score}, grade={self.grade})>"

    def to_dict(self):
        """API 응답용 딕셔너리 변환"""
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "fiscal_year": self.fiscal_year,
            "calculation_date": self.calculation_date.isoformat() if self.calculation_date else None,
            "total_score": float(self.total_score) if self.total_score else None,
            "grade": self.grade,
            # Sub-Index 점수
            "cei_score": float(self.cei_score) if self.cei_score else None,
            "rii_score": float(self.rii_score) if self.rii_score else None,
            "cgi_score": float(self.cgi_score) if self.cgi_score else None,
            "mai_score": float(self.mai_score) if self.mai_score else None,
            # 기존 핵심 지표
            "investment_gap": float(self.investment_gap) if self.investment_gap else None,
            "cash_cagr": float(self.cash_cagr) if self.cash_cagr else None,
            "capex_growth": float(self.capex_growth) if self.capex_growth else None,
            "idle_cash_ratio": float(self.idle_cash_ratio) if self.idle_cash_ratio else None,
            "asset_turnover": float(self.asset_turnover) if self.asset_turnover else None,
            "reinvestment_rate": float(self.reinvestment_rate) if self.reinvestment_rate else None,
            "shareholder_return": float(self.shareholder_return) if self.shareholder_return else None,
            # v4.0 기존 지표
            "cash_tangible_ratio": float(self.cash_tangible_ratio) if self.cash_tangible_ratio else None,
            "fundraising_utilization": float(self.fundraising_utilization) if self.fundraising_utilization else None,
            "short_term_ratio": float(self.short_term_ratio) if self.short_term_ratio else None,
            "capex_trend": self.capex_trend,
            "roic": float(self.roic) if self.roic else None,
            "capex_cv": float(self.capex_cv) if self.capex_cv else None,
            "violation_count": self.violation_count or 0,
            # v2.0/v2.1 지표
            "investment_gap_v2": float(self.investment_gap_v2) if self.investment_gap_v2 else None,
            "investment_gap_v21": float(self.investment_gap_v21) if self.investment_gap_v21 else None,
            "cash_utilization": float(self.cash_utilization) if self.cash_utilization else None,
            "industry_sector": self.industry_sector,
            "weight_adjustment": self.weight_adjustment,
            # v2.1 신규 지표
            "tangible_efficiency": float(self.tangible_efficiency) if self.tangible_efficiency else None,
            "cash_yield": float(self.cash_yield) if self.cash_yield else None,
            "debt_to_ebitda": float(self.debt_to_ebitda) if self.debt_to_ebitda else None,
            "growth_investment_ratio": float(self.growth_investment_ratio) if self.growth_investment_ratio else None,
            # 위험 신호
            "red_flags": self.red_flags or [],
            "yellow_flags": self.yellow_flags or [],
            # 해석
            "verdict": self.verdict,
            "key_risk": self.key_risk,
            "recommendation": self.recommendation,
            "watch_trigger": self.watch_trigger,
            "data_quality_score": float(self.data_quality_score) if self.data_quality_score else None,
        }
