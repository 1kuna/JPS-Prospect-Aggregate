"""Acquisition Gateway scraper."""

# Standard library imports
import os
import sys
import time
import datetime
import traceback
import shutil

# --- Start temporary path adjustment for direct execution ---
# Calculate the path to the project root directory (JPS-Prospect-Aggregate)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
# Add the project root to the Python path if it's not already there
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# --- End temporary path adjustment ---

# Third-party imports
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

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
    
    def download_csv_file(self):
        """
        Download the CSV file from the Acquisition Gateway site.
        Saves the file directly to the scraper's download directory.
        
        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        try:
            # Wait for the page to load
            self.logger.info("Waiting for page to load...")
            self.page.wait_for_load_state('networkidle', timeout=60000)
            
            # Find and click export button, waiting for the download to start
            export_button = self.page.get_by_role('button', name='Export CSV')
            export_button.wait_for(state='visible', timeout=30000)
            
            self.logger.info("Clicking Export CSV and waiting for download...")
            with self.page.expect_download(timeout=60000) as download_info:
                export_button.click()
            
            download = download_info.value
            # The file is saved by the _handle_download callback in BaseScraper
            # Construct the expected final path
            final_path = os.path.join(self.download_path, download.suggested_filename)
            self.logger.info(f"Download complete. File expected at: {final_path}")

            # Verify the file exists (saved by _handle_download)
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                self.logger.error(f"Verification failed: File not found or empty at {final_path}")
                # Attempt to save manually as fallback (using original playwright path)
                try:
                    fallback_path = download.path()
                    shutil.move(fallback_path, final_path)
                    self.logger.warning(f"Manually moved file from {fallback_path} to {final_path}")
                    if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                         raise ScraperError(f"Download failed even after fallback move: File missing or empty at {final_path}")
                except Exception as move_err:
                    raise ScraperError(f"Download failed: File missing/empty at {final_path} and fallback move failed: {move_err}")
            
            # Return the path within the scraper's download directory
            return final_path 
            
        except PlaywrightTimeoutError as e:
            handle_scraper_error(e, self.source_name, "Timeout error during download")
            raise ScraperError(f"Timeout error during download: {str(e)}")
        except Exception as e:
            handle_scraper_error(e, self.source_name, "Error downloading CSV")
            raise ScraperError(f"Error downloading CSV: {str(e)}")
    
    def scrape(self):
        """
        Run the scraper to download the file.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        # Simplified call: only setup and extract
        return self.scrape_with_structure(
            setup_func=self.navigate_to_forecast_page,
            extract_func=self.download_csv_file
            # No process_func needed
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
        # --> Temporarily skip this during direct script execution <---
        # update_scraper_status("Acquisition Gateway Forecast", "working", None)
            
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
        error_msg = f"Error running scraper: {str(e)}" # Added more specific error message
        handle_scraper_error(e, "Acquisition Gateway Forecast", "Error running scraper")
        raise ScraperError(error_msg)
    finally:
        if scraper:
            try:
                local_logger.info("Cleaning up scraper resources")
                scraper.cleanup_browser()
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup: {str(cleanup_error)}")
                local_logger.error(traceback.format_exc())

if __name__ == "__main__":
    # This block allows the script to be run directly for testing
    try:
        run_scraper(force=True)
        print("Scraper finished successfully (DB operations skipped).")
    except Exception as e:
        print(f"Scraper failed: {e}") 