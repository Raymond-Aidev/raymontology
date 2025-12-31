"""add stock_prices table

Revision ID: stock_prices_001
Revises: 1ee6af06d77f
Create Date: 2025-12-31

월별 종가 데이터 저장을 위한 stock_prices 테이블 추가
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'stock_prices_001'
down_revision: Union[str, None] = '1ee6af06d77f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # stock_prices 테이블 생성
    op.create_table(
        'stock_prices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('price_date', sa.Date(), nullable=False),
        sa.Column('year_month', sa.String(length=7), nullable=False),
        sa.Column('close_price', sa.Float(), nullable=False),
        sa.Column('open_price', sa.Float(), nullable=True),
        sa.Column('high_price', sa.Float(), nullable=True),
        sa.Column('low_price', sa.Float(), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('change_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 인덱스 생성
    op.create_index('idx_stock_price_company_date', 'stock_prices', ['company_id', 'price_date'], unique=False)
    op.create_index('idx_stock_price_year_month', 'stock_prices', ['year_month'], unique=False)

    # 유니크 제약조건 (동일 기업의 동일 월 데이터는 하나만)
    op.create_unique_constraint('uq_stock_price_company_month', 'stock_prices', ['company_id', 'year_month'])


def downgrade() -> None:
    # 제약조건 삭제
    op.drop_constraint('uq_stock_price_company_month', 'stock_prices', type_='unique')

    # 인덱스 삭제
    op.drop_index('idx_stock_price_year_month', table_name='stock_prices')
    op.drop_index('idx_stock_price_company_date', table_name='stock_prices')

    # 테이블 삭제
    op.drop_table('stock_prices')
