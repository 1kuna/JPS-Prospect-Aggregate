"""Add settings table for maintenance mode

Revision ID: add_settings_table
Revises: 5fb5cc7eff5b
Create Date: 2025-06-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_settings_table'
down_revision = '5fb5cc7eff5b'
branch_labels = None
depends_on = None


def upgrade():
    # Table is now created in the base migration (000_create_base_tables)
    # This migration is kept for migration history consistency
    pass


def downgrade():
    # Table is managed in the base migration
    pass