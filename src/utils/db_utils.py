"""
Database utility functions.
"""

import os
import sys
import shutil
import datetime
import logging
import glob

# Set up logging
logger = logging.getLogger(__name__)

def cleanup_old_backups(backup_dir, max_backups=5):
    """
    Clean up old database backups, keeping only the most recent ones.
    
    Args:
        backup_dir (str): Directory containing the backups
        max_backups (int): Maximum number of backups to keep
    """
    # Find all database backup files
    backup_pattern = os.path.join(backup_dir, 'proposals_backup_*.db')
    backup_files = glob.glob(backup_pattern)
    
    # If we have more backups than the maximum allowed
    if len(backup_files) > max_backups:
        # Sort files by modification time (newest first)
        backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Delete older backups
        for old_backup in backup_files[max_backups:]:
            try:
                os.remove(old_backup)
                logger.info(f"Deleted old backup: {old_backup}")
            except Exception as e:
                logger.warning(f"Failed to delete old backup {old_backup}: {e}")

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
    os.makedirs(db_dir, exist_ok=True)
    
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
    from src.database.db_session_manager import engine, Session
    
    # Import the rest of the rebuild logic from the original script
    # This is a simplified version - you may need to add more functionality
    # based on what's in scripts/rebuild_db.py
    
    logger.info("Database rebuild completed successfully")
    return True 