"""Department of Transportation (DOT) Forecast scraper."""

# Standard library imports
import os
import sys
import time
import shutil
import datetime # Added datetime import

# --- Start temporary path adjustment for direct execution ---
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# --- End temporary path adjustment ---

# Third-party imports
import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# Local application imports
from app.core.base_scraper import BaseScraper
from app.config import LOGS_DIR, RAW_DATA_DIR, DOT_FORECAST_URL, PAGE_NAVIGATION_TIMEOUT # Use RAW_DATA_DIR
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory
from app.utils.logger import logger
from app.utils.scraper_utils import (
    check_url_accessibility,
    handle_scraper_error
)

# Set up logging
logger = logger.bind(name="scraper.dot_forecast")

class DotScraper(BaseScraper):
    """Scraper for the DOT Forecast site."""

    def __init__(self, debug_mode=False):
        """Initialize the DOT scraper."""
        super().__init__(
            source_name="DOT Forecast", # Changed source name
            base_url=DOT_FORECAST_URL,
            debug_mode=debug_mode
        )
        ensure_directory(self.download_path)

    def navigate_to_forecast_page(self):
        """Navigate to the forecast page, overriding wait_until state."""
        self.logger.info(f"Navigating to {self.base_url} (using wait_until='load')")
        try:
            if not self.page:
                raise ScraperError("Page object is not initialized. Call setup_browser first.")
            # Override the default wait_until state specifically for this scraper
            response = self.page.goto(self.base_url, timeout=90000, wait_until='load') # Use 90s timeout and 'load' state
            if response and not response.ok:
                 self.logger.warning(f"Navigation to {self.base_url} resulted in status {response.status}. URL: {response.url}")
                 # Potentially raise error here if needed
            return True
        except PlaywrightTimeoutError as e:
            error_msg = f"Timeout navigating to DOT URL: {self.base_url}: {str(e)}"
            self.logger.error(error_msg)
            raise ScraperError(error_msg) from e
        except Exception as e:
            error_msg = f"Error navigating to DOT URL {self.base_url}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise ScraperError(error_msg) from e

    def download_dot_csv(self):
        """
        Download the CSV file from the DOT Forecast site.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        try:
            # Wait for the page to load
            self.logger.info("Waiting for page 'load' state...")
            self.page.wait_for_load_state('load', timeout=90000)
            self.logger.info("Page loaded.")

            # Click the 'Apply' button
            apply_button_selector = "button:has-text('Apply')"
            apply_button = self.page.locator(apply_button_selector)
            apply_button.wait_for(state='visible', timeout=30000)
            self.logger.info("Clicking 'Apply' button...")
            apply_button.click()

            # Explicit wait after clicking Apply
            self.logger.info("Waiting 10 seconds after clicking Apply...")
            time.sleep(10)
            self.logger.info("Wait finished. Proceeding to download.")

            # Locate the 'Download CSV' button/link
            # It might be a link styled as a button
            download_link_selector = "a:has-text('Download CSV')"
            download_link = self.page.locator(download_link_selector)
            download_link.wait_for(state='visible', timeout=60000)
            self.logger.info("'Download CSV' link found.")

            self.logger.info("Clicking 'Download CSV' and waiting for new page and download...")

            # Expect a new page/tab to open and the download to start there
            with self.context.expect_page(timeout=60000) as new_page_info:
                download_link.click() # Click the link that opens the new tab

            new_page = new_page_info.value
            self.logger.info(f"New page opened with URL: {new_page.url}")

            # Wait for the download to start on the new page
            # Increased timeout to handle potential server-side preparation
            try:
                with new_page.expect_download(timeout=120000) as download_info:
                     self.logger.info("Waiting for download to initiate on the new page...")
                     # Sometimes an action on the new page might be needed, but often just waiting is enough
                     # If the download doesn't start, add a small wait or interaction here.
                     # For now, just rely on the expect_download timeout.
                     pass # Placeholder, let expect_download handle the wait

                download = download_info.value
                self.logger.info("Download detected on new page.")
            finally:
                 # Ensure the new page is closed even if download fails
                 if new_page and not new_page.is_closed():
                     self.logger.info("Closing the download initiation page.")
                     new_page.close()

            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'dot_download.csv'")
                original_filename = "dot_download.csv"

            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.csv' # Default extension
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'dot'
            final_filename = f"dot_{timestamp_str}{ext}"
            final_path = os.path.join(self.download_path, final_filename)
            self.logger.info(f"Original suggested filename: {original_filename}")
            self.logger.info(f"Saving with standardized filename: {final_filename} to {final_path}")
            # --- End modification ---

            # The file is saved by the _handle_download callback in BaseScraper or manually below
            self.logger.info(f"Download triggered. File expected at: {final_path}")

            # Wait a moment for the file system (allow _handle_download time)
            time.sleep(5)

            # Verify the file exists and is not empty using the new final_path
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                self.logger.error(f"Verification failed: File not found or empty at {final_path}")
                # Attempt to save manually first
                try:
                    download.save_as(final_path)
                    self.logger.warning(f"Manually saved file to {final_path}")
                    if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                        raise ScraperError(f"Download failed even after manual save: File missing or empty at {final_path}")
                except Exception as save_err:
                     # If save_as failed, try moving from playwright temp path
                    try:
                        fallback_path = download.path()
                        if fallback_path and os.path.exists(fallback_path):
                            shutil.move(fallback_path, final_path)
                            self.logger.warning(f"Manually moved file from {fallback_path} to {final_path}")
                            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                                raise ScraperError(f"Download failed after fallback move: File missing or empty at {final_path}")
                        else:
                            raise ScraperError(f"Download failed: File missing/empty at {final_path}, manual save failed ({save_err}), and Playwright temp path unavailable.")
                    except Exception as move_err:
                        raise ScraperError(f"Download failed: File missing/empty at {final_path}. Manual save failed: {save_err}. Fallback move failed: {move_err}")

            self.logger.info(f"Download verification successful. File path: {final_path}")
            return final_path

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout error during DOT CSV download process: {str(e)}")
            screenshot_path = os.path.join(LOGS_DIR, f"dot_timeout_error_{int(time.time())}.png")
            try:
                if self.page and not self.page.is_closed():
                    self.page.screenshot(path=screenshot_path, full_page=True)
                    self.logger.info(f"Screenshot saved to {screenshot_path}")
                else:
                    self.logger.warning("Could not take screenshot, page was closed or not available.")
            except Exception as ss_err:
                self.logger.error(f"Failed to save screenshot: {ss_err}")
            handle_scraper_error(e, self.source_name, "Timeout error during download")
            raise ScraperError(f"Timeout error during download: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error downloading DOT CSV data: {str(e)}", exc_info=True)
            handle_scraper_error(e, self.source_name, "Error downloading DOT CSV data")
            raise ScraperError(f"Error downloading DOT CSV data: {str(e)}")

    def scrape(self):
        """
        Run the scraper to navigate, apply filter, and download the file.
        """
        self.logger.info(f"Starting scrape for {self.source_name}")
        try:
            self.navigate_to_forecast_page()
            downloaded_file_path = self.download_dot_csv()

            if not downloaded_file_path:
                 raise ScraperError("Download function did not return a file path.")

            self.logger.info(f"Successfully downloaded file: {downloaded_file_path}")
            return downloaded_file_path

        except ScraperError as e:
            self.logger.error(f"ScraperError occurred: {e}")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during the scrape process: {str(e)}", exc_info=True)
            handle_scraper_error(e, self.source_name, "Unexpected error during scraping")
            raise ScraperError(f"Unexpected error during scrape: {str(e)}")
        finally:
            self.logger.info(f"Finished scrape attempt for {self.source_name}")

def run_scraper(force=False):
    """
    Run the DOT Forecast scraper.
    """
    local_logger = logger
    scraper = None
    playwright = None # Add playwright instance variable for cleanup
    scraper_success = False
    downloaded_path = None
    source_name = "DOT Forecast" # Default source name - updated

    try:
        # Initialize scraper instance but don't call base setup_browser yet
        scraper = DotScraper(debug_mode=False)
        source_name = scraper.source_name

        # --- Start Custom Browser Setup for DOT (using Firefox) --- 
        try:
            local_logger.info("Starting custom browser setup for DOT using Firefox...")
            playwright = sync_playwright().start()
            scraper.playwright = playwright # Store playwright instance on scraper for cleanup
            
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0" # Firefox User Agent
            local_logger.info(f"Launching Firefox with User-Agent: {user_agent}")

            # Launch Firefox browser
            scraper.browser = playwright.firefox.launch(
                headless=not scraper.debug_mode
            )
            
            # Create new context with specific user agent and ignoring HTTPS errors
            scraper.context = scraper.browser.new_context(
                user_agent=user_agent,
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True 
            )
            # Create new page
            scraper.page = scraper.context.new_page()
            # Re-attach download handler
            scraper.page.on("download", scraper._handle_download)
             # Re-set default timeout
            scraper.page.set_default_timeout(60000) 
            local_logger.info("Custom Firefox browser setup complete.")

        except Exception as browser_setup_err:
            local_logger.error(f"Failed custom browser setup: {browser_setup_err}", exc_info=True)
            raise ScraperError(f"Failed custom browser setup: {browser_setup_err}") from browser_setup_err
        # --- End Custom Browser Setup --- 

        # Check URL accessibility (start with verify_ssl=True)
        # We might need to adjust this check if it also fails, but try first
        if not check_url_accessibility(DOT_FORECAST_URL, verify_ssl=True):
            error_msg = f"URL {DOT_FORECAST_URL} is not accessible"
            handle_scraper_error(ScraperError(error_msg), source_name)
            raise ScraperError(error_msg)

        local_logger.info(f"Running {source_name} scraper")
        downloaded_path = scraper.scrape() # scrape method uses the page created above

        if downloaded_path:
            local_logger.info(f"Scraping successful for {source_name}. File at: {downloaded_path}")
            scraper_success = True
        else:
            local_logger.error(f"{source_name} scrape completed but returned no path.")
            handle_scraper_error(ScraperError("Scraper returned no path"), source_name, "Scraper completed without file path")

        return downloaded_path if scraper_success else None

    except ScraperError as e:
        local_logger.error(f"ScraperError in run_scraper for {source_name}: {e}")
        raise
    except Exception as e:
        error_msg = f"Unexpected error running {source_name} scraper: {str(e)}"
        local_logger.error(error_msg, exc_info=True)
        handle_scraper_error(e, source_name, "Unexpected error in run_scraper")
        raise ScraperError(error_msg) from e
    finally:
        # Ensure cleanup happens even if errors occur
        if scraper:
            try:
                # Use the cleanup method from BaseScraper which handles context, page, browser, playwright
                local_logger.info(f"Cleaning up scraper resources for {source_name}")
                scraper.cleanup_browser() # This should now close the custom browser/playwright instance
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup for {source_name}: {str(cleanup_error)}", exc_info=True)
        # Fallback cleanup if scraper object exists but playwright wasn't assigned (shouldn't happen)
        elif playwright:
             try:
                  local_logger.warning("Cleaning up Playwright instance directly (fallback)." )
                  playwright.stop()
             except Exception as pw_cleanup_error:
                 local_logger.error(f"Error during fallback playwright cleanup: {pw_cleanup_error}")

if __name__ == "__main__":
    print("Running DOT scraper directly...")
    try:
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