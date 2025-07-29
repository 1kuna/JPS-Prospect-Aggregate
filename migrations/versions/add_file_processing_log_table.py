"""Add FileProcessingLog table for intelligent data retention

Revision ID: add_file_processing_log_table
Revises: 20e4b47362d1
Create Date: 2025-06-19 15:18:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_file_processing_log_table'
down_revision = '3c1daf8e563b'
branch_labels = None
depends_on = None


def upgrade():
    # Table is now created in the base migration (000_create_base_tables)
    # This migration is kept for migration history consistency
    pass


def downgrade():
    # Table is managed in the base migration
    pass