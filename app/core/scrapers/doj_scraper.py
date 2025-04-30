"""Department of Justice Opportunity Forecast scraper."""

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
from app.config import DOJ_FORECAST_URL # Need to add this to config.py
from app.utils.scraper_utils import handle_scraper_error

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.doj_forecast")

class DOJForecastScraper(BaseScraper):
    """Scraper for the DOJ Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DOJ Forecast scraper."""
        super().__init__(
            source_name="DOJ Forecast", # Updated source name
            base_url=DOJ_FORECAST_URL, # Updated URL config variable
            debug_mode=debug_mode
        )
    
    def download_forecast_document(self):
        """
        Download the forecast Excel document from the DOJ website.
        Requires clicking the 'Download the Excel File' link.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Attempting to download DOJ forecast document")
        
        # Selector for the Excel download link
        download_link_selector = 'a:has-text("Download the Excel File")' 
        
        try:
            # Navigate to the main forecast page
            self.logger.info(f"Navigating to {self.base_url}")
            self.navigate_to_url()
            self.logger.info("Page loaded.")
            
            # Wait for the download link to be visible and ready
            download_link = self.page.locator(download_link_selector)
            self.logger.info(f"Waiting for '{download_link_selector}' link to be visible...")
            try:
                download_link.wait_for(state='visible', timeout=20000) # Increased timeout slightly
                self.logger.info(f"'{download_link_selector}' link is visible.")
            except PlaywrightTimeoutError as e:
                self.logger.error(f"Download link did not become visible/enabled within 20s: {e}")
                raise ScraperError("Download link did not appear or become enabled")

            # Click the download link and wait for the download
            self.logger.info(f"Clicking download link and waiting for download...")
            with self.page.expect_download(timeout=90000) as download_info:
                 download_link.click()

            download = download_info.value
            download_path = download.path() # Playwright saves to a temp location
            
            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'doj_download.xlsx'")
                original_filename = "doj_download.xlsx"

            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.xlsx' # Default extension
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'doj'
            final_filename = f"doj_{timestamp_str}{ext}" 
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
            self.logger.error(f"Timeout error during DOJ forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Timeout during download process")
            raise ScraperError(f"Timeout during DOJ forecast download process: {str(e)}")
        except Exception as e:
            self.logger.error(f"General error during DOJ forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Error downloading DOJ forecast document")
            if not isinstance(e, ScraperError):
                 raise ScraperError(f"Failed to download DOJ forecast document: {str(e)}") from e
            else:
                 raise
    
    def scrape(self):
        """
        Run the scraper to download the forecast document.
        Returns a result dict from scrape_with_structure.
        """
        return self.scrape_with_structure(
            extract_func=self.download_forecast_document
        )

def run_scraper(force=False):
    """Run the DOJ Forecast scraper."""
    source_name = "DOJ Forecast"
    local_logger = logger
    scraper = None
    
    try:
        scraper = DOJForecastScraper(debug_mode=False)
        local_logger.info(f"Running {source_name} scraper")
        result = scraper.scrape() 
        
        if not result or not result.get("success", False):
            error_msg = result.get("error", f"{source_name} scraper failed without specific error") if result else f"{source_name} scraper failed without specific error"
            raise ScraperError(error_msg)
        
        return {"success": True, "file_path": result.get("file_path"), "message": f"{source_name} scraped successfully"}
    
    except ImportError as e:
        error_msg = f"Import error for {source_name}: {str(e)}"
        local_logger.error(error_msg)
        handle_scraper_error(e, source_name, "Import error")
        raise ScraperError(error_msg) from e
    except ScraperError as e:
        local_logger.error(f"ScraperError occurred for {source_name}: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"Unexpected error running {source_name} scraper: {str(e)}"
        handle_scraper_error(e, source_name, f"Unexpected error in run_scraper for {source_name}")
        raise ScraperError(error_msg) from e
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
            print(f"DOJ Forecast scraper finished successfully. File at: {result.get('file_path', 'N/A')}")
        else:
             print(f"DOJ Forecast scraper failed. Check logs for details.")
             # sys.exit(1) 
    except Exception as e:
        print(f"DOJ Forecast scraper failed: {e}")
        traceback.print_exc()
        # sys.exit(1) 