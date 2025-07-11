#!/usr/bin/env python3
"""
Initialize the business database by creating all tables directly from models.
This bypasses migration issues and creates a clean database state.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app import create_app
from app.database.init_db import initialize_business_database
from app.utils.logger import logger

def init_business_database():
    """Initialize the business database with all tables."""
    app = create_app()
    success = initialize_business_database(app)
    
    if success:
        # List the tables that were created for verification
        from app.database import db
        with app.app_context():
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info("Created tables:")
            for table in sorted(tables):
                logger.info(f"- {table}")
    
    return success

if __name__ == '__main__':
    success = init_business_database()
    if success:
        logger.success("✅ Business database initialized successfully!")
    else:
        logger.error("❌ Failed to initialize business database")
        sys.exit(1)