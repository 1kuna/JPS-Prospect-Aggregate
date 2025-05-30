import datetime
from app.models import db, DataSource, ScraperStatus # ScraperStatus will be handled by the utility
from app.exceptions import NotFoundError, ScraperError, DatabaseError
from app.utils.logger import logger
from app.utils.db_utils import update_scraper_status # Import the utility
from app.core.scrapers import SCRAPERS # Import the central SCRAPERS registry

# Set up logging using the centralized utility
logger = logger.bind(name="services.scraper_service")

class ScraperService:
    @staticmethod
    def trigger_scrape(source_id: int):
        session = db.session
        try:
            data_source = session.query(DataSource).filter_by(id=source_id).first()
            if not data_source:
                raise NotFoundError(f"Data source with ID {source_id} not found.")

            if not data_source.scraper_key:
                raise ScraperError(f"Data source {data_source.name} (ID: {source_id}) does not have a scraper_key configured.")

            ScraperClass = SCRAPERS.get(data_source.scraper_key)
            if not ScraperClass:
                raise ScraperError(f"No scraper configured for scraper_key: '{data_source.scraper_key}' for data source: {data_source.name}")

            scraper_instance = ScraperClass()
            
            # Update status to 'working' before starting
            update_scraper_status(source_id=data_source.id, status='working', details="Scrape process initiated.")

            try:
                logger.info(f"Starting scrape for {data_source.name} (ID: {source_id})")
                # Assuming scraper_instance.run() is the correct method to execute the scrape.
                # If run() is from BaseScraper.scrape() which calls scrape_with_structure,
                # then process_func is part of it. If run() is specific to individual scrapers,
                # ensure it returns a meaningful result or raises specific exceptions.
                scraper_instance.run() # This should ideally return the result of process_func or raise error
                
                # If scrape is successful:
                update_scraper_status(source_id=data_source.id, status='completed', details=f"Scrape completed successfully at {datetime.datetime.utcnow().isoformat()}.")
                data_source.last_scraped = datetime.datetime.utcnow()
                session.commit() # Commit update to data_source.last_scraped
                
                logger.info(f"Scrape for {data_source.name} completed successfully.")
                # Get the latest status for the return message
                latest_status_record = session.query(ScraperStatus).filter_by(source_id=source_id).order_by(ScraperStatus.last_checked.desc()).first()
                final_status_str = latest_status_record.status if latest_status_record else "unknown"
                result_message = f"Data pull for {data_source.name} processed. Final status: {final_status_str}"

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