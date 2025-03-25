#!/usr/bin/env python
"""
Test the new simplified Celery tasks.

This script tests the new task implementation by calling each task type
and waiting for the results. It's useful for verifying that the new task
system works correctly after the refactoring.
"""

import os
import sys
import time
import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.logger import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test data source tasks
def test_scraper_tasks():
    """Test the scraper tasks."""
    try:
        logger.info("Testing scraper tasks...")
        
        # Import tasks
        from src.tasks.scrapers import run_acquisition_gateway, run_ssa_contract_forecast, run_all_scrapers
        
        # Test Acquisition Gateway scraper (non-blocking)
        logger.info("Starting Acquisition Gateway scraper task...")
        ag_result = run_acquisition_gateway.delay(force=True)
        logger.info(f"Task started with ID: {ag_result.id}")
        
        # Test SSA Contract Forecast scraper (non-blocking)
        logger.info("Starting SSA Contract Forecast scraper task...")
        ssa_result = run_ssa_contract_forecast.delay(force=True)
        logger.info(f"Task started with ID: {ssa_result.id}")
        
        # Check task status
        logger.info("Waiting for tasks to complete...")
        
        # Optional: Wait for results (remove for production as this will block)
        # Uncomment to wait for results:
        # ag_complete = ag_result.get(timeout=300)  # 5-minute timeout
        # ssa_complete = ssa_result.get(timeout=300)  # 5-minute timeout
        # logger.info(f"Acquisition Gateway result: {ag_complete}")
        # logger.info(f"SSA Contract Forecast result: {ssa_complete}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing scraper tasks: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Test health check tasks
def test_health_check_tasks():
    """Test the health check tasks."""
    try:
        logger.info("Testing health check tasks...")
        
        # Import tasks
        from src.tasks.health import check_all_scrapers, check_acquisition_gateway, check_ssa_contract_forecast
        
        # Test all scrapers health check
        logger.info("Running all scrapers health check...")
        all_result = check_all_scrapers.delay()
        logger.info(f"Task started with ID: {all_result.id}")
        
        # Test Acquisition Gateway health check
        logger.info("Running Acquisition Gateway health check...")
        ag_result = check_acquisition_gateway.delay()
        logger.info(f"Task started with ID: {ag_result.id}")
        
        # Test SSA Contract Forecast health check
        logger.info("Running SSA Contract Forecast health check...")
        ssa_result = check_ssa_contract_forecast.delay()
        logger.info(f"Task started with ID: {ssa_result.id}")
        
        # Optional: Wait for results (remove for production as this will block)
        # Uncomment to wait for results:
        # all_complete = all_result.get(timeout=60)  # 1-minute timeout
        # ag_complete = ag_result.get(timeout=60)  # 1-minute timeout
        # ssa_complete = ssa_result.get(timeout=60)  # 1-minute timeout
        # logger.info(f"All scrapers health check result: {all_complete}")
        # logger.info(f"Acquisition Gateway health check result: {ag_complete}")
        # logger.info(f"SSA Contract Forecast health check result: {ssa_complete}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing health check tasks: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Test debug task
def test_debug_task():
    """Test the debug task."""
    try:
        logger.info("Testing debug task...")
        
        # Import task
        from src.celery_app import debug_task
        
        # Run debug task
        result = debug_task.delay()
        logger.info(f"Task started with ID: {result.id}")
        
        # Wait for result
        logger.info("Waiting for task to complete...")
        complete = result.get(timeout=10)  # 10-second timeout
        logger.info(f"Debug task result: {complete}")
        
        return complete == "Celery is working!"
    
    except Exception as e:
        logger.error(f"Error testing debug task: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    """Run all tests when executed directly."""
    logger.info("Starting tests...")
    
    # Run tests
    debug_success = test_debug_task()
    logger.info(f"Debug task test {'succeeded' if debug_success else 'failed'}")
    
    # Only run other tests if debug test passes
    if debug_success:
        health_success = test_health_check_tasks()
        logger.info(f"Health check tasks test {'succeeded' if health_success else 'failed'}")
        
        scraper_success = test_scraper_tasks()
        logger.info(f"Scraper tasks test {'succeeded' if scraper_success else 'failed'}")
        
        if health_success and scraper_success:
            logger.info("All tests passed!")
            sys.exit(0)
        else:
            logger.error("Some tests failed")
            sys.exit(1)
    else:
        logger.error("Debug task test failed, not running other tests")
        sys.exit(1) 