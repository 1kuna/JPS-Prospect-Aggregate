import datetime
from datetime import timezone
from app.models import db, DataSource, ScraperStatus
from app.exceptions import NotFoundError, ScraperError, DatabaseError
from app.utils.logger import logger
from app.utils.db_utils import update_scraper_status
from app.core.scrapers import SCRAPERS
from app.config import active_config

# Import all config classes
from app.core.scrapers.configs.acquisition_gateway_config import AcquisitionGatewayConfig
from app.core.scrapers.configs.doc_config import DOCConfig
from app.core.scrapers.configs.dhs_config import DHSConfig
from app.core.scrapers.configs.doj_config import DOJConfig
from app.core.scrapers.configs.dos_config import DOSConfig
from app.core.scrapers.configs.dot_config import DOTConfig
from app.core.scrapers.configs.hhs_config import HHSConfig
from app.core.scrapers.configs.ssa_config import SSAConfig
from app.core.scrapers.configs.treasury_config import TreasuryConfig

# Set up logging using the centralized utility
logger = logger.bind(name="services.scraper_service")

# Map scraper keys to their config classes
SCRAPER_CONFIGS = {
    "acq_gateway": AcquisitionGatewayConfig,
    "doc": DOCConfig,
    "dhs": DHSConfig,
    "doj": DOJConfig,
    "dos": DOSConfig,
    "hhs": HHSConfig,
    "ssa": SSAConfig,
    "treasury": TreasuryConfig,
    "dot": DOTConfig,
}

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
        try:
            data_source = session.query(DataSource).filter_by(id=source_id).first()
            if not data_source:
                raise NotFoundError(f"Data source with ID {source_id} not found.")

            if not data_source.scraper_key:
                raise ScraperError(f"Data source {data_source.name} (ID: {source_id}) does not have a scraper_key configured.")

            ScraperClass = SCRAPERS.get(data_source.scraper_key)
            if not ScraperClass:
                raise ScraperError(f"No scraper configured for scraper_key: '{data_source.scraper_key}' for data source: {data_source.name}")

            ConfigClass = SCRAPER_CONFIGS.get(data_source.scraper_key)
            if not ConfigClass:
                raise ScraperError(f"No config class found for scraper_key: '{data_source.scraper_key}' for data source: {data_source.name}")

            # Create config instance with base_url from active_config if needed
            config = ConfigClass()
            
            # Set base_url from active_config based on scraper_key
            if data_source.scraper_key == 'acq_gateway' and not config.base_url:
                config.base_url = active_config.ACQUISITION_GATEWAY_URL
            elif data_source.scraper_key == 'dhs' and not config.base_url:
                config.base_url = active_config.DHS_FORECAST_URL
            elif data_source.scraper_key == 'doc' and not config.base_url:
                config.base_url = active_config.COMMERCE_FORECAST_URL
            elif data_source.scraper_key == 'doj' and not config.base_url:
                config.base_url = active_config.DOJ_FORECAST_URL
            elif data_source.scraper_key == 'dos' and not config.base_url:
                config.base_url = active_config.DOS_FORECAST_URL
            elif data_source.scraper_key == 'dot' and not config.base_url:
                config.base_url = active_config.DOT_FORECAST_URL
            elif data_source.scraper_key == 'hhs' and not config.base_url:
                config.base_url = active_config.HHS_FORECAST_URL
            elif data_source.scraper_key == 'ssa' and not config.base_url:
                config.base_url = active_config.SSA_CONTRACT_FORECAST_URL
            elif data_source.scraper_key == 'treasury' and not config.base_url:
                config.base_url = active_config.TREASURY_FORECAST_URL

            # Initialize scraper with appropriate debug mode
            # DOT scraper needs special handling due to website blocking
            debug_mode = data_source.scraper_key == 'dot'  # Enable debug mode for DOT scraper
            scraper_instance = ScraperClass(config=config, debug_mode=debug_mode)
            
            # Update status to 'working' before starting
            update_scraper_status(source_id=data_source.id, status='working', details="Scrape process initiated.")

            try:
                logger.info(f"Starting scrape for {data_source.name} (ID: {source_id})")
                # Run the scraper and check the result
                scrape_result = scraper_instance.run()
                
                # Check if the scrape was successful
                if isinstance(scrape_result, dict) and not scrape_result.get('success', False):
                    # Scrape failed
                    error_msg = scrape_result.get('error', 'Unknown error during scraping')
                    logger.error(f"Scraper returned failure for {data_source.name}: {error_msg}")
                    update_scraper_status(source_id=data_source.id, status='failed', details=error_msg[:500])
                    raise ScraperError(f"Scraping {data_source.name} failed: {error_msg}")
                
                # If we get here, scrape is successful
                update_scraper_status(source_id=data_source.id, status='completed', details=f"Scrape completed successfully at {datetime.datetime.now(timezone.utc).isoformat()}.")
                data_source.last_scraped = datetime.datetime.now(timezone.utc)
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