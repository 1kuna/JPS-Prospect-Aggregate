"""Department of Transportation (DOT) Forecast scraper."""

# Standard library imports
import os
import sys
import time
import shutil
import datetime # Added datetime import

# --- Start temporary path adjustment for direct execution ---
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# --- End temporary path adjustment ---

# Third-party imports
import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
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
from app.config import LOGS_DIR, RAW_DATA_DIR, DOT_FORECAST_URL, PAGE_NAVIGATION_TIMEOUT # Use RAW_DATA_DIR
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory, find_files
from app.utils.logger import logger
from app.utils.scraper_utils import (
    check_url_accessibility,
    download_file,
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
            source_name="DOT Forecast", # Changed source name
            base_url=DOT_FORECAST_URL,
            debug_mode=debug_mode
        )
        ensure_directory(self.download_path)

    def navigate_to_forecast_page(self):
        """Navigate to the forecast page, overriding wait_until state."""
        self.logger.info(f"Navigating to {self.base_url} (using wait_until='load')")
        try:
            if not self.page:
                raise ScraperError("Page object is not initialized. Call setup_browser first.")
            # Override the default wait_until state specifically for this scraper
            response = self.page.goto(self.base_url, timeout=90000, wait_until='load') # Use 90s timeout and 'load' state
            if response and not response.ok:
                 self.logger.warning(f"Navigation to {self.base_url} resulted in status {response.status}. URL: {response.url}")
                 # Potentially raise error here if needed
            return True
        except PlaywrightTimeoutError as e:
            error_msg = f"Timeout navigating to DOT URL: {self.base_url}: {str(e)}"
            self.logger.error(error_msg)
            raise ScraperError(error_msg) from e
        except Exception as e:
            error_msg = f"Error navigating to DOT URL {self.base_url}: {str(e)}"
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

            # Wait for the download to start on the new page
            # Increased timeout to handle potential server-side preparation
            try:
                with new_page.expect_download(timeout=120000) as download_info:
                     self.logger.info("Waiting for download to initiate on the new page...")
                     # Sometimes an action on the new page might be needed, but often just waiting is enough
                     # If the download doesn't start, add a small wait or interaction here.
                     # For now, just rely on the expect_download timeout.
                     pass # Placeholder, let expect_download handle the wait

                download = download_info.value
                self.logger.info("Download detected on new page.")
            finally:
                 # Ensure the new page is closed even if download fails
                 if new_page and not new_page.is_closed():
                     self.logger.info("Closing the download initiation page.")
                     new_page.close()

            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'dot_download.csv'")
                original_filename = "dot_download.csv"

            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.csv' # Default extension
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'dot'
            final_filename = f"dot_{timestamp_str}{ext}"
            final_path = os.path.join(self.download_path, final_filename)
            self.logger.info(f"Original suggested filename: {original_filename}")
            self.logger.info(f"Saving with standardized filename: {final_filename} to {final_path}")
            # --- End modification ---

            # The file is saved by the _handle_download callback in BaseScraper or manually below
            self.logger.info(f"Download triggered. File expected at: {final_path}")

            # Wait a moment for the file system (allow _handle_download time)
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
                df['award_date'] = pd.to_datetime(df['award_date_raw'], errors='coerce').dt.date
                df['award_fiscal_year'] = pd.to_datetime(df['award_date_raw'], errors='coerce').dt.year.astype('Int64') # Get year from original raw string
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
            
            df.columns = df.columns.str.strip().str.lower().str.replace(r'\\s+\\(.*?\\)', '', regex=True).str.replace(r'\\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)
            df = df.loc[:, ~df.columns.duplicated()]

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name not in ['loaded_at', 'id', 'source_id']]
            current_cols_normalized = df.columns.tolist()
            unmapped_cols = [col for col in current_cols_normalized if col not in prospect_model_fields]

            if unmapped_cols:
                self.logger.info(f"Found unmapped columns for 'extra' for DOT: {unmapped_cols}")
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
                self.logger.info("After DOT processing, no valid data rows to insert.")
                return

            self.logger.info(f"Attempting to insert/update {len(df_to_insert)} DOT records.")
            bulk_upsert_prospects(df_to_insert)
            self.logger.info(f"Successfully inserted/updated DOT records from {file_path}.")

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

