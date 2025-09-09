"""Merge final and alignment heads

Revision ID: merge_final_and_align
Revises: 999_final_merge, align_numeric_and_json_types
Create Date: 2025-09-09 11:43:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_final_and_align'
down_revision = ('999_final_merge', 'align_numeric_and_json_types')
branch_labels = None
depends_on = None


def upgrade():
    """Merge both heads - no schema changes needed"""
    pass


def downgrade():
    """Cannot downgrade from a merge"""
    pass