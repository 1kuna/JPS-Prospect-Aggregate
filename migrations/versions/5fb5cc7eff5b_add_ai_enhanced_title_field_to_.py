"""Add ai_enhanced_title field to prospects table

Revision ID: 5fb5cc7eff5b
Revises: fbc0e1fbf50d
Create Date: 2025-06-03 19:21:41.711762

"""
from alembic import op
import sqlalchemy as sa
import sys
import os

# Add the migrations directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from alembic_helpers import safe_add_column, safe_drop_column, table_exists
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
    
    def safe_drop_column(table_name, column_name):
        if column_exists(table_name, column_name):
            op.drop_column(table_name, column_name)
            return True
        return False
    
    def table_exists(table_name):
        conn = op.get_bind()
        inspector = inspect(conn)
        return table_name in inspector.get_table_names()


# revision identifiers, used by Alembic.
revision = '5fb5cc7eff5b'
down_revision = 'fbc0e1fbf50d'
branch_labels = None
depends_on = None


def upgrade():
    # Only add the column if the table exists and the column doesn't
    if table_exists('prospects'):
        safe_add_column('prospects', sa.Column('ai_enhanced_title', sa.Text(), nullable=True))


def downgrade():
    # Only drop the column if it exists
    if table_exists('prospects'):
        safe_drop_column('prospects', 'ai_enhanced_title')
