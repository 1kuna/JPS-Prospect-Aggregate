"""Create base tables for fresh installations

Revision ID: 000_create_base_tables
Revises: 
Create Date: 2025-07-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '000_create_base_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create data_sources table
    op.create_table('data_sources',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('scraper_key', sa.String(), nullable=True),
    sa.Column('last_scraped', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('frequency', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_data_sources_name'), 'data_sources', ['name'], unique=False)
    op.create_index(op.f('ix_data_sources_scraper_key'), 'data_sources', ['scraper_key'], unique=False)

    # Create prospects table
    op.create_table('prospects',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('native_id', sa.String(), nullable=True),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('ai_enhanced_title', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('agency', sa.Text(), nullable=True),
    sa.Column('naics', sa.String(), nullable=True),
    sa.Column('naics_description', sa.String(length=200), nullable=True),
    sa.Column('naics_source', sa.String(length=20), nullable=True),
    sa.Column('estimated_value', sa.Numeric(), nullable=True),
    sa.Column('est_value_unit', sa.String(), nullable=True),
    sa.Column('estimated_value_text', sa.String(length=100), nullable=True),
    sa.Column('estimated_value_min', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('estimated_value_max', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('estimated_value_single', sa.Numeric(precision=15, scale=2), nullable=True),
    sa.Column('release_date', sa.Date(), nullable=True),
    sa.Column('award_date', sa.Date(), nullable=True),
    sa.Column('award_fiscal_year', sa.Integer(), nullable=True),
    sa.Column('place_city', sa.Text(), nullable=True),
    sa.Column('place_state', sa.Text(), nullable=True),
    sa.Column('place_country', sa.Text(), nullable=True),
    sa.Column('contract_type', sa.Text(), nullable=True),
    sa.Column('set_aside', sa.Text(), nullable=True),
    sa.Column('set_aside_standardized', sa.String(length=50), nullable=True),
    sa.Column('set_aside_standardized_label', sa.String(length=100), nullable=True),
    sa.Column('primary_contact_email', sa.String(length=100), nullable=True),
    sa.Column('primary_contact_name', sa.String(length=100), nullable=True),
    sa.Column('loaded_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('ollama_processed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('ollama_model_version', sa.String(length=50), nullable=True),
    sa.Column('enhancement_status', sa.String(length=20), nullable=True),
    sa.Column('enhancement_started_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('enhancement_user_id', sa.Integer(), nullable=True),
    sa.Column('extra', sa.JSON(), nullable=True),
    sa.Column('source_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], name='fk_prospects_source_id_data_sources'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prospects_agency'), 'prospects', ['agency'], unique=False)
    op.create_index(op.f('ix_prospects_award_date'), 'prospects', ['award_date'], unique=False)
    op.create_index(op.f('ix_prospects_award_fiscal_year'), 'prospects', ['award_fiscal_year'], unique=False)
    op.create_index(op.f('ix_prospects_description'), 'prospects', ['description'], unique=False)
    op.create_index(op.f('ix_prospects_enhancement_started_at'), 'prospects', ['enhancement_started_at'], unique=False)
    op.create_index(op.f('ix_prospects_enhancement_status'), 'prospects', ['enhancement_status'], unique=False)
    op.create_index(op.f('ix_prospects_enhancement_user_id'), 'prospects', ['enhancement_user_id'], unique=False)
    op.create_index(op.f('ix_prospects_estimated_value_single'), 'prospects', ['estimated_value_single'], unique=False)
    op.create_index(op.f('ix_prospects_loaded_at'), 'prospects', ['loaded_at'], unique=False)
    op.create_index(op.f('ix_prospects_naics'), 'prospects', ['naics'], unique=False)
    op.create_index(op.f('ix_prospects_naics_source'), 'prospects', ['naics_source'], unique=False)
    op.create_index(op.f('ix_prospects_native_id'), 'prospects', ['native_id'], unique=False)
    op.create_index(op.f('ix_prospects_ollama_processed_at'), 'prospects', ['ollama_processed_at'], unique=False)
    op.create_index(op.f('ix_prospects_place_city'), 'prospects', ['place_city'], unique=False)
    op.create_index(op.f('ix_prospects_place_state'), 'prospects', ['place_state'], unique=False)
    op.create_index(op.f('ix_prospects_primary_contact_email'), 'prospects', ['primary_contact_email'], unique=False)
    op.create_index(op.f('ix_prospects_release_date'), 'prospects', ['release_date'], unique=False)
    op.create_index(op.f('ix_prospects_set_aside_standardized'), 'prospects', ['set_aside_standardized'], unique=False)
    op.create_index(op.f('ix_prospects_source_id'), 'prospects', ['source_id'], unique=False)
    op.create_index(op.f('ix_prospects_title'), 'prospects', ['title'], unique=False)

    # Create inferred_prospect_data table
    op.create_table('inferred_prospect_data',
    sa.Column('prospect_id', sa.String(), nullable=False),
    sa.Column('inferred_requirement_title', sa.Text(), nullable=True),
    sa.Column('inferred_requirement_description', sa.Text(), nullable=True),
    sa.Column('inferred_naics', sa.String(), nullable=True),
    sa.Column('inferred_naics_description', sa.String(length=200), nullable=True),
    sa.Column('inferred_estimated_value', sa.Float(), nullable=True),
    sa.Column('inferred_est_value_unit', sa.String(), nullable=True),
    sa.Column('inferred_estimated_value_min', sa.Float(), nullable=True),
    sa.Column('inferred_estimated_value_max', sa.Float(), nullable=True),
    sa.Column('inferred_solicitation_date', sa.Text(), nullable=True),
    sa.Column('inferred_award_date', sa.Text(), nullable=True),
    sa.Column('inferred_place_city', sa.Text(), nullable=True),
    sa.Column('inferred_place_state', sa.Text(), nullable=True),
    sa.Column('inferred_place_country', sa.Text(), nullable=True),
    sa.Column('inferred_contract_type', sa.Text(), nullable=True),
    sa.Column('inferred_set_aside', sa.Text(), nullable=True),
    sa.Column('inferred_primary_contact_email', sa.String(length=100), nullable=True),
    sa.Column('inferred_primary_contact_name', sa.String(length=100), nullable=True),
    sa.Column('llm_confidence_scores', sa.JSON(), nullable=True),
    sa.Column('inferred_at', sa.TIMESTAMP(timezone=False), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('inferred_by_model', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], name='fk_inferred_prospect_data_prospect_id_prospects'),
    sa.PrimaryKeyConstraint('prospect_id')
    )

    # Create scraper_status table
    op.create_table('scraper_status',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('last_checked', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('details', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], name='fk_scraper_status_source_id_data_sources'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scraper_status_source_id'), 'scraper_status', ['source_id'], unique=False)

    # Create go_no_go_decisions table
    op.create_table('go_no_go_decisions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('prospect_id', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('decision', sa.String(length=10), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], ),
    )
    op.create_index('ix_go_no_go_decisions_prospect_id', 'go_no_go_decisions', ['prospect_id'], unique=False)
    op.create_index('ix_go_no_go_decisions_user_id', 'go_no_go_decisions', ['user_id'], unique=False)
    op.create_index('ix_go_no_go_decisions_decision', 'go_no_go_decisions', ['decision'], unique=False)

    # Create settings table
    op.create_table('settings',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('value', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_settings_key'), 'settings', ['key'], unique=True)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('settings')
    op.drop_table('go_no_go_decisions')
    op.drop_table('llm_outputs')
    op.drop_table('scraper_status')
    op.drop_table('inferred_prospect_data')
    op.drop_table('prospects')
    op.drop_table('data_sources')


