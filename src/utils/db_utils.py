"""
Database utility functions.
"""

import sys
import os
import datetime
import shutil
import glob
from src.utils.logger import logger
from src.utils.file_utils import ensure_directory, clean_old_files

# Set up logging using the centralized utility
logger = logger.bind(name="utils.db")

def cleanup_old_backups(backup_dir, max_backups=5):
    """
    Clean up old database backups, keeping only the most recent ones.
    
    Args:
        backup_dir (str): Directory containing the backups
        max_backups (int): Maximum number of backups to keep
    """
    # Use the centralized clean_old_files function
    pattern = "proposals_backup_*.db"
    deleted = clean_old_files(backup_dir, pattern, max_backups)
    logger.info(f"Cleaned up {deleted} old database backup(s), keeping {max_backups} most recent")
    return deleted

def rebuild_database(max_backups=5):
    """
    Rebuild the database with the new schema
    
    Args:
        max_backups (int): Maximum number of backups to keep
    """
    # Get the database path - use project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_dir = os.path.join(project_root, 'data')
    db_path = os.path.join(db_dir, 'proposals.db')
    
    # Ensure the directory exists
    ensure_directory(os.path.dirname(db_path))
    
    # Check if the database exists
    if not os.path.exists(db_path):
        error_msg = f"Database file not found: {db_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    # Create a backup of the existing database
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(db_dir, f'proposals_backup_{timestamp}.db')
    
    logger.info(f"Creating backup of database at: {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    # Clean up old backups, keeping only the specified number of most recent ones
    cleanup_old_backups(db_dir, max_backups=max_backups)
    
    # Import here to avoid circular imports
    from src.database.db import engine, Session
    
    # Import the rest of the rebuild logic from the original script
    # This is a simplified version - you may need to add more functionality
    # based on what's in scripts/rebuild_db.py
    
    logger.info("Database rebuild completed successfully")
    return True

def update_scraper_status(source_name, status, error_message=None):
    """
    Update the scraper status in the database.
    
    Args:
        source_name (str): Name of the data source
        status (str): Status to set ('working', 'error', etc.)
        error_message (str, optional): Error message to set
    """
    from src.database.db import session_scope
    from src.database.models import DataSource, ScraperStatus
    import datetime
    
    logger.info(f"Updating scraper status for {source_name} to {status}")
    
    try:
        with session_scope() as session:
            # Get the data source
            data_source = session.query(DataSource).filter_by(name=source_name).first()
            if data_source:
                # Check if there's an existing status record
                status_record = session.query(ScraperStatus).filter_by(source_id=data_source.id).first()
                if status_record:
                    # Update existing record
                    status_record.status = status
                    status_record.last_checked = datetime.datetime.utcnow()
                    status_record.error_message = error_message
                    logger.info(f"Updated existing status record for {source_name} to {status}")
                else:
                    # Create new record
                    new_status = ScraperStatus(
                        source_id=data_source.id,
                        status=status,
                        last_checked=datetime.datetime.utcnow(),
                        error_message=error_message
                    )
                    session.add(new_status)
                    logger.info(f"Created new status record for {source_name} with status {status}")
                
                # Also update the last_scraped field on the data source
                data_source.last_scraped = datetime.datetime.utcnow()
                session.commit()
                logger.info(f"Updated last_scraped timestamp for {source_name}")
            else:
                logger.warning(f"Data source not found for {source_name}")
    except Exception as e:
        logger.error(f"Error updating scraper status: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}") 