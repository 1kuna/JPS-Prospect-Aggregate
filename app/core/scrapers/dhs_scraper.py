"""Department of Homeland Security Opportunity Forecast scraper."""

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
import re
from datetime import datetime

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, DataSource, db
from app.database.crud import bulk_upsert_prospects
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date
from app.config import DHS_FORECAST_URL
from app.utils.scraper_utils import handle_scraper_error

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.dhs_forecast")

class DHSForecastScraper(BaseScraper):
    """Scraper for the DHS Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DHS Forecast scraper."""
        super().__init__(
            source_name="DHS Forecast",
            base_url=DHS_FORECAST_URL,
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

            download = download_info.value
            download_path = download.path() # Playwright saves to a temp location

            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'dhs_download.csv'")
                original_filename = "dhs_download.csv" # Keep default but extension will be used

            _, ext = os.path.splitext(original_filename)
            if not ext: # Ensure there's an extension
                ext = '.csv' # Default extension if none found
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")
                
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'dhs'
            final_filename = f"dhs_{timestamp_str}{ext}" 
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
            self.logger.error(f"Timeout error during DHS forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Timeout during download process")
            raise ScraperError(f"Timeout during DHS forecast download process: {str(e)}")
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
            # DHS transform script handles both xlsx and csv, assuming xlsx primarily based on current scraper
            # TODO: Determine correct sheet_name and header row for DHS Excel if not default
            df = pd.read_excel(file_path, sheet_name=0, header=0) 
            self.logger.info(f"Loaded {len(df)} rows from {file_path}")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from dhs_transform.normalize_columns_dhs ---
            rename_map = {
                # Raw DHS Name: Prospect Model Field Name (or intermediate)
                'APFS Number': 'native_id',
                'NAICS': 'naics',
                'Component': 'agency', # Maps to Prospect.agency
                'Title': 'title',
                'Contract Type': 'contract_type',
                'Contract Vehicle': 'contract_vehicle',      # To extra
                'Dollar Range': 'estimated_value_raw',      # To be parsed
                'Small Business Set-Aside': 'set_aside',
                'Small Business Program': 'small_business_program', # To extra
                'Contract Status': 'contract_status',        # To extra
                'Place of Performance City': 'place_city',
                'Place of Performance State': 'place_state',
                'Description': 'description',
                'Estimated Solicitation Release': 'release_date', # Maps to Prospect.release_date (raw)
                'Award Quarter': 'award_date_raw'           # To be parsed for award_date & award_fiscal_year
            }
            df.rename(columns=rename_map, inplace=True)

            # Date Parsing (Solicitation/Release Date)
            if 'release_date' in df.columns:
                df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce').dt.date
            else:
                df['release_date'] = None

            # Award Date and Fiscal Year Parsing (from Award Quarter)
            if 'award_date_raw' in df.columns:
                parsed_award_info = df['award_date_raw'].apply(fiscal_quarter_to_date)
                df['award_date'] = parsed_award_info.apply(lambda x: x[0].date() if pd.notna(x[0]) else None)
                df['award_fiscal_year'] = parsed_award_info.apply(lambda x: x[1])
            else: 
                df['award_date'] = None
                df['award_fiscal_year'] = pd.NA
            
            if 'award_fiscal_year' in df.columns: # Ensure correct type
                df['award_fiscal_year'] = df['award_fiscal_year'].astype('Int64')

            # Estimated Value Parsing (from Dollar Range)
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            else:
                df['estimated_value'] = pd.NA 
                df['est_value_unit'] = pd.NA

            # Initialize Place Country if missing (DHS transform assumes USA)
            if 'place_country' not in df.columns:
                 df['place_country'] = 'USA'
            
            # Drop raw columns used for parsing after they are processed
            df.drop(columns=['estimated_value_raw', 'award_date_raw'], errors='ignore', inplace=True)
            # --- End: Logic adapted from dhs_transform.normalize_columns_dhs ---
            
            # Normalize all column names (lowercase, snake_case) - from transform script
            df.columns = df.columns.str.strip().str.lower().str.replace(r'\\s+\\(.*?\\)', '', regex=True).str.replace(r'\\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)
            df = df.loc[:, ~df.columns.duplicated()] # Remove duplicates

            # Define Prospect model fields (excluding auto fields)
            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name not in ['loaded_at', 'id', 'source_id']]
            
            # Handle 'extra' column
            current_cols_normalized = df.columns.tolist()
            unmapped_cols = [col for col in current_cols_normalized if col not in prospect_model_fields]

            if unmapped_cols:
                self.logger.info(f"Found unmapped columns for 'extra': {unmapped_cols}")
                # Convert specific types in unmapped_cols to string before to_dict for JSON compatibility
                for col_name in unmapped_cols:
                    if df[col_name].dtype == 'datetime64[ns]' or df[col_name].dtype.name == 'datetime64[ns, UTC]':
                        df[col_name] = df[col_name].dt.isoformat()
                    # Add other type conversions if needed (e.g., complex objects)
                df['extra'] = df[unmapped_cols].astype(str).to_dict(orient='records')
            else:
                df['extra'] = None
            
            # Ensure all Prospect model columns exist
            for col in prospect_model_fields:
                if col not in df.columns:
                    df[col] = pd.NA
            
            # Add source_id
            data_source_obj = db.session.query(DataSource).filter_by(name=self.source_name).first()
            if data_source_obj:
                df['source_id'] = data_source_obj.id
            else:
                self.logger.warning(f"DataSource '{self.source_name}' not found. 'source_id' will be None.")
                df['source_id'] = None
            
            # --- Start: ID Generation (adapted from dhs_transform.generate_id) ---
            def generate_prospect_id(row: pd.Series) -> str:
                naics_val = str(row.get('naics', ''))
                title_val = str(row.get('title', '')) # Using 'title' as per Prospect model
                desc_val = str(row.get('description', '')) # Using 'description' 
                unique_string = f"{naics_val}-{title_val}-{desc_val}-{self.source_name}"
                return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

            df['id'] = df.apply(generate_prospect_id, axis=1)
            # --- End: ID Generation ---

            # Select final columns for Prospect model
            final_prospect_columns = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            df_to_insert = df[[col for col in final_prospect_columns if col in df.columns]]

            df_to_insert.dropna(how='all', inplace=True)
            if df_to_insert.empty:
                self.logger.info("After processing, no valid data rows to insert.")
                return

            self.logger.info(f"Attempting to insert/update {len(df_to_insert)} records for {self.source_name}.")
            bulk_upsert_prospects(df_to_insert)
            self.logger.info(f"Successfully inserted/updated records for {self.source_name} from {file_path}.")

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
