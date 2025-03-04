"""
Import CSV Script.
This script will:
1. Process the CSV file in the downloads folder
2. Import the data into the database
"""

import os
import sys
import glob
import logging
import datetime

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def import_csv():
    """Import the CSV file into the database"""
    logger.info("Starting CSV import process")
    
    # Import the scraper
    from src.scrapers.acquisition_gateway import AcquisitionGatewayScraper
    from src.database.db import get_session, close_session
    from src.database.models import DataSource
    
    # Get the latest CSV file in the downloads folder
    downloads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'downloads')
    csv_files = glob.glob(os.path.join(downloads_dir, '*.csv'))
    
    if not csv_files:
        logger.error("No CSV files found in the downloads folder")
        return
    
    # Sort by modification time (newest first)
    csv_files.sort(key=os.path.getmtime, reverse=True)
    latest_csv = csv_files[0]
    
    logger.info(f"Found latest CSV file: {latest_csv}")
    
    # Get a database session
    session = get_session()
    
    try:
        # Get or create the data source
        data_source = session.query(DataSource).filter_by(name="Acquisition Gateway Forecast").first()
        
        if not data_source:
            logger.info("Creating new data source")
            data_source = DataSource(
                name="Acquisition Gateway Forecast",
                url="https://acquisitiongateway.gov/forecast",
                description="Acquisition Gateway Forecast data"
            )
            session.add(data_source)
            session.commit()
        
        # Create a scraper instance
        scraper = AcquisitionGatewayScraper(debug_mode=True)
        
        # Process the CSV file
        logger.info(f"Processing CSV file: {latest_csv}")
        new_count = scraper.process_csv(latest_csv, session, data_source)
        
        # Update the last scraped timestamp
        data_source.last_scraped = datetime.datetime.utcnow()
        session.commit()
        
        logger.info(f"CSV processing complete. Added {new_count} new proposals.")
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        session.rollback()
    finally:
        # Close the session
        close_session(session)

if __name__ == "__main__":
    import_csv() 