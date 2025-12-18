"""add convertible bonds table

Revision ID: 161765c6c15b
Revises: ad8b6057b679
Create Date: 2025-11-19 18:31:42.731288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '161765c6c15b'
down_revision: Union[str, None] = 'ad8b6057b679'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create convertible_bonds table
    op.create_table(
        'convertible_bonds',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bond_name', sa.String(length=200), nullable=True),
        sa.Column('bond_type', sa.String(length=50), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('maturity_date', sa.Date(), nullable=True),
        sa.Column('issue_amount', sa.Float(), nullable=True),
        sa.Column('interest_rate', sa.Float(), nullable=True),
        sa.Column('conversion_price', sa.Float(), nullable=True),
        sa.Column('conversion_ratio', sa.Float(), nullable=True),
        sa.Column('conversion_start_date', sa.Date(), nullable=True),
        sa.Column('conversion_end_date', sa.Date(), nullable=True),
        sa.Column('redemption_price', sa.Float(), nullable=True),
        sa.Column('early_redemption_date', sa.Date(), nullable=True),
        sa.Column('outstanding_amount', sa.Float(), nullable=True),
        sa.Column('converted_amount', sa.Float(), nullable=True),
        sa.Column('redeemed_amount', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('source_disclosure_id', sa.String(length=36), nullable=True),
        sa.Column('source_date', sa.String(length=8), nullable=True),
        sa.Column('ontology_object_id', sa.String(length=50), nullable=True),
        sa.Column('properties', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_cb_company_date', 'convertible_bonds', ['company_id', 'source_date'])
    op.create_index('idx_cb_issue_date', 'convertible_bonds', ['issue_date'])
    op.create_index('idx_cb_maturity_date', 'convertible_bonds', ['maturity_date'])
    op.create_index('idx_cb_status', 'convertible_bonds', ['status'])
    op.create_index('idx_unique_cb', 'convertible_bonds', ['company_id', 'bond_name', 'issue_date'], unique=True)
    op.create_index(op.f('ix_convertible_bonds_bond_type'), 'convertible_bonds', ['bond_type'])
    op.create_index(op.f('ix_convertible_bonds_company_id'), 'convertible_bonds', ['company_id'])
    op.create_index(op.f('ix_convertible_bonds_ontology_object_id'), 'convertible_bonds', ['ontology_object_id'], unique=True)
    op.create_index(op.f('ix_convertible_bonds_source_date'), 'convertible_bonds', ['source_date'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_convertible_bonds_source_date'), table_name='convertible_bonds')
    op.drop_index(op.f('ix_convertible_bonds_ontology_object_id'), table_name='convertible_bonds')
    op.drop_index(op.f('ix_convertible_bonds_company_id'), table_name='convertible_bonds')
    op.drop_index(op.f('ix_convertible_bonds_bond_type'), table_name='convertible_bonds')
    op.drop_index('idx_unique_cb', table_name='convertible_bonds')
    op.drop_index('idx_cb_status', table_name='convertible_bonds')
    op.drop_index('idx_cb_maturity_date', table_name='convertible_bonds')
    op.drop_index('idx_cb_issue_date', table_name='convertible_bonds')
    op.drop_index('idx_cb_company_date', table_name='convertible_bonds')

    # Drop table
    op.drop_table('convertible_bonds')
