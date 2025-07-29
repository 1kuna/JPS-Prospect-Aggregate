"""add user and go_no_go_decision tables

Revision ID: b7a9d8e5f4c3
Revises: fbc0e1fbf50d
Create Date: 2025-06-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7a9d8e5f4c3'
down_revision = 'fbc0e1fbf50d'
branch_labels = None
depends_on = None


def upgrade():
    # Tables are now created in the base migration (000_create_base_tables)
    # This migration is kept for migration history consistency
    pass


def downgrade():
    # Tables are managed in the base migration
    pass