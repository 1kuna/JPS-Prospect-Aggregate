"""Acquisition Gateway scraper."""

# Standard library imports
import os
import sys
import time
import datetime
import traceback
import shutil

# Third-party imports
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd

# Local application imports
from app.core.base_scraper import BaseScraper
from app.database.connection import session_scope, get_db as db_session
from app.models import Proposal, ScraperStatus, DataSource
from app.database.download_tracker import download_tracker
from app.config import LOGS_DIR, DOWNLOADS_DIR, ACQUISITION_GATEWAY_URL, PAGE_NAVIGATION_TIMEOUT
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory, find_files
from app.utils.db_utils import update_scraper_status
from app.utils.logger import logger
from app.utils.scraper_utils import (
    check_url_accessibility,
    download_file,
    save_permanent_copy,
    read_dataframe,
    transform_dataframe,
    handle_scraper_error
)

# Set up logging
logger = logger.bind(name="scraper.acquisition_gateway")

def check_url_accessibility(url=None):
    """
    Check if a URL is accessible.
    
    Args:
        url (str, optional): URL to check. If None, uses ACQUISITION_GATEWAY_URL
        
    Returns:
        bool: True if the URL is accessible, False otherwise
    """
    url = url or ACQUISITION_GATEWAY_URL
    logger.info(f"Checking accessibility of {url}")
    
    try:
        # Set a reasonable timeout
        response = requests.head(url, timeout=10)
        
        # Check if the response is successful
        if response.status_code < 400:
            logger.info(f"URL {url} is accessible (status code: {response.status_code})")
            return True
        else:
            logger.error(f"URL {url} returned status code {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking URL {url}: {str(e)}")
        return False

class AcquisitionGatewayScraper(BaseScraper):
    """Scraper for the Acquisition Gateway site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the Acquisition Gateway scraper."""
        super().__init__(
            source_name="Acquisition Gateway",
            base_url=ACQUISITION_GATEWAY_URL,
            debug_mode=debug_mode
        )
    
    def navigate_to_forecast_page(self):
        """Navigate to the forecast page."""
        return self.navigate_to_url()
    
    def _get_field_mapping(self):
        """
        Get the mapping of CSV columns to database fields.
        
        Returns:
            dict: Mapping of CSV column names to database field names
        """
        return {
            'Title': 'title',
            'Agency': 'agency',
            'Description': 'description',
            'NAICS': 'naics_code',
            'Estimated Value': 'estimated_value',
            'Release Date': 'release_date',
            'Response Date': 'response_date',
            'Contact': 'contact_info',
            'URL': 'url',
            'Status': 'status',
            'Contract Type': 'contract_type',
            'Set-Aside': 'set_aside',
            'Competition Type': 'competition_type',
            'Solicitation Number': 'solicitation_number',
            'Award Date': 'award_date',
            'Place of Performance': 'place_of_performance',
            'Incumbent': 'incumbent'
        }
    
    def download_csv_file(self):
        """
        Download the CSV file from the Acquisition Gateway site.
        
        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        try:
            # Wait for the page to load
            self.logger.info("Waiting for page to load...")
            self.page.wait_for_load_state('networkidle', timeout=60000)
            
            # Find and click export button
            export_button = self.page.get_by_role('button', name='Export CSV')
            export_button.wait_for(state='visible', timeout=30000)
            
            # Download the file
            temp_path = download_file(self.page, 'button:has-text("Export CSV")')
            return save_permanent_copy(temp_path, self.source_name, 'csv')
            
        except PlaywrightTimeoutError as e:
            handle_scraper_error(e, self.source_name, "Timeout error during download")
            raise ScraperError(f"Timeout error during download: {str(e)}")
        except Exception as e:
            handle_scraper_error(e, self.source_name, "Error downloading CSV")
            raise ScraperError(f"Error downloading CSV: {str(e)}")
    
    def process_csv_data(self, csv_data, session, data_source):
        """
        Process the extracted CSV data and save to database.
        
        Args:
            csv_data: Path to the CSV file or list containing the path
            session: SQLAlchemy session
            data_source: DataSource object
            
        Returns:
            int: Number of proposals processed
        """
        # If csv_data is a list (from extract_func), get the first element
        if isinstance(csv_data, list):
            csv_data = csv_data[0]
            
        self.logger.info(f"Processing CSV file: {csv_data}")
        
        try:
            # Read the CSV file
            df = read_dataframe(csv_data, 'csv')
            
            # Get field mapping
            field_mapping = self._get_field_mapping()
            
            # Transform the data
            transformed_data = transform_dataframe(
                df=df,
                column_mapping=field_mapping,
                date_columns=['release_date', 'response_date', 'award_date'],
                value_columns=['estimated_value'],
                parse_funcs={
                    'date': self.parse_date,
                    'value': self.parse_value
                }
            )
            
            # Process each row
            count = 0
            for item in transformed_data:
                try:
                    # Add source_id and is_latest flag
                    item['source_id'] = data_source.id
                    item['is_latest'] = True
                    
                    # Update or create proposal
                    existing = self.get_proposal_query(session, item)
                    if existing:
                        for key, value in item.items():
                            setattr(existing, key, value)
                        self.logger.info(f"Updated existing proposal: {item['title']}")
                    else:
                        proposal = Proposal(**item)
                        session.add(proposal)
                        self.logger.info(f"Added new proposal: {item['title']}")
                    
                    count += 1
                except Exception as e:
                    self.logger.error(f"Error processing row: {str(e)}")
                    continue
            
            return count
            
        except Exception as e:
            handle_scraper_error(e, self.source_name, "Failed to process CSV file")
            raise ScraperError(f"Failed to process CSV file: {str(e)}")
    
    def get_proposal_query(self, session, proposal_data):
        """
        Get a query to find an existing proposal.
        
        Args:
            session: SQLAlchemy session
            proposal_data (dict): Proposal data containing at least source_id and title
            
        Returns:
            Proposal or None: Existing proposal if found, None otherwise
        """
        query = session.query(Proposal).filter(
            Proposal.source_id == proposal_data['source_id'],
            Proposal.title == proposal_data['title']
        )
        
        # Add additional filters if available
        if 'agency' in proposal_data and proposal_data['agency']:
            query = query.filter(Proposal.agency == proposal_data['agency'])
        
        if 'solicitation_number' in proposal_data and proposal_data['solicitation_number']:
            query = query.filter(Proposal.solicitation_number == proposal_data['solicitation_number'])
        
        return query.first()
    
    def scrape(self):
        """
        Run the scraper to extract and process data.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        return self.scrape_with_structure(
            setup_func=self.navigate_to_forecast_page,
            extract_func=self.download_csv_file,
            process_func=self.process_csv_data
        )

