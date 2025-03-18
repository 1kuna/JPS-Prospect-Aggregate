"""
Health check tasks for monitoring system and data sources.
"""

from celery import shared_task
from src.utils.logger import logger
from src.data_collectors.health_check import (
    check_all_scrapers as check_all_scrapers_impl,
    check_acquisition_gateway as check_acquisition_gateway_impl,
    check_ssa_contract_forecast as check_ssa_contract_forecast_impl
)

@shared_task(name="src.tasks.health.check_all_scrapers")
def check_all_scrapers():
    """
    Check the health of all scrapers.
    
    Returns:
        dict: Health check results
    """
    logger.info("Starting health check for all scrapers")
    
    try:
        result = check_all_scrapers_impl()
        logger.info("Health check completed")
        
        return {
            "status": "success",
            "message": "Health check completed",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        
        return {
            "status": "error",
            "message": f"Error in health check: {str(e)}"
        }

@shared_task(name="src.tasks.health.check_acquisition_gateway")
def check_acquisition_gateway():
    """
    Check the health of the Acquisition Gateway scraper.
    
    Returns:
        dict: Health check results
    """
    logger.info("Starting health check for Acquisition Gateway")
    
    try:
        result = check_acquisition_gateway_impl()
        logger.info("Health check completed")
        
        return {
            "status": "success",
            "message": "Health check completed",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        
        return {
            "status": "error",
            "message": f"Error in health check: {str(e)}"
        }

@shared_task(name="src.tasks.health.check_ssa_contract_forecast")
def check_ssa_contract_forecast():
    """
    Check the health of the SSA Contract Forecast scraper.
    
    Returns:
        dict: Health check results
    """
    logger.info("Starting health check for SSA Contract Forecast")
    
    try:
        result = check_ssa_contract_forecast_impl()
        logger.info("Health check completed")
        
        return {
            "status": "success",
            "message": "Health check completed",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        
        return {
            "status": "error",
            "message": f"Error in health check: {str(e)}"
        } 