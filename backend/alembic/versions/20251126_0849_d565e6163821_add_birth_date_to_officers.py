"""add_birth_date_to_officers

Revision ID: d565e6163821
Revises: c90ffb9c2a78
Create Date: 2025-11-26 08:49:53.070729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd565e6163821'
down_revision: Union[str, None] = 'c90ffb9c2a78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # officers 테이블에 birth_date, gender 컬럼 추가
    op.add_column('officers', sa.Column('birth_date', sa.String(10), nullable=True, comment='출생년월 (YYYY.MM 또는 YYYY-MM)'))
    op.add_column('officers', sa.Column('gender', sa.String(10), nullable=True, comment='성별 (남/여)'))

    # officer_positions 테이블에 birth_date 컬럼 추가 (각 재직 기록의 원본 데이터 보존)
    op.add_column('officer_positions', sa.Column('birth_date', sa.String(10), nullable=True, comment='출생년월'))
    op.add_column('officer_positions', sa.Column('gender', sa.String(10), nullable=True, comment='성별'))

    # 인덱스 추가
    op.create_index('idx_officer_birth_date', 'officers', ['birth_date'])
    op.create_index('idx_officer_gender', 'officers', ['gender'])


def downgrade() -> None:
    op.drop_index('idx_officer_gender', table_name='officers')
    op.drop_index('idx_officer_birth_date', table_name='officers')
    op.drop_column('officer_positions', 'gender')
    op.drop_column('officer_positions', 'birth_date')
    op.drop_column('officers', 'gender')
    op.drop_column('officers', 'birth_date')
