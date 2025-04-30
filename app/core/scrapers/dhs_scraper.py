"""Department of Homeland Security Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
import sys
import shutil
import datetime

# --- Start temporary path adjustment for direct execution ---
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# --- End temporary path adjustment ---

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
from app.core.base_scraper import BaseScraper
from app.exceptions import ScraperError
from app.utils.logger import logger
# from app.utils.db_utils import update_scraper_status # Keep for commented out code
from app.config import DHS_FORECAST_URL # Need to add this to config.py
from app.utils.scraper_utils import handle_scraper_error

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.dhs_forecast")

class DHSForecastScraper(BaseScraper):
    """Scraper for the DHS Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DHS Forecast scraper."""
        super().__init__(
            source_name="DHS Forecast", # Updated source name
            base_url=DHS_FORECAST_URL, # Updated URL config variable
            debug_mode=debug_mode
        )
    
    def download_forecast_document(self):
        """
        Download the forecast CSV document from the DHS APFS website.
        Requires waiting, then clicking the 'CSV' button.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Attempting to download DHS forecast document")
        
        # Selector for the CSV download button
        csv_button_selector = 'button.buttons-csv' 
        
        try:
            # Navigate to the main forecast page
            self.logger.info(f"Navigating to {self.base_url}")
            self.navigate_to_url()
            self.logger.info("Page loaded.")

            # Explicit wait for 10 seconds
            self.logger.info("Waiting for 10 seconds before interacting...")
            self.page.wait_for_timeout(10000) # 10 seconds explicit wait
            self.logger.info("Wait finished.")
            
            # Wait for the CSV button to be visible and ready
            csv_button = self.page.locator(csv_button_selector)
            self.logger.info(f"Waiting for '{csv_button_selector}' button to be visible...")
            try:
                csv_button.wait_for(state='visible', timeout=15000) # Increased timeout slightly
                self.logger.info(f"'{csv_button_selector}' button is visible.")
            except PlaywrightTimeoutError as e:
                self.logger.error(f"CSV button did not become visible/enabled within 15s: {e}")
                raise ScraperError("CSV download button did not appear or become enabled")

            # Click the CSV button and wait for the download
            self.logger.info(f"Clicking CSV button and waiting for download...")
            with self.page.expect_download(timeout=90000) as download_info:
                 csv_button.click()

            download = download_info.value
            download_path = download.path() # Playwright saves to a temp location

            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'dhs_download.csv'")
                original_filename = "dhs_download.csv" # Keep default but extension will be used

            _, ext = os.path.splitext(original_filename)
            if not ext: # Ensure there's an extension
                ext = '.csv' # Default extension if none found
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")
                
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'dhs'
            final_filename = f"dhs_{timestamp_str}{ext}" 
            final_path = os.path.join(self.download_path, final_filename)
            self.logger.info(f"Original suggested filename: {original_filename}")
            self.logger.info(f"Saving with standardized filename: {final_filename} to {final_path}")
            # --- End modification ---

            # Ensure the target directory exists before moving
            os.makedirs(self.download_path, exist_ok=True)

            # Move the downloaded file to the target directory using the new final_path
            try:
                 shutil.move(download_path, final_path)
                 self.logger.info(f"Download complete. Moved file to: {final_path}")
            except Exception as move_err:
                 self.logger.error(f"Error moving downloaded file from {download_path} to {final_path}: {move_err}")
                 raise ScraperError(f"Failed to move downloaded file: {move_err}") from move_err

            # Verify the file exists using the new final_path
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                self.logger.error(f"Verification failed: File not found or empty at {final_path}")
                raise ScraperError(f"Download verification failed: File missing or empty at {final_path}")

            self.logger.info(f"Download verification successful. File saved at: {final_path}")
            return final_path
            
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout error during DHS forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Timeout during download process")
            raise ScraperError(f"Timeout during DHS forecast download process: {str(e)}")
        except Exception as e:
            self.logger.error(f"General error during DHS forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Error downloading DHS forecast document")
            # Ensure the original exception type isn't lost if it's not a ScraperError already
            if not isinstance(e, ScraperError):
                 raise ScraperError(f"Failed to download DHS forecast document: {str(e)}") from e
            else:
                 raise # Re-raise the original ScraperError
    
    def scrape(self):
        """
        Run the scraper to download the forecast document.
        Returns a result dict from scrape_with_structure.
        """
        return self.scrape_with_structure(
            extract_func=self.download_forecast_document
        )

def run_scraper(force=False):
    """Run the DHS Forecast scraper."""
    source_name = "DHS Forecast"
    local_logger = logger
    scraper = None
    
    try:
        # Check if scraping should be skipped based on frequency
        # Note: `DHS_FORECAST_SCRAPE_INTERVAL_HOURS` would need to be added to config
        # Removed interval check logic
        # if not force and download_tracker.should_download(source_name, DHS_FORECAST_SCRAPE_INTERVAL_HOURS):
        # For now, just using a default or skipping this check if interval not defined
        # Removed interval check logic
        # if not force and download_tracker.should_download(source_name): # Default interval check
        #    local_logger.info(f"Skipping scrape for {source_name} due to recent download")
        #    return {"success": True, "message": "Skipped due to recent download"}

        scraper = DHSForecastScraper(debug_mode=False)
        local_logger.info(f"Running {source_name} scraper")
        result = scraper.scrape() 
        
        if not result or not result.get("success", False):
            error_msg = result.get("error", f"{source_name} scraper failed without specific error") if result else f"{source_name} scraper failed without specific error"
            # Error logging should happen deeper, just raise
            raise ScraperError(error_msg)
        
        # Removed: download_tracker.set_last_download_time(source_name)
        # local_logger.info(f"Updated download tracker for {source_name}")
        # update_scraper_status(source_name, "working", None) # Keep commented out
        return {"success": True, "file_path": result.get("file_path"), "message": f"{source_name} scraped successfully"}
    
    except ImportError as e:
        error_msg = f"Import error for {source_name}: {str(e)}"
        local_logger.error(error_msg)
        handle_scraper_error(e, source_name, "Import error") # Log error centrally
        raise ScraperError(error_msg) from e # Raise specific error type
    except ScraperError as e:
        local_logger.error(f"ScraperError occurred for {source_name}: {str(e)}")
        # Error should have been logged by handle_scraper_error or within scrape method
        raise # Re-raise the original ScraperError
    except Exception as e:
        error_msg = f"Unexpected error running {source_name} scraper: {str(e)}"
        handle_scraper_error(e, source_name, f"Unexpected error in run_scraper for {source_name}")
        raise ScraperError(error_msg) from e # Wrap unexpected errors
    finally:
        if scraper:
            try:
                local_logger.info(f"Cleaning up {source_name} scraper resources")
                scraper.cleanup_browser()
            except Exception as cleanup_error:
                local_logger.error(f"Error during {source_name} scraper cleanup: {str(cleanup_error)}")

if __name__ == "__main__":
    try:
        result = run_scraper(force=True)
        if result and result.get("success"):
            print(f"DHS Forecast scraper finished successfully. File at: {result.get('file_path', 'N/A')}")
        else:
             # Error should have been logged, print a simpler message
             print(f"DHS Forecast scraper failed. Check logs for details.")
             # Optionally, exit with a non-zero code for scripting
             # sys.exit(1) 
    except Exception as e:
        print(f"DHS Forecast scraper failed: {e}")
        # Print detailed traceback for direct execution errors
        traceback.print_exc() 
        # sys.exit(1)
