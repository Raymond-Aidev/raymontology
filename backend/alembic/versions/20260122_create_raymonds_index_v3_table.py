"""Create raymonds_index_v3 table for parallel v3.0 testing

Revision ID: 20260122_ri_v3_table
Revises: 20260122_algo_version
Create Date: 2026-01-22

안전한 마이그레이션 (옵션 A):
- 기존 raymonds_index 테이블 변경 없음
- 별도 raymonds_index_v3 테이블 생성
- v3.0 계산 결과 독립 저장
- 검증 완료 후 테이블 교체 (RENAME)
- 기존 API 영향 없음
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20260122_ri_v3_table'
down_revision = '20260122_algo_version'
branch_labels = None
depends_on = None


def upgrade():
    """
    raymonds_index_v3 테이블 생성

    기존 raymonds_index와 동일한 스키마 + algorithm_version 컬럼
    v3.0 계산 결과를 별도 저장하여 검증 후 교체
    """
    op.create_table(
        'raymonds_index_v3',
        # Primary Key
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Foreign Key
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),

        # Calculation metadata
        sa.Column('calculation_date', sa.Date, nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('fiscal_year', sa.Integer, nullable=False),

        # 종합 점수
        sa.Column('total_score', sa.Numeric(5, 2), nullable=False),
        sa.Column('grade', sa.String(5), nullable=False),

        # Sub-Index 점수
        sa.Column('cei_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('rii_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('cgi_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('mai_score', sa.Numeric(5, 2), nullable=True),

        # 핵심 지표
        sa.Column('investment_gap', sa.Numeric(6, 2), nullable=True),
        sa.Column('cash_cagr', sa.Numeric(6, 2), nullable=True),
        sa.Column('capex_growth', sa.Numeric(6, 2), nullable=True),
        sa.Column('idle_cash_ratio', sa.Numeric(5, 2), nullable=True),
        sa.Column('asset_turnover', sa.Numeric(5, 3), nullable=True),
        sa.Column('reinvestment_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('shareholder_return', sa.Numeric(5, 2), nullable=True),

        # 기존 지표
        sa.Column('cash_tangible_ratio', sa.Numeric(10, 2), nullable=True),
        sa.Column('fundraising_utilization', sa.Numeric(5, 2), nullable=True),
        sa.Column('short_term_ratio', sa.Numeric(5, 2), nullable=True),
        sa.Column('capex_trend', sa.String(20), nullable=True),
        sa.Column('roic', sa.Numeric(6, 2), nullable=True),
        sa.Column('capex_cv', sa.Numeric(5, 3), nullable=True),
        sa.Column('violation_count', sa.Integer, server_default='0'),

        # v2.x 호환 지표
        sa.Column('investment_gap_v2', sa.Numeric(6, 2), nullable=True),
        sa.Column('investment_gap_v21', sa.Numeric(6, 2), nullable=True),
        sa.Column('investment_gap_v21_flag', sa.String(20), nullable=True),
        sa.Column('rd_intensity', sa.Numeric(5, 2), nullable=True),
        sa.Column('ebitda', sa.BigInteger, nullable=True),
        sa.Column('debt_to_ebitda', sa.Numeric(6, 2), nullable=True),
        sa.Column('cash_utilization', sa.Numeric(5, 2), nullable=True),
        sa.Column('industry_sector', sa.String(50), nullable=True),
        sa.Column('weight_adjustment', JSONB, nullable=True),

        # v2.1 신규 지표
        sa.Column('tangible_efficiency', sa.Numeric(6, 3), nullable=True),
        sa.Column('cash_yield', sa.Numeric(6, 2), nullable=True),
        sa.Column('growth_investment_ratio', sa.Numeric(5, 2), nullable=True),

        # 위험 신호
        sa.Column('red_flags', JSONB, server_default='[]'),
        sa.Column('yellow_flags', JSONB, server_default='[]'),

        # 해석
        sa.Column('verdict', sa.String(200), nullable=True),
        sa.Column('key_risk', sa.Text, nullable=True),
        sa.Column('recommendation', sa.Text, nullable=True),
        sa.Column('watch_trigger', sa.Text, nullable=True),

        # v3.0 메타데이터
        sa.Column('algorithm_version', sa.String(10), nullable=False, server_default='3.0'),
        sa.Column('data_quality_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )

    # 인덱스 생성
    op.create_index('idx_ri_v3_company', 'raymonds_index_v3', ['company_id'])
    op.create_index('idx_ri_v3_year', 'raymonds_index_v3', ['fiscal_year'])
    op.create_index('idx_ri_v3_score', 'raymonds_index_v3', ['total_score'])
    op.create_index('idx_ri_v3_grade', 'raymonds_index_v3', ['grade'])

    # 유니크 제약조건 (company_id + fiscal_year)
    op.create_unique_constraint(
        'uq_raymonds_index_v3',
        'raymonds_index_v3',
        ['company_id', 'fiscal_year']
    )


def downgrade():
    """롤백: raymonds_index_v3 테이블 제거"""
    op.drop_table('raymonds_index_v3')
