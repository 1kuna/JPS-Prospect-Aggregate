#!/usr/bin/env python3
"""
Script to add the subtask_id column to the ScraperStatus table.
"""

import os
import sys
import datetime
from alembic import op
import sqlalchemy as sa

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_session_manager import engine, get_session, close_session
from src.database.models import Base, ScraperStatus
from src.utils.logging import get_component_logger

# Set up logging using the centralized utility
logger = get_component_logger('add_subtask_id')

def add_subtask_id_column():
    """Add subtask_id column to ScraperStatus table if it doesn't exist"""
    logger.info("Adding subtask_id column to ScraperStatus table...")
    
    # Check if the column already exists
    with engine.connect() as conn:
        result = conn.execute(sa.text("PRAGMA table_info(scraper_status)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'subtask_id' in columns:
            logger.info("Column 'subtask_id' already exists in ScraperStatus table")
            return
    
    # Add the column
    with engine.connect() as conn:
        conn.execute(sa.text("ALTER TABLE scraper_status ADD COLUMN subtask_id VARCHAR(255)"))
        conn.commit()
    
    logger.info("Column 'subtask_id' added to ScraperStatus table successfully")

if __name__ == '__main__':
    try:
        add_subtask_id_column()
    except Exception as e:
        logger.error(f"Error adding subtask_id column: {str(e)}")
        sys.exit(1) 