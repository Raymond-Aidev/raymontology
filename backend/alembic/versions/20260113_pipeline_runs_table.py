"""add pipeline_runs table

Revision ID: 20260113_pipeline_runs
Revises:
Create Date: 2026-01-13

파이프라인 실행 이력을 저장하는 테이블입니다.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260113_pipeline_runs'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pipeline_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pipeline_type', sa.String(50), nullable=False),  # quarterly, daily, manual
        sa.Column('quarter', sa.String(10), nullable=True),  # Q1, Q2, Q3, Q4
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),  # pending, running, completed, failed
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),

        # 통계
        sa.Column('companies_processed', sa.Integer(), nullable=True),
        sa.Column('files_processed', sa.Integer(), nullable=True),
        sa.Column('officers_inserted', sa.Integer(), nullable=True),
        sa.Column('positions_inserted', sa.Integer(), nullable=True),
        sa.Column('errors_count', sa.Integer(), nullable=True),

        # 메타데이터
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('log_file_path', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),

        # 타임스탬프
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id')
    )

    # 인덱스
    op.create_index('ix_pipeline_runs_status', 'pipeline_runs', ['status'])
    op.create_index('ix_pipeline_runs_pipeline_type', 'pipeline_runs', ['pipeline_type'])
    op.create_index('ix_pipeline_runs_quarter_year', 'pipeline_runs', ['quarter', 'year'])
    op.create_index('ix_pipeline_runs_started_at', 'pipeline_runs', ['started_at'])


def downgrade() -> None:
    op.drop_index('ix_pipeline_runs_started_at', table_name='pipeline_runs')
    op.drop_index('ix_pipeline_runs_quarter_year', table_name='pipeline_runs')
    op.drop_index('ix_pipeline_runs_pipeline_type', table_name='pipeline_runs')
    op.drop_index('ix_pipeline_runs_status', table_name='pipeline_runs')
    op.drop_table('pipeline_runs')
