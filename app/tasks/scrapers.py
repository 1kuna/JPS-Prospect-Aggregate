"""
Scraper tasks for background processing.
"""

from celery import shared_task
from app.utils.logger import logger
from app.core.scrapers.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from app.core.scrapers.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper
from app.exceptions import ScraperError
from app.database.connection import get_db
from app.models import DataSource, ScraperStatus
import datetime
import traceback
from app.utils.db_context import db_session
from functools import wraps

def scraper_task_handler(source_name):
    """
    Decorator to handle common scraper task functionality.
    
    Args:
        source_name: Name of the data source
        
    Returns:
        function: Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, force=False):
            logger.info(f"Starting {source_name} scraper task")
            
            # Update status to running
            _update_scraper_status(source_name, "running")
            
            start_time = datetime.datetime.utcnow()
            
            try:
                # Run the scraper
                result = func(self, force=force)
                
                if result:
                    # Calculate collection time
                    collection_time = (datetime.datetime.utcnow() - start_time).total_seconds()
                    
                    # Get proposal count
                    proposal_count = _count_proposals_for_source(source_name)
                    
                    # Update status to completed
                    _update_scraper_status(source_name, "completed")
                    
                    logger.info(f"Scraper completed successfully. Collected {proposal_count} proposals in {collection_time:.2f} seconds")
                    
                    return {
                        "status": "success",
                        "message": "Scraper completed successfully",
                        "proposals_collected": proposal_count,
                        "collection_time": collection_time
                    }
                else:
                    # Update status to error
                    _update_scraper_status(source_name, "error", "Scraper failed without specific error")
                    
                    # Retry the task
                    logger.error("Scraper failed without specific error")
                    raise self.retry(countdown=60 * 5)  # Retry in 5 minutes
            
            except ScraperError as e:
                # Update status to error
                _update_scraper_status(source_name, "error", str(e))
                
                # Retry the task
                logger.error(f"Scraper error: {str(e)}")
                raise self.retry(exc=e, countdown=60 * 5)  # Retry in 5 minutes
            
            except Exception as e:
                # Update status to error
                _update_scraper_status(source_name, "error", str(e))
                
                # Log the error
                logger.error(f"Unexpected error: {str(e)}")
                
                return {
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}"
                }
        
        return wrapper
    return decorator

@shared_task(bind=True, max_retries=3, name="app.tasks.scrapers.run_acquisition_gateway")
@scraper_task_handler("Acquisition Gateway")
def run_acquisition_gateway(self, force=False):
    """
    Run the Acquisition Gateway scraper.
    
    Args:
        force: Whether to force scraping even if recently done
        
    Returns:
        dict: Result information
    """
    return run_acquisition_gateway_scraper(force=force)

@shared_task(bind=True, max_retries=3, name="app.tasks.scrapers.run_ssa_contract_forecast")
@scraper_task_handler("SSA Contract Forecast")
def run_ssa_contract_forecast(self, force=False):
    """
    Run the SSA Contract Forecast scraper.
    
    Args:
        force: Whether to force scraping even if recently done
        
    Returns:
        dict: Result information
    """
    return run_ssa_contract_forecast_scraper(force=force)

@shared_task(bind=True, name="app.tasks.scrapers.run_all_scrapers")
def run_all_scrapers(self, force=False):
    """
    Run all scrapers.
    
    Args:
        force: Whether to force scraping even if recently done
        
    Returns:
        dict: Result information
    """
    logger.info("Starting all scrapers task")
    
    # Start each scraper as a separate task
    ag_task = run_acquisition_gateway.delay(force=force)
    ssa_task = run_ssa_contract_forecast.delay(force=force)
    
    return {
        "status": "success",
        "message": "All scraper tasks started",
        "tasks": {
            "acquisition_gateway": ag_task.id,
            "ssa_contract_forecast": ssa_task.id
        }
    }

def _update_scraper_status(source_name, status, error_message=None):
    """
    Update the scraper status in the database.
    
    Args:
        source_name: Name of the data source
        status: Status to set
        error_message: Optional error message
    """
    try:
        with get_db() as db:
            # Get the data source
            data_source = db.query(DataSource).filter(
                DataSource.name.like(f'%{source_name}%')
            ).first()
            
            if not data_source:
                logger.warning(f"Data source not found for {source_name}")
                return
            
            # Find or create status record
            status_record = db.query(ScraperStatus).filter(
                ScraperStatus.source_id == data_source.id
            ).first()
            
            if not status_record:
                status_record = ScraperStatus(
                    source_id=data_source.id,
                    status=status,
                    error_message=error_message,
                    last_checked=datetime.datetime.utcnow()
                )
                db.add(status_record)
            else:
                status_record.status = status
                status_record.error_message = error_message
                status_record.last_checked = datetime.datetime.utcnow()
            
            # Update the data source last_scraped timestamp
            data_source.last_scraped = datetime.datetime.utcnow()
            
            logger.info(f"Updated status for {source_name} to {status}")
    
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")

def _count_proposals_for_source(source_name):
    """
    Count proposals for a data source.
    
    Args:
        source_name: Name of the data source
        
    Returns:
        int: Number of proposals
    """
    try:
        with get_db() as db:
            # Find the data source
            data_source = db.query(DataSource).filter(
                DataSource.name.like(f'%{source_name}%')
            ).first()
            
            if not data_source:
                logger.warning(f"Data source not found for {source_name}")
                return 0
            
            # Count proposals
            from app.models import Proposal
            count = db.query(Proposal).filter(
                Proposal.source_id == data_source.id
            ).count()
            
            return count
    
    except Exception as e:
        logger.error(f"Error counting proposals: {str(e)}")
        return 0 