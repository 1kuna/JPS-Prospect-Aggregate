"""
Helper functions for Alembic migrations to handle existing database schemas gracefully.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def safe_add_column(table_name, column):
    """Add a column only if it doesn't already exist."""
    if not column_exists(table_name, column.name):
        op.add_column(table_name, column)
        return True
    return False


def index_exists(index_name):
    """Check if an index exists."""
    conn = op.get_bind()
    
    # SQLite index checking
    result = conn.execute(
        text(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name = :index_name"
        ),
        {"index_name": index_name}
    )
    return result.scalar() is not None


def safe_create_index(index_name, table_name, columns, **kwargs):
    """Create an index only if it doesn't already exist."""
    if not index_exists(index_name):
        op.create_index(index_name, table_name, columns, **kwargs)
        return True
    return False


def safe_drop_column(table_name, column_name):
    """Drop a column only if it exists."""
    if column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)
        return True
    return False


def safe_drop_index(index_name, table_name=None):
    """Drop an index only if it exists."""
    if index_exists(index_name):
        op.drop_index(index_name, table_name=table_name)
        return True
    return False


def table_exists(table_name):
    """Check if a table exists."""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def safe_create_table(table_name, *columns, **kwargs):
    """Create a table only if it doesn't exist."""
    if not table_exists(table_name):
        op.create_table(table_name, *columns, **kwargs)
        return True
    return False