def run_scraper(force=False):
    """
    Run the DOT Forecast scraper.
    """
    local_logger = logger
    scraper = None
    playwright = None # Add playwright instance variable for cleanup
    scraper_success = False
    downloaded_path = None
    source_name = "DOT Forecast" # Default source name - updated

    try:
        # Initialize scraper instance but don't call base setup_browser yet
        scraper = DotScraper(debug_mode=False)
        source_name = scraper.source_name

        # --- Start Custom Browser Setup for DOT (using Firefox) --- 
        try:
            local_logger.info("Starting custom browser setup for DOT using Firefox...")
            playwright = sync_playwright().start()
            scraper.playwright = playwright # Store playwright instance on scraper for cleanup
            
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0" # Firefox User Agent
            local_logger.info(f"Launching Firefox with User-Agent: {user_agent}")

            # Launch Firefox browser
            scraper.browser = playwright.firefox.launch(
                headless=not scraper.debug_mode
            )
            
            # Create new context with specific user agent and ignoring HTTPS errors
            scraper.context = scraper.browser.new_context(
                user_agent=user_agent,
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True 
            )
            # Create new page
            scraper.page = scraper.context.new_page()
            # Re-attach download handler
            scraper.page.on("download", scraper._handle_download)
             # Re-set default timeout
            scraper.page.set_default_timeout(60000) 
            local_logger.info("Custom Firefox browser setup complete.")

        except Exception as browser_setup_err:
            local_logger.error(f"Failed custom browser setup: {browser_setup_err}", exc_info=True)
            raise ScraperError(f"Failed custom browser setup: {browser_setup_err}") from browser_setup_err
        # --- End Custom Browser Setup --- 

        # Check URL accessibility (start with verify_ssl=True)
        # We might need to adjust this check if it also fails, but try first
        if not check_url_accessibility(DOT_FORECAST_URL, verify_ssl=True):
            error_msg = f"URL {DOT_FORECAST_URL} is not accessible"
            handle_scraper_error(ScraperError(error_msg), source_name)
            raise ScraperError(error_msg)

        local_logger.info(f"Running {source_name} scraper")
        downloaded_path = scraper.scrape() # scrape method uses the page created above

        if downloaded_path:
            local_logger.info(f"Scraping successful for {source_name}. File at: {downloaded_path}")
            scraper_success = True
        else:
            local_logger.error(f"{source_name} scrape completed but returned no path.")
            handle_scraper_error(ScraperError("Scraper returned no path"), source_name, "Scraper completed without file path")

        return downloaded_path if scraper_success else None

    except ScraperError as e:
        local_logger.error(f"ScraperError in run_scraper for {source_name}: {e}")
        raise
    except Exception as e:
        error_msg = f"Unexpected error running {source_name} scraper: {str(e)}"
        local_logger.error(error_msg, exc_info=True)
        handle_scraper_error(e, source_name, "Unexpected error in run_scraper")
        raise ScraperError(error_msg) from e
    finally:
        # Ensure cleanup happens even if errors occur
        if scraper:
            try:
                # Use the cleanup method from BaseScraper which handles context, page, browser, playwright
                local_logger.info(f"Cleaning up scraper resources for {source_name}")
                scraper.cleanup_browser() # This should now close the custom browser/playwright instance
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup for {source_name}: {str(cleanup_error)}", exc_info=True)
        # Fallback cleanup if scraper object exists but playwright wasn't assigned (shouldn't happen)
        elif playwright:
             try:
                  local_logger.warning("Cleaning up Playwright instance directly (fallback)." )
                  playwright.stop()
             except Exception as pw_cleanup_error:
                 local_logger.error(f"Error during fallback playwright cleanup: {pw_cleanup_error}")

if __name__ == "__main__":
    print("Running DOT scraper directly...")
    try:
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