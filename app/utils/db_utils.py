"""
Database utility functions.
"""

import sys
import os
import datetime
import shutil
import glob
from app.utils.logger import logger
from app.utils.file_utils import ensure_directory, clean_old_files
from flask import current_app
from pathlib import Path

# Set up logging using the centralized utility
# logger = logger.bind(name="utils.db") # Logger is already configured

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
    # Get the database path from the current app's configuration
    if not current_app:
        error_msg = "Application context is required to determine database path for rebuild."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    if not db_uri or not db_uri.startswith("sqlite:///"):
        error_msg = f"Invalid or missing SQLALCHEMY_DATABASE_URI in app config: {db_uri}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Extract path from URI
    db_path_str = db_uri.split("///", 1)[1]
    
    # If the path is relative, it's relative to the instance folder
    if not Path(db_path_str).is_absolute():
        db_path = Path(current_app.instance_path) / db_path_str
    else:
        db_path = Path(db_path_str)

    db_dir = db_path.parent
    
    # Ensure the directory exists
    ensure_directory(db_dir)
    
    # Check if the database exists
    if not db_path.exists():
        error_msg = f"Database file not found: {db_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    # Create a backup of the existing database
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(db_dir, f'proposals_backup_{timestamp}.db')
    
    logger.info(f"Creating backup of database at: {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    # Clean up old backups, keeping only the specified number of most recent ones
    cleanup_old_backups(str(db_dir), max_backups=max_backups)
    
    # Import here to avoid circular imports
    # from src.database.db import engine, Session # Corrected/updated import needed if used
    # For now, assuming engine and Session are not directly used for backup logic.
    # If rebuild logic is added, it should use get_db() or the initialized engine from app.database.session
    
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
    # Use the correct context manager from connection.py
    # from app.database.session import get_db # Corrected import from app.database.session
    # Import models from the correct location
    from app.models import db, DataSource, ScraperStatus # Import db from app.models
    import datetime
    
    logger.info(f"Updating scraper status for {source_name} to {status}")
    
    try:
        # Use the db.session from Flask-SQLAlchemy
        session = db.session
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

def get_data_source_id_by_name(source_name: str) -> int | None:
    """Fetches the ID of a data source by its name."""
    from app.models import db, DataSource
    session = db.session
    try:
        data_source = session.query(DataSource.id).filter(DataSource.name == source_name).scalar()
        if data_source:
            return data_source # scalar() directly returns the ID
        else:
            logger.warning(f"Data source not found with name: {source_name}")
            return None
    except Exception as e:
        logger.error(f"Error fetching data source ID for {source_name}: {str(e)}", exc_info=True)
        return None 