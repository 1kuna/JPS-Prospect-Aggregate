import logging
from src.celery_app import celery_app
from src.scrapers.health_check import check_all_scrapers, check_acquisition_gateway, check_ssa_contract_forecast

# Set up logging
logger = logging.getLogger(__name__)

@celery_app.task(name='src.tasks.health_check_tasks.check_all_scrapers_task')
def check_all_scrapers_task():
    """Celery task to check the health of all scrapers"""
    logger.info("Starting health check task for all scrapers")
    try:
        results = check_all_scrapers()
        logger.info(f"Health check completed for all scrapers: {results}")
        return {"status": "success", "results": results}
    except Exception as e:
        logger.exception(f"Error checking all scrapers: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name='src.tasks.health_check_tasks.check_acquisition_gateway_task')
def check_acquisition_gateway_task():
    """Celery task to check the health of the Acquisition Gateway scraper"""
    logger.info("Starting health check task for Acquisition Gateway")
    try:
        result = check_acquisition_gateway()
        logger.info(f"Health check completed for Acquisition Gateway: {result}")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception(f"Error checking Acquisition Gateway: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name='src.tasks.health_check_tasks.check_ssa_contract_forecast_task')
def check_ssa_contract_forecast_task():
    """Celery task to check the health of the SSA Contract Forecast scraper"""
    logger.info("Starting health check task for SSA Contract Forecast")
    try:
        result = check_ssa_contract_forecast()
        logger.info(f"Health check completed for SSA Contract Forecast: {result}")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception(f"Error checking SSA Contract Forecast: {e}")
        return {"status": "error", "message": str(e)} 