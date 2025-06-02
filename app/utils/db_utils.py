"""
Database utility functions.
"""

import datetime
from datetime import timezone
# import shutil # Removed as it was only used by rebuild_database
from typing import Optional # Added for type hinting
from app.utils.logger import logger
# from flask import current_app # Removed as it was only used by rebuild_database
# from pathlib import Path # Removed as it was only used by rebuild_database

# Set up logging using the centralized utility

# Ensure datetime is imported if not already at the top of the file
# import datetime # This should be at the top of the file

# The rebuild_database function has been removed as it's unused.

def update_scraper_status(source_id: int, status: str, details: Optional[str] = None):
    """
    Update the scraper status in the database for a given source_id.
    
    Args:
        source_id (int): The ID of the data source.
        status (str): Status to set (e.g., 'working', 'completed', 'failed').
        details (Optional[str]): Additional details or error message.
    """
    from app.models import db # For db instance
    from app.database.models import DataSource, ScraperStatus # For models
    # Ensure datetime is available (already imported at the top)

    logger.info(f"Updating scraper status for source ID {source_id} to '{status}'. Details: {details}")
    
    session = db.session
    try:
        # Verify DataSource exists
        data_source = session.query(DataSource).filter_by(id=source_id).first()
        if not data_source:
            logger.warning(f"DataSource with ID {source_id} not found. Cannot update status.")
            return

        # Find the most recent status record to update, or create a new one
        status_record = session.query(ScraperStatus).filter_by(source_id=source_id).order_by(ScraperStatus.last_checked.desc()).first()
        
        current_time = datetime.datetime.now(timezone.utc)

        if not status_record:
            status_record = ScraperStatus(
                source_id=source_id,
                status=status,
                details=details,
                last_checked=current_time 
            )
            session.add(status_record)
            logger.info(f"Created new status record for source ID {source_id} with status '{status}'.")
        else:
            status_record.status = status
            status_record.details = details
            status_record.last_checked = current_time
            logger.info(f"Updated existing status record for source ID {source_id} to '{status}'.")
            
        session.commit()
        logger.info(f"Successfully committed status update for source ID {source_id}.")

    except Exception as e:
        logger.error(f"Error updating scraper status for source ID {source_id}: {str(e)}", exc_info=True)
        try:
            session.rollback()
        except Exception as rb_exc:
            logger.error(f"Failed to rollback session during status update error: {rb_exc}", exc_info=True)