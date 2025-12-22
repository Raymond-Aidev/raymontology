"""add_oauth_fields_to_users

Revision ID: 1ee6af06d77f
Revises: a1b2c3d4e5f6
Create Date: 2025-12-22 13:57:18.484462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1ee6af06d77f'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add OAuth fields to users table
    op.add_column('users', sa.Column('profile_image', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('oauth_provider', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('oauth_provider_id', sa.String(length=255), nullable=True))

    # Allow hashed_password to be nullable for OAuth users
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)

    # Create index for oauth_provider_id
    op.create_index(op.f('ix_users_oauth_provider_id'), 'users', ['oauth_provider_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_oauth_provider_id'), table_name='users')
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
    op.drop_column('users', 'oauth_provider_id')
    op.drop_column('users', 'oauth_provider')
    op.drop_column('users', 'profile_image')
