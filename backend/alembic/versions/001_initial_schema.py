"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')  # For trigram search

    # ========================================
    # companies 테이블
    # ========================================
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticker', sa.String(20), nullable=True, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('name_en', sa.String(200), nullable=True),
        sa.Column('business_number', sa.String(20), nullable=True, unique=True),
        sa.Column('sector', sa.String(100), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('market', sa.String(20), nullable=True),
        sa.Column('market_cap', sa.Float, nullable=True),
        sa.Column('revenue', sa.Float, nullable=True),
        sa.Column('net_income', sa.Float, nullable=True),
        sa.Column('total_assets', sa.Float, nullable=True),
        sa.Column('ownership_concentration', sa.Float, nullable=True),
        sa.Column('affiliate_transaction_ratio', sa.Float, nullable=True),
        sa.Column('cb_issuance_count', sa.Float, default=0),
        sa.Column('ontology_object_id', sa.String(50), nullable=True, unique=True),
        sa.Column('properties', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_company_ticker', 'companies', ['ticker'])
    op.create_index('idx_company_name', 'companies', ['name'])
    op.create_index('idx_company_market_sector', 'companies', ['market', 'sector'])
    op.create_index('idx_company_name_trigram', 'companies', ['name'], postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('idx_company_ontology', 'companies', ['ontology_object_id'])

    # ========================================
    # officers 테이블
    # ========================================
    op.create_table(
        'officers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('name_en', sa.String(100), nullable=True),
        sa.Column('resident_number_hash', sa.String(64), nullable=True, unique=True),
        sa.Column('position', sa.String(100), nullable=True),
        sa.Column('current_company_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('career_history', postgresql.JSONB, default=[]),
        sa.Column('education', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('board_count', sa.Integer, default=0),
        sa.Column('network_centrality', sa.Float, nullable=True),
        sa.Column('influence_score', sa.Float, default=0.0),
        sa.Column('has_conflict_of_interest', sa.Boolean, default=False),
        sa.Column('insider_trading_count', sa.Integer, default=0),
        sa.Column('ontology_object_id', sa.String(50), nullable=True, unique=True),
        sa.Column('properties', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_officer_name', 'officers', ['name'])
    op.create_index('idx_officer_position', 'officers', ['position'])
    op.create_index('idx_officer_influence', 'officers', ['influence_score'])
    op.create_index('idx_officer_name_trigram', 'officers', ['name'], postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('idx_officer_current_company', 'officers', ['current_company_id'])
    op.create_index('idx_officer_ontology', 'officers', ['ontology_object_id'])

    # ========================================
    # ontology_objects 테이블
    # ========================================
    op.create_table(
        'ontology_objects',
        sa.Column('object_id', sa.String(50), primary_key=True),
        sa.Column('object_type', sa.String(50), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer, nullable=False, default=1),
        sa.Column('source_documents', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('confidence', sa.Float, nullable=False, default=1.0),
        sa.Column('properties', postgresql.JSONB, nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_ontology_object_type', 'ontology_objects', ['object_type'])
    op.create_index('idx_ontology_object_valid', 'ontology_objects', ['valid_from', 'valid_until'])
    op.create_index('idx_ontology_object_properties', 'ontology_objects', ['properties'], postgresql_using='gin')
    op.create_index('idx_ontology_object_type_valid', 'ontology_objects', ['object_type', 'valid_from'])

    # ========================================
    # ontology_links 테이블
    # ========================================
    op.create_table(
        'ontology_links',
        sa.Column('link_id', sa.String(50), primary_key=True),
        sa.Column('link_type', sa.String(50), nullable=False),
        sa.Column('source_object_id', sa.String(50), nullable=False),
        sa.Column('target_object_id', sa.String(50), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('strength', sa.Float, nullable=False, default=0.5),
        sa.Column('confidence', sa.Float, nullable=False, default=1.0),
        sa.Column('properties', postgresql.JSONB, nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['source_object_id'], ['ontology_objects.object_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_object_id'], ['ontology_objects.object_id'], ondelete='CASCADE'),
    )
    op.create_index('idx_ontology_link_type', 'ontology_links', ['link_type'])
    op.create_index('idx_ontology_link_source', 'ontology_links', ['source_object_id'])
    op.create_index('idx_ontology_link_target', 'ontology_links', ['target_object_id'])
    op.create_index('idx_ontology_link_source_target', 'ontology_links', ['source_object_id', 'target_object_id'])
    op.create_index('idx_ontology_link_type_source', 'ontology_links', ['link_type', 'source_object_id'])
    op.create_index('idx_ontology_link_valid', 'ontology_links', ['valid_from', 'valid_until'])
    op.create_index('idx_ontology_link_properties', 'ontology_links', ['properties'], postgresql_using='gin')

    # ========================================
    # risk_signals 테이블
    # ========================================
    op.create_table(
        'risk_signals',
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('target_company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pattern_type', sa.String(100), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='riskseverity'), nullable=False),
        sa.Column('status', sa.Enum('DETECTED', 'INVESTIGATING', 'CONFIRMED', 'FALSE_POSITIVE', 'RESOLVED', name='riskstatus'), nullable=False),
        sa.Column('risk_score', sa.Float, nullable=False),
        sa.Column('exploitation_probability', sa.Float, nullable=True),
        sa.Column('expected_retail_loss', sa.Float, nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.String(2000), nullable=False),
        sa.Column('evidence', postgresql.JSONB, default=[]),
        sa.Column('involved_object_ids', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('involved_link_ids', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('ontology_object_id', sa.String(50), nullable=True, unique=True),
        sa.Column('properties', postgresql.JSONB, default={}),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['target_company_id'], ['companies.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_risk_signal_company_severity', 'risk_signals', ['target_company_id', 'severity'])
    op.create_index('idx_risk_signal_score', 'risk_signals', ['risk_score'])
    op.create_index('idx_risk_signal_status_severity', 'risk_signals', ['status', 'severity'])
    op.create_index('idx_risk_signal_pattern', 'risk_signals', ['pattern_type'])
    op.create_index('idx_risk_signal_detected', 'risk_signals', ['detected_at'])
    op.create_index('idx_risk_signal_ontology', 'risk_signals', ['ontology_object_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('risk_signals')
    op.drop_table('ontology_links')
    op.drop_table('ontology_objects')
    op.drop_table('officers')
    op.drop_table('companies')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS riskseverity')
    op.execute('DROP TYPE IF EXISTS riskstatus')
