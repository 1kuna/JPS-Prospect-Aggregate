#!/usr/bin/env python3
"""
Script to add the subtask_id column to the ScraperStatus table.
"""

import os
import sys
import logging
from sqlalchemy import Column, String, text

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import project modules
from src.database.db_session_manager import session_scope
from src.database.connection_pool import get_engine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def add_subtask_id_column():
    """Add the subtask_id column to the ScraperStatus table."""
    logger.info("Adding subtask_id column to ScraperStatus table...")
    
    engine = get_engine()
    
    # Check if the column already exists
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(scraper_status)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'subtask_id' in columns:
            logger.info("Column 'subtask_id' already exists in ScraperStatus table")
            return
    
    # Add the column
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE scraper_status ADD COLUMN subtask_id VARCHAR(255)"))
        conn.commit()
    
    logger.info("Column 'subtask_id' added to ScraperStatus table successfully")

if __name__ == '__main__':
    try:
        add_subtask_id_column()
    except Exception as e:
        logger.error(f"Error adding subtask_id column: {str(e)}")
        sys.exit(1) 