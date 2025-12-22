"""add_password_reset_tokens

Revision ID: a1b2c3d4e5f6
Revises: d565e6163821
Create Date: 2025-12-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd565e6163821'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # password_reset_tokens 테이블 생성
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 인덱스 추가
    op.create_index('idx_password_reset_token_hash', 'password_reset_tokens', ['token_hash'])
    op.create_index('idx_password_reset_user_id', 'password_reset_tokens', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_password_reset_user_id', table_name='password_reset_tokens')
    op.drop_index('idx_password_reset_token_hash', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
