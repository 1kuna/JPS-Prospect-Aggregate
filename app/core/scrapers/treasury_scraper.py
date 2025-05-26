"""Treasury Forecast scraper."""

# Standard library imports
import os
# import sys # Unused
import time
# import shutil # Unused

# Third-party imports
# import requests # Unused
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
import traceback # Added traceback
# import re # Unused

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect # Added Prospect, DataSource, db
# from app.database.crud import bulk_upsert_prospects # Unused
from app.config import active_config # Import active_config
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory # find_files was unused
from app.utils.logger import logger
from app.utils.scraper_utils import (
    # check_url_accessibility, # Unused
    # download_file, # Unused
    # save_permanent_copy, # Unused
    handle_scraper_error
)
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date, split_place # Added parsing utils

# Set up logging
logger = logger.bind(name="scraper.treasury_forecast")

# Placeholder for URL check function if needed, similar to acquisition_gateway
# def check_url_accessibility(url=None): ...

class TreasuryScraper(BaseScraper):
    """Scraper for the Treasury Forecast site."""

    def __init__(self, debug_mode=False):
        """Initialize the Treasury scraper."""
        super().__init__(
            source_name="Treasury Forecast",
            base_url=active_config.TREASURY_FORECAST_URL, # Use config URL
            debug_mode=debug_mode
        )
        # Ensure the specific download directory for this scraper exists
        ensure_directory(self.download_path)

    def navigate_to_forecast_page(self):
        """Navigate to the forecast page."""
        self.logger.info(f"Navigating to {self.base_url}")
        return self.navigate_to_url()

    def download_opportunity_data(self):
        """
        Download the Opportunity Data file from the Treasury Forecast site.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        try:
            # Wait for the page to load completely (changed from networkidle to load)
            self.logger.info("Waiting for page 'load' state...")
            self.page.wait_for_load_state('load', timeout=90000)
            self.logger.info("Page loaded. Waiting for download button.")

            # Locate the download button using XPath
            download_button_xpath = "//lightning-button/button[contains(text(), 'Download Opportunity Data')]"
            download_button = self.page.locator(download_button_xpath)

            # Wait for the button to be visible
            download_button.wait_for(state='visible', timeout=60000)
            self.logger.info("Download button found and visible.")

            self.logger.info("Clicking 'Download Opportunity Data' and waiting for download...")
            with self.page.expect_download(timeout=120000) as download_info: # Increased download timeout
                # Sometimes clicks need retries or alternative methods if obscured
                try:
                    download_button.click(timeout=15000)
                except PlaywrightTimeoutError:
                    self.logger.warning("Initial click timed out, trying JavaScript click.")
                    self.page.evaluate(f"document.evaluate('{download_button_xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click();")
                except Exception as click_err:
                    self.logger.error(f"Error during button click: {click_err}")
                    raise

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
            self.logger.error(f"Timeout error during download process: {str(e)}")
            # Capture screenshot for debugging timeouts
            screenshot_path = os.path.join(active_config.LOGS_DIR, f"treasury_timeout_error_{int(time.time())}.png")
            try:
                self.page.screenshot(path=screenshot_path, full_page=True)
                self.logger.info(f"Screenshot saved to {screenshot_path}")
            except Exception as ss_err:
                self.logger.error(f"Failed to save screenshot: {ss_err}")
            handle_scraper_error(e, self.source_name, "Timeout error during download")
            raise ScraperError(f"Timeout error during download: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error downloading data: {str(e)}")
            handle_scraper_error(e, self.source_name, "Error downloading opportunity data")
            raise ScraperError(f"Error downloading opportunity data: {str(e)}")

    def scrape(self):
        """
        Run the scraper to navigate and download the file.

        Returns:
            str: Path to the downloaded file if successful, raises ScraperError otherwise.
        """
        # Use the structured scrape method from the base class
        return self.scrape_with_structure(
            setup_func=self.navigate_to_forecast_page,
            extract_func=self.download_opportunity_data,
            process_func=self.process_func
        )

    def process_func(self, file_path: str):
        """
        Process the downloaded HTML file (masquerading as .xls), transform data to Prospect objects,
        and insert into the database using logic adapted from treasury_transform.py.
        """
        self.logger.info(f"Processing downloaded file (expected HTML as .xls): {file_path}")
        try:
            # Treasury transform: reads HTML table (often saved as .xls), header row 0
            # pd.read_html returns a list of DataFrames
            try:
                df_list = pd.read_html(file_path, header=0)
                if not df_list:
                    self.logger.error(f"No tables found in HTML file: {file_path}")
                    raise ScraperError(f"No tables found in HTML file: {file_path}")
                df = df_list[0] # Assume the first table is the correct one
                self.logger.info(f"Successfully read HTML table from {file_path}. Shape: {df.shape}")
            except ValueError as ve:
                 # Fallback if it's a real Excel file (though less common for Treasury)
                self.logger.warning(f"Could not read {file_path} as HTML table ({ve}), attempting pd.read_excel...")
                try:
                    df = pd.read_excel(file_path, header=0) # Basic excel read as fallback
                    self.logger.info(f"Successfully read as Excel file {file_path}. Shape: {df.shape}")
                except Exception as ex_err:
                    self.logger.error(f"Failed to read {file_path} as either HTML or Excel: {ex_err}")
                    raise ScraperError(f"Could not parse file {file_path} as HTML or Excel.") from ex_err
            
            df.dropna(how='all', inplace=True) # Pre-processing from transform script
            self.logger.info(f"Loaded {len(df)} rows from {file_path} after initial dropna.")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from treasury_transform.normalize_columns_treasury ---
            rename_map = {
                'Specific Id': 'native_id',
                'Bureau': 'agency', # Mapped to Prospect.agency (was 'office' in transform)
                'PSC': 'title', # Mapped to Prospect.title (was 'requirement_title' in transform)
                # 'Type of Requirement': 'requirement_type', # This will go to extra
                'Place of Performance': 'place_raw',
                'Contract Type': 'contract_type',
                'NAICS': 'naics',
                'Estimated Total Contract Value': 'estimated_value_raw',
                'Type of Small Business Set-aside': 'set_aside',
                'Projected Award FY_Qtr': 'award_qtr_raw',
                'Project Period of Performance Start': 'release_date_raw' # Mapped to Prospect.release_date
            }

            # Handle alternative native_id fields from transform script
            if 'Specific Id' not in df.columns and 'ShopCart/req' in df.columns:
                rename_map['ShopCart/req'] = 'native_id'
            elif 'Specific Id' not in df.columns and 'Contract Number' in df.columns:
                rename_map['Contract Number'] = 'native_id'

            rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=rename_map_existing, inplace=True)

            # Place of Performance Parsing
            if 'place_raw' in df.columns:
                split_places_data = df['place_raw'].apply(split_place)
                df['place_city'] = split_places_data.apply(lambda x: x[0])
                df['place_state'] = split_places_data.apply(lambda x: x[1])
                df['place_country'] = 'USA'  # Assume USA
            else:
                df['place_city'], df['place_state'], df['place_country'] = pd.NA, pd.NA, 'USA'

            # Estimated Value Parsing
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            else:
                df['estimated_value'], df['est_value_unit'] = pd.NA, pd.NA

            # Award Date and Fiscal Year Parsing (from Projected Award FY_Qtr)
            if 'award_qtr_raw' in df.columns:
                parsed_award_info = df['award_qtr_raw'].apply(fiscal_quarter_to_date)
                df['award_date'] = parsed_award_info.apply(lambda x: x[0].date() if pd.notna(x[0]) else None)
                df['award_fiscal_year'] = parsed_award_info.apply(lambda x: x[1])
            else:
                df['award_date'] = None
                df['award_fiscal_year'] = pd.NA
            if 'award_fiscal_year' in df.columns: # Ensure correct type
                df['award_fiscal_year'] = pd.to_numeric(df['award_fiscal_year'], errors='coerce').astype('Int64')

            # Solicitation Date (Release Date) Parsing
            if 'release_date_raw' in df.columns:
                df['release_date'] = pd.to_datetime(df['release_date_raw'], errors='coerce').dt.date
            else:
                df['release_date'] = None

            # Initialize Prospect.description as None (Treasury source lacks detailed description)
            df['description'] = None 

            # Drop raw/intermediate columns
            cols_to_drop = ['place_raw', 'estimated_value_raw', 'award_qtr_raw', 'release_date_raw']
            df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore', inplace=True)
            # --- End: Logic adapted from treasury_transform.normalize_columns_treasury ---

            # Define the final column rename map.
            final_column_rename_map = {
                'native_id': 'native_id',
                'agency': 'agency',
                'title': 'title', # Mapped from 'PSC'
                'description': 'description', # Initialized as None
                'place_city': 'place_city',
                'place_state': 'place_state',
                'place_country': 'place_country',
                'contract_type': 'contract_type',
                'naics': 'naics',
                'estimated_value': 'estimated_value',
                'est_value_unit': 'est_value_unit',
                'set_aside': 'set_aside',
                'award_date': 'award_date',
                'award_fiscal_year': 'award_fiscal_year',
                'release_date': 'release_date',
                # 'Type of Requirement' was in original source, if renamed to 'requirement_type',
                # it will be handled by 'extra' if not in prospect_model_fields.
            }

            # Ensure all columns in final_column_rename_map exist in df.
            for col_name in final_column_rename_map.keys():
                if col_name not in df.columns:
                    df[col_name] = pd.NA
            
            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            # Original ID generation: naics, title (as PSC), description (None), agency
            fields_for_id_hash = ['naics', 'title', 'description', 'agency']

            return self._process_and_load_data(df, final_column_rename_map, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"Treasury file not found: {file_path}")
            raise ScraperError(f"Processing failed: Treasury file not found: {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty Treasury file: {file_path}")
            return # Not a ScraperError
        except KeyError as e:
            self.logger.error(f"Missing expected column during Treasury processing: {e}.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing Treasury file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing Treasury file {file_path}: {str(e)}")

# Placeholder for check_last_download function if needed
# def check_last_download(): ...