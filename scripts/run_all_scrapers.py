#!/usr/bin/env python3
"""
Script to run all scrapers sequentially.

This script runs all configured scrapers to pull data from various government sources.
"""

import sys
import logging
import time
import argparse # Add argparse
from pathlib import Path

# --- Path Setup ---
# Add the project root directory to the Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# --- End Path Setup ---

# --- Import Application Components ---
from app import create_app
from app.database import db
from app.database.models import DataSource
from app.services.scraper_service import ScraperService
from app.exceptions import ScraperError, NotFoundError
# --- End Imports ---

# --- Logging Setup ---
# Use a basic configuration for this script
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.propagate = False

# Silence SQLAlchemy INFO logs
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
# --- End Logging Setup ---


def run_single_scraper(source_id: int, source_name: str):
    """
    Runs a single scraper and logs the outcome.
    
    Args:
        source_id: The database ID of the data source
        source_name: The name of the data source
        
    Returns:
        tuple: (success: bool, duration: float, message: str)
    """
    start_time = time.time()
    logger.info(f"--- Running Scraper: {source_name} (ID: {source_id}) ---")
    
    try:
        result = ScraperService.trigger_scrape(source_id)
        duration = time.time() - start_time
        message = result.get("message", "Completed successfully")
        logger.info(f"--- Completed {source_name} in {duration:.2f}s ---")
        return True, duration, message
    except (ScraperError, NotFoundError) as e:
        duration = time.time() - start_time
        error_msg = str(e)
        logger.error(f"--- FAILED {source_name} after {duration:.2f}s: {error_msg} ---")
        return False, duration, error_msg
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"--- FAILED {source_name} after {duration:.2f}s: {error_msg} ---", exc_info=True)
        return False, duration, error_msg


def main():
    """Main function to run all scrapers sequentially."""
    
    app = create_app()
    with app.app_context():
        # --- Ensure Database Tables Exist ---
        logger.info("Checking and creating database tables if necessary...")
        try:
            db.create_all()
            logger.info("Database tables checked/created successfully.")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}", exc_info=True)
            sys.exit(1)
        # --- End Table Creation ---
        
        parser = argparse.ArgumentParser(description="Run scrapers for specified data sources.")
        parser.add_argument("--source-id", type=int, help="Run scraper for a single source ID.")
        parser.add_argument("--scraper-key", type=str, help="Run scraper for a single scraper key.")
        args = parser.parse_args()

        logger.info(">>> Starting scraper execution <<<")
        overall_start_time = time.time()
        
        # Get data sources based on arguments
        try:
            if args.source_id:
                data_sources = DataSource.query.filter_by(id=args.source_id).all()
                if not data_sources:
                    logger.error(f"No data source found with ID: {args.source_id}")
                    return
            elif args.scraper_key:
                data_sources = DataSource.query.filter_by(scraper_key=args.scraper_key).all()
                if not data_sources:
                    logger.error(f"No data source found with scraper key: {args.scraper_key}")
                    return
            else:
                # Default: Get all data sources that have scraper_keys configured
                data_sources = DataSource.query.filter(
                    DataSource.scraper_key.isnot(None)
                ).order_by(DataSource.id).all()
            
            if not data_sources:
                logger.warning("No data sources found to scrape based on criteria!")
                return
                
            logger.info(f"Found {len(data_sources)} data sources to scrape")
            
        except Exception as e:
            logger.error(f"Error fetching data sources: {e}", exc_info=True)
            sys.exit(1)
        
        # Run each scraper
        success_count = 0
        failure_count = 0
        results = []
        
        for source in data_sources:
            success, duration, message = run_single_scraper(source.id, source.name)
            results.append({
                'source': source.name,
                'success': success,
                'duration': duration,
                'message': message
            })
            
            if success:
                success_count += 1
            else:
                failure_count += 1
            
            # Small delay between scrapers to be respectful
            if source != data_sources[-1]:  # Don't wait after the last one
                logger.info("Waiting 2 seconds before next scraper...")
                time.sleep(2)
        
        overall_duration = time.time() - overall_start_time
        logger.info(">>> All scrapers finished <<<")
        logger.info(f"Summary: Success={success_count}, Failure={failure_count}")
        logger.info(f"Total execution time: {overall_duration:.2f}s")
        
        # Print detailed results
        logger.info("\n=== Detailed Results ===")
        detailed_results_path = Path(project_root) / "temp" / "run_all_scrapers_results.log"
        detailed_results_path.parent.mkdir(parents=True, exist_ok=True) # Ensure temp dir exists

        with open(detailed_results_path, "w") as f_log:
            f_log.write("=== Detailed Results ===\n")
            for result in results:
                status = "SUCCESS" if result['success'] else "FAILED"
                log_line = f"{result['source']}: {status} ({result['duration']:.2f}s) - {result['message']}\n"
                logger.info(log_line.strip()) # Log to stdout as well
                f_log.write(log_line)

            if not results and (args.source_id or args.scraper_key):
                 no_scraper_ran_msg = "No scraper was run for the specified criteria.\n"
                 logger.info(no_scraper_ran_msg.strip())
                 f_log.write(no_scraper_ran_msg)
        logger.info(f"Detailed results also saved to {detailed_results_path}")


if __name__ == "__main__":
    main()