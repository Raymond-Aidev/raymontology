"""add disclosure models

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add corp_code to companies table
    op.add_column('companies', sa.Column('corp_code', sa.String(length=8), nullable=True))
    op.create_index('ix_companies_corp_code', 'companies', ['corp_code'], unique=True)

    # Create disclosures table
    op.create_table(
        'disclosures',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rcept_no', sa.String(length=14), nullable=False, comment='접수번호 (고유키)'),
        sa.Column('corp_code', sa.String(length=8), nullable=False, comment='기업 코드'),
        sa.Column('corp_name', sa.String(length=200), nullable=False),
        sa.Column('stock_code', sa.String(length=6), nullable=True),
        sa.Column('report_nm', sa.String(length=500), nullable=False, comment='보고서명'),
        sa.Column('rcept_dt', sa.String(length=8), nullable=False, comment='접수일자 (YYYYMMDD)'),
        sa.Column('flr_nm', sa.String(length=200), nullable=True, comment='공시 제출인명'),
        sa.Column('rm', sa.Text(), nullable=True, comment='비고'),
        sa.Column('storage_url', sa.String(length=500), nullable=True, comment='S3/R2 문서 URL'),
        sa.Column('storage_key', sa.String(length=500), nullable=True, comment='S3/R2 객체 키'),
        sa.Column('crawled_at', sa.DateTime(), nullable=False, comment='크롤링 시각'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='업데이트 시각'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True, comment='추가 메타데이터 (JSON)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['corp_code'], ['companies.corp_code'], ondelete='CASCADE'),
    )
    op.create_index('ix_disclosures_rcept_no', 'disclosures', ['rcept_no'], unique=True)
    op.create_index('ix_disclosures_corp_code', 'disclosures', ['corp_code'])
    op.create_index('ix_disclosures_stock_code', 'disclosures', ['stock_code'])
    op.create_index('ix_disclosures_rcept_dt', 'disclosures', ['rcept_dt'])
    op.create_index('idx_disclosures_corp_date', 'disclosures', ['corp_code', 'rcept_dt'])
    op.create_index('idx_disclosures_stock_date', 'disclosures', ['stock_code', 'rcept_dt'])
    op.create_index(
        'idx_disclosures_report_nm_trgm',
        'disclosures',
        ['report_nm'],
        postgresql_using='gin',
        postgresql_ops={'report_nm': 'gin_trgm_ops'}
    )

    # Create disclosure_parsed_data table
    op.create_table(
        'disclosure_parsed_data',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('rcept_no', sa.String(length=14), nullable=False),
        sa.Column('parsed_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='파싱된 공시 데이터'),
        sa.Column('parsed_at', sa.DateTime(), nullable=False, comment='파싱 시각'),
        sa.Column('parser_version', sa.String(length=20), nullable=True, comment='파서 버전'),
        sa.Column('sections_count', sa.Integer(), server_default='0', nullable=True, comment='섹션 수'),
        sa.Column('tables_count', sa.Integer(), server_default='0', nullable=True, comment='테이블 수'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['rcept_no'], ['disclosures.rcept_no'], ondelete='CASCADE'),
    )
    op.create_index('ix_disclosure_parsed_data_rcept_no', 'disclosure_parsed_data', ['rcept_no'], unique=True)
    op.create_index(
        'idx_parsed_data_jsonb',
        'disclosure_parsed_data',
        ['parsed_data'],
        postgresql_using='gin'
    )

    # Create crawl_jobs table
    op.create_table(
        'crawl_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_type', sa.String(length=50), nullable=False, comment='작업 유형 (full, recent, company)'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending', comment='작업 상태 (pending, running, completed, failed)'),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True, comment='작업 파라미터 (JSON)'),
        sa.Column('total_companies', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_disclosures', sa.Integer(), server_default='0', nullable=True),
        sa.Column('downloaded_documents', sa.Integer(), server_default='0', nullable=True),
        sa.Column('failed_downloads', sa.Integer(), server_default='0', nullable=True),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True, comment='에러 목록 (JSON)'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='에러 메시지'),
        sa.Column('started_at', sa.DateTime(), nullable=True, comment='시작 시각'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='완료 시각'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='생성 시각'),
        sa.Column('task_id', sa.String(length=100), nullable=True, comment='Celery 태스크 ID'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_crawl_jobs_job_type', 'crawl_jobs', ['job_type'])
    op.create_index('ix_crawl_jobs_status', 'crawl_jobs', ['status'])
    op.create_index('ix_crawl_jobs_task_id', 'crawl_jobs', ['task_id'], unique=True)
    op.create_index('idx_crawl_jobs_type_status', 'crawl_jobs', ['job_type', 'status'])


def downgrade() -> None:
    # Drop crawl_jobs table
    op.drop_index('idx_crawl_jobs_type_status', table_name='crawl_jobs')
    op.drop_index('ix_crawl_jobs_task_id', table_name='crawl_jobs')
    op.drop_index('ix_crawl_jobs_status', table_name='crawl_jobs')
    op.drop_index('ix_crawl_jobs_job_type', table_name='crawl_jobs')
    op.drop_table('crawl_jobs')

    # Drop disclosure_parsed_data table
    op.drop_index('idx_parsed_data_jsonb', table_name='disclosure_parsed_data')
    op.drop_index('ix_disclosure_parsed_data_rcept_no', table_name='disclosure_parsed_data')
    op.drop_table('disclosure_parsed_data')

    # Drop disclosures table
    op.drop_index('idx_disclosures_report_nm_trgm', table_name='disclosures')
    op.drop_index('idx_disclosures_stock_date', table_name='disclosures')
    op.drop_index('idx_disclosures_corp_date', table_name='disclosures')
    op.drop_index('ix_disclosures_rcept_dt', table_name='disclosures')
    op.drop_index('ix_disclosures_stock_code', table_name='disclosures')
    op.drop_index('ix_disclosures_corp_code', table_name='disclosures')
    op.drop_index('ix_disclosures_rcept_no', table_name='disclosures')
    op.drop_table('disclosures')

    # Remove corp_code from companies table
    op.drop_index('ix_companies_corp_code', table_name='companies')
    op.drop_column('companies', 'corp_code')
