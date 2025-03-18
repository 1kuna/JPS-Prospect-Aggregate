#!/usr/bin/env python3
"""
Test the health check functionality using the new Celery task system.
This script tests the health check tasks for all scrapers.
"""

import os
import sys
import time
import datetime

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import session_scope
from src.database.models import DataSource, ScraperStatus
from src.data_collectors.health_check import check_acquisition_gateway, check_ssa_contract_forecast
from src.utils.logger import logger

# Set up logging using the centralized utility
logger = logger.bind(name="test_health_check")

# Import the health check tasks
from src.background_tasks.health_check_tasks import (
    check_all_scrapers_task,
    check_acquisition_gateway_task,
    check_ssa_contract_forecast_task
)

def test_health_checks():
    """Test health checks for all scrapers"""
    logger.info("Starting health check tests...")
    
    # Test the all scrapers health check
    logger.info("Testing all scrapers health check...")
    all_scrapers_result = check_all_scrapers_task.delay().get(timeout=60)
    logger.info(f"All scrapers health check result: {all_scrapers_result}")
    
    # Test the Acquisition Gateway health check
    logger.info("Testing Acquisition Gateway health check...")
    acquisition_gateway_result = check_acquisition_gateway_task.delay().get(timeout=60)
    logger.info(f"Acquisition Gateway health check result: {acquisition_gateway_result}")
    
    # Test the SSA Contract Forecast health check
    logger.info("Testing SSA Contract Forecast health check...")
    ssa_contract_forecast_result = check_ssa_contract_forecast_task.delay().get(timeout=60)
    logger.info(f"SSA Contract Forecast health check result: {ssa_contract_forecast_result}")
    
    logger.info("Health check tests completed")
    
    # Return True if all health checks were successful
    return (
        all_scrapers_result.get("status") == "success" and
        acquisition_gateway_result.get("status") == "success" and
        ssa_contract_forecast_result.get("status") == "success"
    )

if __name__ == "__main__":
    success = test_health_checks()
    sys.exit(0 if success else 1) 