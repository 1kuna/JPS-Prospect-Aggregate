#!/usr/bin/env python3
"""
Initialize the user database with required tables.

This script creates the user authentication database separately
from the business database for security isolation.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app import create_app
from app.database import db
from app.utils.logger import logger

def init_user_database():
    """Initialize the user database with tables."""
    app = create_app()
    
    with app.app_context():
        logger.info("Initializing user database...")
        
        try:
            # Create all tables in the users bind
            db.create_all(bind_key='users')
            
            logger.info("User database initialized successfully!")
            logger.info("Created tables:")
            logger.info("- users")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing user database: {str(e)}")
            return False

if __name__ == '__main__':
    success = init_user_database()
    if success:
        print("✅ User database initialized successfully!")
    else:
        print("❌ Failed to initialize user database")
        sys.exit(1)