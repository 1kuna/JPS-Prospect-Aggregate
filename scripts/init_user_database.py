#!/usr/bin/env python3
"""Initialize the user database with required tables.

This script creates the user authentication database separately
from the business database for security isolation.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app import create_app
from app.database.init_db import initialize_user_database
from app.utils.logger import logger


def init_user_database():
    """Initialize the user database with tables."""
    app = create_app()
    success = initialize_user_database(app)

    if success:
        logger.info("Created tables:")
        logger.info("- users")

    return success


if __name__ == "__main__":
    success = init_user_database()
    if success:
        logger.success("✅ User database initialized successfully!")
    else:
        logger.error("❌ Failed to initialize user database")
        sys.exit(1)
