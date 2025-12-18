"""add_officer_positions_temporal_table

Revision ID: c90ffb9c2a78
Revises: 16ab7b40051b
Create Date: 2025-11-21 12:52:07.742838

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c90ffb9c2a78'
down_revision: Union[str, None] = '16ab7b40051b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # officer_positions 테이블 생성 (temporal 데이터 저장)
    op.create_table(
        'officer_positions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('officer_id', UUID(as_uuid=True), sa.ForeignKey('officers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('position', sa.String(100), nullable=False),
        sa.Column('term_start_date', sa.Date, nullable=True, index=True),
        sa.Column('term_end_date', sa.Date, nullable=True, index=True),
        sa.Column('is_current', sa.Boolean, default=False, nullable=False, index=True),
        sa.Column('source_disclosure_id', sa.String(36), nullable=True),
        sa.Column('source_report_date', sa.Date, nullable=True, index=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )

    # UNIQUE 제약조건 추가 (중복 방지)
    op.create_unique_constraint(
        'uq_officer_position_term',
        'officer_positions',
        ['officer_id', 'company_id', 'term_start_date', 'source_disclosure_id']
    )

    # cb_subscribers 테이블에 officer_id와 subscriber_company_id 외래키 추가
    op.add_column('cb_subscribers',
        sa.Column('subscriber_officer_id', UUID(as_uuid=True), sa.ForeignKey('officers.id', ondelete='SET NULL'), nullable=True)
    )
    op.add_column('cb_subscribers',
        sa.Column('subscriber_company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='SET NULL'), nullable=True)
    )

    # 인덱스 추가
    op.create_index('ix_cb_subscribers_officer_id', 'cb_subscribers', ['subscriber_officer_id'])
    op.create_index('ix_cb_subscribers_company_id', 'cb_subscribers', ['subscriber_company_id'])

    # source_report_date 컬럼 추가 (audit trail)
    op.add_column('cb_subscribers',
        sa.Column('source_report_date', sa.Date, nullable=True, index=True)
    )


def downgrade() -> None:
    # cb_subscribers 테이블 변경사항 롤백
    op.drop_index('ix_cb_subscribers_company_id', 'cb_subscribers')
    op.drop_index('ix_cb_subscribers_officer_id', 'cb_subscribers')
    op.drop_column('cb_subscribers', 'source_report_date')
    op.drop_column('cb_subscribers', 'subscriber_company_id')
    op.drop_column('cb_subscribers', 'subscriber_officer_id')

    # officer_positions 테이블 삭제
    op.drop_constraint('uq_officer_position_term', 'officer_positions')
    op.drop_table('officer_positions')
