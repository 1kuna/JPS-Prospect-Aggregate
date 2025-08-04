"""Create base tables for fresh installations (SQLite compatible)

Revision ID: 000_create_base_tables_sqlite_fix
Revises: 
Create Date: 2025-08-01 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
# SQLite-compatible migration

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
    sa.Column('last_scraped', sa.TIMESTAMP(), nullable=True),
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
    sa.Column('estimated_value', sa.Float(), nullable=True),  # Changed from Numeric
    sa.Column('est_value_unit', sa.String(), nullable=True),
    sa.Column('estimated_value_text', sa.String(length=100), nullable=True),
    sa.Column('estimated_value_min', sa.Float(), nullable=True),  # Changed from Numeric
    sa.Column('estimated_value_max', sa.Float(), nullable=True),  # Changed from Numeric
    sa.Column('estimated_value_single', sa.Float(), nullable=True),  # Changed from Numeric
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
    sa.Column('loaded_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),  # SQLite compatible
    sa.Column('ollama_processed_at', sa.TIMESTAMP(), nullable=True),
    sa.Column('ollama_model_version', sa.String(length=50), nullable=True),
    sa.Column('enhancement_status', sa.String(length=20), nullable=True),
    sa.Column('enhancement_started_at', sa.TIMESTAMP(), nullable=True),
    sa.Column('enhancement_user_id', sa.Integer(), nullable=True),
    sa.Column('extra', sa.Text(), nullable=True),  # Changed from JSON for SQLite
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
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('prospect_id', sa.String(), nullable=False),
    sa.Column('inferred_naics', sa.Text(), nullable=True),
    sa.Column('inferred_naics_description', sa.String(length=200), nullable=True),
    sa.Column('inferred_estimated_value', sa.Text(), nullable=True),
    sa.Column('inferred_est_value_unit', sa.Text(), nullable=True),
    sa.Column('inferred_solicitation_date', sa.Text(), nullable=True),
    sa.Column('inferred_award_date', sa.Text(), nullable=True),
    sa.Column('inferred_place_city', sa.Text(), nullable=True),
    sa.Column('inferred_place_state', sa.Text(), nullable=True),
    sa.Column('inferred_place_country', sa.Text(), nullable=True),
    sa.Column('inferred_contract_type', sa.Text(), nullable=True),
    sa.Column('inferred_set_aside', sa.Text(), nullable=True),
    sa.Column('inferred_primary_contact_email', sa.String(length=100), nullable=True),
    sa.Column('inferred_primary_contact_name', sa.String(length=100), nullable=True),
    sa.Column('llm_confidence_scores', sa.Text(), nullable=True),  # Changed from JSON
    sa.Column('inferred_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('inferred_by_model', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], name='fk_inferred_prospect_data_prospect_id_prospects'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('prospect_id')
    )

    # Create scraper_status table
    op.create_table('scraper_status',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('last_checked', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('details', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], name='fk_scraper_status_source_id_data_sources'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scraper_status_last_checked'), 'scraper_status', ['last_checked'], unique=False)
    op.create_index(op.f('ix_scraper_status_source_id'), 'scraper_status', ['source_id'], unique=False)
    op.create_index(op.f('ix_scraper_status_status'), 'scraper_status', ['status'], unique=False)

    # Create duplicate_prospects table
    op.create_table('duplicate_prospects',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('original_id', sa.String(), nullable=False),
    sa.Column('duplicate_id', sa.String(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('match_type', sa.String(), nullable=True),
    sa.Column('marked_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('ai_data_preserved', sa.Boolean(), server_default=sa.text('0'), nullable=True),
    sa.ForeignKeyConstraint(['duplicate_id'], ['prospects.id'], name='fk_duplicate_prospects_duplicate_id_prospects'),
    sa.ForeignKeyConstraint(['original_id'], ['prospects.id'], name='fk_duplicate_prospects_original_id_prospects'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_duplicate_prospects_confidence'), 'duplicate_prospects', ['confidence'], unique=False)
    op.create_index(op.f('ix_duplicate_prospects_duplicate_id'), 'duplicate_prospects', ['duplicate_id'], unique=False)
    op.create_index(op.f('ix_duplicate_prospects_marked_at'), 'duplicate_prospects', ['marked_at'], unique=False)
    op.create_index(op.f('ix_duplicate_prospects_original_id'), 'duplicate_prospects', ['original_id'], unique=False)

    # Create file_processing_log table
    op.create_table('file_processing_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('source_name', sa.String(), nullable=True),
    sa.Column('file_path', sa.String(), nullable=True),
    sa.Column('processed_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('row_count', sa.Integer(), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # Create go_no_go_decisions table
    op.create_table('go_no_go_decisions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('prospect_id', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('decision', sa.String(length=10), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], name='fk_go_no_go_decisions_prospect_id_prospects'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_go_no_go_decisions_created_at'), 'go_no_go_decisions', ['created_at'], unique=False)
    op.create_index(op.f('ix_go_no_go_decisions_decision'), 'go_no_go_decisions', ['decision'], unique=False)
    op.create_index(op.f('ix_go_no_go_decisions_prospect_id'), 'go_no_go_decisions', ['prospect_id'], unique=False)
    op.create_index(op.f('ix_go_no_go_decisions_user_id'), 'go_no_go_decisions', ['user_id'], unique=False)
    op.create_index('idx_user_prospect_unique', 'go_no_go_decisions', ['user_id', 'prospect_id'], unique=True)

    # Create llm_outputs table
    op.create_table('llm_outputs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('timestamp', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('prospect_id', sa.String(), nullable=False),
    sa.Column('enhancement_type', sa.String(length=50), nullable=False),
    sa.Column('prompt', sa.Text(), nullable=False),
    sa.Column('response', sa.Text(), nullable=True),
    sa.Column('parsed_result', sa.Text(), nullable=True),  # Changed from JSON
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('processing_time', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], name='fk_llm_outputs_prospect_id_prospects'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_outputs_enhancement_type'), 'llm_outputs', ['enhancement_type'], unique=False)
    op.create_index(op.f('ix_llm_outputs_prospect_id'), 'llm_outputs', ['prospect_id'], unique=False)
    op.create_index(op.f('ix_llm_outputs_success'), 'llm_outputs', ['success'], unique=False)
    op.create_index(op.f('ix_llm_outputs_timestamp'), 'llm_outputs', ['timestamp'], unique=False)

    # Create settings table
    op.create_table('settings',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('settings')
    op.drop_table('llm_outputs')
    op.drop_table('go_no_go_decisions')
    op.drop_table('file_processing_log')
    op.drop_table('duplicate_prospects')
    op.drop_table('scraper_status')
    op.drop_table('inferred_prospect_data')
    op.drop_table('prospects')
    op.drop_table('data_sources')