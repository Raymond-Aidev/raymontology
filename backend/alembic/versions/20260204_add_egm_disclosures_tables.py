"""Add EGM (임시주주총회) disclosures and dispute officers tables

Revision ID: 20260204_egm
Revises: 20260126_add_ma_target_tables
Create Date: 2026-02-04

경영분쟁 임원 수집 시스템을 위한 신규 테이블:
1. egm_disclosures - 임시주주총회 공시 정보
2. dispute_officers - 분쟁 선임 임원 정보
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260204_egm'
down_revision: Union[str, None] = '20260126_ma_target'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # 1. egm_disclosures 테이블 생성
    # ==========================================================================
    op.create_table(
        'egm_disclosures',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),

        # 공시 메타데이터
        sa.Column('disclosure_id', sa.String(50), nullable=False),  # rcept_no
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('corp_code', sa.String(8), nullable=False),
        sa.Column('corp_name', sa.String(200), nullable=True),

        # 임시주주총회 정보
        sa.Column('egm_date', sa.Date(), nullable=True),
        sa.Column('egm_type', sa.String(30), nullable=True, server_default='REGULAR'),
        sa.Column('disclosure_date', sa.Date(), nullable=True),

        # 경영분쟁 분류
        sa.Column('is_dispute_related', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('dispute_type', sa.String(50), nullable=True),
        sa.Column('dispute_confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('dispute_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),

        # 안건 정보
        sa.Column('agenda_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('officer_changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),

        # 임원 변동 요약
        sa.Column('officers_appointed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('officers_dismissed', sa.Integer(), nullable=False, server_default='0'),

        # 파싱 메타데이터
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('parse_status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('parse_confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('parse_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('parse_version', sa.String(10), nullable=True, server_default='v1.0'),

        # 수동 검토
        sa.Column('needs_manual_review', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('manual_review_reason', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),

        # 타임스탬프
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Primary Key
        sa.PrimaryKeyConstraint('id'),

        # Foreign Keys
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
    )

    # egm_disclosures 인덱스
    op.create_index('idx_egm_disclosures_disclosure', 'egm_disclosures', ['disclosure_id'], unique=True)
    op.create_index('idx_egm_disclosures_company', 'egm_disclosures', ['company_id'])
    op.create_index('idx_egm_disclosures_corp_code', 'egm_disclosures', ['corp_code'])
    op.create_index('idx_egm_disclosures_dispute', 'egm_disclosures', ['is_dispute_related'])
    op.create_index('idx_egm_disclosures_egm_date', 'egm_disclosures', ['egm_date'])
    op.create_index('idx_egm_disclosures_parse_status', 'egm_disclosures', ['parse_status'])
    op.create_index('idx_egm_disclosures_needs_review', 'egm_disclosures', ['needs_manual_review'])

    # ==========================================================================
    # 2. dispute_officers 테이블 생성
    # ==========================================================================
    op.create_table(
        'dispute_officers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),

        # 임원 연결 (소프트 참조)
        sa.Column('officer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('officer_match_confidence', sa.String(10), nullable=True),

        # 임원 기본 정보
        sa.Column('officer_name', sa.String(100), nullable=False),
        sa.Column('birth_date', sa.String(10), nullable=True),
        sa.Column('gender', sa.String(10), nullable=True),

        # 선임 정보
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('position', sa.String(100), nullable=True),
        sa.Column('egm_disclosure_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appointment_date', sa.Date(), nullable=True),

        # 경력 정보
        sa.Column('career_from_disclosure', sa.Text(), nullable=True),
        sa.Column('career_parsed', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('education_from_disclosure', sa.Text(), nullable=True),

        # 분쟁 맥락
        sa.Column('appointment_context', sa.String(30), nullable=False, server_default='UNKNOWN'),
        sa.Column('replaced_officer_name', sa.String(100), nullable=True),
        sa.Column('replacement_reason', sa.Text(), nullable=True),

        # 투표 결과
        sa.Column('vote_result', sa.String(200), nullable=True),
        sa.Column('vote_for_ratio', sa.String(10), nullable=True),
        sa.Column('vote_against_ratio', sa.String(10), nullable=True),

        # 안건 정보
        sa.Column('agenda_number', sa.String(20), nullable=True),
        sa.Column('agenda_title', sa.String(300), nullable=True),

        # 검증 상태
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by', sa.String(100), nullable=True),

        # 파싱 메타데이터
        sa.Column('extraction_confidence', sa.String(10), nullable=True),
        sa.Column('extraction_source', sa.String(50), nullable=True),

        # 타임스탬프
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Primary Key
        sa.PrimaryKeyConstraint('id'),

        # Foreign Keys
        sa.ForeignKeyConstraint(['officer_id'], ['officers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['egm_disclosure_id'], ['egm_disclosures.id'], ondelete='CASCADE'),
    )

    # dispute_officers 인덱스
    op.create_index('idx_dispute_officers_name', 'dispute_officers', ['officer_name'])
    op.create_index('idx_dispute_officers_officer', 'dispute_officers', ['officer_id'])
    op.create_index('idx_dispute_officers_company', 'dispute_officers', ['company_id'])
    op.create_index('idx_dispute_officers_egm', 'dispute_officers', ['egm_disclosure_id'])
    op.create_index('idx_dispute_officers_context', 'dispute_officers', ['appointment_context'])
    op.create_index('idx_dispute_officers_verified', 'dispute_officers', ['is_verified'])
    op.create_index('idx_dispute_officers_position', 'dispute_officers', ['position'])


def downgrade() -> None:
    # dispute_officers 테이블 삭제
    op.drop_index('idx_dispute_officers_position', table_name='dispute_officers')
    op.drop_index('idx_dispute_officers_verified', table_name='dispute_officers')
    op.drop_index('idx_dispute_officers_context', table_name='dispute_officers')
    op.drop_index('idx_dispute_officers_egm', table_name='dispute_officers')
    op.drop_index('idx_dispute_officers_company', table_name='dispute_officers')
    op.drop_index('idx_dispute_officers_officer', table_name='dispute_officers')
    op.drop_index('idx_dispute_officers_name', table_name='dispute_officers')
    op.drop_table('dispute_officers')

    # egm_disclosures 테이블 삭제
    op.drop_index('idx_egm_disclosures_needs_review', table_name='egm_disclosures')
    op.drop_index('idx_egm_disclosures_parse_status', table_name='egm_disclosures')
    op.drop_index('idx_egm_disclosures_egm_date', table_name='egm_disclosures')
    op.drop_index('idx_egm_disclosures_dispute', table_name='egm_disclosures')
    op.drop_index('idx_egm_disclosures_corp_code', table_name='egm_disclosures')
    op.drop_index('idx_egm_disclosures_company', table_name='egm_disclosures')
    op.drop_index('idx_egm_disclosures_disclosure', table_name='egm_disclosures')
    op.drop_table('egm_disclosures')
