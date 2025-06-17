"""Merge migration heads

Revision ID: 20e4b47362d1
Revises: a6bc8592cdf2, add_settings_table, b7a9d8e5f4c3
Create Date: 2025-06-17 19:01:32.721316

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20e4b47362d1'
down_revision = ('a6bc8592cdf2', 'add_settings_table', 'b7a9d8e5f4c3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
