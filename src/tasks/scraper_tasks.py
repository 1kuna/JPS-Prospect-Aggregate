import logging
import os
from datetime import datetime

from src.celery_app import celery_app
from src.scrapers.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.scrapers.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper
from src.database.db import session_scope
from src.database.models import DataSource

# Set up logging
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='src.tasks.scraper_tasks.run_acquisition_gateway_scraper_task', max_retries=3)
def run_acquisition_gateway_scraper_task(self):
    """Celery task to run the Acquisition Gateway scraper"""
    logger.info("Starting Acquisition Gateway scraper task")
    try:
        # Run the scraper with force=True to ensure it runs
        success = run_acquisition_gateway_scraper(force=True)
        
        if success:
            logger.info("Acquisition Gateway scraper completed successfully")
            return {"status": "success", "message": "Scraper completed successfully"}
        else:
            logger.error("Acquisition Gateway scraper failed")
            # Retry the task if it fails
            self.retry(countdown=60 * 5)  # Retry after 5 minutes
            return {"status": "error", "message": "Scraper failed"}
    except Exception as e:
        logger.exception(f"Error running Acquisition Gateway scraper: {e}")
        # Retry the task if it fails
        self.retry(countdown=60 * 5, exc=e)  # Retry after 5 minutes
        return {"status": "error", "message": str(e)}

@celery_app.task(bind=True, name='src.tasks.scraper_tasks.run_ssa_contract_forecast_scraper_task', max_retries=3)
def run_ssa_contract_forecast_scraper_task(self):
    """Celery task to run the SSA Contract Forecast scraper"""
    logger.info("Starting SSA Contract Forecast scraper task")
    try:
        # Run the scraper with force=True to ensure it runs
        success = run_ssa_contract_forecast_scraper(force=True)
        
        if success:
            logger.info("SSA Contract Forecast scraper completed successfully")
            return {"status": "success", "message": "Scraper completed successfully"}
        else:
            logger.error("SSA Contract Forecast scraper failed")
            # Retry the task if it fails
            self.retry(countdown=60 * 5)  # Retry after 5 minutes
            return {"status": "error", "message": "Scraper failed"}
    except Exception as e:
        logger.exception(f"Error running SSA Contract Forecast scraper: {e}")
        # Retry the task if it fails
        self.retry(countdown=60 * 5, exc=e)  # Retry after 5 minutes
        return {"status": "error", "message": str(e)}

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