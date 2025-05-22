"""Acquisition Gateway scraper."""

# Standard library imports
import os
import sys
import time
import datetime
import traceback
import shutil

# Third-party imports
import requests
import pandas as pd # Add pandas
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from playwright_stealth import stealth_sync
import traceback # Add traceback

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, ScraperStatus, DataSource, db
from app.config import active_config # Import active_config
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory
from app.utils.logger import logger
from app.utils.scraper_utils import handle_scraper_error
from app.database.crud import bulk_upsert_prospects # Add bulk_upsert_prospects
# import hashlib # No longer needed here

# Set up logging
logger = logger.bind(name="scraper.acquisition_gateway")

# Removed local check_url_accessibility function. Use self.check_url_accessibility() from BaseScraper.

class AcquisitionGatewayScraper(BaseScraper):
    """Scraper for the Acquisition Gateway site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the Acquisition Gateway scraper."""
        super().__init__(
            source_name="Acquisition Gateway",
            base_url=active_config.ACQUISITION_GATEWAY_URL,
            debug_mode=debug_mode,
            use_stealth=True # Enable stealth mode for this scraper
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
            # Wait for the page to load using 'load' state
            self.logger.info("Waiting for page to load ('load')...")
            self.page.wait_for_load_state('load', timeout=90000) # Changed to 'load', kept long timeout
            
            # Explicit wait after load
            self.logger.info("Waiting 5 seconds after load for page to settle...") # Reduced wait back to 5s
            self.page.wait_for_timeout(5000) # Reduced wait back to 5s
            self.logger.info("Wait finished. Locating Export button.")
            
            # --- Debug Screenshot After Wait REMOVED ---
            # debug_timestamp_after_wait = ...
            # screenshot_path_after_wait = ...
            # try:
            # ...
            # except ...
            # --- End Debug Screenshot After Wait REMOVED ---
            
            # Find export button using ID
            export_button_selector = 'button#export-0' 
            export_button = self.page.locator(export_button_selector)
            
            # Wait for the button to be VISIBLE in the DOM
            try:
                export_button.wait_for(state='visible', timeout=60000) # Changed state back to 'visible'
                self.logger.info("Export button is visible.")
            except PlaywrightTimeoutError as wait_error:
                self.logger.error(f"Timeout waiting for export button ({export_button_selector}) to be visible.") # Updated log message
                # --- Debug Output REMOVED ---
                # debug_timestamp = ...
                # screenshot_path = ...
                # html_path = ...
                # try:
                # ...
                # except ...
                # --- End Debug Output REMOVED ---
                raise ScraperError(f"Timeout waiting for export button {export_button_selector} to become visible") from wait_error # Updated error message
            
            self.logger.info("Attempting to click Export CSV and waiting for download...")
            
            # Start waiting for the download BEFORE clicking
            with self.page.expect_download(timeout=120000) as download_info: # Increased timeout
                # Try standard click first, then JS click fallback
                try:
                    self.logger.info("Attempting standard click...")
                    export_button.click(timeout=15000) # Shorter timeout for the click itself
                    self.logger.info("Standard click successful.")
                except PlaywrightTimeoutError:
                    self.logger.warning("Standard click timed out or failed, trying JavaScript click.")
                    # Evaluate JS to click the first matching element
                    self.page.evaluate(f"document.querySelector('{export_button_selector}').click();")
                    self.logger.info("JavaScript click executed.")
                except Exception as click_err:
                    self.logger.error(f"Error during button click attempt: {click_err}")
                    raise # Re-raise other click errors
            
            # Download object is available here (download_info.value)
            # The actual saving and path setting is now handled by BaseScraper._handle_download
            self.logger.info(f"Download triggered for {self.source_name}, should be handled by BaseScraper._handle_download.")
            
            # Wait a brief moment for the download event to be processed by the callback
            # This might need adjustment if downloads are very fast or very slow to register
            self.page.wait_for_timeout(2000) # 2 seconds, adjust as needed

            if not self._last_download_path or not os.path.exists(self._last_download_path):
                # Attempt to get the path from the download object if _last_download_path wasn't set
                # This is a fallback, ideally _handle_download should reliably set it.
                try:
                    download = download_info.value
                    temp_playwright_path = download.path()
                    self.logger.warning(f"BaseScraper._last_download_path not set or invalid. Playwright temp path: {temp_playwright_path}")
                    # If we have a path from Playwright, and _handle_download failed to save it to the final location,
                    # this indicates an issue in _handle_download. We should not try to re-implement saving here.
                    # For now, we will raise an error if _last_download_path is not correctly set.
                except Exception as path_err:
                    self.logger.error(f"Could not retrieve Playwright download path: {path_err}")
                
                raise ScraperError("Download failed: File not found or path not set by BaseScraper._handle_download.")

            self.logger.info(f"Download process completed. File saved at: {self._last_download_path}")
            return self._last_download_path

        except PlaywrightTimeoutError as e:
            handle_scraper_error(e, self.source_name, "Timeout error during download initiation")
            raise ScraperError(f"Timeout error during download initiation: {str(e)}")
        except Exception as e:
            handle_scraper_error(e, self.source_name, "Error downloading CSV")
            raise ScraperError(f"Error downloading CSV: {str(e)}")
    
    def process_func(self, file_path: str):
        """
        Process the downloaded CSV file, transform data to Prospect objects, 
        and insert into the database using logic adapted from acqg_transform.py.
        """
        self.logger.info(f"Processing downloaded CSV file: {file_path}")
        try:
            df = pd.read_csv(file_path, header=0, on_bad_lines='skip')
            self.logger.info(f"Loaded {len(df)} rows from {file_path}")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return 0 # Return 0 as no records processed

            # Scraper-specific parsing (before common processing)
            # Fallback for description (already handled by rename_map if 'Body' exists)
            if 'Body' not in df.columns and 'Summary' in df.columns:
                 df.rename(columns={'Summary': 'Body'}, inplace=True) # Rename Summary to Body so map picks it up

            # Date Parsing
            if 'Estimated Solicitation Date' in df.columns:
                df['Estimated Solicitation Date'] = pd.to_datetime(df['Estimated Solicitation Date'], errors='coerce').dt.date
            
            if 'Ultimate Completion Date' in df.columns: # This is for 'award_date_raw'
                df['Ultimate Completion Date'] = pd.to_datetime(df['Ultimate Completion Date'], errors='coerce').dt.date

            # Fiscal Year Parsing/Extraction - simplified as common logic will handle this if column exists
            if 'Estimated Award FY' in df.columns:
                df['Estimated Award FY'] = pd.to_numeric(df['Estimated Award FY'], errors='coerce')
                # Fallback for NA fiscal years if award_date (from Ultimate Completion Date) is present
                if 'Ultimate Completion Date' in df.columns:
                    fallback_mask = df['Estimated Award FY'].isna() & df['Ultimate Completion Date'].notna()
                    df.loc[fallback_mask, 'Estimated Award FY'] = df.loc[fallback_mask, 'Ultimate Completion Date'].dt.year
            elif 'Ultimate Completion Date' in df.columns and df['Ultimate Completion Date'].notna().any():
                self.logger.warning("'Estimated Award FY' not in source, extracting year from 'Ultimate Completion Date' as fallback for award_fiscal_year.")
                df['Estimated Award FY'] = df['Ultimate Completion Date'].dt.year # Create the column
            
            # Ensure 'Estimated Award FY' is Int64 if it exists
            if 'Estimated Award FY' in df.columns:
                 df['Estimated Award FY'] = df['Estimated Award FY'].astype('Int64')


            # Estimated Value Parsing
            if 'Estimated Contract Value' in df.columns:
                df['Estimated Contract Value'] = pd.to_numeric(df['Estimated Contract Value'], errors='coerce')
            # est_value_unit is None for AcqG, so no specific parsing needed here for it.

            # Define mappings and call the common processing method
            column_rename_map = {
                'Listing ID': 'native_id',
                'Title': 'title',
                'Body': 'description', # Renamed 'Summary' to 'Body' above if 'Body' was missing
                'NAICS Code': 'naics',
                'Estimated Contract Value': 'estimated_value',
                'Estimated Solicitation Date': 'release_date',
                'Ultimate Completion Date': 'award_date', # Directly map to award_date after parsing
                'Estimated Award FY': 'award_fiscal_year',
                'Organization': 'agency',
                'Place of Performance City': 'place_city',
                'Place of Performance State': 'place_state',
                'Place of Performance Country': 'place_country',
                'Contract Type': 'contract_type',
                'Set Aside Type': 'set_aside'
            }
            
            # Ensure all mapped source columns exist in df before passing to _process_and_load_data
            # This is implicitly handled by how rename works (only existing columns are renamed)
            # and how _process_and_load_data handles missing fields later.

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            fields_for_id_hash = ['naics', 'title', 'description'] # After renaming

            return self._process_and_load_data(df, column_rename_map, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"CSV file not found at {file_path}")
            raise ScraperError(f"Processing failed: CSV file not found at {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty CSV file at {file_path}")
            # No ScraperError here, just log and return, as it's not a processing failure but empty source data.
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during CSV processing: {e}. This might indicate a change in the CSV format or an issue with mappings.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing file {file_path}: {str(e)}")
    
    def scrape(self):
        """
        Run the scraper to download the file.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        # Simplified call: only setup and extract
        return self.scrape_with_structure(
            setup_func=self.navigate_to_forecast_page,
            extract_func=self.download_csv_file,
            process_func=self.process_func # Add process_func
        )

# Removed check_last_download function as it's obsolete.

def run_scraper():
    """
    Run the Acquisition Gateway scraper.
    
    Args:
        force (bool): Whether to force scraping (currently unused as interval logic is removed).
        
    Returns:
        str: Path to the downloaded file if successful, otherwise raises an exception.
    """
    local_logger = logger.bind(name="scraper.acquisition_gateway.run_scraper")
    scraper_instance = None
    source_name = "Acquisition Gateway" # Default, instance will have the true one

    try:
        # Interval check logic (if any to be restored) would go here

        scraper_instance = AcquisitionGatewayScraper(debug_mode=False) # Or get debug_mode from arg
        source_name = scraper_instance.source_name # Get source_name from instance

        # URL accessibility check (now uses base method)
        # Note: BaseScraper's check_url_accessibility uses requests.head, which is less likely to be blocked
        # than a full browser navigation, so it's a good preliminary check.
        if not scraper_instance.check_url_accessibility(): 
            error_msg = f"URL {scraper_instance.base_url} is not accessible via HEAD request."
            # Log this specific error before raising a more generic ScraperError
            local_logger.error(error_msg)
            raise ScraperError(error_msg)

        local_logger.info(f"Running {source_name} scraper via instance method")
        
        # The scrape() method (which calls scrape_with_structure) handles:
        # 1. setup_browser (now stealth-aware)
        # 2. navigate_to_forecast_page (setup_func)
        # 3. download_csv_file (extract_func)
        # 4. process_func (if file downloaded)
        # 5. cleanup_browser
        result = scraper_instance.scrape() 

        if result and result.get("success"):
            # The 'data' key from scrape_with_structure holds the return of extract_func (download_csv_file)
            # which is the path to the downloaded file.
            downloaded_file_path = result.get("data") 
            if downloaded_file_path:
                local_logger.info(f"Scraping successful for {source_name}. File at: {downloaded_file_path}")
                # update_scraper_status logic (if any to be restored, e.g., using a ScraperService)
                return downloaded_file_path
            else:
                # This case should ideally be caught earlier if download_csv_file returns None or raises error
                error_msg = f"{source_name} scrape reported success, but no downloaded file path was returned."
                local_logger.error(error_msg)
                raise ScraperError(error_msg)
        else:
            error_msg = result.get("error", "Scraping failed without specific error message.") if result else "Scraping failed (no result)."
            # Log the specific error message from the result if available
            local_logger.error(f"{source_name} scraping failed: {error_msg}")
            raise ScraperError(error_msg)

    except ScraperError as e:
        # Log specific scraper errors (already logged deeper if coming from scraper methods)
        local_logger.error(f"ScraperError in {source_name} run_scraper: {e}")
        # update_scraper_status logic (if any to be restored)
        raise # Re-raise to be caught by main caller or script exit
    except Exception as e:
        # Catch-all for unexpected errors during run_scraper setup or result handling
        error_msg = f"Unexpected error running {source_name} scraper: {str(e)}"
        local_logger.error(error_msg, exc_info=True) # Log with traceback
        # update_scraper_status logic (if any to be restored)
        raise ScraperError(error_msg) from e # Wrap in ScraperError and chain
    # No finally block for scraper_instance.cleanup_browser() needed here, 
    # as scrape() method (via scrape_with_structure) handles its own cleanup.

if __name__ == "__main__":
    # This block allows the script to be run directly for testing
    print("Running Acquisition Gateway scraper directly...")
    try:
        # Example of running with force flag (though 'force' is not used in current run_scraper)
        result_path = run_scraper(force=True) 
        if result_path:
            print(f"Scraper finished successfully. Downloaded file: {result_path}")
        else:
            # This path should ideally not be reached if errors are raised correctly
            print("Scraper run did not result in a downloaded file (or an error was expected but not raised). Check logs.")
    except ScraperError as e:
        print(f"Scraper failed with error: {e}")
    except Exception as e:
        # This will catch errors from run_scraper if they weren't ScraperError type (should be wrapped)
        print(f"An unexpected error occurred at the main execution level: {e}")
        import traceback
        traceback.print_exc()