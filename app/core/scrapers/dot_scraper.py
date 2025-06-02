"""Department of Transportation (DOT) Forecast scraper."""

# Standard library imports
import os
# import sys # Unused
import time

# Third-party imports
# import requests # Unused
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
# from playwright.sync_api import sync_playwright # Unused
import pandas as pd
import traceback # Added traceback
# import re # Unused

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect # Added Prospect, DataSource, db
# from app.database.crud import bulk_upsert_prospects # Unused
from app.config import active_config, LOGS_DIR # Import active_config
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory # find_files was unused
from app.utils.logger import logger
from app.utils.scraper_utils import (
    # check_url_accessibility, # Unused
    # download_file, # Unused
    handle_scraper_error
)
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date, split_place # Added parsing utils

# Set up logging
logger = logger.bind(name="scraper.dot_forecast")

class DotScraper(BaseScraper):
    """Scraper for the DOT Forecast site."""

    def __init__(self, debug_mode=False):
        """Initialize the DOT scraper."""
        super().__init__(
            source_name="Department of Transportation",
            base_url=active_config.DOT_FORECAST_URL,
            debug_mode=debug_mode,
            use_stealth=True
        )
        ensure_directory(self.download_path)

    def navigate_to_forecast_page(self):
        """Navigate to the forecast page with retry logic for HTTP/2 protocol errors."""
        self.logger.info(f"Navigating to {self.base_url} (using wait_until='load')")
        
        if not self.page:
            raise ScraperError("Page object is not initialized. Call setup_browser first.")
        
        # Add a small delay before navigation to ensure browser is ready
        time.sleep(2)
        
        # Try multiple approaches to handle HTTP/2 protocol errors and timeouts
        attempts = [
            {'wait_until': 'load', 'timeout': 120000},
            {'wait_until': 'domcontentloaded', 'timeout': 90000}, 
            {'wait_until': 'networkidle', 'timeout': 60000},
            {'wait_until': 'commit', 'timeout': 45000}
        ]
        
        for i, params in enumerate(attempts, 1):
            try:
                self.logger.info(f"Navigation attempt {i}/{len(attempts)} with {params}")
                
                # Add extra delay for subsequent attempts
                if i > 1:
                    delay_time = i * 5
                    self.logger.info(f"Waiting {delay_time} seconds before attempt {i}...")
                    time.sleep(delay_time)
                
                response = self.page.goto(self.base_url, **params)
                
                if response and not response.ok:
                    self.logger.warning(f"Navigation resulted in status {response.status}. URL: {response.url}")
                    if i == len(attempts):  # Last attempt
                        raise ScraperError(f"Navigation failed with status {response.status}")
                    continue
                
                self.logger.info(f"Successfully navigated to {self.base_url} on attempt {i}")
                return True
                
            except PlaywrightTimeoutError as e:
                self.logger.warning(f"Attempt {i} timed out: {str(e)}")
                if i == len(attempts):
                    error_msg = f"All navigation attempts timed out for DOT URL: {self.base_url}"
                    self.logger.error(error_msg)
                    raise ScraperError(error_msg) from e
                # Add progressive delay for timeout retries
                retry_delay = i * 10
                self.logger.info(f"Waiting {retry_delay} seconds before timeout retry...")
                time.sleep(retry_delay)
                continue
                
            except Exception as e:
                error_str = str(e)
                if "ERR_HTTP2_PROTOCOL_ERROR" in error_str:
                    self.logger.warning(f"HTTP/2 protocol error on attempt {i}: {error_str}")
                    if i == len(attempts):
                        error_msg = f"HTTP/2 protocol error persists after all attempts for DOT URL: {self.base_url}"
                        self.logger.error(error_msg)
                        raise ScraperError(error_msg) from e
                    # Add delay before retry
                    self.logger.info(f"Waiting {i * 3} seconds before retry...")
                    time.sleep(i * 3)
                    continue
                elif "ERR_TIMED_OUT" in error_str:
                    self.logger.warning(f"Network timeout error on attempt {i}: {error_str}")
                    if i == len(attempts):
                        error_msg = f"Network timeout error persists after all attempts for DOT URL: {self.base_url}"
                        self.logger.error(error_msg)
                        raise ScraperError(error_msg) from e
                    # Add progressive delay for network timeout retries
                    timeout_delay = i * 15
                    self.logger.info(f"Waiting {timeout_delay} seconds before timeout retry...")
                    time.sleep(timeout_delay)
                    continue
                else:
                    error_msg = f"Unexpected error navigating to DOT URL {self.base_url}: {error_str}"
                    self.logger.error(error_msg, exc_info=True)
                    raise ScraperError(error_msg) from e

    def download_dot_csv(self):
        """
        Download the CSV file from the DOT Forecast site.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        try:
            # Wait for the page to load
            self.logger.info("Waiting for page 'load' state...")
            self.page.wait_for_load_state('load', timeout=90000)
            self.logger.info("Page loaded.")

            # Click the 'Apply' button
            apply_button_selector = "button:has-text('Apply')"
            apply_button = self.page.locator(apply_button_selector)
            apply_button.wait_for(state='visible', timeout=30000)
            self.logger.info("Clicking 'Apply' button...")
            apply_button.click()

            # Explicit wait after clicking Apply
            self.logger.info("Waiting 10 seconds after clicking Apply...")
            time.sleep(10)
            self.logger.info("Wait finished. Proceeding to download.")

            # Locate the 'Download CSV' button/link
            # It might be a link styled as a button
            download_link_selector = "a:has-text('Download CSV')"
            download_link = self.page.locator(download_link_selector)
            download_link.wait_for(state='visible', timeout=60000)
            self.logger.info("'Download CSV' link found.")

            self.logger.info("Clicking 'Download CSV' and waiting for new page and download...")

            # Expect a new page/tab to open and the download to start there
            with self.context.expect_page(timeout=60000) as new_page_info:
                download_link.click() # Click the link that opens the new tab

            new_page = new_page_info.value
            self.logger.info(f"New page opened with URL: {new_page.url}")

            # Set up download handler for the new page
            new_page.on("download", self._handle_download)
            
            # Wait for the download to start on the new page
            # Increased timeout to handle potential server-side preparation
            download_obj = None
            try:
                with new_page.expect_download(timeout=120000) as download_info:
                     self.logger.info("Waiting for download to initiate on the new page...")
                     # Sometimes an action on the new page might be needed, but often just waiting is enough
                     # If the download doesn't start, add a small wait or interaction here.
                     # For now, just rely on the expect_download timeout.
                     pass # Placeholder, let expect_download handle the wait

                download_obj = download_info.value # Access the download object
                self.logger.info("Download detected on new page.")
                
                # Manually handle the download since the event handler might not be triggered
                if not self._last_download_path:
                    self.logger.info("Manual download handling since automatic handler didn't trigger...")
                    self._handle_download(download_obj)
                    
            finally:
                 # Ensure the new page is closed even if download fails
                 if new_page and not new_page.is_closed():
                     self.logger.info("Closing the download initiation page.")
                     new_page.close()

            # Wait a brief moment for the download event to be processed by the callback
            self.page.wait_for_timeout(2000) # Brief wait for file system operations

            if not self._last_download_path or not os.path.exists(self._last_download_path):
                self.logger.error(f"BaseScraper._last_download_path not set or invalid. Value: {self._last_download_path}")
                # Fallback: Try to save from the download object directly
                if download_obj:
                    try:
                        temp_playwright_path = download_obj.path()
                        self.logger.info(f"Attempting to copy from Playwright temp path: {temp_playwright_path}")
                        
                        # Generate our own filename
                        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                        final_filename = f"department_of_transportation_{timestamp_str}.csv"
                        final_save_path = os.path.join(self.download_path, final_filename)
                        
                        # Copy the file manually
                        import shutil
                        shutil.copy2(temp_playwright_path, final_save_path)
                        self._last_download_path = final_save_path
                        self.logger.info(f"Successfully copied download to: {final_save_path}")
                        
                    except Exception as copy_err:
                        self.logger.error(f"Failed to copy download manually: {copy_err}")
                        raise ScraperError("Download failed: File not found or path not set by BaseScraper._handle_download.")
                else:
                    raise ScraperError("Download failed: File not found or path not set by BaseScraper._handle_download.")

            self.logger.info(f"Download process completed. File saved at: {self._last_download_path}")
            return self._last_download_path

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout error during DOT CSV download process: {str(e)}")
            screenshot_path = os.path.join(LOGS_DIR, f"dot_timeout_error_{int(time.time())}.png")
            try:
                if self.page and not self.page.is_closed():
                    self.page.screenshot(path=screenshot_path, full_page=True)
                    self.logger.info(f"Screenshot saved to {screenshot_path}")
                else:
                    self.logger.warning("Could not take screenshot, page was closed or not available.")
            except Exception as ss_err:
                self.logger.error(f"Failed to save screenshot: {ss_err}")
            handle_scraper_error(e, self.source_name, "Timeout error during download")
            raise ScraperError(f"Timeout error during download: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error downloading DOT CSV data: {str(e)}", exc_info=True)
            handle_scraper_error(e, self.source_name, "Error downloading DOT CSV data")
            raise ScraperError(f"Error downloading DOT CSV data: {str(e)}")

    def scrape(self):
        """
        Run the scraper to navigate, apply filter, and download the file.
        """
        # Use the structured scrape method from the base class
        return self.scrape_with_structure(
            setup_func=self.navigate_to_forecast_page, # Setup navigates to the page
            extract_func=self.download_dot_csv,       # Extract downloads the CSV
            process_func=self.process_func           # Process handles the data
        )

    def process_func(self, file_path: str):
        """
        Process the downloaded CSV file, transform data to Prospect objects, 
        and insert into the database using logic adapted from dot_transform.py.
        """
        self.logger.info(f"Processing downloaded CSV file: {file_path}")
        try:
            df = pd.read_csv(file_path, header=0, on_bad_lines='skip')
            df.dropna(how='all', inplace=True) # Pre-processing from transform script
            self.logger.info(f"Loaded {len(df)} rows from {file_path} after initial dropna.")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from dot_transform.normalize_columns_dot ---
            rename_map = {
                'Sequence Number': 'native_id',
                'Procurement Office': 'agency', # To Prospect.agency
                'Project Title': 'title',
                'Description': 'description',
                'Estimated Value': 'estimated_value_raw',
                'NAICS': 'naics',
                'Competition Type': 'set_aside',
                'RFP Quarter': 'solicitation_qtr_raw',
                'Anticipated Award Date': 'award_date_raw',
                'Place of Performance': 'place_raw',
                # For 'extra'
                'Action/Award Type': 'action_award_type',
                'Contract Vehicle': 'contract_vehicle'
            }
            rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=rename_map_existing, inplace=True)

            # Place of Performance
            if 'place_raw' in df.columns:
                split_places_data = df['place_raw'].apply(split_place)
                df['place_city'] = split_places_data.apply(lambda x: x[0])
                df['place_state'] = split_places_data.apply(lambda x: x[1])
                df['place_country'] = 'USA' # Default from transform
            else:
                df['place_city'], df['place_state'], df['place_country'] = pd.NA, pd.NA, 'USA'

            # Estimated Value
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            else:
                df['estimated_value'], df['est_value_unit'] = pd.NA, pd.NA

            # Solicitation Date (Prospect.release_date) from RFP Quarter
            if 'solicitation_qtr_raw' in df.columns:
                # fiscal_quarter_to_date returns (timestamp, fiscal_year)
                parsed_sol_info = df['solicitation_qtr_raw'].apply(fiscal_quarter_to_date)
                df['release_date'] = parsed_sol_info.apply(lambda x: x[0].date() if pd.notna(x[0]) else None)
                # df['solicitation_fiscal_year'] = parsed_sol_info.apply(lambda x: x[1]) # Not in Prospect model
            else:
                df['release_date'] = None

            # Award Date and Fiscal Year
            if 'award_date_raw' in df.columns:
                # Try multiple date formats to avoid pandas warning
                date_formats = ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']
                df['award_date'] = None
                df['award_fiscal_year'] = pd.NA
                
                for fmt in date_formats:
                    try:
                        parsed_dates = pd.to_datetime(df['award_date_raw'], format=fmt, errors='coerce')
                        valid_mask = parsed_dates.notna()
                        if valid_mask.any():
                            df.loc[valid_mask, 'award_date'] = parsed_dates[valid_mask].dt.date
                            df.loc[valid_mask, 'award_fiscal_year'] = parsed_dates[valid_mask].dt.year.astype('Int64')
                            break
                    except:
                        continue
                
                # Fallback to flexible parsing if no format worked
                if df['award_date'].isna().all():
                    with pd.option_context('mode.chained_assignment', None):
                        parsed_dates = pd.to_datetime(df['award_date_raw'], errors='coerce', infer_datetime_format=True)
                        valid_mask = parsed_dates.notna()
                        if valid_mask.any():
                            df.loc[valid_mask, 'award_date'] = parsed_dates[valid_mask].dt.date
                            df.loc[valid_mask, 'award_fiscal_year'] = parsed_dates[valid_mask].dt.year.astype('Int64')
            else:
                df['award_date'] = None
                df['award_fiscal_year'] = pd.NA
            
            if 'award_fiscal_year' in df.columns:
                 df['award_fiscal_year'] = df['award_fiscal_year'].astype('Int64')

            # Contract Type (Missing from direct mapping in transform, but Prospect has it)
            # Check if 'action_award_type' or 'contract_vehicle' can serve as contract_type or if it needs to be NA
            if 'action_award_type' in df.columns and 'contract_type' not in df.columns:
                 self.logger.info("Using 'action_award_type' for 'contract_type' for DOT as fallback.")
                 df['contract_type'] = df['action_award_type']
            elif 'contract_type' not in df.columns:
                 df['contract_type'] = pd.NA

            cols_to_drop = ['place_raw', 'estimated_value_raw', 'solicitation_qtr_raw', 'award_date_raw']
            df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore', inplace=True)
            # --- End: Logic adapted from dot_transform.normalize_columns_dot ---
            
            # Define the final column rename map.
            final_column_rename_map = {
                'native_id': 'native_id',
                'agency': 'agency',
                'title': 'title',
                'description': 'description',
                'naics': 'naics',
                'set_aside': 'set_aside',
                'release_date': 'release_date',
                'award_date': 'award_date',
                'award_fiscal_year': 'award_fiscal_year',
                'place_city': 'place_city',
                'place_state': 'place_state',
                'place_country': 'place_country',
                'estimated_value': 'estimated_value',
                'est_value_unit': 'est_value_unit',
                'contract_type': 'contract_type',
                # Fields intended for 'extra' should have their current names in df as keys
                'action_award_type': 'action_award_type', 
                'contract_vehicle': 'contract_vehicle'
            }

            # Ensure all columns in final_column_rename_map exist in df.
            for col_name in final_column_rename_map.keys():
                if col_name not in df.columns:
                    df[col_name] = pd.NA
            
            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            # Original ID generation: unique_string = f"{naics_val}-{title_val}-{desc_val}-{self.source_name}"
            # These correspond to 'naics', 'title', 'description' in the df after initial renaming.
            # Include native_id and location to ensure uniqueness
            fields_for_id_hash = ['native_id', 'naics', 'title', 'description', 'place_city', 'place_state']

            return self._process_and_load_data(df, final_column_rename_map, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"DOT CSV file not found: {file_path}")
            raise ScraperError(f"Processing failed: DOT CSV file not found: {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty DOT CSV file: {file_path}")
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during DOT CSV processing: {e}.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing DOT file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing DOT file {file_path}: {str(e)}")