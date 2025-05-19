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
import pandas as pd
import hashlib
import traceback
import re
from datetime import datetime
import json

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, DataSource, db
from app.database.crud import bulk_upsert_prospects
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.config import HHS_FORECAST_URL
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
            base_url=HHS_FORECAST_URL,
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

            # Standardize column names
            df.columns = df.columns.str.strip().str.lower().str.replace(r'\\s+\\(.*?\\)', '', regex=True).str.replace(r'\\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)
            df = df.loc[:, ~df.columns.duplicated()]

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name not in ['loaded_at', 'id', 'source_id']]
            current_cols_normalized = df.columns.tolist()
            unmapped_cols = [col for col in current_cols_normalized if col not in prospect_model_fields]

            if unmapped_cols:
                self.logger.info(f"Found unmapped columns for 'extra' for HHS: {unmapped_cols}")
                def row_to_extra_json(row):
                    extra_dict = {}
                    for col_name in unmapped_cols:
                        val = row.get(col_name)
                        if pd.isna(val):
                            extra_dict[col_name] = None
                        elif pd.api.types.is_datetime64_any_dtype(val) or isinstance(val, (datetime, pd.Timestamp)):
                            extra_dict[col_name] = pd.to_datetime(val).isoformat()
                        elif isinstance(val, (int, float, bool, str)):
                            extra_dict[col_name] = val
                        else:
                            try: extra_dict[col_name] = str(val)
                            except Exception: extra_dict[col_name] = "CONVERSION_ERROR"
                    try:
                        return json.dumps(extra_dict)
                    except TypeError:
                        # Fallback for any unexpected types that json.dumps can't handle
                        self.logger.warning(f"Could not serialize extra_dict to JSON: {extra_dict}, falling back to string representation.")
                        return str(extra_dict)
                df['extra'] = df.apply(row_to_extra_json, axis=1)
            else:
                df['extra'] = None

            for col in prospect_model_fields:
                if col not in df.columns:
                    df[col] = pd.NA

            data_source_obj = db.session.query(DataSource).filter_by(name=self.source_name).first()
            df['source_id'] = data_source_obj.id if data_source_obj else None

            # --- ID Generation (adapted from hhs_transform.generate_id) ---
            def generate_prospect_id(row: pd.Series) -> str:
                # HHS transform uses native_id if available, else title, desc, agency
                native_id_val = str(row.get('native_id', ''))
                if native_id_val and native_id_val != 'nan' and native_id_val != 'None':
                    unique_string = f"{native_id_val}-{self.source_name}"
                else:
                    title_val = str(row.get('title', ''))
                    desc_val = str(row.get('description', ''))
                    agency_val = str(row.get('agency', '')) # HHS transform uses agency in fallback
                    unique_string = f"{title_val}-{desc_val}-{agency_val}-{self.source_name}"
                return hashlib.md5(unique_string.encode('utf-8')).hexdigest()
            df['id'] = df.apply(generate_prospect_id, axis=1)
            # --- End: ID Generation ---

            final_prospect_columns = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            df_to_insert = df[[col for col in final_prospect_columns if col in df.columns]]

            df_to_insert.dropna(how='all', inplace=True)
            if df_to_insert.empty:
                self.logger.info("After HHS processing, no valid data rows to insert.")
                return

            self.logger.info(f"Attempting to insert/update {len(df_to_insert)} HHS records.")
            bulk_upsert_prospects(df_to_insert)
            self.logger.info(f"Successfully inserted/updated HHS records from {file_path}.")

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