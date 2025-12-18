"""add affiliates table

Revision ID: ad8b6057b679
Revises: 092196cbada8
Create Date: 2025-11-19 15:25:56.185415

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad8b6057b679'
down_revision: Union[str, None] = '092196cbada8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create affiliates table
    op.create_table(
        'affiliates',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_company_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('affiliate_company_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('affiliate_name', sa.String(length=200), nullable=False),
        sa.Column('business_number', sa.String(length=20), nullable=True),
        sa.Column('relationship_type', sa.String(length=50), nullable=True),
        sa.Column('is_listed', sa.Boolean(), nullable=True),
        sa.Column('ownership_ratio', sa.Float(), nullable=True),
        sa.Column('voting_rights_ratio', sa.Float(), nullable=True),
        sa.Column('total_assets', sa.Float(), nullable=True),
        sa.Column('revenue', sa.Float(), nullable=True),
        sa.Column('net_income', sa.Float(), nullable=True),
        sa.Column('source_disclosure_id', sa.String(length=36), nullable=True),
        sa.Column('source_date', sa.String(length=8), nullable=True),
        sa.Column('ontology_object_id', sa.String(length=50), nullable=True),
        sa.Column('properties', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['affiliate_company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_affiliate_parent', 'affiliates', ['parent_company_id', 'source_date'])
    op.create_index('idx_affiliate_company', 'affiliates', ['affiliate_company_id'])
    op.create_index('idx_affiliate_type', 'affiliates', ['relationship_type'])
    op.create_index('idx_unique_affiliation', 'affiliates', ['parent_company_id', 'affiliate_company_id', 'source_date'], unique=True)
    op.create_index(op.f('ix_affiliates_affiliate_name'), 'affiliates', ['affiliate_name'])
    op.create_index(op.f('ix_affiliates_is_listed'), 'affiliates', ['is_listed'])
    op.create_index(op.f('ix_affiliates_ontology_object_id'), 'affiliates', ['ontology_object_id'], unique=True)
    op.create_index(op.f('ix_affiliates_parent_company_id'), 'affiliates', ['parent_company_id'])
    op.create_index(op.f('ix_affiliates_relationship_type'), 'affiliates', ['relationship_type'])
    op.create_index(op.f('ix_affiliates_source_date'), 'affiliates', ['source_date'])
    op.create_index(op.f('ix_affiliates_affiliate_company_id'), 'affiliates', ['affiliate_company_id'])

    # Create GIN trigram index for affiliate name (requires pg_trgm extension)
    op.execute('CREATE INDEX IF NOT EXISTS idx_affiliate_name_trigram ON affiliates USING gin (affiliate_name gin_trgm_ops)')


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_affiliate_name_trigram', table_name='affiliates')
    op.drop_index(op.f('ix_affiliates_affiliate_company_id'), table_name='affiliates')
    op.drop_index(op.f('ix_affiliates_source_date'), table_name='affiliates')
    op.drop_index(op.f('ix_affiliates_relationship_type'), table_name='affiliates')
    op.drop_index(op.f('ix_affiliates_parent_company_id'), table_name='affiliates')
    op.drop_index(op.f('ix_affiliates_ontology_object_id'), table_name='affiliates')
    op.drop_index(op.f('ix_affiliates_is_listed'), table_name='affiliates')
    op.drop_index(op.f('ix_affiliates_affiliate_name'), table_name='affiliates')
    op.drop_index('idx_unique_affiliation', table_name='affiliates')
    op.drop_index('idx_affiliate_type', table_name='affiliates')
    op.drop_index('idx_affiliate_company', table_name='affiliates')
    op.drop_index('idx_affiliate_parent', table_name='affiliates')

    # Drop table
    op.drop_table('affiliates')
