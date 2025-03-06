"""Celery tasks for running scrapers."""

# Import from common imports module
from src.utils.imports import (
    logging, os, traceback, datetime,
    requests, RequestException, Timeout, RequestsConnectionError
)

# Import Celery app
from src.celery_app import celery_app

# Import scrapers
from src.scrapers.acquisition_gateway import run_scraper as run_acquisition_gateway_scraper
from src.scrapers.ssa_contract_forecast import run_scraper as run_ssa_contract_forecast_scraper

# Import database
from src.database.db import session_scope
from src.database.models import DataSource

# Import exceptions
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
    start_time = datetime.utcnow()
    
    try:
        # Run the scraper with force=True to ensure it runs
        success = run_acquisition_gateway_scraper(force=True)
        
        if success:
            # Calculate collection time
            end_time = datetime.utcnow()
            collection_time = (end_time - start_time).total_seconds()
            
            # Count proposals collected
            with session_scope() as session:
                from src.database.models import Proposal
                source = session.query(DataSource).filter(DataSource.name.like('%Acquisition Gateway%')).first()
                if source:
                    proposal_count = session.query(Proposal).filter(
                        Proposal.source_id == source.id
                    ).count()
                else:
                    proposal_count = 0
            
            logger.info(f"Acquisition Gateway scraper completed successfully. Collected {proposal_count} proposals in {collection_time:.2f} seconds")
            return {
                "status": "success", 
                "message": "Scraper completed successfully", 
                "task_id": task_id,
                "proposals_collected": proposal_count,
                "collection_time": collection_time
            }
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
    start_time = datetime.utcnow()
    
    try:
        # Run the scraper with force=True to ensure it runs
        success = run_ssa_contract_forecast_scraper(force=True)
        
        if success:
            # Calculate collection time
            end_time = datetime.utcnow()
            collection_time = (end_time - start_time).total_seconds()
            
            # Count proposals collected
            with session_scope() as session:
                from src.database.models import Proposal
                source = session.query(DataSource).filter(DataSource.name.like('%SSA Contract Forecast%')).first()
                if source:
                    proposal_count = session.query(Proposal).filter(
                        Proposal.source_id == source.id
                    ).count()
                else:
                    proposal_count = 0
            
            logger.info(f"SSA Contract Forecast scraper completed successfully. Collected {proposal_count} proposals in {collection_time:.2f} seconds")
            return {
                "status": "success", 
                "message": "Scraper completed successfully", 
                "task_id": task_id,
                "proposals_collected": proposal_count,
                "collection_time": collection_time
            }
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

@celery_app.task(bind=True, name='src.tasks.scraper_tasks.run_all_scrapers_task')
def run_all_scrapers_task(self):
    """Celery task to run all scrapers in parallel"""
    logger.info("Starting all scrapers task")
    task_id = self.request.id
    start_time = datetime.utcnow()
    
    try:
        # Import celery.group here to avoid circular imports
        from celery import group
        
        # Create a group of tasks to run in parallel
        tasks = group([
            run_acquisition_gateway_scraper_task.s(),
            run_ssa_contract_forecast_scraper_task.s()
        ])
        
        # Run the tasks in parallel
        result = tasks.apply_async()
        
        # Wait for all tasks to complete
        task_results = result.get()
        
        # Calculate total collection time
        end_time = datetime.utcnow()
        collection_time = (end_time - start_time).total_seconds()
        
        # Count total proposals collected
        total_proposals = 0
        
        # Update the last_scraped timestamp for all data sources
        with session_scope() as session:
            data_sources = session.query(DataSource).all()
            for data_source in data_sources:
                data_source.last_scraped = datetime.utcnow()
                
                # Count proposals for this source
                from src.database.models import Proposal
                proposal_count = session.query(Proposal).filter(
                    Proposal.source_id == data_source.id
                ).count()
                total_proposals += proposal_count
                
            session.commit()
        
        logger.info(f"All scrapers completed. Collected {total_proposals} proposals in {collection_time:.2f} seconds")
        return {
            "status": "success", 
            "message": "All scrapers completed", 
            "task_id": task_id, 
            "results": task_results,
            "proposals_collected": total_proposals,
            "collection_time": collection_time
        }
        
    except Exception as e:
        logger.exception(f"Unexpected error running all scrapers: {e}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": f"Unexpected error: {str(e)}", "error_code": "TASK_ERROR", "task_id": task_id}

@celery_app.task(bind=True, name='src.tasks.scraper_tasks.force_collect_task')
def force_collect_task(self, source_id=None):
    """
    Celery task to force collection from a specific source.
    
    Args:
        source_id (int, optional): ID of the data source to collect from.
            If None, collect from all sources.
    """
    logger.info(f"Starting force collect task for source_id={source_id}")
    task_id = self.request.id
    
    try:
        if source_id is None:
            # Run all scrapers
            return run_all_scrapers_task.delay().get()
        
        # Get the data source
        with session_scope() as session:
            data_source = session.query(DataSource).filter(DataSource.id == source_id).first()
            
            if not data_source:
                error_msg = f"Data source with ID {source_id} not found"
                logger.error(error_msg)
                return {"status": "error", "message": error_msg, "error_code": "RESOURCE_NOT_FOUND", "task_id": task_id}
            
            # Run the appropriate scraper based on the data source name
            if "Acquisition Gateway" in data_source.name:
                return run_acquisition_gateway_scraper_task.delay().get()
            elif "SSA Contract Forecast" in data_source.name:
                return run_ssa_contract_forecast_scraper_task.delay().get()
            else:
                error_msg = f"No scraper available for data source: {data_source.name}"
                logger.error(error_msg)
                return {"status": "error", "message": error_msg, "error_code": "SCRAPER_ERROR", "task_id": task_id}
                
    except Exception as e:
        logger.exception(f"Unexpected error in force collect task: {e}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": f"Unexpected error: {str(e)}", "error_code": "TASK_ERROR", "task_id": task_id} 