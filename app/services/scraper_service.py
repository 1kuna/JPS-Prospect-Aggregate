import datetime
import asyncio
from datetime import timezone
from app.models import db, DataSource, ScraperStatus
from app.exceptions import NotFoundError, ScraperError, DatabaseError
from app.utils.logger import logger
from app.utils.db_utils import update_scraper_status
from app.core.scrapers import SCRAPERS
from app.config import active_config

# Set up logging using the centralized utility
logger = logger.bind(name="services.scraper_service")

class ScraperService:
    @staticmethod
    def trigger_scrape(source_id: int):
        # Import Flask's current_app here to avoid circular imports
        from flask import current_app
        
        # Ensure we have an application context
        if current_app is None:
            from app import create_app
            app = create_app()
            with app.app_context():
                return asyncio.run(ScraperService._execute_scrape(source_id))
        else:
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
                
                # Try to detect if we're in an existing event loop
                try:
                    current_loop = asyncio.get_running_loop()
                    logger.info("Detected existing event loop, using asyncio.create_task")
                    
                    # We're in an existing loop, need to run as task
                    task = asyncio.create_task(scraper_instance.scrape())
                    records_loaded = await task
                    
                except RuntimeError:
                    # No running loop, we can use asyncio.run() directly
                    logger.info("No existing event loop detected, using asyncio.run()")
                    records_loaded = asyncio.run(scraper_instance.scrape())
                
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

    # TODO: Add other scraper-related service methods here 