"""Acquisition Gateway scraper."""

# Standard library imports
import os
import sys
import time
import datetime
import traceback
import logging
import shutil

# Third-party imports
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd

# Local application imports
from src.data_collectors.base_scraper import BaseScraper
from src.database.db import session_scope
from src.database.models import Proposal, ScraperStatus, DataSource
from src.database.download_tracker import download_tracker
from src.config import LOGS_DIR, DOWNLOADS_DIR, ACQUISITION_GATEWAY_URL, PAGE_NAVIGATION_TIMEOUT
from src.exceptions import ScraperError
from src.utils.file_utils import ensure_directory
from src.utils.db_utils import update_scraper_status
from src.utils.logger import logger
from src.utils.db_context import db_session

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
    
    def _download_and_verify_csv(self) -> str:
        """Download CSV file and verify its contents."""
        try:
            # Wait for the page to load
            self.logger.info("Waiting for page to load...")
            self.page.wait_for_load_state('networkidle', timeout=60000)
            
            # Find and click export button
            export_button = self.page.get_by_role('button', name='Export CSV')
            export_button.wait_for(state='visible', timeout=30000)
            
            with self.page.expect_download(timeout=60000) as download_info:
                export_button.click()
                download = download_info.value
                
                # Save and verify file
                download_path = download.path()
                if not os.path.exists(download_path) or os.path.getsize(download_path) == 0:
                    raise ScraperError("Download failed: File is empty or does not exist")
                
                return download_path
                
        except PlaywrightTimeoutError as e:
            raise ScraperError(f"Timeout error during download: {str(e)}")
        except Exception as e:
            raise ScraperError(f"Error downloading CSV: {str(e)}")
    
    def _save_permanent_copy(self, temp_path: str) -> str:
        """Save a permanent copy of the CSV file with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"acquisition_gateway_forecast_{timestamp}.csv"
        permanent_path = os.path.join(DOWNLOADS_DIR, filename)
        
        ensure_directory(os.path.dirname(permanent_path))
        shutil.copy2(temp_path, permanent_path)
        self.logger.info(f"Saved permanent copy to {permanent_path}")
        
        return permanent_path
    
    def _read_and_validate_csv(self, file_path: str) -> pd.DataFrame:
        """Read and validate CSV file contents."""
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                raise ScraperError("CSV file has no data rows")
            return df
        except pd.errors.EmptyDataError:
            raise ScraperError("CSV file is empty or has no data")
        except Exception as e:
            raise ScraperError(f"Error reading CSV file: {str(e)}")
    
    def _process_proposal(self, row: dict, data_source: DataSource, session) -> None:
        """Process a single proposal row."""
        try:
            # Extract data
            proposal_data = {
                'source_id': data_source.id,
                'title': row.get('Title', ''),
                'agency': row.get('Agency', ''),
                'description': row.get('Description', ''),
                'naics_code': row.get('NAICS', ''),
                'estimated_value': self.parse_value(row.get('Estimated Value', '')),
                'release_date': self.parse_date(row.get('Release Date', '')),
                'response_date': self.parse_date(row.get('Response Date', '')),
                'contact_info': row.get('Contact', ''),
                'url': self.base_url,
                'is_latest': True
            }
            
            # Skip rows without title
            if not proposal_data['title']:
                return
            
            # Update or create proposal
            existing = self.get_proposal_query(session, proposal_data)
            if existing:
                for key, value in proposal_data.items():
                    setattr(existing, key, value)
                self.logger.info(f"Updated existing proposal: {proposal_data['title']}")
            else:
                proposal = Proposal(**proposal_data)
                session.add(proposal)
                self.logger.info(f"Added new proposal: {proposal_data['title']}")
            
        except Exception as e:
            self.logger.error(f"Error processing proposal row: {str(e)}")
            self.logger.error(f"Row data: {row}")
    
    def process_csv_data(self, csv_data, session, data_source):
        """Process the extracted CSV data and save to database."""
        self.logger.info(f"Processing {len(csv_data)} rows of CSV data")
        
        count = 0
        for row in csv_data:
            try:
                self._process_proposal(row, data_source, session)
                count += 1
            except Exception as e:
                self.logger.error(f"Error processing row: {str(e)}")
                continue
        
        self.logger.info(f"Processed {count} proposals")
        return count
    
    def scrape(self):
        """Run the scraper to extract and process data."""
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
    # Use the scraper logger from logging
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
        if not scraper.check_url_accessibility():
            error_msg = f"URL {ACQUISITION_GATEWAY_URL} is not accessible"
            local_logger.error(error_msg)
            
            # Update the status in the database
            update_scraper_status("Acquisition Gateway Forecast", "error", error_msg)
            
            raise ScraperError(error_msg)
        
        # Run the scraper
        local_logger.info("Running Acquisition Gateway scraper")
        success = scraper.scrape()
        
        # If scraper.scrape() returns False, it means an error occurred
        if not success:
            error_msg = "Scraper failed without specific error"
            local_logger.error(error_msg)
            
            # Update the status in the database
            update_scraper_status("Acquisition Gateway Forecast", "error", error_msg)
            
            raise ScraperError(error_msg)
        
        # Update the download tracker with the current time
        download_tracker.set_last_download_time("Acquisition Gateway Forecast")
        local_logger.info("Updated download tracker with current time")
        
        # Update the ScraperStatus table to indicate success
        update_scraper_status("Acquisition Gateway Forecast", "working", None)
            
        return True
    except ImportError as e:
        # This will catch any ImportError that might occur when importing Playwright
        error_msg = f"Import error: {str(e)}"
        local_logger.error(error_msg)
        local_logger.error("Playwright module not found. Please install it with 'pip install playwright'")
        local_logger.error("Then run 'playwright install' to install the browsers")
        
        # Update the status in the database
        update_scraper_status("Acquisition Gateway Forecast", "error", error_msg)
        
        raise ScraperError(error_msg)
    except ScraperError as e:
        # Update the status in the database
        update_scraper_status("Acquisition Gateway Forecast", "error", str(e))
        
        # Re-raise ScraperError exceptions to propagate them
        raise
    except Exception as e:
        error_msg = f"Error running scraper: {str(e)}"
        local_logger.error(error_msg)
        local_logger.error(traceback.format_exc())
        
        # Update the status in the database
        update_scraper_status("Acquisition Gateway Forecast", "error", error_msg)
        
        raise ScraperError(error_msg)
    finally:
        # Ensure proper cleanup of resources
        if scraper:
            try:
                local_logger.info("Cleaning up scraper resources")
                scraper.cleanup()
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup: {str(cleanup_error)}")
                local_logger.error(traceback.format_exc())

if __name__ == "__main__":
    run_scraper() 