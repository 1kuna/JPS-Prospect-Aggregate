import logging
import os
import traceback
from datetime import datetime
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError as RequestsConnectionError

from src.celery_app import celery_app
from src.scrapers.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.scrapers.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper
from src.database.db import session_scope
from src.database.models import DataSource
from src.exceptions import (
    ScraperError, NetworkError, TimeoutError as AppTimeoutError, 
    ConnectionError as AppConnectionError, DatabaseError, TaskError
)

# Set up logging
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='src.tasks.scraper_tasks.run_acquisition_gateway_scraper_task', max_retries=3)
def run_acquisition_gateway_scraper_task(self):
    """Celery task to run the Acquisition Gateway scraper"""
    logger.info("Starting Acquisition Gateway scraper task")
    task_id = self.request.id
    
    try:
        # Run the scraper with force=True to ensure it runs
        success = run_acquisition_gateway_scraper(force=True)
        
        if success:
            logger.info("Acquisition Gateway scraper completed successfully")
            return {"status": "success", "message": "Scraper completed successfully", "task_id": task_id}
        else:
            logger.error("Acquisition Gateway scraper failed")
            # Retry the task if it fails
            raise ScraperError("Acquisition Gateway scraper failed without specific error")
            
    except ScraperError as e:
        logger.error(f"Scraper error: {e.message}")
        self.retry(countdown=60 * 5, exc=e)
        return {"status": "error", "message": e.message, "error_code": e.error_code, "task_id": task_id}
        
    except (Timeout, AppTimeoutError) as e:
        logger.error(f"Timeout error: {str(e)}")
        # Use longer delay for timeouts
        self.retry(countdown=60 * 10, exc=AppTimeoutError(f"Scraper timed out: {str(e)}"))
        return {"status": "error", "message": f"Timeout error: {str(e)}", "error_code": "TIMEOUT_ERROR", "task_id": task_id}
        
    except (RequestsConnectionError, AppConnectionError) as e:
        logger.error(f"Connection error: {str(e)}")
        # Use longer delay for connection issues
        self.retry(countdown=60 * 15, exc=AppConnectionError(f"Connection error: {str(e)}"))
        return {"status": "error", "message": f"Connection error: {str(e)}", "error_code": "CONNECTION_ERROR", "task_id": task_id}
        
    except RequestException as e:
        logger.error(f"Network error: {str(e)}")
        self.retry(countdown=60 * 10, exc=NetworkError(f"Network error: {str(e)}"))
        return {"status": "error", "message": f"Network error: {str(e)}", "error_code": "NETWORK_ERROR", "task_id": task_id}
        
    except DatabaseError as e:
        logger.error(f"Database error: {e.message}")
        self.retry(countdown=60 * 5, exc=e)
        return {"status": "error", "message": e.message, "error_code": e.error_code, "task_id": task_id}
        
    except Exception as e:
        logger.exception(f"Unexpected error running Acquisition Gateway scraper: {e}")
        # Log the full traceback for debugging
        logger.error(traceback.format_exc())
        # Retry the task if it fails
        self.retry(countdown=60 * 5, exc=TaskError(f"Unexpected error: {str(e)}"))
        return {"status": "error", "message": f"Unexpected error: {str(e)}", "error_code": "TASK_ERROR", "task_id": task_id}
    finally:
        # Cleanup code if needed
        pass

