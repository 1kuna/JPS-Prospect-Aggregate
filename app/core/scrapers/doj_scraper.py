"""Department of Justice Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
# import sys # Unused
# import datetime # Unused at top level, `from datetime import datetime` is used

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
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date, split_place

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.doj_forecast")

class DOJForecastScraper(BaseScraper):
    """Scraper for the DOJ Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DOJ Forecast scraper."""
        super().__init__(
            source_name="DOJ Forecast", # Updated source name
            base_url=active_config.DOJ_FORECAST_URL, # Updated URL config variable
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
            self.logger.info("Clicking download link and waiting for download...")
            with self.page.expect_download(timeout=90000) as download_info:
                 download_link.click()

            _ = download_info.value # Access the download object

            # Wait a brief moment for the download event to be processed by the callback
            self.page.wait_for_timeout(2000) # Adjust as needed

            if not self._last_download_path or not os.path.exists(self._last_download_path):
                self.logger.error(f"BaseScraper._last_download_path not set or invalid. Value: {self._last_download_path}")
                # Attempt to get the path from the download object if _last_download_path wasn't set
                try:
                    download = download_info.value # Get download object if needed for path
                    temp_playwright_path = download.path()
                    self.logger.warning(f"Playwright temp download path: {temp_playwright_path}")
                    # This indicates an issue in _handle_download or event processing timing.
                except Exception as path_err:
                    self.logger.error(f"Could not retrieve Playwright download path: {path_err}")
                raise ScraperError("Download failed: File not found or path not set by BaseScraper._handle_download.")

            self.logger.info(f"Download process completed. File saved at: {self._last_download_path}")
            return self._last_download_path
            
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
            
            # Define the final column rename map.
            final_column_rename_map = {
                'native_id': 'native_id',
                'agency': 'agency',
                'title': 'title',
                'description': 'description',
                'contract_type': 'contract_type',
                'naics': 'naics',
                'set_aside': 'set_aside',
                'estimated_value': 'estimated_value',
                'est_value_unit': 'est_value_unit',
                'release_date': 'release_date',
                'award_date': 'award_date',
                'award_fiscal_year': 'award_fiscal_year',
                'place_city': 'place_city',
                'place_state': 'place_state',
                'place_country': 'place_country',
                # Raw fields that will go to 'extra'. Ensure they exist in df.
                # If 'Country' was renamed to 'place_country' and also needs to be in extra,
                # it needs a different key here or handle it before this map.
                # For now, assuming direct fields are handled and 'extra' takes others.
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