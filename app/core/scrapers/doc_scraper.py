"""Department of Commerce Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
import sys
import shutil
import datetime # Added datetime import
from urllib.parse import urljoin

# --- Start temporary path adjustment for direct execution ---
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# --- End temporary path adjustment ---

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
from app.core.base_scraper import BaseScraper
# Proposal model likely not needed if just downloading
# from app.models import Proposal
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.utils.db_utils import update_scraper_status # Keep for commented out code
# We need to add COMMERCE_FORECAST_URL to config.py
from app.config import COMMERCE_FORECAST_URL 
from app.utils.scraper_utils import (
    # check_url_accessibility, # Removed this check
    # download_file, # Not directly used
    # save_permanent_copy, # Not directly used
    handle_scraper_error
)

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.doc")

class DocScraper(BaseScraper):
    """Scraper for the Department of Commerce (DOC) Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DOC Forecast scraper."""
        super().__init__(
            source_name="DOC Forecast",
            base_url=COMMERCE_FORECAST_URL,
            debug_mode=debug_mode
        )
    
    def _find_download_link_locator(self):
        """
        Find the locator for the forecast file download link.
        
        Returns:
            Locator: Playwright Locator object for the download link, or None.
        """
        link_text = "Current Procurement Forecasts"
        selector = f'a:has-text("{link_text}")'
        
        self.logger.info(f"Searching for download link locator with text: '{link_text}'")
        locator = self.page.locator(selector)
        
        if locator.count() > 0:
            try:
                href = locator.first.get_attribute('href')
                if href:
                    absolute_url = urljoin(self.page.url, href)
                    self.logger.info(f"Found download link locator. Href: {href} (Absolute: {absolute_url})")
                    # Optional: Add check if URL looks valid?
                else:
                     self.logger.warning("Found download link locator, but it has no href.")
                return locator.first
            except Exception as e:
                self.logger.error(f"Error getting href from locator: {e}")
                return locator.first
        
        self.logger.error(f"Could not find locator for link with text: '{link_text}'")
        return None
    
    def _save_debug_info(self):
        """Save debug information when the download link is not found."""
        # Save a screenshot for debugging
        screenshot_path = os.path.join(self.download_path, 'page_screenshot.png') # Save in scraper's dir
        self.page.screenshot(path=screenshot_path)
        self.logger.info(f"Saved screenshot to {screenshot_path}")
        
        # Save page content for debugging
        html_path = os.path.join(self.download_path, 'page_content.html') # Save in scraper's dir
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.page.content())
        self.logger.info(f"Saved page content to {html_path}")
    
    def download_forecast_document(self):
        """
        Download the forecast document from the Commerce website.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Attempting to download Commerce forecast document")
        
        try:
            # Navigate to the main forecast page first to establish context/cookies if needed
            self.logger.info(f"Navigating to {self.base_url}")
            self.navigate_to_url()
            
            # Find the locator for the download link
            download_locator = self._find_download_link_locator()
            
            if not download_locator:
                self.logger.error("Could not find the DOC download link locator")
                self._save_debug_info()
                raise ScraperError("Could not find the DOC forecast download link locator")

            # Dispatch click event on the locator and wait for the download
            self.logger.info(f"Dispatching click event on download link locator and waiting for download...")
            with self.page.expect_download(timeout=90000) as download_info:
                 # Use dispatch_event on the located element
                 download_locator.dispatch_event('click')

            download = download_info.value

            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'doc_download.xlsx'") # Assuming excel
                original_filename = "doc_download.xlsx"

            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.xlsx' # Default extension
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'doc'
            final_filename = f"doc_{timestamp_str}{ext}" 
            final_path = os.path.join(self.download_path, final_filename)
            self.logger.info(f"Original suggested filename: {original_filename}")
            self.logger.info(f"Saving with standardized filename: {final_filename} to {final_path}")
            # --- End modification ---

            # Use the new final_path for saving and verification
            self.logger.info(f"Download complete. File expected at: {final_path}")

            # Verify the file exists (saved by _handle_download or playwright) using the new path
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                self.logger.error(f"Verification failed: File not found or empty at {final_path}")
                # Attempt to save manually as fallback (using original playwright path)
                try:
                    # Save the download to the *new* final_path
                    download.save_as(final_path)
                    self.logger.warning(f"Manually saved file to {final_path}")
                    if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                         raise ScraperError(f"Download failed even after manual save: File missing or empty at {final_path}")
                except Exception as save_err:
                    # Try moving if save_as fails (e.g., if BaseScraper saved it somewhere else)
                    try:
                        fallback_path = download.path() # Playwright's temporary path
                        shutil.move(fallback_path, final_path)
                        self.logger.warning(f"Manually moved file from {fallback_path} to {final_path}")
                        if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                            raise ScraperError(f"Download failed after fallback move: File missing or empty at {final_path}")
                    except Exception as move_err:
                        raise ScraperError(f"Download failed: File missing/empty at {final_path}. Manual save failed: {save_err}. Fallback move failed: {move_err}")

            self.logger.info(f"Download verification successful. File saved at: {final_path}")
            return final_path
            
        except PlaywrightTimeoutError as e:
            handle_scraper_error(e, self.source_name, "Timeout downloading DOC forecast document")
            raise ScraperError(f"Timeout downloading DOC forecast document: {str(e)}")
        except Exception as e:
            # Ensure error is re-raised after handling
            handle_scraper_error(e, self.source_name, "Error downloading DOC forecast document")
            raise ScraperError(f"Failed to download DOC forecast document: {str(e)}")
    
    def scrape(self):
        """
        Run the scraper to download the forecast document.
        
        Returns:
            dict: Result object from scrape_with_structure
        """
        # Use the structured scrape method from the base class - only extract
        return self.scrape_with_structure(
            # Setup is handled within download_forecast_document now
            extract_func=self.download_forecast_document
        )

