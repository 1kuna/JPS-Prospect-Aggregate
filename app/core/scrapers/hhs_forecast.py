"""Department of Health and Human Services Opportunity Forecast scraper."""

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
from app.config import HHS_FORECAST_URL # Need to add this to config.py
from app.utils.scraper_utils import handle_scraper_error

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.hhs_forecast")

class HHSForecastScraper(BaseScraper):
    """Scraper for the HHS Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the HHS Forecast scraper."""
        super().__init__(
            source_name="HHS Forecast", # Updated source name
            base_url=HHS_FORECAST_URL, # Updated URL config variable
            debug_mode=debug_mode
        )
    
    def download_forecast_document(self):
        """
        Download the forecast document from the HHS website.
        Requires clicking 'View All' then 'Export'.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Attempting to download HHS forecast document")
        
        # Selectors (these might need adjustment based on actual page structure)
        view_all_selector = 'button[data-cy="viewAllBtn"]' 
        export_button_selector = 'button:has-text("Export")' 
        # Add a check for a table or data container to ensure data is loaded
        data_container_selector = 'div.view-content' # Example: Adjust based on inspection
        
        try:
            # Navigate to the main forecast page
            self.logger.info(f"Navigating to {self.base_url}")
            self.navigate_to_url()
            self.logger.info("Page loaded.")

            # Wait specifically for the 'View All' button
            self.logger.info(f"Waiting for '{view_all_selector}' button to be visible...")
            try:
                self.page.locator(view_all_selector).wait_for(state='visible', timeout=10000) # 10 seconds
                self.logger.info(f"'{view_all_selector}' button is visible.")
            except PlaywrightTimeoutError:
                self.logger.error("Could not find 'View All' button within timeout.")
                raise ScraperError("Could not find 'View All' button on the page after waiting")
            
            # Click 'View All'
            self.logger.info(f"Locating and clicking '{view_all_selector}'")
            self.page.locator(view_all_selector).click()
            self.logger.info("Clicked 'View All'. Waiting for data container and Export button...")

            # Wait for the data container to become visible after clicking 'View All'
            try:
                self.page.locator(data_container_selector).wait_for(state='visible', timeout=10000) # 10 seconds
                self.logger.info("Data container found after clicking 'View All'.")
            except PlaywrightTimeoutError:
                self.logger.warning("Data container did not become visible within 10s after clicking 'View All'.")
                # Continue, maybe the export button is still available

            # Wait for the Export button to be visible and ready
            export_button = self.page.locator(export_button_selector)
            try:
                export_button.wait_for(state='visible', timeout=10000) # Shortened to 10 seconds
                self.logger.info("Export button is visible.")
            except PlaywrightTimeoutError as e:
                self.logger.error(f"Export button did not become visible/enabled within 10s: {e}")
                raise ScraperError("Export button did not appear or become enabled after clicking 'View All'")

            # Click the Export button and wait for the download
            self.logger.info(f"Clicking Export button and waiting for download...")
            with self.page.expect_download(timeout=90000) as download_info:
                 export_button.click()

            download = download_info.value
            download_path = download.path() # Playwright saves to a temp location

            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'hhs_download.xlsx'") # Assuming excel
                original_filename = "hhs_download.xlsx"

            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.xlsx' # Default extension
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")
                
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'hhs'
            final_filename = f"hhs_{timestamp_str}{ext}" 
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
            self.logger.error(f"Timeout error during HHS forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Timeout during download process")
            raise ScraperError(f"Timeout during HHS forecast download process: {str(e)}")
        except Exception as e:
            self.logger.error(f"General error during HHS forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Error downloading HHS forecast document")
            # Ensure the original exception type isn't lost if it's not a ScraperError already
            if not isinstance(e, ScraperError):
                 raise ScraperError(f"Failed to download HHS forecast document: {str(e)}") from e
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
    """Run the HHS Forecast scraper."""
    source_name = "HHS Forecast"
    local_logger = logger
    scraper = None
    
    try:
        # Removed interval check logic
        # if not force and download_tracker.should_download(source_name):
        #     local_logger.info(f"Skipping scrape for {source_name} due to recent download")
        #     return True

        scraper = HHSForecastScraper(debug_mode=False)
        local_logger.info(f"Running {source_name} scraper")
        result = scraper.scrape() 
        
        if not result or not result.get("success", False):
            error_msg = result.get("error", f"{source_name} scraper failed without specific error") if result else f"{source_name} scraper failed without specific error"
            # Error logging should happen deeper, just raise
            raise ScraperError(error_msg)
        
        # Removed: download_tracker.set_last_download_time(source_name)
        # local_logger.info(f"Updated download tracker for {source_name}")
        # update_scraper_status(source_name, "working", None) # Keep commented out
        return True
    except ImportError as e:
        error_msg = f"Import error for {source_name}: {str(e)}"
        local_logger.error(error_msg)
        # handle_scraper_error(e, source_name, "Import error") # Already called?
        raise
    except ScraperError as e:
        local_logger.error(f"ScraperError occurred for {source_name}: {str(e)}")
        # Error should have been logged by handle_scraper_error already
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
        run_scraper(force=True)
        print("HHS Forecast scraper finished successfully (DB operations skipped).")
    except Exception as e:
        print(f"HHS Forecast scraper failed: {e}")
        # Print detailed traceback for direct execution errors
        traceback.print_exc() 