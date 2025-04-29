"""Department Of State Opportunity Forecast scraper."""

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
from app.database.download_tracker import download_tracker
from app.exceptions import ScraperError
from app.utils.logger import logger
# from app.utils.db_utils import update_scraper_status # Keep for commented out code
from app.config import DOS_FORECAST_URL, DOWNLOADS_DIR # Import DOWNLOADS_DIR
from app.utils.scraper_utils import handle_scraper_error

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.dos_forecast")

class DOSForecastScraper(BaseScraper):
    """Scraper for the DOS Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DOS Forecast scraper."""
        super().__init__(
            source_name="DOS Forecast", # Updated source name
            base_url=DOS_FORECAST_URL, # Updated URL config variable
            debug_mode=debug_mode
        )
    
    def download_forecast_document(self):
        """
        Download the forecast document directly from the known URL for the DOS website.
        Bypasses clicking elements on the main page.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Attempting to download DOS forecast document directly via URL")
        
        # Known direct URL to the file
        # Ideally, this might be discoverable dynamically, but using the known one for now
        file_url = "https://www.state.gov/wp-content/uploads/2025/02/FY25-Procurement-Forecast-2.xlsx"
        # Extract filename from URL or define a standard one
        try:
            suggested_filename = os.path.basename(file_url)
        except Exception:
            suggested_filename = f"dos_forecast_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Use the scraper's specific download path
        target_download_dir = self.download_path 
        final_path = os.path.join(target_download_dir, suggested_filename)
        
        # Ensure the target directory exists
        os.makedirs(target_download_dir, exist_ok=True)
        self.logger.info(f"Ensured download directory exists: {target_download_dir}")

        try:
            # Optional: Navigate to the base page first if needed for session/cookies
            # self.logger.info(f"Navigating to base URL {self.base_url} first (optional step)")
            # self.navigate_to_url() 
            # self.logger.info("Base page navigation complete.")

            self.logger.info(f"Attempting direct download from: {file_url}")
            # Use Playwright's request context to download
            api_request_context = self.playwright.request.new_context()
            
            # Define headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*' 
            }

            response = api_request_context.get(file_url, headers=headers)

            if not response.ok:
                self.logger.error(f"Direct download request failed with status {response.status}: {response.status_text}")
                # Attempt to read response body for clues if available
                try:
                    body_preview = response.text(timeout=1000)[:500] # Get first 500 chars
                    self.logger.warning(f"Response body preview (might be HTML error page): {body_preview}")
                except Exception:
                    self.logger.warning("Could not read response body preview.")
                api_request_context.dispose() # Dispose context on failure
                raise ScraperError(f"Failed to download file directly. Status: {response.status}")
            
            # Check Content-Type before saving
            content_type = response.headers.get('content-type', '').lower()
            expected_excel_types = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel', 'application/octet-stream']
            self.logger.info(f"Response Content-Type: {content_type}")

            if not any(expected in content_type for expected in expected_excel_types):
                self.logger.error(f"Downloaded file has unexpected Content-Type: {content_type}. Expected an Excel type. Saving as .html for inspection.")
                # Log response body for debugging
                try:
                    body_content = response.text(timeout=5000) 
                    self.logger.debug(f"Full response body (unexpected content):\n{body_content[:1000]}...") # Log first 1000 chars
                    # Optionally save the HTML for inspection
                    html_path = final_path.replace('.xlsx', '.html')
                    with open(html_path, 'w', encoding='utf-8') as f_html:
                         f_html.write(body_content)
                    self.logger.warning(f"Saved unexpected content as HTML for inspection: {html_path}")
                except Exception as log_err:
                    self.logger.error(f"Could not log/save full response body on content type mismatch: {log_err}")
                api_request_context.dispose() # Dispose context on failure
                raise ScraperError(f"Downloaded file content type ({content_type}) is not Excel.")

            # Save the response body to the file
            self.logger.info("Content-Type appears valid, saving file...")
            with open(final_path, 'wb') as f:
                f.write(response.body())
            
            self.logger.info(f"Successfully downloaded file content to: {final_path}")

            # Clean up the API request context
            api_request_context.dispose()

            # Verify the file exists and is not empty
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                self.logger.error(f"Verification failed: File not found or empty at {final_path} after direct download")
                raise ScraperError("Download verification failed after direct download: File missing or empty")

            self.logger.info(f"Direct download verification successful. File saved at: {final_path}")
            return final_path

        except PlaywrightTimeoutError as e: # Keep timeout handling just in case network is slow
            self.logger.error(f"Timeout error during direct download: {e}")
            handle_scraper_error(e, self.source_name, "Timeout during direct download process")
            raise ScraperError(f"Timeout during direct download process: {str(e)}")
        except Exception as e:
            # Ensure context is disposed even on error if it exists
            if 'api_request_context' in locals() and api_request_context:
                 try:
                      api_request_context.dispose()
                 except Exception as dispose_err:
                      self.logger.error(f"Error disposing API request context during exception handling: {dispose_err}")
            
            self.logger.error(f"General error during direct download: {e}")
            handle_scraper_error(e, self.source_name, "Error during direct download")
            if not isinstance(e, ScraperError):
                 raise ScraperError(f"Failed to download DOS forecast document directly: {str(e)}") from e
            else:
                 raise
    
    def scrape(self):
        """
        Run the scraper to download the forecast document.
        Returns a result dict from scrape_with_structure.
        """
        # Modify scrape_with_structure if it assumes page interaction, or call download directly
        # For simplicity, let's assume scrape_with_structure handles setup/cleanup okay
        # and we just pass the direct download function.
        return self.scrape_with_structure(
            extract_func=self.download_forecast_document
        )

def run_scraper(force=False):
    """Run the DOS Forecast scraper."""
    source_name = "DOS Forecast"
    local_logger = logger
    scraper = None
    
    try:
        if not force and download_tracker.should_download(source_name): 
            local_logger.info(f"Skipping scrape for {source_name} due to recent download")
            return {"success": True, "message": "Skipped due to recent download"}
        
        scraper = DOSForecastScraper(debug_mode=False)
        local_logger.info(f"Running {source_name} scraper")
        result = scraper.scrape() 
        
        if not result or not result.get("success", False):
            error_msg = result.get("error", f"{source_name} scraper failed without specific error") if result else f"{source_name} scraper failed without specific error"
            # Log specific note if site might be down
            if "site might be down" in error_msg or "forbidden" in error_msg:
                 local_logger.warning(f"{source_name} scraper failed, potentially due to site technical difficulties.")
            raise ScraperError(error_msg)
        
        download_tracker.set_last_download_time(source_name)
        local_logger.info(f"Updated download tracker for {source_name}")
        return {"success": True, "file_path": result.get("file_path"), "message": f"{source_name} scraped successfully"}
    
    except ImportError as e:
        error_msg = f"Import error for {source_name}: {str(e)}"
        local_logger.error(error_msg)
        handle_scraper_error(e, source_name, "Import error")
        raise ScraperError(error_msg) from e
    except ScraperError as e:
        local_logger.error(f"ScraperError occurred for {source_name}: {str(e)}")
        # Add warning about potential site issues
        if "site might be down" in str(e) or "forbidden" in str(e):
            local_logger.warning(f"{source_name} failed. The site may be experiencing technical difficulties.")
        raise
    except Exception as e:
        error_msg = f"Unexpected error running {source_name} scraper: {str(e)}"
        local_logger.error(error_msg)
        local_logger.warning(f"The site ({DOS_FORECAST_URL}) may be experiencing technical difficulties.")
        handle_scraper_error(e, source_name, f"Unexpected error in run_scraper for {source_name} (site might be down)")
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
            print(f"DOS Forecast scraper finished successfully. File at: {result.get('file_path', 'N/A')}")
        else:
             error_msg = result.get("error", "Unknown error") if result else "Unknown error"
             print(f"DOS Forecast scraper failed: {error_msg}. Check logs for details.")
             if "site might be down" in error_msg or "forbidden" in error_msg:
                 print("Note: The target site may be experiencing technical difficulties.")
             # sys.exit(1) 
    except Exception as e:
        print(f"DOS Forecast scraper failed: {e}")
        if "site might be down" in str(e) or "forbidden" in str(e):
            print("Note: The target site may be experiencing technical difficulties.")
        traceback.print_exc()
        # sys.exit(1)