"""create service_applications table

Revision ID: service_applications_001
Revises: stock_prices_001
Create Date: 2026-01-06

서비스 이용신청 테이블 추가 (수동 입금확인 방식)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'service_applications_001'
down_revision: Union[str, None] = 'stock_prices_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # service_applications 테이블 생성
    op.create_table(
        'service_applications',
        # Primary Key
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # 신청자 정보
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('applicant_email', sa.String(length=255), nullable=False),

        # 사업자등록증 파일 (Base64)
        sa.Column('business_registration_file_content', sa.Text(), nullable=True),
        sa.Column('business_registration_file_name', sa.String(length=255), nullable=True),
        sa.Column('business_registration_mime_type', sa.String(length=50), nullable=True),

        # 플랜 정보
        sa.Column('plan_type', sa.String(length=20), nullable=False),
        sa.Column('plan_amount', sa.Integer(), nullable=False),

        # 상태
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),

        # 처리 정보
        sa.Column('admin_memo', sa.Text(), nullable=True),
        sa.Column('processed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),

        # 이용권 정보 (승인 시)
        sa.Column('subscription_start_date', sa.Date(), nullable=True),
        sa.Column('subscription_end_date', sa.Date(), nullable=True),

        # 타임스탬프
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 인덱스 생성
    op.create_index('idx_service_applications_user', 'service_applications', ['user_id'], unique=False)
    op.create_index('idx_service_applications_status', 'service_applications', ['status'], unique=False)
    op.create_index('idx_service_applications_created', 'service_applications', ['created_at'], unique=False)


def downgrade() -> None:
    # 인덱스 삭제
    op.drop_index('idx_service_applications_created', table_name='service_applications')
    op.drop_index('idx_service_applications_status', table_name='service_applications')
    op.drop_index('idx_service_applications_user', table_name='service_applications')

    # 테이블 삭제
    op.drop_table('service_applications')
