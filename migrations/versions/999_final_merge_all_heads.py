"""Final merge of all migration heads for Docker deployment

Revision ID: 999_final_merge
Revises: abc123def456, add_file_processing_log_table
Create Date: 2025-07-29 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '999_final_merge'
down_revision = ('abc123def456', 'add_file_processing_log_table')
branch_labels = None
depends_on = None


def upgrade():
    """Merge all migration heads - no changes needed as all tables are already created in individual migrations"""
    pass


def downgrade():
    """Cannot downgrade from a merge - would need to revert to individual heads"""
    pass