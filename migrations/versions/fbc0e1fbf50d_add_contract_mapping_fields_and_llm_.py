"""add_contract_mapping_fields_and_llm_support

Revision ID: fbc0e1fbf50d
Revises: 4627cb27031b
Create Date: 2025-06-02 19:26:15.092858

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fbc0e1fbf50d'
down_revision = '4627cb27031b'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to the prospects table for contract mapping standardization
    # These fields support the modular LLM enhancement approach
    
    # Core fields that might be populated from original data
    op.add_column('prospects', sa.Column('estimated_value_text', sa.String(100), nullable=True))
    op.add_column('prospects', sa.Column('naics_description', sa.String(200), nullable=True))
    op.add_column('prospects', sa.Column('naics_source', sa.String(20), nullable=True))  # 'original', 'llm_inferred', 'llm_enhanced'
    
    # LLM-enhanced fields (populated by optional qwen3:8b module)
    op.add_column('prospects', sa.Column('estimated_value_min', sa.Numeric(15, 2), nullable=True))
    op.add_column('prospects', sa.Column('estimated_value_max', sa.Numeric(15, 2), nullable=True))
    op.add_column('prospects', sa.Column('estimated_value_single', sa.Numeric(15, 2), nullable=True))
    op.add_column('prospects', sa.Column('primary_contact_email', sa.String(100), nullable=True))
    op.add_column('prospects', sa.Column('primary_contact_name', sa.String(100), nullable=True))
    
    # LLM processing metadata
    op.add_column('prospects', sa.Column('ollama_processed_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('prospects', sa.Column('ollama_model_version', sa.String(50), nullable=True))
    
    # Add indexes for LLM-enhanced fields
    op.create_index('idx_naics_source', 'prospects', ['naics_source'])
    op.create_index('idx_estimated_value_single', 'prospects', ['estimated_value_single'])
    op.create_index('idx_primary_contact_email', 'prospects', ['primary_contact_email'])
    op.create_index('idx_ollama_processed_at', 'prospects', ['ollama_processed_at'])
    
    # Update the inferred_prospect_data table to add new inferable fields
    op.add_column('inferred_prospect_data', sa.Column('inferred_naics_description', sa.String(200), nullable=True))
    op.add_column('inferred_prospect_data', sa.Column('inferred_estimated_value_min', sa.Float, nullable=True))
    op.add_column('inferred_prospect_data', sa.Column('inferred_estimated_value_max', sa.Float, nullable=True))
    op.add_column('inferred_prospect_data', sa.Column('inferred_primary_contact_email', sa.String(100), nullable=True))
    op.add_column('inferred_prospect_data', sa.Column('inferred_primary_contact_name', sa.String(100), nullable=True))
    op.add_column('inferred_prospect_data', sa.Column('llm_confidence_scores', sa.JSON, nullable=True))  # Store confidence scores for each inferred field


def downgrade():
    # Drop indexes first
    op.drop_index('idx_ollama_processed_at', 'prospects')
    op.drop_index('idx_primary_contact_email', 'prospects')
    op.drop_index('idx_estimated_value_single', 'prospects')
    op.drop_index('idx_naics_source', 'prospects')
    
    # Drop columns from inferred_prospect_data
    op.drop_column('inferred_prospect_data', 'llm_confidence_scores')
    op.drop_column('inferred_prospect_data', 'inferred_primary_contact_name')
    op.drop_column('inferred_prospect_data', 'inferred_primary_contact_email')
    op.drop_column('inferred_prospect_data', 'inferred_estimated_value_max')
    op.drop_column('inferred_prospect_data', 'inferred_estimated_value_min')
    op.drop_column('inferred_prospect_data', 'inferred_naics_description')
    
    # Drop columns from prospects
    op.drop_column('prospects', 'ollama_model_version')
    op.drop_column('prospects', 'ollama_processed_at')
    op.drop_column('prospects', 'primary_contact_name')
    op.drop_column('prospects', 'primary_contact_email')
    op.drop_column('prospects', 'estimated_value_single')
    op.drop_column('prospects', 'estimated_value_max')
    op.drop_column('prospects', 'estimated_value_min')
    op.drop_column('prospects', 'naics_source')
    op.drop_column('prospects', 'naics_description')
    op.drop_column('prospects', 'estimated_value_text')
