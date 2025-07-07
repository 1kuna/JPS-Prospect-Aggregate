import datetime
import asyncio
import threading
from datetime import timezone
from app.database import db
from app.database.models import DataSource, ScraperStatus
from app.exceptions import NotFoundError, ScraperError, DatabaseError
from app.utils.logger import logger
from app.utils.database_helpers import update_scraper_status
from app.core.scrapers import SCRAPERS
from app.config import active_config

# Set up logging using the centralized utility
logger = logger.bind(name="services.scraper_service")

class ScraperService:
    # Class-level lock to prevent multiple scrapers from running simultaneously
    _scraper_locks = {}
    _locks_mutex = threading.Lock()
    
    @staticmethod
    def _get_or_create_lock(source_id: int) -> threading.Lock:
        """Get or create a lock for a specific source ID."""
        with ScraperService._locks_mutex:
            if source_id not in ScraperService._scraper_locks:
                ScraperService._scraper_locks[source_id] = threading.Lock()
            return ScraperService._scraper_locks[source_id]
    
    @staticmethod
    def trigger_scrape(source_id: int):
        # Get lock for this source ID to prevent concurrent execution
        scraper_lock = ScraperService._get_or_create_lock(source_id)
        
        # Try to acquire lock without blocking
        if not scraper_lock.acquire(blocking=False):
            raise ScraperError(f"Scraper for source ID {source_id} is already running")
        
        try:
            # Import Flask's current_app here to avoid circular imports
            from flask import current_app
            
            # Ensure we have an application context
            if current_app is None:
                from app import create_app
                app = create_app()
                with app.app_context():
                    return ScraperService._run_scrape_with_loop_handling(source_id)
            else:
                return ScraperService._run_scrape_with_loop_handling(source_id)
        finally:
            # Always release the lock
            scraper_lock.release()
    
    @staticmethod
    def _run_scrape_with_loop_handling(source_id: int):
        """Handle event loop detection and execution properly."""
        try:
            # Check if we're already in an event loop
            current_loop = asyncio.get_running_loop()
            # If we get here, there's already a running loop
            # We need to run in a thread to avoid the conflict
            import concurrent.futures
            
            def run_in_new_loop():
                # Create a new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(ScraperService._execute_scrape(source_id))
                finally:
                    new_loop.close()
            
            # Run in a separate thread with its own event loop
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()
                
        except RuntimeError:
            # No running loop, we can use asyncio.run() directly
            return asyncio.run(ScraperService._execute_scrape(source_id))
    
    @staticmethod
    async def _execute_scrape(source_id: int):
        session = db.session
        data_source = None
        try:
            data_source = session.query(DataSource).filter_by(id=source_id).first()
            if not data_source:
                raise NotFoundError(f"Data source with ID {source_id} not found.")

            if not data_source.scraper_key:
                raise ScraperError(f"Data source {data_source.name} (ID: {source_id}) does not have a scraper_key configured.")

            ScraperClass = SCRAPERS.get(data_source.scraper_key)
            if not ScraperClass:
                raise ScraperError(f"No scraper configured for scraper_key: '{data_source.scraper_key}' for data source: {data_source.name}")

            # Consolidated scrapers don't need config parameters - they handle config internally
            scraper_instance = ScraperClass()
            
            # Update status to 'working' before starting
            update_scraper_status(source_id=data_source.id, status='working', details="Scrape process initiated.")

            try:
                logger.info(f"Starting scrape for {data_source.name} (ID: {source_id})")
                
                # Since we handle event loop detection in _run_scrape_with_loop_handling,
                # we can safely await the scraper directly
                records_loaded = await scraper_instance.scrape()
                
                if records_loaded > 0:
                    # Successful scrape
                    update_scraper_status(
                        source_id=data_source.id, 
                        status='completed', 
                        details=f"Scrape completed successfully. Loaded {records_loaded} records at {datetime.datetime.now().isoformat()}."
                    )
                    data_source.last_scraped = datetime.datetime.now()
                    session.commit()
                    
                    logger.info(f"Scrape for {data_source.name} completed successfully. Loaded {records_loaded} records.")
                    latest_status_record = session.query(ScraperStatus).filter_by(source_id=source_id).order_by(ScraperStatus.last_checked.desc()).first()
                    final_status_str = latest_status_record.status if latest_status_record else "completed"
                    result_message = f"Data pull for {data_source.name} completed successfully. Loaded {records_loaded} records."
                    
                else:
                    # No records loaded (could be empty data source or processing error)
                    update_scraper_status(
                        source_id=data_source.id, 
                        status='completed', 
                        details=f"Scrape completed but no records were loaded at {datetime.datetime.now().isoformat()}."
                    )
                    data_source.last_scraped = datetime.datetime.now()
                    session.commit()
                    
                    logger.warning(f"Scrape for {data_source.name} completed but no records were loaded.")
                    final_status_str = "completed"
                    result_message = f"Data pull for {data_source.name} completed but no records were loaded."

            except Exception as scrape_exc: # Catch any exception from scraper_instance.run()
                logger.error(f"Scraper for {data_source.name} failed: {scrape_exc}", exc_info=True)
                error_detail = f"Scrape failed: {str(scrape_exc)[:500]}"
                update_scraper_status(source_id=data_source.id, status='failed', details=error_detail)
                # Re-raise as ScraperError to be handled by the route or a global error handler
                raise ScraperError(f"Scraping {data_source.name} failed: {scrape_exc}") from scrape_exc
            # No 'finally' block here to commit status, as update_scraper_status handles its own commits.

            return {"status": "success", "message": result_message, "data_source_name": data_source.name, "scraper_status": final_status_str}

        except NotFoundError as nfe:
            # db.session.rollback() # Typically handled by app error handlers or session teardown
            raise nfe # Re-raise to be caught by Flask error handlers
        except ScraperError as se:
            # db.session.rollback()
            logger.error(f"Scraper service error for source ID {source_id}: {se}", exc_info=True)
            raise se
        except Exception as e:
            # db.session.rollback()
            logger.error(f"Unexpected error in scraper service for source ID {source_id}: {e}", exc_info=True)
            if data_source: # Check if data_source object was fetched
                error_detail = f"Pull process failed unexpectedly in service: {str(e)[:500]}"
                update_scraper_status(source_id=data_source.id, status='failed', details=error_detail)
            raise DatabaseError(f"Unexpected error processing pull for {data_source.name if data_source else source_id} in service")

