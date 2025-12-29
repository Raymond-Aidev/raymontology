"""
Financial Details 모델 - RaymondsIndex용 상세 재무 데이터
"""
from sqlalchemy import Column, String, BigInteger, Integer, Date, DateTime, ForeignKey, UniqueConstraint, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class FinancialDetails(Base):
    """
    상세 재무 데이터 테이블 (RaymondsIndex 계산용)

    기존 financial_statements와 별도로 관리하며,
    현금흐름 상세 항목 (CAPEX, 배당금 등)을 포함
    """
    __tablename__ = "financial_details"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)

    # Period information
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer, nullable=True)  # NULL=연간, 1-4=분기
    report_type = Column(String(20), default='annual')

    # ═══════════════════════════════════════════════════════════════
    # 재무상태표 (Balance Sheet)
    # ═══════════════════════════════════════════════════════════════

    # --- 유동자산 (Current Assets) ---
    current_assets = Column(BigInteger, nullable=True)            # 유동자산 총계
    cash_and_equivalents = Column(BigInteger, nullable=True)      # 현금및현금성자산
    short_term_investments = Column(BigInteger, nullable=True)    # 단기금융상품
    trade_and_other_receivables = Column(BigInteger, nullable=True)  # 매출채권및기타채권
    inventories = Column(BigInteger, nullable=True)               # 재고자산
    current_tax_assets = Column(BigInteger, nullable=True)        # 당기법인세자산
    other_financial_assets_current = Column(BigInteger, nullable=True)  # 기타금융자산
    other_assets_current = Column(BigInteger, nullable=True)      # 기타자산

    # --- 비유동자산 (Non-current Assets) ---
    non_current_assets = Column(BigInteger, nullable=True)        # 비유동자산 총계
    fvpl_financial_assets = Column(BigInteger, nullable=True)     # 당기손익공정가치측정금융자산
    investments_in_associates = Column(BigInteger, nullable=True) # 관계기업투자
    tangible_assets = Column(BigInteger, nullable=True)           # 유형자산
    intangible_assets = Column(BigInteger, nullable=True)         # 무형자산
    right_of_use_assets = Column(BigInteger, nullable=True)       # 사용권자산
    net_defined_benefit_assets = Column(BigInteger, nullable=True)  # 순확정급여자산
    deferred_tax_assets = Column(BigInteger, nullable=True)       # 이연법인세자산
    other_financial_assets_non_current = Column(BigInteger, nullable=True)  # 기타금융자산(비유동)
    other_assets_non_current = Column(BigInteger, nullable=True)  # 기타자산(비유동)

    # --- 자산총계 ---
    total_assets = Column(BigInteger, nullable=True)              # 자산총계

    # --- 유동부채 (Current Liabilities) ---
    current_liabilities = Column(BigInteger, nullable=True)       # 유동부채 총계
    trade_payables = Column(BigInteger, nullable=True)            # 매입채무
    short_term_borrowings = Column(BigInteger, nullable=True)     # 단기차입금
    current_portion_long_term_debt = Column(BigInteger, nullable=True)  # 유동성장기부채
    other_current_liabilities = Column(BigInteger, nullable=True) # 기타유동부채
    current_tax_liabilities = Column(BigInteger, nullable=True)   # 당기법인세부채
    provisions_current = Column(BigInteger, nullable=True)        # 유동충당부채

    # --- 비유동부채 (Non-current Liabilities) ---
    non_current_liabilities = Column(BigInteger, nullable=True)   # 비유동부채 총계
    long_term_borrowings = Column(BigInteger, nullable=True)      # 장기차입금
    bonds_payable = Column(BigInteger, nullable=True)             # 사채
    convertible_bonds = Column(BigInteger, nullable=True)         # 전환사채
    lease_liabilities = Column(BigInteger, nullable=True)         # 리스부채
    deferred_tax_liabilities = Column(BigInteger, nullable=True)  # 이연법인세부채
    provisions_non_current = Column(BigInteger, nullable=True)    # 비유동충당부채
    other_non_current_liabilities = Column(BigInteger, nullable=True)  # 기타비유동부채

    # --- 부채/자본 총계 ---
    total_liabilities = Column(BigInteger, nullable=True)         # 부채총계
    total_equity = Column(BigInteger, nullable=True)              # 자본총계

    # --- 자본 세부항목 (Capital Structure) ---
    capital_stock = Column(BigInteger, nullable=True)             # 자본금
    capital_surplus = Column(BigInteger, nullable=True)           # 자본잉여금
    retained_earnings = Column(BigInteger, nullable=True)         # 이익잉여금
    treasury_stock = Column(BigInteger, nullable=True)            # 자기주식

    # ═══════════════════════════════════════════════════════════════
    # 손익계산서 (Income Statement)
    # ═══════════════════════════════════════════════════════════════
    revenue = Column(BigInteger, nullable=True)                   # 매출액
    cost_of_sales = Column(BigInteger, nullable=True)             # 매출원가
    selling_admin_expenses = Column(BigInteger, nullable=True)    # 판매비와관리비
    operating_income = Column(BigInteger, nullable=True)          # 영업이익
    net_income = Column(BigInteger, nullable=True)                # 당기순이익

    # --- v2.0 신규 손익 항목 ---
    r_and_d_expense = Column(BigInteger, nullable=True)           # 연구개발비
    depreciation_expense = Column(BigInteger, nullable=True)      # 감가상각비
    interest_expense = Column(BigInteger, nullable=True)          # 이자비용
    tax_expense = Column(BigInteger, nullable=True)               # 법인세비용

    # ═══════════════════════════════════════════════════════════════
    # 현금흐름표 (Cash Flow Statement) - RaymondsIndex 핵심
    # ═══════════════════════════════════════════════════════════════
    operating_cash_flow = Column(BigInteger, nullable=True)       # 영업활동현금흐름
    investing_cash_flow = Column(BigInteger, nullable=True)       # 투자활동현금흐름
    financing_cash_flow = Column(BigInteger, nullable=True)       # 재무활동현금흐름
    capex = Column(BigInteger, nullable=True)                     # 유형자산의취득 ⭐ 핵심
    intangible_acquisition = Column(BigInteger, nullable=True)    # 무형자산의취득
    dividend_paid = Column(BigInteger, nullable=True)             # 배당금지급
    treasury_stock_acquisition = Column(BigInteger, nullable=True) # 자기주식취득
    stock_issuance = Column(BigInteger, nullable=True)            # 주식발행(유상증자)
    bond_issuance = Column(BigInteger, nullable=True)             # 사채발행

    # ═══════════════════════════════════════════════════════════════
    # 메타데이터
    # ═══════════════════════════════════════════════════════════════
    fs_type = Column(String(10), default='CFS')                   # CFS=연결, OFS=별도
    data_source = Column(String(50), default='DART')
    source_rcept_no = Column(String(20), nullable=True)           # DART 접수번호
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    company = relationship("Company", back_populates="financial_details")

    # Constraints
    __table_args__ = (
        UniqueConstraint('company_id', 'fiscal_year', 'fiscal_quarter', 'fs_type', name='uq_financial_details'),
        Index('idx_fd_company', 'company_id'),
        Index('idx_fd_year', 'fiscal_year'),
        Index('idx_fd_quarter', 'fiscal_quarter'),
        Index('idx_fd_fs_type', 'fs_type'),
    )

    def __repr__(self):
        return f"<FinancialDetails(company_id={self.company_id}, year={self.fiscal_year}, quarter={self.fiscal_quarter})>"
