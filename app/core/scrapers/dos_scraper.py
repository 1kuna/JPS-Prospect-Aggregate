"""Department Of State Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
# import sys # Unused
# import shutil # Unused
import datetime # Used for datetime.datetime

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
# import re # Unused

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect
# from app.database.crud import bulk_upsert_prospects # Unused
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
        file_url = "https://www.state.gov/wp-content/uploads/2025/02/FY25-Procurement-Forecast-2.xlsx"
        api_request_context = None # Ensure it's defined for the finally block

        try:
            # Determine extension from URL or Content-Type
            original_filename_from_url = os.path.basename(file_url)
            _, ext = os.path.splitext(original_filename_from_url)
            if not ext: # Fallback if URL has no extension
                ext = '.xlsx' # Default for this scraper
                self.logger.warning(f"URL '{file_url}' has no extension, defaulting to '{ext}'. Consider checking Content-Type.")

            # Generate filename consistent with _handle_download convention
            final_filename = f"{self.source_name.lower().replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            final_save_path = os.path.join(self.download_path, final_filename)

            # Ensure the target directory exists
            os.makedirs(self.download_path, exist_ok=True)
            self.logger.info(f"Ensured download directory exists: {self.download_path}")

            self.logger.info(f"Attempting direct download from: {file_url} to {final_save_path}")
            
            # Use Playwright's request context to download
            # Ensure self.playwright is initialized (should be by setup_browser)
            if not self.playwright:
                raise ScraperError("Playwright instance not available. Call setup_browser first.")
            api_request_context = self.playwright.request.new_context()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*' 
            }
            response = api_request_context.get(file_url, headers=headers, timeout=90000) # Added timeout

            if not response.ok:
                self.logger.error(f"Direct download request failed with status {response.status}: {response.status_text}")
                raise ScraperError(f"Failed to download file directly. Status: {response.status}")
            
            # Optional: More robust Content-Type check if needed, for now assumes URL extension is reliable enough or default is okay
            content_type = response.headers.get('content-type', '').lower()
            self.logger.info(f"Response Content-Type: {content_type}")
            # Basic check if URL-derived extension needs override (e.g. if ext was default and content-type is specific)
            if ext == '.xlsx' and not any(excel_type in content_type for excel_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel', 'application/octet-stream']):
                 self.logger.warning(f"Content-Type '{content_type}' does not strongly indicate Excel, but proceeding with '.xlsx' extension based on URL/default.")
            
            with open(final_save_path, 'wb') as f:
                f.write(response.body())
            self.logger.info(f"Successfully downloaded file content to: {final_save_path}")
            
            self._last_download_path = final_save_path

            # Verification
            if not self._last_download_path or not os.path.exists(self._last_download_path) or os.path.getsize(self._last_download_path) == 0:
                self.logger.error(f"Download verification failed: File missing or empty at {self._last_download_path}")
                raise ScraperError("Download verification failed: File missing or empty after direct download.")

            self.logger.info(f"Direct download verification successful. File saved at: {self._last_download_path}")
            return self._last_download_path

        except PlaywrightTimeoutError as e: 
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
                if col_place not in df.columns:
                    df[col_place] = pd.NA
            if 'place_country' not in df.columns:
                df['place_country'] = 'USA'

            cols_to_drop = ['estimated_value_raw1', 'estimated_value_raw2', 'award_date_raw', 'award_qtr_raw', 'award_fiscal_year_raw', 'release_date_raw']
            df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore', inplace=True)
            # --- End: Logic adapted from dos_transform.normalize_columns_dos ---
            
            # Define the final column rename map.
            final_column_rename_map = {
                'native_id': 'native_id',
                'agency': 'agency',
                'title': 'title',
                'description': 'description',
                'naics': 'naics', # Will be NA for DOS
                'place_country': 'place_country',
                'place_city': 'place_city',
                'place_state': 'place_state',
                'contract_type': 'contract_type',
                'award_date': 'award_date',
                'award_fiscal_year': 'award_fiscal_year',
                'set_aside': 'set_aside',
                'release_date': 'release_date',
                'estimated_value': 'estimated_value',
                'est_value_unit': 'est_value_unit',
                # Any other columns that are direct mappings or already processed to final names
            }

            # Ensure all columns in final_column_rename_map exist in df.
            for col_name in final_column_rename_map.keys():
                if col_name not in df.columns:
                    df[col_name] = pd.NA

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            # Original ID generation: unique_string = f"{naics_val}-{title_val}-{desc_val}-{self.source_name}"
            # These correspond to 'naics', 'title', 'description' in the df after initial renaming.
            fields_for_id_hash = ['naics', 'title', 'description']

            return self._process_and_load_data(df, final_column_rename_map, prospect_model_fields, fields_for_id_hash)

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