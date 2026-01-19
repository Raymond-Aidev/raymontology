"""Add financial_ratios table and new columns to financial_details

Revision ID: 20260115_financial_ratios
Revises: 20260113_pipeline_runs_table
Create Date: 2026-01-15

재무건전성 평가 시스템 구축:
- financial_ratios 테이블 신규 생성 (25개 재무비율)
- financial_details 테이블에 4개 컬럼 추가 (gross_profit, interest_income, income_before_tax, amortization)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260115_financial_ratios'
down_revision = '20260113_pipeline_runs_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. financial_details 테이블에 신규 컬럼 추가
    op.add_column('financial_details', sa.Column('gross_profit', sa.BigInteger(), nullable=True))
    op.add_column('financial_details', sa.Column('interest_income', sa.BigInteger(), nullable=True))
    op.add_column('financial_details', sa.Column('income_before_tax', sa.BigInteger(), nullable=True))
    op.add_column('financial_details', sa.Column('amortization', sa.BigInteger(), nullable=True))

    # 2. financial_ratios 테이블 생성
    op.create_table(
        'financial_ratios',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Foreign Keys
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('financial_detail_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('financial_details.id', ondelete='SET NULL'), nullable=True),

        # Period information
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('fiscal_quarter', sa.Integer(), nullable=True),
        sa.Column('calculation_date', sa.DateTime(timezone=True), server_default=sa.func.now()),

        # 안정성 지표 (Stability) - 6개
        sa.Column('current_ratio', sa.Numeric(10, 2), nullable=True),
        sa.Column('quick_ratio', sa.Numeric(10, 2), nullable=True),
        sa.Column('debt_ratio', sa.Numeric(10, 2), nullable=True),
        sa.Column('equity_ratio', sa.Numeric(10, 2), nullable=True),
        sa.Column('debt_dependency', sa.Numeric(10, 2), nullable=True),
        sa.Column('non_current_ratio', sa.Numeric(10, 2), nullable=True),

        # 수익성 지표 (Profitability) - 6개 + EBITDA
        sa.Column('operating_margin', sa.Numeric(10, 2), nullable=True),
        sa.Column('net_profit_margin', sa.Numeric(10, 2), nullable=True),
        sa.Column('roa', sa.Numeric(10, 2), nullable=True),
        sa.Column('roe', sa.Numeric(10, 2), nullable=True),
        sa.Column('gross_margin', sa.Numeric(10, 2), nullable=True),
        sa.Column('ebitda_margin', sa.Numeric(10, 2), nullable=True),
        sa.Column('ebitda', sa.BigInteger(), nullable=True),

        # 성장성 지표 (Growth) - 4개
        sa.Column('revenue_growth', sa.Numeric(10, 2), nullable=True),
        sa.Column('operating_income_growth', sa.Numeric(10, 2), nullable=True),
        sa.Column('net_income_growth', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_assets_growth', sa.Numeric(10, 2), nullable=True),
        sa.Column('growth_data_available', sa.Boolean(), default=False),

        # 활동성 지표 (Activity) - 4개 + 회수/보유기간
        sa.Column('asset_turnover', sa.Numeric(10, 2), nullable=True),
        sa.Column('receivables_turnover', sa.Numeric(10, 2), nullable=True),
        sa.Column('inventory_turnover', sa.Numeric(10, 2), nullable=True),
        sa.Column('payables_turnover', sa.Numeric(10, 2), nullable=True),
        sa.Column('receivables_days', sa.Numeric(10, 2), nullable=True),
        sa.Column('inventory_days', sa.Numeric(10, 2), nullable=True),
        sa.Column('payables_days', sa.Numeric(10, 2), nullable=True),
        sa.Column('cash_conversion_cycle', sa.Numeric(10, 2), nullable=True),

        # 현금흐름 지표 (Cash Flow) - 3개 + FCF 마진
        sa.Column('ocf_ratio', sa.Numeric(10, 2), nullable=True),
        sa.Column('ocf_interest_coverage', sa.Numeric(10, 2), nullable=True),
        sa.Column('free_cash_flow', sa.BigInteger(), nullable=True),
        sa.Column('fcf_margin', sa.Numeric(10, 2), nullable=True),

        # 레버리지 지표 (Leverage) - 4개 + 절대값
        sa.Column('interest_coverage', sa.Numeric(10, 2), nullable=True),
        sa.Column('ebitda_interest_coverage', sa.Numeric(10, 2), nullable=True),
        sa.Column('net_debt_to_ebitda', sa.Numeric(10, 2), nullable=True),
        sa.Column('financial_expense_ratio', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_borrowings', sa.BigInteger(), nullable=True),
        sa.Column('net_debt', sa.BigInteger(), nullable=True),

        # 연속 적자/흑자 정보
        sa.Column('consecutive_loss_quarters', sa.Integer(), default=0),
        sa.Column('consecutive_profit_quarters', sa.Integer(), default=0),
        sa.Column('is_loss_making', sa.Boolean(), default=False),

        # 카테고리별 점수 (0-100)
        sa.Column('stability_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('profitability_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('growth_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('activity_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('cashflow_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('leverage_score', sa.Numeric(5, 2), nullable=True),

        # 종합 평가
        sa.Column('financial_health_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('financial_health_grade', sa.String(5), nullable=True),
        sa.Column('financial_risk_level', sa.String(20), nullable=True),

        # 메타데이터
        sa.Column('data_completeness', sa.Numeric(5, 2), nullable=True),
        sa.Column('calculation_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. 인덱스 생성
    op.create_index('idx_fr_company', 'financial_ratios', ['company_id'])
    op.create_index('idx_fr_year', 'financial_ratios', ['fiscal_year'])
    op.create_index('idx_fr_quarter', 'financial_ratios', ['fiscal_quarter'])
    op.create_index('idx_fr_health_score', 'financial_ratios', ['financial_health_score'])
    op.create_index('idx_fr_grade', 'financial_ratios', ['financial_health_grade'])
    op.create_index('idx_fr_risk_level', 'financial_ratios', ['financial_risk_level'])

    # 4. 유니크 제약 조건
    op.create_unique_constraint('uq_financial_ratios', 'financial_ratios', ['company_id', 'fiscal_year', 'fiscal_quarter'])


def downgrade() -> None:
    # 1. financial_ratios 테이블 삭제
    op.drop_table('financial_ratios')

    # 2. financial_details에서 신규 컬럼 삭제
    op.drop_column('financial_details', 'gross_profit')
    op.drop_column('financial_details', 'interest_income')
    op.drop_column('financial_details', 'income_before_tax')
    op.drop_column('financial_details', 'amortization')
