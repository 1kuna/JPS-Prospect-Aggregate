"""Treasury Forecast scraper."""

# Standard library imports
import os
import sys
import time
import shutil
import datetime # Added datetime import

# Third-party imports
import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
import hashlib
import traceback # Added traceback
import re # Added re
from datetime import datetime # Added datetime
import json # Added json

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, DataSource, db # Added Prospect, DataSource, db
from app.database.crud import bulk_upsert_prospects # Added bulk_upsert_prospects
from app.config import active_config # Import active_config
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory, find_files # Added find_files
from app.utils.logger import logger
from app.utils.scraper_utils import (
    check_url_accessibility,
    download_file,
    save_permanent_copy,
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

            download = download_info.value

            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                # Treasury files are often CSV, but check content type if unsure
                self.logger.warning("Download suggested_filename is empty, using default 'treasury_download.csv'")
                original_filename = "treasury_download.csv"

            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.csv' # Default extension
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")
                
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'treasury'
            final_filename = f"treasury_{timestamp_str}{ext}" 
            final_path = os.path.join(self.download_path, final_filename)
            self.logger.info(f"Original suggested filename: {original_filename}")
            self.logger.info(f"Saving with standardized filename: {final_filename} to {final_path}")
            # --- End modification ---

            # The file is saved by the _handle_download callback in BaseScraper or manually below
            self.logger.info(f"Download triggered. File expected at: {final_path}")

            # Wait a moment for the file system to register the download completely
            time.sleep(5)

            # Verify the file exists and is not empty using the new final_path
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                self.logger.error(f"Verification failed: File not found or empty at {final_path}")
                # Attempt to save manually first
                try:
                    download.save_as(final_path)
                    self.logger.warning(f"Manually saved file to {final_path}")
                    if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                        raise ScraperError(f"Download failed even after manual save: File missing or empty at {final_path}")
                except Exception as save_err:
                    # If save_as failed, try moving from playwright temp path
                    try:
                        fallback_path = download.path()
                        if fallback_path and os.path.exists(fallback_path):
                            shutil.move(fallback_path, final_path)
                            self.logger.warning(f"Manually moved file from {fallback_path} to {final_path}")
                            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                                raise ScraperError(f"Download failed after fallback move: File missing or empty at {final_path}")
                        else:
                            raise ScraperError(f"Download failed: File missing/empty at {final_path}, manual save failed ({save_err}), and Playwright temp path unavailable.")
                    except Exception as move_err:
                        raise ScraperError(f"Download failed: File missing/empty at {final_path}. Manual save failed: {save_err}. Fallback move failed: {move_err}")

            self.logger.info(f"Download verification successful. File path: {final_path}")
            return final_path

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

            # Standardize column names
            df.columns = df.columns.str.strip().str.lower().str.replace(r'\\s+\\(.*?\\)', '', regex=True).str.replace(r'\\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)
            df = df.loc[:, ~df.columns.duplicated()]

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name not in ['loaded_at', 'id', 'source_id']]
            current_cols_normalized = df.columns.tolist()
            unmapped_cols = [col for col in current_cols_normalized if col not in prospect_model_fields]

            if unmapped_cols:
                self.logger.info(f"Found unmapped columns for 'extra' for Treasury: {unmapped_cols}")
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

            # --- ID Generation (adapted from treasury_transform.generate_id) ---
            # Transform used: naics, requirement_title (now Prospect.title), requirement_description (now Prospect.description)
            # Adjusting to use Prospect.naics, Prospect.title, and Prospect.agency for consistency and uniqueness.
            def generate_prospect_id(row: pd.Series) -> str:
                naics_val = str(row.get('naics', ''))
                title_val = str(row.get('title', '')) 
                desc_val = str(row.get('description', '')) # Will be 'None' or empty string
                agency_val = str(row.get('agency', '')) # Adding agency for better uniqueness
                unique_string = f"{naics_val}-{title_val}-{desc_val}-{agency_val}-{self.source_name}"
                return hashlib.md5(unique_string.encode('utf-8')).hexdigest()
            df['id'] = df.apply(generate_prospect_id, axis=1)
            # --- End: ID Generation ---

            final_prospect_columns = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            df_to_insert = df[[col for col in final_prospect_columns if col in df.columns]]

            df_to_insert.dropna(how='all', inplace=True)
            if df_to_insert.empty:
                self.logger.info("After Treasury processing, no valid data rows to insert.")
                return

            self.logger.info(f"Attempting to insert/update {len(df_to_insert)} Treasury records.")
            bulk_upsert_prospects(df_to_insert)
            self.logger.info(f"Successfully inserted/updated Treasury records from {file_path}.")

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

def run_scraper(force=False):
    """
    Run the Treasury Forecast scraper.

    Args:
        force (bool): Whether to force the scraper to run even if it ran recently.

    Returns:
        str: Path to the downloaded file if successful, None otherwise.

    Raises:
        ScraperError: If an error occurs during scraping.
    """
    local_logger = logger
    scraper = None  # Initialize scraper to None
    scraper_success = False
    downloaded_path = None
    source_name = "Treasury Forecast" # Define default source name for logging - updated

    try:
        # Check if we should run based on last download time
        # Removed interval check logic
        # scrape_interval_hours = 24 # Example interval
        # Use the default source_name here as scraper instance doesn't exist yet
        # Removed interval check logic
        # if not force and download_tracker.should_download(source_name, scrape_interval_hours):
        #      local_logger.info(f"Skipping {source_name} scrape due to recent download.")
             # update_scraper_status(source_name, "skipped", "Ran recently") # Optional: Update status
        #      return None # Indicate skipped, not failed

        # Create an instance of the scraper
        scraper = TreasuryScraper(debug_mode=False)
        source_name = scraper.source_name # Update source_name from instance

        # Setup the browser before using the page object
        scraper.setup_browser()

        # Check URL accessibility, bypassing SSL verification for this specific site
        if not check_url_accessibility(active_config.TREASURY_FORECAST_URL, verify_ssl=False):
            error_msg = f"URL {active_config.TREASURY_FORECAST_URL} is not accessible"
            handle_scraper_error(ScraperError(error_msg), source_name)
            raise ScraperError(error_msg)

        local_logger.info(f"Running {source_name} scraper")
        downloaded_path = scraper.scrape() # scrape now returns the path or raises error

        if downloaded_path:
            local_logger.info(f"Scraping successful for {source_name}. File at: {downloaded_path}")
            # update_scraper_status(source_name, "working", None) # Update status to working
            scraper_success = True
        else:
            # This case should ideally be covered by exceptions in scrape()
            local_logger.error(f"{source_name} scrape completed but returned no path.")
            handle_scraper_error(ScraperError("Scraper returned no path"), source_name, "Scraper completed without file path")
            # update_scraper_status(source_name, "failed", "Scraper returned no path")

        return downloaded_path if scraper_success else None

    except ScraperError as e:
        # Use source_name which is set either by default or from scraper instance
        local_logger.error(f"ScraperError in run_scraper for {source_name}: {e}")
        # update_scraper_status(source_name, "failed", str(e)) # Update status to failed
        raise # Re-raise the specific scraper error
    except Exception as e:
        # Use source_name which is set either by default or from scraper instance
        error_msg = f"Unexpected error running {source_name} scraper: {str(e)}"
        local_logger.error(error_msg, exc_info=True)
        handle_scraper_error(e, source_name, "Unexpected error in run_scraper")
        # update_scraper_status(source_name, "failed", error_msg)
        raise ScraperError(error_msg) from e # Wrap in ScraperError
    finally:
        # Ensure cleanup happens even if errors occur
        if scraper:
            try:
                local_logger.info(f"Cleaning up scraper resources for {source_name}")
                scraper.cleanup_browser()
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup for {source_name}: {str(cleanup_error)}", exc_info=True)

if __name__ == "__main__":
    print("Running Treasury scraper directly...")
    try:
        # Example of running with force flag, adjust as needed
        result_path = run_scraper(force=True)
        if result_path:
            print(f"Scraper finished successfully. Downloaded file: {result_path}")
        else:
            print("Scraper run did not result in a downloaded file (skipped or failed). Check logs.")
    except ScraperError as e:
        print(f"Scraper failed with error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc() 