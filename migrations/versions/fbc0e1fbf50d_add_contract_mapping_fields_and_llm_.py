"""add_contract_mapping_fields_and_llm_support

Revision ID: fbc0e1fbf50d
Revises: 4627cb27031b
Create Date: 2025-06-02 19:26:15.092858

"""
from alembic import op
import sqlalchemy as sa
import sys
import os

# Add the migrations directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from alembic_helpers import safe_add_column, safe_create_index, table_exists
except ImportError:
    # Fallback implementation if helper is not available
    from sqlalchemy import inspect
    
    def column_exists(table_name, column_name):
        conn = op.get_bind()
        inspector = inspect(conn)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    
    def safe_add_column(table_name, column):
        if not column_exists(table_name, column.name):
            op.add_column(table_name, column)
            return True
        return False
    
    def safe_create_index(index_name, table_name, columns, **kwargs):
        conn = op.get_bind()
        result = conn.execute(
            sa.text("SELECT 1 FROM sqlite_master WHERE type='index' AND name = :index_name"),
            {"index_name": index_name}
        )
        if result.scalar() is None:
            op.create_index(index_name, table_name, columns, **kwargs)
            return True
        return False
    
    def table_exists(table_name):
        conn = op.get_bind()
        inspector = inspect(conn)
        return table_name in inspector.get_table_names()


# revision identifiers, used by Alembic.
revision = 'fbc0e1fbf50d'
down_revision = '4627cb27031b'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to the prospects table for contract mapping standardization
    # These fields support the modular LLM enhancement approach
    
    # Only proceed if the prospects table exists
    if not table_exists('prospects'):
        return
    
    # Core fields that might be populated from original data
    safe_add_column('prospects', sa.Column('estimated_value_text', sa.String(100), nullable=True))
    safe_add_column('prospects', sa.Column('naics_description', sa.String(200), nullable=True))
    safe_add_column('prospects', sa.Column('naics_source', sa.String(20), nullable=True))  # 'original', 'llm_inferred', 'llm_enhanced'
    
    # LLM-enhanced fields (populated by optional qwen3:8b module)
    safe_add_column('prospects', sa.Column('estimated_value_min', sa.Numeric(15, 2), nullable=True))
    safe_add_column('prospects', sa.Column('estimated_value_max', sa.Numeric(15, 2), nullable=True))
    safe_add_column('prospects', sa.Column('estimated_value_single', sa.Numeric(15, 2), nullable=True))
    safe_add_column('prospects', sa.Column('primary_contact_email', sa.String(100), nullable=True))
    safe_add_column('prospects', sa.Column('primary_contact_name', sa.String(100), nullable=True))
    
    # LLM processing metadata
    safe_add_column('prospects', sa.Column('ollama_processed_at', sa.TIMESTAMP(timezone=True), nullable=True))
    safe_add_column('prospects', sa.Column('ollama_model_version', sa.String(50), nullable=True))
    
    # Add indexes for LLM-enhanced fields
    safe_create_index('idx_naics_source', 'prospects', ['naics_source'])
    safe_create_index('idx_estimated_value_single', 'prospects', ['estimated_value_single'])
    safe_create_index('idx_primary_contact_email', 'prospects', ['primary_contact_email'])
    safe_create_index('idx_ollama_processed_at', 'prospects', ['ollama_processed_at'])
    
    # Update the inferred_prospect_data table to add new inferable fields
    if table_exists('inferred_prospect_data'):
        safe_add_column('inferred_prospect_data', sa.Column('inferred_naics_description', sa.String(200), nullable=True))
        safe_add_column('inferred_prospect_data', sa.Column('inferred_estimated_value_min', sa.Float, nullable=True))
        safe_add_column('inferred_prospect_data', sa.Column('inferred_estimated_value_max', sa.Float, nullable=True))
        safe_add_column('inferred_prospect_data', sa.Column('inferred_primary_contact_email', sa.String(100), nullable=True))
        safe_add_column('inferred_prospect_data', sa.Column('inferred_primary_contact_name', sa.String(100), nullable=True))
        safe_add_column('inferred_prospect_data', sa.Column('llm_confidence_scores', sa.JSON, nullable=True))  # Store confidence scores for each inferred field


def downgrade():
    # Import safe drop functions
    try:
        from alembic_helpers import safe_drop_column, safe_drop_index
    except ImportError:
        # Fallback implementation
        def safe_drop_column(table_name, column_name):
            if column_exists(table_name, column_name):
                op.drop_column(table_name, column_name)
                return True
            return False
        
        def safe_drop_index(index_name, table_name=None):
            conn = op.get_bind()
            result = conn.execute(
                sa.text("SELECT 1 FROM sqlite_master WHERE type='index' AND name = :index_name"),
                {"index_name": index_name}
            )
            if result.scalar() is not None:
                op.drop_index(index_name, table_name=table_name)
                return True
            return False
    
    # Drop indexes first
    safe_drop_index('idx_ollama_processed_at', 'prospects')
    safe_drop_index('idx_primary_contact_email', 'prospects')
    safe_drop_index('idx_estimated_value_single', 'prospects')
    safe_drop_index('idx_naics_source', 'prospects')
    
    # Drop columns from inferred_prospect_data
    if table_exists('inferred_prospect_data'):
        safe_drop_column('inferred_prospect_data', 'llm_confidence_scores')
        safe_drop_column('inferred_prospect_data', 'inferred_primary_contact_name')
        safe_drop_column('inferred_prospect_data', 'inferred_primary_contact_email')
        safe_drop_column('inferred_prospect_data', 'inferred_estimated_value_max')
        safe_drop_column('inferred_prospect_data', 'inferred_estimated_value_min')
        safe_drop_column('inferred_prospect_data', 'inferred_naics_description')
    
    # Drop columns from prospects
    if table_exists('prospects'):
        safe_drop_column('prospects', 'ollama_model_version')
        safe_drop_column('prospects', 'ollama_processed_at')
        safe_drop_column('prospects', 'primary_contact_name')
        safe_drop_column('prospects', 'primary_contact_email')
        safe_drop_column('prospects', 'estimated_value_single')
        safe_drop_column('prospects', 'estimated_value_max')
        safe_drop_column('prospects', 'estimated_value_min')
        safe_drop_column('prospects', 'naics_source')
        safe_drop_column('prospects', 'naics_description')
        safe_drop_column('prospects', 'estimated_value_text')
