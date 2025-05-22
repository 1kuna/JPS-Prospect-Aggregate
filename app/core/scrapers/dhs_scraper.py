"""Department of Homeland Security Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
import sys
import shutil
import datetime

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
# import hashlib # No longer needed here
import re
from datetime import datetime

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, DataSource, db
from app.database.crud import bulk_upsert_prospects
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date
from app.config import active_config # Import active_config
from app.utils.scraper_utils import handle_scraper_error

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.dhs_forecast")

class DHSForecastScraper(BaseScraper):
    """Scraper for the DHS Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DHS Forecast scraper."""
        super().__init__(
            source_name="DHS Forecast",
            base_url=active_config.DHS_FORECAST_URL,
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
            # download = download_info.value # This line might not be needed if _handle_download sets the path correctly
            self.logger.info(f"Download triggered for {self.source_name}, should be handled by BaseScraper._handle_download.")

            # Wait a brief moment for the download event to be processed by the callback
            self.page.wait_for_timeout(2000) # 2 seconds, adjust as needed

            if not self._last_download_path or not os.path.exists(self._last_download_path):
                # Attempt to get the path from the download object if _last_download_path wasn't set
                try:
                    download = download_info.value # Get download object if needed for path
                    temp_playwright_path = download.path()
                    self.logger.warning(f"BaseScraper._last_download_path not set or invalid. Playwright temp path: {temp_playwright_path}")
                except Exception as path_err:
                    self.logger.error(f"Could not retrieve Playwright download path: {path_err}")
                
                raise ScraperError("Download failed: File not found or path not set by BaseScraper._handle_download.")

            self.logger.info(f"Download process completed. File saved at: {self._last_download_path}")
            return self._last_download_path
            
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout error during DHS forecast download initiation: {e}")
            handle_scraper_error(e, self.source_name, "Timeout during download process initiation")
            raise ScraperError(f"Timeout during DHS forecast download process initiation: {str(e)}")
        except Exception as e:
            self.logger.error(f"General error during DHS forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Error downloading DHS forecast document")
            # Ensure the original exception type isn't lost if it's not a ScraperError already
            if not isinstance(e, ScraperError):
                 raise ScraperError(f"Failed to download DHS forecast document: {str(e)}") from e
            else:
                 raise # Re-raise the original ScraperError
    
    def process_func(self, file_path: str):
        """
        Process the downloaded Excel file, transform data to Prospect objects, 
        and insert into the database using logic adapted from dhs_transform.py.
        """
        self.logger.info(f"Processing downloaded Excel file: {file_path}")
        try:
            df = pd.read_excel(file_path, sheet_name=0, header=0) 
            self.logger.info(f"Loaded {len(df)} rows from {file_path}")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return 0 # Return 0 as no records processed

            # --- Scraper-specific pre-processing ---
            # Initial rename to standardized intermediate names, some of which might be final
            # Prospect field names.
            initial_rename_map = {
                'APFS Number': 'native_id', # Final Prospect field
                'NAICS': 'naics',           # Final Prospect field
                'Component': 'agency',      # Final Prospect field
                'Title': 'title',           # Final Prospect field
                'Contract Type': 'contract_type', # Final Prospect field
                'Contract Vehicle': 'contract_vehicle_raw', # Will go to extra
                'Dollar Range': 'estimated_value_raw',      # Needs parsing
                'Small Business Set-Aside': 'set_aside',     # Final Prospect field
                'Small Business Program': 'small_business_program_raw', # Will go to extra
                'Contract Status': 'contract_status_raw',        # Will go to extra
                'Place of Performance City': 'place_city',    # Final Prospect field
                'Place of Performance State': 'place_state',   # Final Prospect field
                'Description': 'description', # Final Prospect field
                'Estimated Solicitation Release': 'release_date_raw', # Needs parsing
                'Award Quarter': 'award_date_raw'           # Needs parsing
            }
            df.rename(columns=initial_rename_map, inplace=True)

            # Date Parsing (Solicitation/Release Date)
            df['release_date'] = pd.to_datetime(df.get('release_date_raw'), errors='coerce').dt.date if 'release_date_raw' in df.columns else None
            
            # Award Date and Fiscal Year Parsing
            if 'award_date_raw' in df.columns:
                parsed_award_info = df['award_date_raw'].apply(fiscal_quarter_to_date)
                df['award_date'] = parsed_award_info.apply(lambda x: x[0].date() if pd.notna(x[0]) else None)
                df['award_fiscal_year'] = parsed_award_info.apply(lambda x: x[1])
            else: 
                df['award_date'] = None
                df['award_fiscal_year'] = pd.NA
            if 'award_fiscal_year' in df.columns:
                df['award_fiscal_year'] = df['award_fiscal_year'].astype('Int64')

            # Estimated Value Parsing
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            else:
                df['estimated_value'] = pd.NA 
                df['est_value_unit'] = pd.NA

            # Initialize Place Country (DHS transform assumes USA)
            df['place_country'] = 'USA'
            
            # Columns that were raw and have been parsed can be dropped if desired,
            # or let _process_and_load_data handle them via 'extra' if they are not in final rename map.
            # For clarity, we might drop them here if they are truly intermediate.
            # df.drop(columns=['release_date_raw', 'award_date_raw', 'estimated_value_raw'], errors='ignore', inplace=True)
            # However, if we want them in 'extra', we should keep them and ensure they are not in the final_rename_map's values.

            # --- Define mappings for _process_and_load_data ---
            # These are the columns that are now ready to be mapped to final Prospect model fields
            # or are already named as such.
            final_column_rename_map = {
                # Source (already renamed or parsed) : Prospect Model Field
                'native_id': 'native_id',
                'naics': 'naics',
                'agency': 'agency',
                'title': 'title',
                'description': 'description',
                'contract_type': 'contract_type',
                'release_date': 'release_date', # Parsed from release_date_raw
                'award_date': 'award_date',       # Parsed from award_date_raw
                'award_fiscal_year': 'award_fiscal_year', # Parsed from award_date_raw
                'estimated_value': 'estimated_value', # Parsed from estimated_value_raw
                'est_value_unit': 'est_value_unit', # Parsed from estimated_value_raw
                'set_aside': 'set_aside',
                'place_city': 'place_city',
                'place_state': 'place_state',
                'place_country': 'place_country',
                # Raw fields that will go to 'extra' if not explicitly mapped to a model field
                'contract_vehicle_raw': 'contract_vehicle_raw', 
                'small_business_program_raw': 'small_business_program_raw',
                'contract_status_raw': 'contract_status_raw',
                # Also include original raw fields if they are needed in 'extra' and not dropped
                'release_date_raw': 'release_date_raw', 
                'award_date_raw': 'award_date_raw', 
                'estimated_value_raw': 'estimated_value_raw'
            }
            
            # Filter map for only columns present in df to avoid errors during rename
            final_column_rename_map_existing = {k: v for k, v in final_column_rename_map.items() if k in df.columns}

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            fields_for_id_hash = ['naics', 'title', 'description'] # Use final Prospect field names

            return self._process_and_load_data(df, final_column_rename_map_existing, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"Excel file not found at {file_path}")
            raise ScraperError(f"Processing failed: Excel file not found at {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty Excel file at {file_path}")
            return # Not a ScraperError, just empty source.
        except KeyError as e:
            self.logger.error(f"Missing expected column during Excel processing: {e}. Check mappings or file format.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing file {file_path}: {str(e)}")

    def scrape(self):
        """
        Run the scraper to download the forecast document.
        Returns a result dict from scrape_with_structure.
        """
        return self.scrape_with_structure(
            extract_func=self.download_forecast_document,
            process_func=self.process_func
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
