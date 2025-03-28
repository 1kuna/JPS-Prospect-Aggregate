import os
import sys
import time
import datetime

from app.database.connection import session_scope
from app.models import DataSource, ScraperStatus
from app.config import LOGS_DIR
from app.utils.logger import logger, cleanup_logs

# Set up logging with the centralized utility
logger = logger.bind(name="health_check")

logger.info("Health check module initialized")

def check_scraper_health(scraper_instance, source_name):
    """
    Test if a scraper can connect to its target site and extract basic data.
    This is a lightweight test that doesn't perform a full scrape.
    
    Args:
        scraper_instance: An instance of the scraper class
        source_name: The name of the data source
        
    Returns:
        dict: A dictionary with status information
    """
    start_time = time.time()
    status = "not_working"
    error_message = None
    
    try:
        logger.info(f"Running health check for {source_name}")
        
        # Set up the browser
        if not scraper_instance.setup_browser():
            raise Exception("Failed to set up browser")
        
        logger.info(f"Browser setup successful for {source_name}")
        
        # Navigate to the site
        logger.info(f"Navigating to {scraper_instance.base_url}")
        scraper_instance.page.goto(scraper_instance.base_url)
        
        # Perform a basic check (this will vary by scraper)
        # For example, check if a specific element exists
        if scraper_instance.page.is_visible("table") or scraper_instance.page.is_visible(".data-table"):
            logger.info(f"Found data table on page for {source_name}")
            status = "working"
        else:
            error_message = "Could not find data table on page"
            logger.warning(f"Could not find data table on page for {source_name}")
            
    except Exception as e:
        error_message = str(e)
        logger.error(f"Health check failed for {source_name}: {e}")
    finally:
        # Clean up
        try:
            scraper_instance.cleanup_browser()
            logger.info(f"Browser cleanup completed for {source_name}")
        except Exception as e:
            logger.error(f"Error during browser cleanup for {source_name}: {e}")
    
    response_time = time.time() - start_time
    logger.info(f"Health check for {source_name} completed in {response_time:.2f} seconds with status: {status}")
    
    # Update the database
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
                status_record.response_time = response_time
                logger.info(f"Updated existing status record for {source_name}")
            else:
                # Create new record
                new_status = ScraperStatus(
                    source_id=data_source.id,
                    status=status,
                    last_checked=datetime.datetime.utcnow(),
                    error_message=error_message,
                    response_time=response_time
                )
                session.add(new_status)
                logger.info(f"Created new status record for {source_name}")
        else:
            logger.warning(f"Data source not found for {source_name}")
    
    return {
        "source_name": source_name,
        "status": status,
        "error_message": error_message,
        "response_time": response_time
    }

def check_acquisition_gateway():
    """Check the health of the Acquisition Gateway scraper"""
    from app.core.scrapers.acquisition_gateway import AcquisitionGatewayScraper
    logger.info("Starting health check for Acquisition Gateway Forecast")
    scraper = AcquisitionGatewayScraper()
    return check_scraper_health(scraper, "Acquisition Gateway Forecast")

def check_ssa_contract_forecast():
    """Check the health of the SSA Contract Forecast scraper"""
    from app.core.scrapers.ssa_contract_forecast import SSAContractForecastScraper
    logger.info("Starting health check for SSA Contract Forecast")
    scraper = SSAContractForecastScraper()
    return check_scraper_health(scraper, "SSA Contract Forecast")

# Add more check functions for each scraper as needed

def check_all_scrapers():
    """Check the health of all scrapers"""
    logger.info("Starting health checks for all scrapers")
    results = []
    
    # Check each scraper
    try:
        results.append(check_acquisition_gateway())
    except Exception as e:
        logger.error(f"Error checking Acquisition Gateway Forecast: {e}")
        results.append({
            "source_name": "Acquisition Gateway Forecast",
            "status": "not_working",
            "error_message": str(e),
            "response_time": 0
        })
    
    try:
        results.append(check_ssa_contract_forecast())
    except Exception as e:
        logger.error(f"Error checking SSA Contract Forecast: {e}")
        results.append({
            "source_name": "SSA Contract Forecast",
            "status": "not_working",
            "error_message": str(e),
            "response_time": 0
        })
    
    # Clean up old log files, keeping only the last 3
    try:
        cleanup_results = cleanup_logs(LOGS_DIR, keep_count=3)
        for log_type, count in cleanup_results.items():
            if count > 0:
                logger.info(f"Cleaned up {count} old {log_type} log files")
    except Exception as e:
        logger.error(f"Error cleaning up log files: {e}")
    
    return results

if __name__ == "__main__":
    """Run health checks when script is executed directly"""
    check_all_scrapers() 