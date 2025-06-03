import datetime
from datetime import timezone
from app.models import db # For db instance
from app.database.models import DataSource, ScraperStatus # For models
from app.exceptions import NotFoundError, ScraperError, DatabaseError
from app.utils.logger import logger
from app.utils.db_utils import update_scraper_status
from app.core.scrapers import SCRAPERS

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
                return ScraperService._execute_scrape(source_id)
        else:
            return ScraperService._execute_scrape(source_id)
    
    @staticmethod
    def _execute_scrape(source_id: int):
        session = db.session
        data_source = None
        initial_status_update_failed = False
        original_exception_from_initial_status_update = None
        try:
            data_source = session.query(DataSource).filter_by(id=source_id).first()
            if not data_source:
                raise NotFoundError(f"Data source with ID {source_id} not found.")

            if not data_source.scraper_key:
                raise ScraperError(f"Data source {data_source.name} (ID: {source_id}) does not have a scraper_key configured.")

            ScraperClass = SCRAPERS.get(data_source.scraper_key)
            if not ScraperClass:
                raise ScraperError(f"No scraper configured for scraper_key: '{data_source.scraper_key}' for data source: {data_source.name}")

            # Initialize scraper with appropriate debug mode
            # All scrapers run by the service should be headless (debug_mode=False)
            # Stealth and specific launch args are handled in BaseScraper/individual scrapers.
            scraper_instance = ScraperClass(debug_mode=False)
            
            initial_status_update_succeeded = False
            try:
                # Update status to 'working' before starting
                update_scraper_status(source_id=data_source.id, status='working', details="Scrape process initiated.")
                initial_status_update_succeeded = True
            except Exception as initial_status_exc:
                initial_status_update_failed = True
                original_exception_from_initial_status_update = initial_status_exc
                # update_scraper_status already logs and rolls back.
                # Re-raise to be caught by the main exception handler.
                raise # Using bare raise to re-raise the original exception initial_status_exc

            if initial_status_update_succeeded:
                try:
                    logger.info(f"Starting scrape for {data_source.name} (ID: {source_id})")
                    scrape_result = scraper_instance.run()

                    if isinstance(scrape_result, dict) and not scrape_result.get('success', False):
                        error_msg = scrape_result.get('error', 'Unknown error during scraping')
                        logger.error(f"Scraper returned failure for {data_source.name}: {error_msg}")
                        update_scraper_status(source_id=data_source.id, status='failed', details=error_msg[:500])
                        raise ScraperError(f"Scraping {data_source.name} failed: {error_msg}")

                    update_scraper_status(source_id=data_source.id, status='completed', details=f"Scrape completed successfully at {datetime.datetime.now(timezone.utc).isoformat()}.")
                    data_source.last_scraped = datetime.datetime.now(timezone.utc)
                    session.commit()
                    logger.info(f"Scrape for {data_source.name} completed successfully.")
                    latest_status_record = session.query(ScraperStatus).filter_by(source_id=source_id).order_by(ScraperStatus.last_checked.desc()).first()
                    final_status_str = latest_status_record.status if latest_status_record else "unknown"
                    result_message = f"Data pull for {data_source.name} processed. Final status: {final_status_str}"
                    return {"status": "success", "message": result_message, "data_source_name": data_source.name, "scraper_status": final_status_str}

                except Exception as scrape_exc: # Catch any exception from scraper_instance.run() or the success logic above
                    logger.error(f"Scraper for {data_source.name} failed: {scrape_exc}", exc_info=True)
                    error_detail = f"Scrape failed: {str(scrape_exc)[:500]}"
                    update_scraper_status(source_id=data_source.id, status='failed', details=error_detail)
                    raise ScraperError(f"Scraping {data_source.name} failed: {scrape_exc}") from scrape_exc
            # If initial_status_update_succeeded is False, it implies an exception was raised from the initial
            # update_scraper_status call, which is then caught by the main exception handlers below.
            # Thus, no explicit 'else' block is needed here to handle that failure path.

        except NotFoundError as nfe:
            session.rollback() # Ensure rollback is called
            raise nfe # Re-raise to be caught by Flask error handlers
        except ScraperError as se:
            # Rollback might have been handled by update_scraper_status if it was called for failure
            # However, if ScraperError is raised before that, a rollback here could be useful.
            # For now, let's assume update_scraper_status handles its transaction or the generic except does.
            logger.error(f"Scraper service error for source ID {source_id}: {se}", exc_info=True)
            raise se
        except Exception as e:
            # Rollback might have been handled by update_scraper_status if it was called for failure
            # However, if ScraperError is raised before that, a rollback here could be useful.
            # For now, let's assume update_scraper_status handles its transaction or the generic except does.
            logger.error(f"Unexpected error in scraper service for source ID {source_id}: {e}", exc_info=True)

            if initial_status_update_failed:
                # Initial status update failed, update_scraper_status already handled rollback and logging.
                # We just need to raise a ScraperError. original_exception_from_initial_status_update has the original error.
                # The data_source should be available here because the failure happened after fetching it.
                raise ScraperError(f"Initial status update for {data_source.name if data_source else source_id} failed: {str(original_exception_from_initial_status_update)}") from original_exception_from_initial_status_update
            else:
                # Error occurred after initial 'working' status was set, or data_source was not fetched.
                try:
                    session.rollback() # Attempt rollback first
                except Exception as rb_exc:
                    logger.error(f"Rollback failed during generic exception handling for source ID {source_id}: {rb_exc}", exc_info=True)

                if data_source: # Check if data_source object was fetched and initial status was likely set
                    error_detail = f"Pull process failed unexpectedly in service: {str(e)[:500]}"
                    # This update_scraper_status will attempt its own session commit.
                    update_scraper_status(source_id=data_source.id, status='failed', details=error_detail)

                # Consistently raise ScraperError for issues within the service execution logic
                ds_name_for_error = data_source.name if data_source else f"ID {source_id}"
                raise ScraperError(f"Unexpected error processing pull for {ds_name_for_error} in service: {e}") from e

    # TODO: Add other scraper-related service methods here 