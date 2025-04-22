#!/usr/bin/env python3
"""
Unit test for the scraper tasks.
This script tests the scraper tasks for all data sources.
"""

import os
import sys
import time
import argparse

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import session_scope
from src.database.models import DataSource, Proposal
from src.utils.logger import logger

# Set up logging using the centralized utility
logger = logger.bind(name="test_pull")

def test_pull_source(source_id=None, source_name=None):
    """Test pulling data from a specific source"""

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
from src.utils.logging import configure_logging
configure_logging()

# Import the task registry and scraper tasks
from src.background_tasks.registry import task_registry
from src.background_tasks.scraper_tasks import force_collect_task

def test_scraper_tasks():
    """Test the scraper tasks for all data sources."""
    logger.info("Starting scraper task tests...")
    
    # Get all data sources
    with session_scope() as session:
        data_sources = session.query(DataSource).all()
        
        if not data_sources:
            logger.error("No data sources found!")
            return False
        
        # Log the data sources
        logger.info(f"Found {len(data_sources)} data sources:")
        for source in data_sources:
            logger.info(f"  - ID: {source.id}, Name: {source.name}")
        
        # Test each data source
        for source in data_sources:
            logger.info(f"Testing scraper task for {source.name} (ID: {source.id})")
            
            # Use the force_collect_task to run the scraper
            result = force_collect_task.delay(source.id).get(timeout=300)  # 5-minute timeout
            
            # Check if the task was successful
            if result.get("status") == "success":
                logger.info(f"Scraper task for {source.name} completed successfully")
                logger.info(f"Result: {result}")
            else:
                logger.error(f"Scraper task for {source.name} failed: {result.get('message', 'Unknown error')}")
                return False
    
    # Test the run_all_scrapers_task
    logger.info("Testing run_all_scrapers_task...")
    all_scrapers_result = task_registry.all_scrapers_task.delay().get(timeout=600)  # 10-minute timeout
    
    if all_scrapers_result.get("status") == "success":
        logger.info("All scrapers task completed successfully")
        logger.info(f"Result: {all_scrapers_result}")
        return True
    else:
        logger.error(f"All scrapers task failed: {all_scrapers_result.get('message', 'Unknown error')}")
        return False

if __name__ == "__main__":
    success = test_scraper_tasks()
    sys.exit(0 if success else 1) 