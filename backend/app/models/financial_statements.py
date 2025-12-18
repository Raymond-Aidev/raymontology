"""
Financial Statement 모델
"""
from sqlalchemy import Column, String, BigInteger, Integer, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class FinancialStatement(Base):
    """
    재무제표 테이블

    DART API의 단일회사 전체 재무제표 데이터 저장
    """
    __tablename__ = "financial_statements"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)

    # Period information
    fiscal_year = Column(Integer, nullable=False)
    quarter = Column(String(2), nullable=True)  # NULL=annual, Q1, Q2, Q3, Q4
    statement_date = Column(Date, nullable=False)
    report_type = Column(String(50), nullable=False)  # '사업보고서', '반기보고서', '분기보고서'

    # Balance Sheet (재무상태표)
    cash_and_equivalents = Column(BigInteger, nullable=True)  # 현금및현금성자산
    short_term_investments = Column(BigInteger, nullable=True)  # 단기금융상품
    accounts_receivable = Column(BigInteger, nullable=True)  # 매출채권
    inventory = Column(BigInteger, nullable=True)  # 재고자산
    current_assets = Column(BigInteger, nullable=True)  # 유동자산
    non_current_assets = Column(BigInteger, nullable=True)  # 비유동자산
    total_assets = Column(BigInteger, nullable=True)  # 자산총계

    accounts_payable = Column(BigInteger, nullable=True)  # 매입채무
    short_term_debt = Column(BigInteger, nullable=True)  # 단기차입금
    current_liabilities = Column(BigInteger, nullable=True)  # 유동부채
    long_term_debt = Column(BigInteger, nullable=True)  # 장기차입금
    non_current_liabilities = Column(BigInteger, nullable=True)  # 비유동부채
    total_liabilities = Column(BigInteger, nullable=True)  # 부채총계

    capital_stock = Column(BigInteger, nullable=True)  # 자본금
    retained_earnings = Column(BigInteger, nullable=True)  # 이익잉여금
    total_equity = Column(BigInteger, nullable=True)  # 자본총계

    # Income Statement (손익계산서)
    revenue = Column(BigInteger, nullable=True)  # 매출액
    cost_of_sales = Column(BigInteger, nullable=True)  # 매출원가
    gross_profit = Column(BigInteger, nullable=True)  # 매출총이익
    operating_expenses = Column(BigInteger, nullable=True)  # 판매비와관리비
    operating_profit = Column(BigInteger, nullable=True)  # 영업이익
    net_income = Column(BigInteger, nullable=True)  # 당기순이익

    # Cash Flow Statement (현금흐름표)
    operating_cash_flow = Column(BigInteger, nullable=True)  # 영업활동현금흐름
    investing_cash_flow = Column(BigInteger, nullable=True)  # 투자활동현금흐름
    financing_cash_flow = Column(BigInteger, nullable=True)  # 재무활동현금흐름

    # Metadata
    source_rcept_no = Column(String(20), nullable=True)  # DART 접수번호
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('company_id', 'fiscal_year', 'quarter', name='uq_company_fiscal_quarter'),
        Index('idx_financial_company_id', 'company_id'),
        Index('idx_financial_fiscal_year', 'fiscal_year'),
        Index('idx_financial_quarter', 'quarter'),
        Index('idx_financial_statement_date', 'statement_date'),
    )

    def __repr__(self):
        return f"<FinancialStatement(company_id={self.company_id}, year={self.fiscal_year}, quarter={self.quarter})>"
