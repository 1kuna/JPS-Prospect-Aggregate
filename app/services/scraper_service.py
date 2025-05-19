import datetime
from app.models import db, DataSource, ScraperStatus
from app.exceptions import NotFoundError, ScraperError, DatabaseError
from app.utils.logger import logger
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
            status_record = session.query(ScraperStatus).filter_by(source_id=source_id).order_by(ScraperStatus.last_checked.desc()).first()
            if not status_record: # Should have been created with data source
                status_record = ScraperStatus(source_id=source_id, status='pending', details='Status record created on first pull trigger.')
                session.add(status_record)

            status_record.status = 'working'
            status_record.last_checked = datetime.datetime.utcnow()
            status_record.details = "Scrape process initiated."
            session.commit()

            try:
                logger.info(f"Starting scrape for {data_source.name} (ID: {source_id})")
                scraper_instance.run() 
                
                status_record.status = 'completed'
                status_record.details = f"Scrape completed successfully at {datetime.datetime.utcnow().isoformat()}."
                data_source.last_scraped = datetime.datetime.utcnow() # Update last_scraped on successful completion
                logger.info(f"Scrape for {data_source.name} completed successfully.")
                result_message = f"Data pull for {data_source.name} initiated successfully. Final status: {status_record.status}"

            except Exception as scrape_exc:
                logger.error(f"Scraper for {data_source.name} failed: {scrape_exc}", exc_info=True)
                status_record.status = 'failed'
                status_record.details = f"Scrape failed: {str(scrape_exc)[:500]}" # Truncate long errors
                # We re-raise the ScraperError to be handled by the route or a global error handler
                raise ScraperError(f"Scraping {data_source.name} failed: {scrape_exc}")
            finally:
                status_record.last_checked = datetime.datetime.utcnow()
                session.commit()

            return {"status": "success", "message": result_message, "data_source_name": data_source.name, "scraper_status": status_record.status}

        except NotFoundError as nfe:
            db.session.rollback()
            # Re-raise to be caught by Flask error handlers
            raise nfe
        except ScraperError as se:
            db.session.rollback()
            # Log here or ensure it's logged by the caller/global handler
            logger.error(f"Scraper service error for source ID {source_id}: {se}", exc_info=True)
            raise se
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in scraper service for source ID {source_id}: {e}", exc_info=True)
            # Attempt to update status record if it exists
            if 'status_record' in locals() and status_record:
                try:
                    status_record.status = 'failed'
                    status_record.details = f"Pull process failed unexpectedly in service: {str(e)[:500]}"
                    status_record.last_checked = datetime.datetime.utcnow()
                    session.commit()
                except Exception as final_commit_e:
                    logger.error(f"Failed to commit final error status in service for source ID {source_id}: {final_commit_e}", exc_info=True)
                    db.session.rollback() # Rollback this nested attempt
            raise DatabaseError(f"Unexpected error processing pull for {data_source.name if 'data_source' in locals() and data_source else source_id} in service")

    # TODO: Add other scraper-related service methods here 