"""
Create a new database with the updated schema.
This script will:
1. Back up the existing database
2. Create a new database with the updated schema
"""

import os
import sys
import shutil
import datetime
import logging

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_new_database():
    """Create a new database with the updated schema"""
    # Get the database path
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    db_path = os.path.join(db_dir, 'proposals.db')
    
    # Ensure the directory exists
    os.makedirs(db_dir, exist_ok=True)
    
    # Create a backup of the existing database if it exists
    if os.path.exists(db_path):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(db_dir, f'proposals_backup_{timestamp}.db')
        
        logger.info(f"Creating backup of database at: {backup_path}")
        shutil.copy2(db_path, backup_path)
        
        # Remove the existing database
        try:
            os.remove(db_path)
            logger.info(f"Removed existing database file: {db_path}")
        except PermissionError:
            logger.error("Could not delete database file - it's still in use by another process")
            return
        except Exception as e:
            logger.error(f"Error removing database file: {e}")
            return
    
    # Import the database models
    from src.database.models import Base
    from src.database.db import engine
    
    # Create the tables
    logger.info("Creating new database with updated schema")
    Base.metadata.create_all(engine)
    
    logger.info("Database creation completed successfully!")

if __name__ == "__main__":
    create_new_database() 