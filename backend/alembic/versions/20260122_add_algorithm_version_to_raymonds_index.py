"""Add algorithm_version column to raymonds_index table

Revision ID: 20260122_algo_version
Revises: 20260115_add_financial_ratios_table
Create Date: 2026-01-22

안전한 마이그레이션:
- algorithm_version 컬럼 추가 (기본값 '2.1')
- 기존 데이터는 모두 '2.1'로 설정
- v3.0 계산 시 '3.0' 값으로 저장
- 기존 서비스 영향 없음 (호환성 유지)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260122_algo_version'
down_revision = '20260115_financial_ratios'
branch_labels = None
depends_on = None


def upgrade():
    """
    algorithm_version 컬럼 추가

    - 기존 레코드: '2.1' (현재 운영 버전)
    - 신규 v3.0 레코드: '3.0'
    - 향후 버전 관리 및 병렬 운영 지원
    """
    # 1. algorithm_version 컬럼 추가 (기본값 '2.1')
    op.add_column(
        'raymonds_index',
        sa.Column(
            'algorithm_version',
            sa.String(10),
            nullable=False,
            server_default='2.1',
            comment='계산 알고리즘 버전 (2.1, 3.0 등)'
        )
    )

    # 2. 인덱스 추가 (버전별 조회 최적화)
    op.create_index(
        'idx_ri_algorithm_version',
        'raymonds_index',
        ['algorithm_version']
    )

    # 3. 복합 인덱스 추가 (회사+연도+버전 조회)
    op.create_index(
        'idx_ri_company_year_version',
        'raymonds_index',
        ['company_id', 'fiscal_year', 'algorithm_version']
    )


def downgrade():
    """롤백: algorithm_version 컬럼 제거"""
    # 인덱스 제거
    op.drop_index('idx_ri_company_year_version', table_name='raymonds_index')
    op.drop_index('idx_ri_algorithm_version', table_name='raymonds_index')

    # 컬럼 제거
    op.drop_column('raymonds_index', 'algorithm_version')
