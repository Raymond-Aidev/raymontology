"""add_financial_statements_table

Revision ID: 16ab7b40051b
Revises: e4f697667073
Create Date: 2025-11-20 13:41:15.086860

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16ab7b40051b'
down_revision: Union[str, None] = 'e4f697667073'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create financial_statements table
    op.create_table(
        'financial_statements',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),

        # Period information
        sa.Column('fiscal_year', sa.Integer, nullable=False),
        sa.Column('quarter', sa.String(2), nullable=True),  # NULL=annual, Q1, Q2, Q3, Q4
        sa.Column('statement_date', sa.Date, nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),  # '사업보고서', '반기보고서', '분기보고서'

        # Balance Sheet (재무상태표)
        sa.Column('cash_and_equivalents', sa.BigInteger, nullable=True),  # 현금및현금성자산
        sa.Column('short_term_investments', sa.BigInteger, nullable=True),  # 단기금융상품
        sa.Column('accounts_receivable', sa.BigInteger, nullable=True),  # 매출채권
        sa.Column('inventory', sa.BigInteger, nullable=True),  # 재고자산
        sa.Column('current_assets', sa.BigInteger, nullable=True),  # 유동자산
        sa.Column('non_current_assets', sa.BigInteger, nullable=True),  # 비유동자산
        sa.Column('total_assets', sa.BigInteger, nullable=True),  # 자산총계

        sa.Column('accounts_payable', sa.BigInteger, nullable=True),  # 매입채무
        sa.Column('short_term_debt', sa.BigInteger, nullable=True),  # 단기차입금
        sa.Column('current_liabilities', sa.BigInteger, nullable=True),  # 유동부채
        sa.Column('long_term_debt', sa.BigInteger, nullable=True),  # 장기차입금
        sa.Column('non_current_liabilities', sa.BigInteger, nullable=True),  # 비유동부채
        sa.Column('total_liabilities', sa.BigInteger, nullable=True),  # 부채총계

        sa.Column('capital_stock', sa.BigInteger, nullable=True),  # 자본금
        sa.Column('retained_earnings', sa.BigInteger, nullable=True),  # 이익잉여금
        sa.Column('total_equity', sa.BigInteger, nullable=True),  # 자본총계

        # Income Statement (손익계산서)
        sa.Column('revenue', sa.BigInteger, nullable=True),  # 매출액
        sa.Column('cost_of_sales', sa.BigInteger, nullable=True),  # 매출원가
        sa.Column('gross_profit', sa.BigInteger, nullable=True),  # 매출총이익
        sa.Column('operating_expenses', sa.BigInteger, nullable=True),  # 판매비와관리비
        sa.Column('operating_profit', sa.BigInteger, nullable=True),  # 영업이익
        sa.Column('net_income', sa.BigInteger, nullable=True),  # 당기순이익

        # Cash Flow Statement (현금흐름표)
        sa.Column('operating_cash_flow', sa.BigInteger, nullable=True),  # 영업활동현금흐름
        sa.Column('investing_cash_flow', sa.BigInteger, nullable=True),  # 투자활동현금흐름
        sa.Column('financing_cash_flow', sa.BigInteger, nullable=True),  # 재무활동현금흐름

        # Metadata
        sa.Column('source_rcept_no', sa.String(20), nullable=True),  # DART 접수번호
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Constraints
        sa.UniqueConstraint('company_id', 'fiscal_year', 'quarter', name='uq_company_fiscal_quarter')
    )

    # Create indexes
    op.create_index('idx_financial_company_id', 'financial_statements', ['company_id'])
    op.create_index('idx_financial_fiscal_year', 'financial_statements', ['fiscal_year'])
    op.create_index('idx_financial_quarter', 'financial_statements', ['quarter'])
    op.create_index('idx_financial_statement_date', 'financial_statements', ['statement_date'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_financial_statement_date', table_name='financial_statements')
    op.drop_index('idx_financial_quarter', table_name='financial_statements')
    op.drop_index('idx_financial_fiscal_year', table_name='financial_statements')
    op.drop_index('idx_financial_company_id', table_name='financial_statements')

    # Drop table
    op.drop_table('financial_statements')
