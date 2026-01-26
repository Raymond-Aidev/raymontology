"""Add M&A target analysis tables

Revision ID: 20260126_ma_target
Revises: 20260122_create_raymonds_index_v3_table
Create Date: 2026-01-26

Tables:
- daily_stock_prices: 일별 종가 데이터 (KRX)
- stock_info: 발행주식수 이력 (DART)
- financial_snapshots: 일별 재무 스냅샷 (M&A 타겟 분석용)
- companies 컬럼 추가: shares_outstanding, shares_updated_at
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20260126_ma_target'
down_revision = '20260122_ri_v3_table'
branch_labels = None
depends_on = None


def upgrade():
    # 1. companies 테이블에 발행주식수 컬럼 추가
    op.add_column('companies',
        sa.Column('shares_outstanding', sa.BigInteger(), nullable=True, comment='발행주식수 (유통주식)')
    )
    op.add_column('companies',
        sa.Column('shares_updated_at', sa.DateTime(timezone=True), nullable=True, comment='발행주식수 갱신일')
    )

    # 2. daily_stock_prices 테이블 생성 (KRX 일별 종가)
    op.create_table(
        'daily_stock_prices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('price_date', sa.Date(), nullable=False, comment='거래일'),
        sa.Column('close_price', sa.Integer(), nullable=False, comment='종가 (원)'),
        sa.Column('open_price', sa.Integer(), nullable=True, comment='시가'),
        sa.Column('high_price', sa.Integer(), nullable=True, comment='고가'),
        sa.Column('low_price', sa.Integer(), nullable=True, comment='저가'),
        sa.Column('volume', sa.BigInteger(), nullable=True, comment='거래량'),
        sa.Column('trading_value', sa.BigInteger(), nullable=True, comment='거래대금'),
        sa.Column('market_cap', sa.BigInteger(), nullable=True, comment='시가총액 (KRX 제공)'),
        sa.Column('listed_shares', sa.BigInteger(), nullable=True, comment='상장주식수 (KRX 제공)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('company_id', 'price_date', name='uq_daily_stock_price_company_date'),
    )
    op.create_index('idx_daily_stock_prices_date', 'daily_stock_prices', ['price_date'])
    op.create_index('idx_daily_stock_prices_company', 'daily_stock_prices', ['company_id'])

    # 3. stock_info 테이블 생성 (DART 발행주식수 이력)
    op.create_table(
        'stock_info',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False, comment='사업연도'),
        sa.Column('report_code', sa.String(10), nullable=True, comment='보고서 코드 (11011: 사업보고서)'),
        # 주식 수
        sa.Column('common_shares', sa.BigInteger(), nullable=True, comment='보통주 발행주식총수'),
        sa.Column('preferred_shares', sa.BigInteger(), nullable=True, comment='우선주 발행주식총수'),
        sa.Column('total_shares', sa.BigInteger(), nullable=True, comment='발행주식총수'),
        sa.Column('treasury_shares', sa.BigInteger(), nullable=True, comment='자기주식수'),
        sa.Column('outstanding_shares', sa.BigInteger(), nullable=True, comment='유통주식수 (발행-자기주식)'),
        # 메타
        sa.Column('data_source', sa.String(50), nullable=True, default='DART', comment='데이터 소스'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('company_id', 'fiscal_year', name='uq_stock_info_company_year'),
    )
    op.create_index('idx_stock_info_company', 'stock_info', ['company_id'])

    # 4. financial_snapshots 테이블 생성 (M&A 타겟 분석용 일별 스냅샷)
    op.create_table(
        'financial_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False, comment='스냅샷 일자'),

        # 주가 데이터 (KRX)
        sa.Column('close_price', sa.Integer(), nullable=True, comment='전일 종가'),
        sa.Column('market_cap_krx', sa.BigInteger(), nullable=True, comment='KRX 제공 시가총액'),

        # 발행주식수 (DART/companies)
        sa.Column('shares_outstanding', sa.BigInteger(), nullable=True, comment='유통주식수'),

        # 계산된 시가총액
        sa.Column('market_cap_calculated', sa.BigInteger(), nullable=True, comment='계산된 시가총액 (종가×주식수)'),

        # 재무 지표 (분기별 갱신, 최신 값 저장)
        sa.Column('cash_and_equivalents', sa.BigInteger(), nullable=True, comment='현금 및 현금성자산'),
        sa.Column('short_term_investments', sa.BigInteger(), nullable=True, comment='단기금융상품'),
        sa.Column('total_liquid_assets', sa.BigInteger(), nullable=True, comment='현금성 유동자산 합계'),
        sa.Column('tangible_assets', sa.BigInteger(), nullable=True, comment='유형자산'),
        sa.Column('revenue', sa.BigInteger(), nullable=True, comment='매출액'),
        sa.Column('operating_profit', sa.BigInteger(), nullable=True, comment='영업이익'),

        # YoY 증감율 (%)
        sa.Column('tangible_assets_growth', sa.Numeric(10, 2), nullable=True, comment='유형자산 증가율'),
        sa.Column('revenue_growth', sa.Numeric(10, 2), nullable=True, comment='매출 증감율'),
        sa.Column('operating_profit_growth', sa.Numeric(10, 2), nullable=True, comment='영업이익 증감율'),

        # M&A 타겟 점수
        sa.Column('ma_target_score', sa.Numeric(5, 2), nullable=True, comment='M&A 타겟 점수 (0-100)'),
        sa.Column('ma_target_grade', sa.String(5), nullable=True, comment='M&A 타겟 등급'),
        sa.Column('ma_target_factors', postgresql.JSONB(), nullable=True, comment='M&A 타겟 요소별 점수'),

        # 메타
        sa.Column('fiscal_year', sa.Integer(), nullable=True, comment='재무데이터 기준 사업연도'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('company_id', 'snapshot_date', name='uq_financial_snapshot_company_date'),
    )
    op.create_index('idx_financial_snapshots_date', 'financial_snapshots', ['snapshot_date'])
    op.create_index('idx_financial_snapshots_company', 'financial_snapshots', ['company_id'])
    op.create_index('idx_financial_snapshots_ma_score', 'financial_snapshots', ['ma_target_score'])


def downgrade():
    # 테이블 삭제
    op.drop_table('financial_snapshots')
    op.drop_table('stock_info')
    op.drop_table('daily_stock_prices')

    # companies 컬럼 삭제
    op.drop_column('companies', 'shares_updated_at')
    op.drop_column('companies', 'shares_outstanding')
