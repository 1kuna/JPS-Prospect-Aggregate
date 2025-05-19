"""Department of Justice Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
import sys
import shutil
import datetime
import json

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
from app.config import DOJ_FORECAST_URL # Need to add this to config.py
from app.utils.scraper_utils import handle_scraper_error
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date, split_place

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.doj_forecast")

class DOJForecastScraper(BaseScraper):
    """Scraper for the DOJ Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DOJ Forecast scraper."""
        super().__init__(
            source_name="DOJ Forecast", # Updated source name
            base_url=DOJ_FORECAST_URL, # Updated URL config variable
            debug_mode=debug_mode
        )
    
    def download_forecast_document(self):
        """
        Download the forecast Excel document from the DOJ website.
        Requires clicking the 'Download the Excel File' link.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Attempting to download DOJ forecast document")
        
        # Selector for the Excel download link
        download_link_selector = 'a:has-text("Download the Excel File")' 
        
        try:
            # Navigate to the main forecast page
            self.logger.info(f"Navigating to {self.base_url}")
            self.navigate_to_url()
            self.logger.info("Page loaded.")
            
            # Wait for the download link to be visible and ready
            download_link = self.page.locator(download_link_selector)
            self.logger.info(f"Waiting for '{download_link_selector}' link to be visible...")
            try:
                download_link.wait_for(state='visible', timeout=20000) # Increased timeout slightly
                self.logger.info(f"'{download_link_selector}' link is visible.")
            except PlaywrightTimeoutError as e:
                self.logger.error(f"Download link did not become visible/enabled within 20s: {e}")
                raise ScraperError("Download link did not appear or become enabled")

            # Click the download link and wait for the download
            self.logger.info(f"Clicking download link and waiting for download...")
            with self.page.expect_download(timeout=90000) as download_info:
                 download_link.click()

            download = download_info.value
            download_path = download.path() # Playwright saves to a temp location
            
            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'doj_download.xlsx'")
                original_filename = "doj_download.xlsx"

            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.xlsx' # Default extension
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'doj'
            final_filename = f"doj_{timestamp_str}{ext}" 
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
            self.logger.error(f"Timeout error during DOJ forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Timeout during download process")
            raise ScraperError(f"Timeout during DOJ forecast download process: {str(e)}")
        except Exception as e:
            self.logger.error(f"General error during DOJ forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Error downloading DOJ forecast document")
            if not isinstance(e, ScraperError):
                 raise ScraperError(f"Failed to download DOJ forecast document: {str(e)}") from e
            else:
                 raise
    
    def process_func(self, file_path: str):
        """
        Process the downloaded Excel file, transform data to Prospect objects, 
        and insert into the database using logic adapted from doj_transform.py.
        """
        self.logger.info(f"Processing downloaded Excel file: {file_path}")
        try:
            # DOJ transform: sheet 'Contracting Opportunities Data', header index 12
            df = pd.read_excel(file_path, sheet_name='Contracting Opportunities Data', header=12)
            self.logger.info(f"Loaded {len(df)} rows from {file_path}")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from doj_transform.normalize_columns_doj ---
            rename_map = {
                'Action Tracking Number': 'native_id',
                'Bureau': 'agency', # Maps to Prospect.agency
                'Contract Name': 'title',
                'Description of Requirement': 'description',
                'Contract Type (Pricing)': 'contract_type',
                'NAICS Code': 'naics',
                'Small Business Approach': 'set_aside',
                'Estimated Total Contract Value (Range)': 'estimated_value_raw',
                'Target Solicitation Date': 'release_date_raw', # Raw for Prospect.release_date
                'Target Award Date': 'award_date_raw',
                'Place of Performance': 'place_raw',
                'Country': 'place_country' # Directly mapped to Prospect.place_country
            }
            rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=rename_map_existing, inplace=True)

            # Split Place of Performance
            if 'place_raw' in df.columns:
                split_places_data = df['place_raw'].apply(split_place)
                df['place_city'] = split_places_data.apply(lambda x: x[0])
                df['place_state'] = split_places_data.apply(lambda x: x[1])
            else:
                df['place_city'] = pd.NA
                df['place_state'] = pd.NA
            
            # Default place_country if not specifically provided or after split_place if it was complex
            if 'place_country' not in df.columns or df['place_country'].isna().all():
                 # Check if place_raw might have contained it and split_place set it.
                 # If still no country, default to USA as per transform script practice.
                df['place_country'] = df.get('place_country', pd.Series(index=df.index, dtype=object)).fillna('USA')

            # Parse Estimated Value
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            else:
                df['estimated_value'] = pd.NA
                df['est_value_unit'] = pd.NA

            # Parse Solicitation Date (Prospect.release_date)
            if 'release_date_raw' in df.columns:
                df['release_date'] = pd.to_datetime(df['release_date_raw'], errors='coerce').dt.date
            else:
                df['release_date'] = None

            # Parse Award Date and Fiscal Year (Prospect.award_date, Prospect.award_fiscal_year)
            df['award_date'] = None
            df['award_fiscal_year'] = pd.NA
            if 'award_date_raw' in df.columns:
                # Try direct date parsing
                df['award_date'] = pd.to_datetime(df['award_date_raw'], errors='coerce')
                df['award_fiscal_year'] = df['award_date'].dt.year # Get year from successfully parsed dates
                
                needs_fallback_parse_mask = df['award_date'].isna() & df['award_date_raw'].notna()
                if needs_fallback_parse_mask.any():
                    self.logger.info("DOJ Award Date: Direct date parse failed for some rows, trying fiscal_quarter_to_date fallback...")
                    parsed_qtr_info = df.loc[needs_fallback_parse_mask, 'award_date_raw'].apply(fiscal_quarter_to_date)
                    df.loc[needs_fallback_parse_mask, 'award_date'] = parsed_qtr_info.apply(lambda x: x[0])
                    df.loc[needs_fallback_parse_mask, 'award_fiscal_year'] = parsed_qtr_info.apply(lambda x: x[1])
            
            # Finalize types
            if 'award_date' in df.columns:
                df['award_date'] = pd.to_datetime(df['award_date'], errors='coerce').dt.date # Ensure it is date object
            if 'award_fiscal_year' in df.columns:
                df['award_fiscal_year'] = pd.to_numeric(df['award_fiscal_year'], errors='coerce').astype('Int64')

            # Drop raw/intermediate columns
            cols_to_drop = ['place_raw', 'estimated_value_raw', 'award_date_raw', 'release_date_raw']
            df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore', inplace=True)
            # --- End: Logic adapted from doj_transform.normalize_columns_doj ---
            
            df.columns = df.columns.str.strip().str.lower().str.replace(r'\\s+\\(.*?\\)', '', regex=True).str.replace(r'\\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)
            df = df.loc[:, ~df.columns.duplicated()]

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name not in ['loaded_at', 'id', 'source_id']]
            current_cols_normalized = df.columns.tolist()
            unmapped_cols = [col for col in current_cols_normalized if col not in prospect_model_fields]

            if unmapped_cols:
                self.logger.info(f"Found unmapped columns for 'extra' for DOJ: {unmapped_cols}")
                # DOJ transform script stringifies, does not use JSON for extra, adapt if Prospect.extra is JSON
                # Assuming Prospect.extra is JSON, using similar robust JSON handling as DOC
                def row_to_extra_json(row):
                    extra_dict = {}
                    for col_name in unmapped_cols:
                        val = row.get(col_name)
                        if pd.isna(val):
                            extra_dict[col_name] = None
                        elif isinstance(val, (datetime, pd.Timestamp)):
                            extra_dict[col_name] = val.isoformat()
                        elif isinstance(val, (int, float, bool, str)):
                            extra_dict[col_name] = val
                        else:
                            try: extra_dict[col_name] = str(val)
                            except Exception: extra_dict[col_name] = "CONVERSION_ERROR"
                    try: return json.dumps(extra_dict) # Need import json
                    except TypeError: return str(extra_dict)
                df['extra'] = df.apply(row_to_extra_json, axis=1)
            else:
                df['extra'] = None # This should be None for DB if Prospect.extra is nullable JSON
            
            for col in prospect_model_fields:
                if col not in df.columns:
                    df[col] = pd.NA
            
            data_source_obj = db.session.query(DataSource).filter_by(name=self.source_name).first()
            df['source_id'] = data_source_obj.id if data_source_obj else None
            
            def generate_prospect_id(row: pd.Series) -> str:
                naics_val = str(row.get('naics', ''))
                title_val = str(row.get('title', ''))
                desc_val = str(row.get('description', ''))
                unique_string = f"{naics_val}-{title_val}-{desc_val}-{self.source_name}"
                return hashlib.md5(unique_string.encode('utf-8')).hexdigest()
            df['id'] = df.apply(generate_prospect_id, axis=1)

            final_prospect_columns = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            df_to_insert = df[[col for col in final_prospect_columns if col in df.columns]]

            df_to_insert.dropna(how='all', inplace=True)
            if df_to_insert.empty:
                self.logger.info("After DOJ processing, no valid data rows to insert.")
                return

            self.logger.info(f"Attempting to insert/update {len(df_to_insert)} DOJ records.")
            bulk_upsert_prospects(df_to_insert)
            self.logger.info(f"Successfully inserted/updated DOJ records from {file_path}.")

        except FileNotFoundError:
            self.logger.error(f"DOJ Excel file not found: {file_path}")
            raise ScraperError(f"Processing failed: DOJ Excel file not found: {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty DOJ Excel file: {file_path}")
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during DOJ Excel processing: {e}.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing DOJ file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing DOJ file {file_path}: {str(e)}")

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
    """Run the DOJ Forecast scraper."""
    source_name = "DOJ Forecast"
    local_logger = logger
    scraper = None
    
    try:
        scraper = DOJForecastScraper(debug_mode=False)
        local_logger.info(f"Running {source_name} scraper")
        result = scraper.scrape() 
        
        if not result or not result.get("success", False):
            error_msg = result.get("error", f"{source_name} scraper failed without specific error") if result else f"{source_name} scraper failed without specific error"
            raise ScraperError(error_msg)
        
        return {"success": True, "file_path": result.get("file_path"), "message": f"{source_name} scraped successfully"}
    
    except ImportError as e:
        error_msg = f"Import error for {source_name}: {str(e)}"
        local_logger.error(error_msg)
        handle_scraper_error(e, source_name, "Import error")
        raise ScraperError(error_msg) from e
    except ScraperError as e:
        local_logger.error(f"ScraperError occurred for {source_name}: {str(e)}")
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
        result = run_scraper(force=True)
        if result and result.get("success"):
            print(f"DOJ Forecast scraper finished successfully. File at: {result.get('file_path', 'N/A')}")
        else:
             print(f"DOJ Forecast scraper failed. Check logs for details.")
             # sys.exit(1) 
    except Exception as e:
        print(f"DOJ Forecast scraper failed: {e}")
        traceback.print_exc()
        # sys.exit(1) 