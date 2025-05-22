"""Department Of State Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
import sys
import shutil
import datetime

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
import hashlib
import re
import json
from datetime import datetime

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, DataSource, db
from app.database.crud import bulk_upsert_prospects
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.config import active_config # Import active_config
from app.utils.scraper_utils import handle_scraper_error
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.dos_forecast")

class DOSForecastScraper(BaseScraper):
    """Scraper for the DOS Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DOS Forecast scraper."""
        super().__init__(
            source_name="DOS Forecast", # Updated source name
            base_url=active_config.DOS_FORECAST_URL, # Updated URL config variable
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

        # --- Start modification for timestamped filename ---
        # Extract original filename from URL
        try:
            original_filename = os.path.basename(file_url)
            if not original_filename: # Handle cases where basename might be empty
                raise ValueError("Could not extract filename from URL")
        except Exception as e:
            self.logger.warning(f"Could not extract filename from URL '{file_url}', using default. Error: {e}")
            original_filename = "dos_forecast_download.xlsx"

        base_name, ext = os.path.splitext(original_filename)
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use hardcoded identifier 'dos'
        final_filename = f"dos_{timestamp_str}{ext}" 

        # Use the scraper's specific download path
        target_download_dir = self.download_path
        final_path = os.path.join(target_download_dir, final_filename)
        self.logger.info(f"Original filename from URL: {original_filename}")
        self.logger.info(f"Saving with standardized filename: {final_filename} to {final_path}")
        # --- End modification ---

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

            # Save the response body to the file using the new final_path
            self.logger.info("Content-Type appears valid, saving file...")
            with open(final_path, 'wb') as f:
                f.write(response.body())
            
            self.logger.info(f"Successfully downloaded file content to: {final_path}")

            # Clean up the API request context
            api_request_context.dispose()

            # Verify the file exists and is not empty using the new final_path
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
    
    def process_func(self, file_path: str):
        """
        Process the downloaded Excel file, transform data to Prospect objects, 
        and insert into the database using logic adapted from dos_transform.py.
        """
        self.logger.info(f"Processing downloaded Excel file: {file_path}")
        try:
            # DOS transform: sheet 'FY25-Procurement-Forecast', header index 0
            df = pd.read_excel(file_path, sheet_name='FY25-Procurement-Forecast', header=0)
            df.dropna(how='all', inplace=True) # Pre-processing from transform script
            self.logger.info(f"Loaded {len(df)} rows from {file_path} after initial dropna.")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from dos_transform.normalize_columns_dos ---
            rename_map = {
                'Contract Number': 'native_id',
                'Office Symbol': 'agency', # Maps to Prospect.agency
                'Requirement Title': 'title',
                'Requirement Description': 'description',
                'Estimated Value': 'estimated_value_raw1', 
                'Dollar Value': 'estimated_value_raw2', 
                'Place of Performance Country': 'place_country',
                'Place of Performance City': 'place_city',
                'Place of Performance State': 'place_state',
                'Award Type': 'contract_type',
                'Anticipated Award Date': 'award_date_raw',
                'Target Award Quarter': 'award_qtr_raw',
                'Fiscal Year': 'award_fiscal_year_raw',
                'Anticipated Set Aside': 'set_aside',
                'Anticipated Solicitation Release Date': 'release_date_raw' # for Prospect.release_date
            }
            rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=rename_map_existing, inplace=True)

            # Award Date/Year Parsing (Priority: FY raw -> Date raw -> Quarter raw)
            df['award_date'] = None # Initialize with None for dt.date compatibility later
            df['award_fiscal_year'] = pd.NA

            if 'award_fiscal_year_raw' in df.columns:
                df['award_fiscal_year'] = pd.to_numeric(df['award_fiscal_year_raw'], errors='coerce')

            if 'award_date_raw' in df.columns:
                parsed_direct_award_date = pd.to_datetime(df['award_date_raw'], errors='coerce')
                # Fill award_date if it's still None (it is, from initialization)
                df['award_date'] = df['award_date'].fillna(parsed_direct_award_date.dt.date) 
                
                needs_fy_from_date_mask = df['award_fiscal_year'].isna() & parsed_direct_award_date.notna()
                if needs_fy_from_date_mask.any():
                    df.loc[needs_fy_from_date_mask, 'award_fiscal_year'] = parsed_direct_award_date[needs_fy_from_date_mask].dt.year

            if 'award_qtr_raw' in df.columns:
                needs_qtr_parse_mask = df['award_date'].isna() & df['award_fiscal_year'].isna() & df['award_qtr_raw'].notna()
                if needs_qtr_parse_mask.any():
                    parsed_qtr_info = df.loc[needs_qtr_parse_mask, 'award_qtr_raw'].apply(fiscal_quarter_to_date)
                    df.loc[needs_qtr_parse_mask, 'award_date'] = parsed_qtr_info.apply(lambda x: x[0].date() if pd.notna(x[0]) else None)
                    df.loc[needs_qtr_parse_mask, 'award_fiscal_year'] = parsed_qtr_info.apply(lambda x: x[1])
            
            if 'award_fiscal_year' in df.columns: # Ensure type
                 df['award_fiscal_year'] = pd.to_numeric(df['award_fiscal_year'], errors='coerce').astype('Int64')

            # Estimated Value Parsing (Priority: raw1 then raw2)
            if 'estimated_value_raw1' in df.columns and df['estimated_value_raw1'].notna().any():
                parsed_values = df['estimated_value_raw1'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            elif 'estimated_value_raw2' in df.columns:
                df['estimated_value'] = pd.to_numeric(df['estimated_value_raw2'], errors='coerce')
                df['est_value_unit'] = None 
            else:
                df['estimated_value'] = pd.NA
                df['est_value_unit'] = pd.NA

            # Solicitation Date (Prospect.release_date)
            if 'release_date_raw' in df.columns:
                df['release_date'] = pd.to_datetime(df['release_date_raw'], errors='coerce').dt.date
            else:
                df['release_date'] = None
            
            # Initialize NAICS (not in DOS source)
            df['naics'] = pd.NA
            
            # Initialize Place columns if missing (default country USA)
            for col_place in ['place_city', 'place_state']:
                if col_place not in df.columns: df[col_place] = pd.NA
            if 'place_country' not in df.columns: df['place_country'] = 'USA'

            cols_to_drop = ['estimated_value_raw1', 'estimated_value_raw2', 'award_date_raw', 'award_qtr_raw', 'award_fiscal_year_raw', 'release_date_raw']
            df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore', inplace=True)
            # --- End: Logic adapted from dos_transform.normalize_columns_dos ---
            
            df.columns = df.columns.str.strip().str.lower().str.replace(r'\\s+\\(.*?\\)', '', regex=True).str.replace(r'\\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)
            df = df.loc[:, ~df.columns.duplicated()]

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name not in ['loaded_at', 'id', 'source_id']]
            current_cols_normalized = df.columns.tolist()
            unmapped_cols = [col for col in current_cols_normalized if col not in prospect_model_fields]

            if unmapped_cols:
                self.logger.info(f"Found unmapped columns for 'extra' for DOS: {unmapped_cols}")
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
                    try: return json.dumps(extra_dict)
                    except TypeError: return str(extra_dict)
                df['extra'] = df.apply(row_to_extra_json, axis=1)
            else:
                df['extra'] = None

            for col in prospect_model_fields:
                if col not in df.columns:
                    df[col] = pd.NA
            
            data_source_obj = db.session.query(DataSource).filter_by(name=self.source_name).first()
            df['source_id'] = data_source_obj.id if data_source_obj else None
            
            def generate_prospect_id(row: pd.Series) -> str:
                naics_val = str(row.get('naics', '')) # Will be 'nan' or 'None' for DOS
                title_val = str(row.get('title', ''))
                desc_val = str(row.get('description', ''))
                unique_string = f"{naics_val}-{title_val}-{desc_val}-{self.source_name}"
                return hashlib.md5(unique_string.encode('utf-8')).hexdigest()
            df['id'] = df.apply(generate_prospect_id, axis=1)

            final_prospect_columns = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            df_to_insert = df[[col for col in final_prospect_columns if col in df.columns]]

            df_to_insert.dropna(how='all', inplace=True)
            if df_to_insert.empty:
                self.logger.info("After DOS processing, no valid data rows to insert.")
                return

            self.logger.info(f"Attempting to insert/update {len(df_to_insert)} DOS records.")
            bulk_upsert_prospects(df_to_insert)
            self.logger.info(f"Successfully inserted/updated DOS records from {file_path}.")

        except FileNotFoundError:
            self.logger.error(f"DOS Excel file not found: {file_path}")
            raise ScraperError(f"Processing failed: DOS Excel file not found: {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty DOS Excel file: {file_path}")
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during DOS Excel processing: {e}.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing DOS file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing DOS file {file_path}: {str(e)}")

    def scrape(self):
        """
        Run the scraper to download the forecast document.
        Returns a result dict from scrape_with_structure.
        """
        # Modify scrape_with_structure if it assumes page interaction, or call download directly
        # For simplicity, let's assume scrape_with_structure handles setup/cleanup okay
        # and we just pass the direct download function.
        return self.scrape_with_structure(
            extract_func=self.download_forecast_document,
            process_func=self.process_func
        )

def run_scraper(force=False):
    """Run the DOS Forecast scraper."""
    source_name = "DOS Forecast"
    local_logger = logger
    scraper = None
    
    try:
        # Removed interval check logic
        # if not force and download_tracker.should_download(source_name):
        #     local_logger.info(f"Skipping scrape for {source_name} due to recent download")
        #     return {"success": True, "message": "Skipped due to recent download"}

        scraper = DOSForecastScraper(debug_mode=False)
        local_logger.info(f"Running {source_name} scraper")
        result = scraper.scrape() 
        
        if not result or not result.get("success", False):
            error_msg = result.get("error", f"{source_name} scraper failed without specific error") if result else f"{source_name} scraper failed without specific error"
            # Log specific note if site might be down
            if "site might be down" in error_msg or "forbidden" in error_msg:
                 local_logger.warning(f"{source_name} scraper failed, potentially due to site technical difficulties.")
            raise ScraperError(error_msg)
        
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
        local_logger.warning(f"The site ({active_config.DOS_FORECAST_URL}) may be experiencing technical difficulties.")
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