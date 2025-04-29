"""Social Security Administration Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
import sys
import shutil

# --- Start temporary path adjustment for direct execution ---
# Calculate the path to the project root directory (JPS-Prospect-Aggregate)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
# Add the project root to the Python path if it's not already there
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# --- End temporary path adjustment ---

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Proposal
from app.database.download_tracker import DownloadTracker
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.utils.db_utils import update_scraper_status
from app.config import SSA_CONTRACT_FORECAST_URL
from app.utils.scraper_utils import (
    check_url_accessibility,
    download_file,
    save_permanent_copy,
    handle_scraper_error
)

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.ssa_contract_forecast")

class SSAContractForecastScraper(BaseScraper):
    """Scraper for the SSA Contract Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the SSA Contract Forecast scraper."""
        super().__init__(
            source_name="SSA Contract Forecast",
            base_url=SSA_CONTRACT_FORECAST_URL,
            debug_mode=debug_mode
        )
    
    def _find_excel_link(self):
        """
        Find the Excel file link on the page.
        
        Returns:
            str: URL of the Excel file, or None if not found
        """
        # Try different selectors to find the Excel link
        selectors = [
            'a[href$=".xlsx"]',
            'a[href$=".xls"]',
            'a:has-text("Excel")',
            'a:has-text("Forecast")'
        ]
        
        self.logger.info("Searching for Excel link...")
        # Prioritize the specific link text observed
        selectors.insert(0, 'a:has-text("FY25 SSA Contract Forecast")') 

        for selector in selectors:
            self.logger.info(f"Trying selector: {selector}")
            links = self.page.query_selector_all(selector)
            if links:
                self.logger.info(f"Found {len(links)} links with selector {selector}")
                for link in links:
                    href = link.get_attribute('href')
                    if href and ('.xls' in href.lower() or 'forecast' in href.lower()):
                        self.logger.info(f"Found Excel link: {href}")
                        return href
        return None
    
    def _save_debug_info(self):
        """Save debug information when Excel link is not found."""
        # Save a screenshot for debugging
        screenshot_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'downloads', 'page_screenshot.png')
        self.page.screenshot(path=screenshot_path)
        self.logger.info(f"Saved screenshot to {screenshot_path}")
        
        # Save page content for debugging
        html_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'downloads', 'page_content.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.page.content())
        self.logger.info(f"Saved page content to {html_path}")
    
    def download_forecast_document(self):
        """
        Download the forecast document from the SSA website.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Downloading forecast document")
        
        try:
            # Navigate to the forecast page
            self.logger.info(f"Navigating to {self.base_url}")
            try:
                # Assuming navigate_to_url sets up self.page correctly
                self.navigate_to_url() 
            except Exception as e:
                self.logger.error(f"Error navigating to forecast page: {str(e)}")
                self.logger.error(traceback.format_exc())
                raise # Re-raise the navigation error
            
            # Find the Excel link
            excel_link_href = self._find_excel_link()
            
            if not excel_link_href:
                self.logger.error("Could not find Excel link on the page")
                self._save_debug_info() # Save debug info if link not found
                raise ScraperError("Could not find Excel download link on the page")
            
            # Click the link and wait for the download
            self.logger.info(f"Clicking link '{excel_link_href}' and waiting for download...")
            # Use the specific link found
            link_selector = f'a[href="{excel_link_href}"]' 
            with self.page.expect_download(timeout=60000) as download_info:
                 self.page.click(link_selector)
            
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
            
            # Removed old download_file and save_permanent_copy logic
            # temp_path = download_file(self.page, f'a[href="{excel_link}"]')
            # return save_permanent_copy(temp_path, self.source_name, 'xlsx')
            
        except PlaywrightTimeoutError as e:
            handle_scraper_error(e, self.source_name, "Timeout downloading forecast document")
            raise ScraperError(f"Timeout downloading forecast document: {str(e)}")
        except Exception as e:
            handle_scraper_error(e, self.source_name, "Error downloading forecast document")
            raise ScraperError(f"Failed to download forecast document: {str(e)}")
    
    def scrape(self):
        """
        Run the scraper to download the forecast document.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        # Use the structured scrape method from the base class - only extract
        return self.scrape_with_structure(
            # No setup_func needed if navigation happens in extract
            extract_func=self.download_forecast_document
            # No process_func needed
        )

def run_scraper(force=False):
    """
    Run the SSA Contract Forecast scraper.
    
    Args:
        force (bool): Whether to force scraping even if recently run
        
    Returns:
        bool: True if scraping was successful
        
    Raises:
        ScraperError: If an error occurs during scraping
        ImportError: If required dependencies are not installed
    """
    local_logger = logger
    scraper = None
    download_tracker = DownloadTracker()
    
    try:
        # Check if we should run the scraper
        if not force and download_tracker.should_download("SSA Contract Forecast"):
            local_logger.info("Skipping scrape due to recent download")
            return True
        
        # Create an instance of the scraper
        scraper = SSAContractForecastScraper(debug_mode=False)
        
        # Run the scraper
        local_logger.info("Running SSA Contract Forecast scraper")
        success = scraper.scrape()
        
        # If scraper.scrape() returns False, it means an error occurred
        if not success:
            error_msg = "Scraper failed without specific error"
            handle_scraper_error(ScraperError(error_msg), "SSA Contract Forecast")
            raise ScraperError(error_msg)
        
        # Update the download tracker with the current time
        download_tracker.set_last_download_time("SSA Contract Forecast")
        local_logger.info("Updated download tracker with current time")
        
        # Update the ScraperStatus table to indicate success
        # --> Temporarily skip this during direct script execution <---
        # update_scraper_status("SSA Contract Forecast", "working", None)
            
        return True
    except ImportError as e:
        error_msg = f"Import error: {str(e)}"
        local_logger.error(error_msg)
        local_logger.error("Playwright module not found. Please install it with 'pip install playwright'")
        local_logger.error("Then run 'playwright install' to install the browsers")
        handle_scraper_error(e, "SSA Contract Forecast", "Import error")
        raise
    except ScraperError as e:
        handle_scraper_error(e, "SSA Contract Forecast")
        raise
    except Exception as e:
        # Ensure error_msg is defined or handled appropriately
        error_msg = f"Error running scraper: {str(e)}"
        handle_scraper_error(e, "SSA Contract Forecast", "Error running scraper")
        raise ScraperError(error_msg)
    finally:
        if scraper:
            try:
                local_logger.info("Cleaning up scraper resources")
                scraper.cleanup_browser() # Correct method name
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup: {str(cleanup_error)}")

if __name__ == "__main__":
    # This block allows the script to be run directly for testing
    try:
        run_scraper(force=True)
        print("Scraper finished successfully (DB operations skipped).")
    except Exception as e:
        print(f"Scraper failed: {e}")