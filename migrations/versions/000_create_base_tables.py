"""Create base tables for fresh installations

Revision ID: 000_create_base_tables
Revises: 
Create Date: 2025-07-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

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
    sa.Column('loaded_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
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
    sa.Column('llm_confidence_scores', sa.JSON(), nullable=True),
    sa.Column('inferred_at', sa.TIMESTAMP(timezone=False), server_default=sa.text('now()'), nullable=True),
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
    sa.Column('last_checked', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('details', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], name='fk_scraper_status_source_id_data_sources'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scraper_status_source_id'), 'scraper_status', ['source_id'], unique=False)

    # Create users table
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=False)

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
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
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
    
    # Insert the maintenance_mode setting with default value
    op.execute("INSERT INTO settings (key, value, description) VALUES ('maintenance_mode', 'false', 'Controls whether the site is in maintenance mode')")

    # Populate initial data sources - these are hardcoded and required for the application to function
    data_sources_sql = """
    INSERT INTO data_sources (name, scraper_key, url, description, frequency) VALUES
    ('Acquisition Gateway', 'ACQGW', 'https://hallways.cap.gsa.gov/app/#/gateway/acquisition-gateway/forecast-documents', 'GSA Acquisition Gateway forecast documents', 'weekly'),
    ('Department of Commerce', 'DOC', 'https://www.commerce.gov/', 'Department of Commerce procurement forecasts', 'weekly'),
    ('Department of Homeland Security', 'DHS', 'https://www.dhs.gov/', 'DHS procurement forecasts', 'weekly'),
    ('Department of Justice', 'DOJ', 'https://www.justice.gov/', 'DOJ procurement forecasts', 'weekly'),
    ('Department of State', 'DOS', 'https://www.state.gov/', 'DOS procurement forecasts', 'weekly'),
    ('Department of Transportation', 'DOT', 'https://www.transportation.gov/', 'DOT procurement forecasts', 'weekly'),
    ('Health and Human Services', 'HHS', 'https://www.hhs.gov/', 'HHS procurement forecasts', 'weekly'),
    ('Social Security Administration', 'SSA', 'https://www.ssa.gov/', 'SSA procurement forecasts', 'weekly'),
    ('Department of Treasury', 'TREAS', 'https://www.treasury.gov/', 'Treasury procurement forecasts', 'weekly');
    """
    op.execute(data_sources_sql)

    # Create initial scraper status for each data source
    # Note: This uses a subquery to reference the newly inserted data sources
    initial_status_sql = """
    INSERT INTO scraper_status (source_id, status, last_checked, details)
    SELECT id, 'pending', CURRENT_TIMESTAMP, 'Newly created data source, awaiting first scrape.'
    FROM data_sources;
    """
    op.execute(initial_status_sql)

    # Create file_processing_logs table
    op.create_table('file_processing_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('file_path', sa.String(length=500), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('file_timestamp', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('processing_started_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('processing_completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('records_extracted', sa.Integer(), nullable=True),
    sa.Column('records_inserted', sa.Integer(), nullable=True),
    sa.Column('schema_columns', sa.JSON(), nullable=True),
    sa.Column('schema_issues', sa.JSON(), nullable=True),
    sa.Column('validation_warnings', sa.JSON(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('processing_duration', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_file_processing_logs_file_name'), 'file_processing_logs', ['file_name'], unique=False)
    op.create_index(op.f('ix_file_processing_logs_file_path'), 'file_processing_logs', ['file_path'], unique=False)
    op.create_index(op.f('ix_file_processing_logs_file_timestamp'), 'file_processing_logs', ['file_timestamp'], unique=False)
    op.create_index(op.f('ix_file_processing_logs_processing_completed_at'), 'file_processing_logs', ['processing_completed_at'], unique=False)
    op.create_index(op.f('ix_file_processing_logs_processing_started_at'), 'file_processing_logs', ['processing_started_at'], unique=False)
    op.create_index(op.f('ix_file_processing_logs_source_id'), 'file_processing_logs', ['source_id'], unique=False)
    op.create_index(op.f('ix_file_processing_logs_success'), 'file_processing_logs', ['success'], unique=False)


def downgrade():
    # Drop tables in reverse order to handle foreign key dependencies
    op.drop_table('file_processing_logs')
    op.drop_table('settings')
    op.drop_table('go_no_go_decisions')
    op.drop_table('users')
    op.drop_table('scraper_status')
    op.drop_table('inferred_prospect_data')
    op.drop_table('prospects')
    op.drop_table('data_sources')