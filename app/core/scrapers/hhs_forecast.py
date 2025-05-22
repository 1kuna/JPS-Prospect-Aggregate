"""Department of Health and Human Services Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
# import sys # Unused
import shutil
import datetime # Used for datetime.datetime

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
import hashlib
# import traceback # Redundant
# import re # Unused
from datetime import datetime # Used for type hinting and direct use
import json

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, DataSource, db
# from app.database.crud import bulk_upsert_prospects # Unused
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.config import active_config # Import active_config
from app.utils.scraper_utils import handle_scraper_error
from app.utils.parsing import parse_value_range

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.hhs_forecast")

class HHSForecastScraper(BaseScraper):
    """Scraper for the HHS Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the HHS Forecast scraper."""
        super().__init__(
            source_name="HHS Forecast",
            base_url=active_config.HHS_FORECAST_URL,
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
    
    def process_func(self, file_path: str):
        """
        Process the downloaded CSV file, transform data to Prospect objects,
        and insert into the database using logic adapted from hhs_transform.py.
        """
        self.logger.info(f"Processing downloaded CSV file: {file_path}")
        try:
            df = pd.read_csv(file_path, header=0, on_bad_lines='skip')
            df.dropna(how='all', inplace=True) # Pre-processing from transform script
            self.logger.info(f"Loaded {len(df)} rows from {file_path} after initial dropna.")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from hhs_transform.normalize_columns_hhs ---
            rename_map = {
                # Raw HHS Name: Prospect Model Field Name (or intermediate)
                'Procurement Number': 'native_id',
                'Operating Division': 'agency', # Maps to Prospect.agency
                'Requirement Title': 'title',
                'Requirement Description': 'description',
                'NAICS Code': 'naics',
                'Contract Vehicle': 'contract_vehicle', # To extra
                'Contract Type': 'contract_type',
                'Estimated Contract Value': 'estimated_value_raw',
                'Anticipated Award Date': 'award_date_raw',
                'Anticipated Solicitation Release Date': 'release_date_raw',
                'Small Business Set-Aside': 'set_aside',
                'Place of Performance City': 'place_city',
                'Place of Performance State': 'place_state',
                'Place of Performance Country': 'place_country'
                # 'Contact Name', 'Contact Email', 'Contact Phone' -> To extra
            }
            
            # Rename only columns that exist
            rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=rename_map_existing, inplace=True)

            # Date Parsing
            if 'award_date_raw' in df.columns:
                df['award_date'] = pd.to_datetime(df['award_date_raw'], errors='coerce').dt.date
                df['award_fiscal_year'] = pd.to_datetime(df['award_date_raw'], errors='coerce').dt.year.astype('Int64')
            else:
                df['award_date'] = None
                df['award_fiscal_year'] = pd.NA

            if 'release_date_raw' in df.columns:
                df['release_date'] = pd.to_datetime(df['release_date_raw'], errors='coerce').dt.date
            else:
                df['release_date'] = None

            # Estimated Value Parsing
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            else:
                df['estimated_value'] = pd.NA
                df['est_value_unit'] = pd.NA

            # Default place_country if not present (HHS transform assumes USA)
            if 'place_country' not in df.columns:
                 df['place_country'] = 'USA'
            elif 'place_country' in df.columns: # Ensure consistent handling of empty/NaN
                 df['place_country'] = df['place_country'].fillna('USA')


            # Drop raw/intermediate columns
            cols_to_drop = ['award_date_raw', 'release_date_raw', 'estimated_value_raw']
            df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore', inplace=True)
            # --- End: Logic adapted from hhs_transform.normalize_columns_hhs ---

            # Define the final column rename map.
            final_column_rename_map = {
                'native_id': 'native_id',
                'agency': 'agency',
                'title': 'title',
                'description': 'description',
                'naics': 'naics',
                'contract_vehicle': 'contract_vehicle', # This will go to extra
                'contract_type': 'contract_type',
                'estimated_value': 'estimated_value',
                'est_value_unit': 'est_value_unit',
                'award_date': 'award_date',
                'award_fiscal_year': 'award_fiscal_year',
                'release_date': 'release_date',
                'set_aside': 'set_aside',
                'place_city': 'place_city',
                'place_state': 'place_state',
                'place_country': 'place_country',
                # Columns like 'Contact Name', 'Contact Email', 'Contact Phone'
                # will be handled by _process_and_load_data if they exist in df
                # and are not in prospect_model_fields, so they don't need explicit map here
                # unless renaming them.
                # Assuming they are already named e.g., 'contact_name' from initial rename or direct from source.
                # If their original names are 'Contact Name', they should be included in the initial rename_map.
            }
            
            # Ensure all columns in final_column_rename_map exist in df.
            for col_name in final_column_rename_map.keys():
                if col_name not in df.columns:
                    df[col_name] = pd.NA

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            # Original ID generation: native_id if available, else title, desc, agency
            # Using native_id as primary, common logic in _process_and_load_data will use fields_for_id_hash
            # if 'id' column isn't already populated. Here, we assume 'native_id' is the preferred unique key.
            # If 'native_id' is consistently present and unique, this is fine.
            # Otherwise, a composite key might be better.
            # For now, let's use the more robust composite key as per original logic.
            # The _process_and_load_data will generate 'id' if not present.
            # We need to ensure the columns for the hash are correctly named.
            # The original hash logic was:
            #   if native_id_val: unique_string = f"{native_id_val}-{self.source_name}"
            #   else: unique_string = f"{title_val}-{desc_val}-{agency_val}-{self.source_name}"
            # This conditional logic is not directly supported by fields_for_id_hash.
            # We will rely on a consistent set of fields for hashing.
            # If native_id is present, it should be part of the hash.
            fields_for_id_hash = ['native_id', 'title', 'description', 'agency']


            return self._process_and_load_data(df, final_column_rename_map, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"HHS CSV file not found: {file_path}")
            raise ScraperError(f"Processing failed: HHS CSV file not found: {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty HHS CSV file: {file_path}")
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during HHS CSV processing: {e}.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing HHS file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing HHS file {file_path}: {str(e)}")

    def scrape(self):
        """
        Run the scraper to download the forecast document.
        Returns a result dict from scrape_with_structure.
        """
        return self.scrape_with_structure(
            extract_func=self.download_forecast_document,
            process_func=self.process_func
        )