def run_scraper(force=False):
    """
    Run the Commerce Forecast scraper.
    
    Args:
        force (bool): Whether to force scraping even if recently run
        
    Returns:
        bool: True if scraping was successful
        
    Raises:
        ScraperError: If an error occurs during scraping
        ImportError: If required dependencies are not installed
    """
    source_name = "DOC Forecast"
    local_logger = logger
    scraper = None
    
    try:
        # Check if we should run the scraper using the singleton instance
        # Removed interval check logic
        # if not force and download_tracker.should_download(source_name):
        #     local_logger.info(f"Skipping scrape for {source_name} due to recent download")
        #     return True

        # Create an instance of the scraper
        scraper = DocScraper(debug_mode=False)
        
        # Run the scraper
        local_logger.info(f"Running {source_name} scraper")
        # scrape_with_structure returns a dict, check 'success' key
        result = scraper.scrape() 
        
        # Check the success key in the result dictionary
        if not result or not result.get("success", False):
            # Error should have been logged within scrape_with_structure or download_forecast_document
            # Re-raise a generic error if needed, or rely on logged errors.
            # Error details are in result['error'] if it exists
            error_msg = result.get("error", "Scraper failed without specific error") if result else "Scraper failed without specific error"
            # handle_scraper_error is likely called internally, avoid double logging/handling if possible
            # handle_scraper_error(ScraperError(error_msg), source_name)
            raise ScraperError(error_msg)
        
        # Update the download tracker with the current time
        # Removed: download_tracker.set_last_download_time(source_name)
        # local_logger.info(f"Updated download tracker for {source_name}")
            
        # Update the ScraperStatus table to indicate success (Currently Commented Out)
        # update_scraper_status(source_name, "working", None)
            
        return True
    except ImportError as e:
        error_msg = f"Import error for {source_name}: {str(e)}"
        local_logger.error(error_msg)
        local_logger.error("Playwright module not found? Run 'pip install playwright' and 'playwright install'")
        # handle_scraper_error(e, source_name, "Import error") # Already called? Check logic
        raise # Re-raise import error
    except ScraperError as e:
        # Scraper specific errors (including those from download/navigation)
        # Error should already be logged by handle_scraper_error called deeper
        local_logger.error(f"ScraperError occurred for {source_name}: {str(e)}")
        raise # Re-raise scraper error
    except Exception as e:
        # Catch-all for unexpected errors
        error_msg = f"Unexpected error running {source_name} scraper: {str(e)}"
        handle_scraper_error(e, source_name, f"Unexpected error in run_scraper for {source_name}")
        raise ScraperError(error_msg) from e
    finally:
        if scraper:
            try:
                local_logger.info(f"Cleaning up {source_name} scraper resources")
                scraper.cleanup_browser() # Correct method name
            except Exception as cleanup_error:
                local_logger.error(f"Error during {source_name} scraper cleanup: {str(cleanup_error)}")

if __name__ == "__main__":
    # This block allows the script to be run directly for testing
    try:
        run_scraper(force=True)
        print("DOC Forecast scraper finished successfully (DB operations skipped).")
    except Exception as e:
        print(f"DOC Forecast scraper failed: {e}") 