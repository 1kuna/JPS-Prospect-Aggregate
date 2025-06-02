"""
Models Package

This package previously consolidated SQLAlchemy models for the application
by re-exporting them from app.database.models.

Models should now be imported directly from app.database.models.
This __init__.py now primarily re-exports the 'db' instance from app.database.
"""

from app.database import db

__all__ = [
    "db"
] 