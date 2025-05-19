"""
Models Package

This package consolidates all SQLAlchemy models for the application.
It imports the `db` instance from `app.database` and all model classes
from `app.database.models`.

This allows other parts of the application to import models from a single
location, e.g., `from app.models import db, Prospect, DataSource`.
"""

from app.database import db
from app.database.models import (
    Prospect,
    InferredProspectData,
    DataSource,
    ScraperStatus
)

__all__ = [
    "db",
    "Prospect",
    "InferredProspectData",
    "DataSource",
    "ScraperStatus"
] 