@celery_app.task(bind=True, name='src.tasks.scraper_tasks.run_ssa_contract_forecast_scraper_task', max_retries=3)
def run_ssa_contract_forecast_scraper_task(self):
    """Celery task to run the SSA Contract Forecast scraper"""
    logger.info("Starting SSA Contract Forecast scraper task")
    task_id = self.request.id
    
    try:
        # Run the scraper with force=True to ensure it runs
        success = run_ssa_contract_forecast_scraper(force=True)
        
        if success:
            logger.info("SSA Contract Forecast scraper completed successfully")
            return {"status": "success", "message": "Scraper completed successfully", "task_id": task_id}
        else:
            logger.error("SSA Contract Forecast scraper failed")
            # Retry the task if it fails
            raise ScraperError("SSA Contract Forecast scraper failed without specific error")
            
    except ScraperError as e:
        logger.error(f"Scraper error: {e.message}")
        self.retry(countdown=60 * 5, exc=e)
        return {"status": "error", "message": e.message, "error_code": e.error_code, "task_id": task_id}
        
    except (Timeout, AppTimeoutError) as e:
        logger.error(f"Timeout error: {str(e)}")
        # Use longer delay for timeouts
        self.retry(countdown=60 * 10, exc=AppTimeoutError(f"Scraper timed out: {str(e)}"))
        return {"status": "error", "message": f"Timeout error: {str(e)}", "error_code": "TIMEOUT_ERROR", "task_id": task_id}
        
    except (RequestsConnectionError, AppConnectionError) as e:
        logger.error(f"Connection error: {str(e)}")
        # Use longer delay for connection issues
        self.retry(countdown=60 * 15, exc=AppConnectionError(f"Connection error: {str(e)}"))
        return {"status": "error", "message": f"Connection error: {str(e)}", "error_code": "CONNECTION_ERROR", "task_id": task_id}
        
    except RequestException as e:
        logger.error(f"Network error: {str(e)}")
        self.retry(countdown=60 * 10, exc=NetworkError(f"Network error: {str(e)}"))
        return {"status": "error", "message": f"Network error: {str(e)}", "error_code": "NETWORK_ERROR", "task_id": task_id}
        
    except DatabaseError as e:
        logger.error(f"Database error: {e.message}")
        self.retry(countdown=60 * 5, exc=e)
        return {"status": "error", "message": e.message, "error_code": e.error_code, "task_id": task_id}
        
    except Exception as e:
        logger.exception(f"Unexpected error running SSA Contract Forecast scraper: {e}")
        # Log the full traceback for debugging
        logger.error(traceback.format_exc())
        # Retry the task if it fails
        self.retry(countdown=60 * 5, exc=TaskError(f"Unexpected error: {str(e)}"))
        return {"status": "error", "message": f"Unexpected error: {str(e)}", "error_code": "TASK_ERROR", "task_id": task_id}
    finally:
        # Cleanup code if needed
        pass

@celery_app.task(name='src.tasks.scraper_tasks.run_all_scrapers_task')
def run_all_scrapers_task():
    """Celery task to run all scrapers"""
    logger.info("Starting all scrapers task")
    
    # Run both scrapers in parallel using Celery's group feature
    from celery import group
    job = group([
        run_acquisition_gateway_scraper_task.s(),
        run_ssa_contract_forecast_scraper_task.s()
    ])
    result = job.apply_async()
    
    # Wait for all tasks to complete
    result.get()
    
    # Update the last_scraped timestamp for all data sources
    with session_scope() as session:
        try:
            # Update all data sources with the current timestamp
            current_time = datetime.utcnow()
            session.query(DataSource).update({"last_scraped": current_time})
            logger.info("Updated last_scraped timestamp for all data sources")
        except Exception as e:
            logger.error(f"Error updating data source timestamps: {e}")
    
    return {"status": "success", "message": "All scrapers completed"}

@celery_app.task(bind=True, name='src.tasks.scraper_tasks.force_collect_task', max_retries=3)
def force_collect_task(self, source_id):
    """Celery task to force collect data from a specific source"""
    logger.info(f"Starting force collect task for source_id={source_id}")
    
    with session_scope() as session:
        try:
            # Get the data source
            data_source = session.query(DataSource).filter(DataSource.id == source_id).first()
            
            if not data_source:
                logger.error(f"Data source not found for source_id={source_id}")
                return {"status": "error", "message": "Data source not found"}
            
            # Run the appropriate scraper based on the data source name
            if data_source.name == "Acquisition Gateway Forecast":
                success = run_acquisition_gateway_scraper(force=True)
            elif data_source.name == "SSA Contract Forecast":
                success = run_ssa_contract_forecast_scraper(force=True)
            else:
                logger.error(f"Unknown data source: {data_source.name}")
                return {"status": "error", "message": f"Unknown data source: {data_source.name}"}
            
            if success:
                logger.info(f"Force collect completed successfully for {data_source.name}")
                return {
                    "status": "success", 
                    "message": f"Force collect completed successfully for {data_source.name}",
                    "source_name": data_source.name
                }
            else:
                logger.error(f"Force collect failed for {data_source.name}")
                # Retry the task if it fails
                self.retry(countdown=60)  # Retry after 1 minute
                return {"status": "error", "message": f"Force collect failed for {data_source.name}"}
                
        except Exception as e:
            logger.exception(f"Error in force collect task: {e}")
            # Retry the task if it fails
            self.retry(countdown=60, exc=e)  # Retry after 1 minute
            return {"status": "error", "message": str(e)} 