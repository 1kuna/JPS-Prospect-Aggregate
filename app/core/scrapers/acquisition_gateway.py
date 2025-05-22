"""Acquisition Gateway scraper."""

# Standard library imports
import os
import traceback # Keep one traceback

# Third-party imports
import pandas as pd # Add pandas
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from playwright_stealth import stealth_sync

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, DataSource, db # Removed ScraperStatus
from app.config import active_config # Import active_config
from app.exceptions import ScraperError
# from app.utils.file_utils import ensure_directory # Removed ensure_directory
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
            
            _ = download_info.value # Access the download object

            # Wait a brief moment for the download event to be processed by the callback
            self.page.wait_for_timeout(2000) # Adjust as needed

            if not self._last_download_path or not os.path.exists(self._last_download_path):
                self.logger.error(f"BaseScraper._last_download_path not set or invalid. Value: {self._last_download_path}")
                # Fallback or detailed error logging
                try:
                    download_obj_for_debug = download_info.value 
                    temp_playwright_path = download_obj_for_debug.path()
                    self.logger.warning(f"Playwright temp download path for debugging: {temp_playwright_path}")
                except Exception as path_err:
                    self.logger.error(f"Could not retrieve Playwright temp download path for debugging: {path_err}")
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