def check_last_download():
    """
    Check when the last download was performed.
    
    Returns:
        bool: True if a download was performed in the last 24 hours, False otherwise
    """
    # Use the scraper logger
    logger = logger.bind(name="scraper.acquisition_gateway")
    
    try:
        # Check if we should download using the download tracker
        scrape_interval_hours = 24  # Default to 24 hours
        
        if download_tracker.should_download("Acquisition Gateway", scrape_interval_hours):
            logger.info("No recent download found, proceeding with scrape")
            return False
        else:
            logger.info(f"Recent download found (within {scrape_interval_hours} hours), skipping scrape")
            return True
    except Exception as e:
        logger.error(f"Error checking last download: {str(e)}")
        return False

def run_scraper(force=False):
    """
    Run the Acquisition Gateway scraper.
    
    Args:
        force (bool): Whether to force the scraper to run even if it ran recently
        
    Returns:
        bool: True if scraping was successful, False otherwise
        
    Raises:
        ScraperError: If an error occurs during scraping
    """
    # Use a local logger from the module-level logger
    local_logger = logger 
    scraper = None
    
    try:
        # Check if we should run the scraper
        if not force and check_last_download():
            local_logger.info("Skipping scrape due to recent download")
            return True
        
        # Create an instance of the scraper
        scraper = AcquisitionGatewayScraper(debug_mode=False)
        
        # Check if the URL is accessible
        if not check_url_accessibility(ACQUISITION_GATEWAY_URL):
            error_msg = f"URL {ACQUISITION_GATEWAY_URL} is not accessible"
            handle_scraper_error(ScraperError(error_msg), "Acquisition Gateway Forecast")
            raise ScraperError(error_msg)
        
        # Run the scraper
        local_logger.info("Running Acquisition Gateway scraper")
        success = scraper.scrape()
        
        # If scraper.scrape() returns False, it means an error occurred
        if not success:
            error_msg = "Scraper failed without specific error"
            handle_scraper_error(ScraperError(error_msg), "Acquisition Gateway Forecast")
            raise ScraperError(error_msg)
        
        # Update the download tracker with the current time
        download_tracker.set_last_download_time("Acquisition Gateway Forecast")
        local_logger.info("Updated download tracker with current time")
        
        # Update the ScraperStatus table to indicate success
        update_scraper_status("Acquisition Gateway Forecast", "working", None)
            
        return True
    except ImportError as e:
        error_msg = f"Import error: {str(e)}"
        local_logger.error(error_msg)
        local_logger.error("Playwright module not found. Please install it with 'pip install playwright'")
        local_logger.error("Then run 'playwright install' to install the browsers")
        handle_scraper_error(e, "Acquisition Gateway Forecast", "Import error")
        raise ScraperError(error_msg)
    except ScraperError as e:
        handle_scraper_error(e, "Acquisition Gateway Forecast")
        raise
    except Exception as e:
        handle_scraper_error(e, "Acquisition Gateway Forecast", "Error running scraper")
        raise ScraperError(error_msg)
    finally:
        if scraper:
            try:
                local_logger.info("Cleaning up scraper resources")
                scraper.cleanup()
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup: {str(cleanup_error)}")
                local_logger.error(traceback.format_exc())

if __name__ == "__main__":
    run_scraper() 