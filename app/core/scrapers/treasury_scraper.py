"""Treasury Forecast scraper."""

# Standard library imports
import os
import sys
import time
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
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
from app.core.base_scraper import BaseScraper
from app.database.download_tracker import download_tracker
from app.config import LOGS_DIR, DOWNLOADS_DIR, TREASURY_FORECAST_URL, PAGE_NAVIGATION_TIMEOUT # Assuming TREASURY_FORECAST_URL exists in config
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory, find_files
from app.utils.logger import logger
from app.utils.scraper_utils import (
    check_url_accessibility,
    download_file,
    save_permanent_copy,
    handle_scraper_error
)

# Set up logging
logger = logger.bind(name="scraper.treasury_forecast")

# Placeholder for URL check function if needed, similar to acquisition_gateway
# def check_url_accessibility(url=None): ...

class TreasuryScraper(BaseScraper):
    """Scraper for the Treasury Forecast site."""

    def __init__(self, debug_mode=False):
        """Initialize the Treasury scraper."""
        super().__init__(
            source_name="Treasury Forecast",
            base_url=TREASURY_FORECAST_URL, # Use config URL
            debug_mode=debug_mode
        )
        # Ensure the specific download directory for this scraper exists
        ensure_directory(self.download_path)

    def navigate_to_forecast_page(self):
        """Navigate to the forecast page."""
        self.logger.info(f"Navigating to {self.base_url}")
        return self.navigate_to_url()

    def download_opportunity_data(self):
        """
        Download the Opportunity Data file from the Treasury Forecast site.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        try:
            # Wait for the page to load completely (changed from networkidle to load)
            self.logger.info("Waiting for page 'load' state...")
            self.page.wait_for_load_state('load', timeout=90000)
            self.logger.info("Page loaded. Waiting for download button.")

            # Locate the download button using XPath
            download_button_xpath = "//lightning-button/button[contains(text(), 'Download Opportunity Data')]"
            download_button = self.page.locator(download_button_xpath)

            # Wait for the button to be visible
            download_button.wait_for(state='visible', timeout=60000)
            self.logger.info("Download button found and visible.")

            self.logger.info("Clicking 'Download Opportunity Data' and waiting for download...")
            with self.page.expect_download(timeout=120000) as download_info: # Increased download timeout
                # Sometimes clicks need retries or alternative methods if obscured
                try:
                    download_button.click(timeout=15000)
                except PlaywrightTimeoutError:
                    self.logger.warning("Initial click timed out, trying JavaScript click.")
                    self.page.evaluate(f"document.evaluate('{download_button_xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click();")
                except Exception as click_err:
                    self.logger.error(f"Error during button click: {click_err}")
                    raise

            download = download_info.value
            # The file is saved by the _handle_download callback in BaseScraper
            final_path = os.path.join(self.download_path, download.suggested_filename)
            self.logger.info(f"Download triggered. File expected at: {final_path}")

            # Wait a moment for the file system to register the download completely
            time.sleep(5)

            # Verify the file exists and is not empty
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                self.logger.error(f"Verification failed: File not found or empty at {final_path}")
                # Attempt to save manually as fallback
                try:
                    fallback_path = download.path()
                    if fallback_path and os.path.exists(fallback_path):
                        shutil.move(fallback_path, final_path)
                        self.logger.warning(f"Manually moved file from {fallback_path} to {final_path}")
                        if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                             raise ScraperError(f"Download failed even after fallback move: File missing or empty at {final_path}")
                    else:
                        raise ScraperError(f"Download failed: File missing/empty at {final_path} and Playwright download path unavailable.")
                except Exception as move_err:
                    raise ScraperError(f"Download failed: File missing/empty at {final_path} and fallback move failed: {move_err}")

            self.logger.info(f"Download verification successful. File path: {final_path}")
            return final_path

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout error during download process: {str(e)}")
            # Capture screenshot for debugging timeouts
            screenshot_path = os.path.join(LOGS_DIR, f"treasury_timeout_error_{int(time.time())}.png")
            try:
                self.page.screenshot(path=screenshot_path, full_page=True)
                self.logger.info(f"Screenshot saved to {screenshot_path}")
            except Exception as ss_err:
                self.logger.error(f"Failed to save screenshot: {ss_err}")
            handle_scraper_error(e, self.source_name, "Timeout error during download")
            raise ScraperError(f"Timeout error during download: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error downloading data: {str(e)}")
            handle_scraper_error(e, self.source_name, "Error downloading opportunity data")
            raise ScraperError(f"Error downloading opportunity data: {str(e)}")

    def scrape(self):
        """
        Run the scraper to navigate and download the file.

        Returns:
            str: Path to the downloaded file if successful, raises ScraperError otherwise.
        """
        self.logger.info(f"Starting scrape for {self.source_name}")
        try:
            self.navigate_to_forecast_page()
            downloaded_file_path = self.download_opportunity_data()

            if not downloaded_file_path:
                 raise ScraperError("Download function did not return a file path.")

            # Record successful download
            download_tracker.set_last_download_time(self.source_name)
            self.logger.info(f"Successfully downloaded file: {downloaded_file_path}")

            # Optionally save a permanent copy - adapt path as needed
            # permanent_path = save_permanent_copy(downloaded_file_path, self.source_name)
            # self.logger.info(f"Permanent copy saved to {permanent_path}")

            return downloaded_file_path # Return path for potential further processing

        except ScraperError as e:
            self.logger.error(f"ScraperError occurred: {e}")
            # Error already handled and logged, re-raise to signal failure
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during the scrape process: {str(e)}", exc_info=True)
            handle_scraper_error(e, self.source_name, "Unexpected error during scraping")
            raise ScraperError(f"Unexpected error during scrape: {str(e)}")
        finally:
            self.logger.info(f"Finished scrape attempt for {self.source_name}")
            # Cleanup handled by the context manager in run_scraper or main script

# Placeholder for check_last_download function if needed
# def check_last_download(): ...

def run_scraper(force=False):
    """
    Run the Treasury Forecast scraper.

    Args:
        force (bool): Whether to force the scraper to run even if it ran recently.

    Returns:
        str: Path to the downloaded file if successful, None otherwise.

    Raises:
        ScraperError: If an error occurs during scraping.
    """
    local_logger = logger
    scraper = None  # Initialize scraper to None
    scraper_success = False
    downloaded_path = None
    source_name = "Treasury Forecast" # Define default source name for logging - updated

    try:
        # Check if we should run based on last download time
        scrape_interval_hours = 24 # Example interval
        # Use the default source_name here as scraper instance doesn't exist yet
        if not force and download_tracker.should_download(source_name, scrape_interval_hours):
             local_logger.info(f"Skipping {source_name} scrape due to recent download.")
             # update_scraper_status(source_name, "skipped", "Ran recently") # Optional: Update status
             return None # Indicate skipped, not failed

        # Create an instance of the scraper
        scraper = TreasuryScraper(debug_mode=False)
        source_name = scraper.source_name # Update source_name from instance

        # Setup the browser before using the page object
        scraper.setup_browser()

        # Check URL accessibility, bypassing SSL verification for this specific site
        if not check_url_accessibility(TREASURY_FORECAST_URL, verify_ssl=False):
            error_msg = f"URL {TREASURY_FORECAST_URL} is not accessible"
            handle_scraper_error(ScraperError(error_msg), source_name)
            raise ScraperError(error_msg)

        local_logger.info(f"Running {source_name} scraper")
        downloaded_path = scraper.scrape() # scrape now returns the path or raises error

        if downloaded_path:
            local_logger.info(f"Scraping successful for {source_name}. File at: {downloaded_path}")
            # update_scraper_status(source_name, "working", None) # Update status to working
            scraper_success = True
        else:
            # This case should ideally be covered by exceptions in scrape()
            local_logger.error(f"{source_name} scrape completed but returned no path.")
            handle_scraper_error(ScraperError("Scraper returned no path"), source_name, "Scraper completed without file path")
            # update_scraper_status(source_name, "failed", "Scraper returned no path")

        return downloaded_path if scraper_success else None

    except ScraperError as e:
        # Use source_name which is set either by default or from scraper instance
        local_logger.error(f"ScraperError in run_scraper for {source_name}: {e}")
        # update_scraper_status(source_name, "failed", str(e)) # Update status to failed
        raise # Re-raise the specific scraper error
    except Exception as e:
        # Use source_name which is set either by default or from scraper instance
        error_msg = f"Unexpected error running {source_name} scraper: {str(e)}"
        local_logger.error(error_msg, exc_info=True)
        handle_scraper_error(e, source_name, "Unexpected error in run_scraper")
        # update_scraper_status(source_name, "failed", error_msg)
        raise ScraperError(error_msg) from e # Wrap in ScraperError
    finally:
        # Ensure cleanup happens even if errors occur
        if scraper:
            try:
                local_logger.info(f"Cleaning up scraper resources for {source_name}")
                scraper.cleanup_browser()
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup for {source_name}: {str(cleanup_error)}", exc_info=True)

if __name__ == "__main__":
    print("Running Treasury scraper directly...")
    try:
        # Example of running with force flag, adjust as needed
        result_path = run_scraper(force=True)
        if result_path:
            print(f"Scraper finished successfully. Downloaded file: {result_path}")
        else:
            print("Scraper run did not result in a downloaded file (skipped or failed). Check logs.")
    except ScraperError as e:
        print(f"Scraper failed with error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc() 