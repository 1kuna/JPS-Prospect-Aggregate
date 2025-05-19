"""Acquisition Gateway scraper."""

# Standard library imports
import os
import sys
import time
import datetime
import traceback
import shutil

# --- Start temporary path adjustment for direct execution ---
# Calculate the path to the project root directory (JPS-Prospect-Aggregate)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
# Add the project root to the Python path if it's not already there
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# --- End temporary path adjustment ---

# Third-party imports
import requests
import pandas as pd # Add pandas
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from playwright_stealth import stealth_sync
import traceback # Add traceback

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, ScraperStatus, DataSource, db
from app.config import LOGS_DIR, RAW_DATA_DIR, ACQUISITION_GATEWAY_URL, PAGE_NAVIGATION_TIMEOUT
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory
from app.utils.logger import logger
from app.utils.scraper_utils import handle_scraper_error
from app.database.crud import bulk_upsert_prospects # Add bulk_upsert_prospects
import hashlib # Add hashlib

# Set up logging
logger = logger.bind(name="scraper.acquisition_gateway")

def check_url_accessibility(url=None):
    """
    Check if a URL is accessible.
    
    Args:
        url (str, optional): URL to check. If None, uses ACQUISITION_GATEWAY_URL
        
    Returns:
        bool: True if the URL is accessible, False otherwise
    """
    url = url or ACQUISITION_GATEWAY_URL
    logger.info(f"Checking accessibility of {url}")
    
    try:
        # Set a reasonable timeout
        response = requests.head(url, timeout=10)
        
        # Check if the response is successful
        if response.status_code < 400:
            logger.info(f"URL {url} is accessible (status code: {response.status_code})")
            return True
        else:
            logger.error(f"URL {url} returned status code {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking URL {url}: {str(e)}")
        return False

class AcquisitionGatewayScraper(BaseScraper):
    """Scraper for the Acquisition Gateway site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the Acquisition Gateway scraper."""
        super().__init__(
            source_name="Acquisition Gateway",
            base_url=ACQUISITION_GATEWAY_URL,
            debug_mode=debug_mode
        )
    
    def navigate_to_forecast_page(self):
        """Navigate to the forecast page."""
        return self.navigate_to_url()
    
    def download_csv_file(self):
        """
        Download the CSV file from the Acquisition Gateway site.
        Saves the file directly to the scraper's download directory.
        
        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        try:
            # Wait for the page to load using 'load' state
            self.logger.info("Waiting for page to load ('load')...")
            self.page.wait_for_load_state('load', timeout=90000) # Changed to 'load', kept long timeout
            
            # Explicit wait after load
            self.logger.info("Waiting 5 seconds after load for page to settle...") # Reduced wait back to 5s
            self.page.wait_for_timeout(5000) # Reduced wait back to 5s
            self.logger.info("Wait finished. Locating Export button.")
            
            # --- Debug Screenshot After Wait REMOVED ---
            # debug_timestamp_after_wait = ...
            # screenshot_path_after_wait = ...
            # try:
            # ...
            # except ...
            # --- End Debug Screenshot After Wait REMOVED ---
            
            # Find export button using ID
            export_button_selector = 'button#export-0' 
            export_button = self.page.locator(export_button_selector)
            
            # Wait for the button to be VISIBLE in the DOM
            try:
                export_button.wait_for(state='visible', timeout=60000) # Changed state back to 'visible'
                self.logger.info("Export button is visible.")
            except PlaywrightTimeoutError as wait_error:
                self.logger.error(f"Timeout waiting for export button ({export_button_selector}) to be visible.") # Updated log message
                # --- Debug Output REMOVED ---
                # debug_timestamp = ...
                # screenshot_path = ...
                # html_path = ...
                # try:
                # ...
                # except ...
                # --- End Debug Output REMOVED ---
                raise ScraperError(f"Timeout waiting for export button {export_button_selector} to become visible") from wait_error # Updated error message
            
            self.logger.info("Attempting to click Export CSV and waiting for download...")
            
            # Start waiting for the download BEFORE clicking
            with self.page.expect_download(timeout=120000) as download_info: # Increased timeout
                # Try standard click first, then JS click fallback
                try:
                    self.logger.info("Attempting standard click...")
                    export_button.click(timeout=15000) # Shorter timeout for the click itself
                    self.logger.info("Standard click successful.")
                except PlaywrightTimeoutError:
                    self.logger.warning("Standard click timed out or failed, trying JavaScript click.")
                    # Evaluate JS to click the first matching element
                    self.page.evaluate(f"document.querySelector('{export_button_selector}').click();")
                    self.logger.info("JavaScript click executed.")
                except Exception as click_err:
                    self.logger.error(f"Error during button click attempt: {click_err}")
                    raise # Re-raise other click errors
            
            # Download object is available here
            download = download_info.value
            self.logger.info(f"Download started: {download.suggested_filename}")
            
            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'acqgateway_download.csv'")
                original_filename = "acqgateway_download.csv"
                
            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.csv' # Default extension
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")
                
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'acqgateway'
            final_filename = f"acqgateway_{timestamp_str}{ext}" 
            final_path = os.path.join(self.download_path, final_filename)
            self.logger.info(f"Download suggested filename: {original_filename}")
            self.logger.info(f"Saving with standardized filename: {final_filename}")
            # --- End modification ---

            # Use the new final_path for saving and verification
            # Playwright's download handler in BaseScraper might need adjustment if it saves before returning here.
            # Assuming the current logic relies on moving/verifying *after* this point.

            self.logger.info(f"Download complete. File expected at: {final_path}")

            # Verify the file exists (saved by _handle_download or playwright) using the new path
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                self.logger.error(f"Verification failed: File not found or empty at {final_path}")
                # Attempt to save manually as fallback (using original playwright path)
                try:
                    # Save the download to the *new* final_path
                    download.save_as(final_path)
                    self.logger.warning(f"Manually saved file to {final_path}")
                    if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                         raise ScraperError(f"Download failed even after manual save: File missing or empty at {final_path}")
                except Exception as save_err:
                    # Try moving if save_as fails (e.g., if BaseScraper saved it somewhere else)
                    try:
                        fallback_path = download.path() # Playwright's temporary path
                        shutil.move(fallback_path, final_path)
                        self.logger.warning(f"Manually moved file from {fallback_path} to {final_path}")
                        if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                            raise ScraperError(f"Download failed after fallback move: File missing or empty at {final_path}")
                    except Exception as move_err:
                        raise ScraperError(f"Download failed: File missing/empty at {final_path}. Manual save failed: {save_err}. Fallback move failed: {move_err}")

            # Return the path within the scraper's download directory
            return final_path

        except PlaywrightTimeoutError as e:
            handle_scraper_error(e, self.source_name, "Timeout error during download")
            raise ScraperError(f"Timeout error during download: {str(e)}")
        except Exception as e:
            handle_scraper_error(e, self.source_name, "Error downloading CSV")
            raise ScraperError(f"Error downloading CSV: {str(e)}")
    
    def process_func(self, file_path: str):
        """
        Process the downloaded CSV file, transform data to Prospect objects, 
        and insert into the database using logic adapted from acqg_transform.py.
        """
        self.logger.info(f"Processing downloaded CSV file: {file_path}")
        try:
            df = pd.read_csv(file_path, header=0, on_bad_lines='skip')
            self.logger.info(f"Loaded {len(df)} rows from {file_path}")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from acqg_transform.normalize_columns ---
            rename_map = {
                # Raw Name from AcqG CSV : Prospect Model Field Name
                'Listing ID': 'native_id',
                'Title': 'title',
                'Body': 'description', # Prioritizing Body
                'NAICS Code': 'naics',
                'Estimated Contract Value': 'estimated_value',
                'Estimated Solicitation Date': 'release_date', # Maps to Prospect.release_date
                'Ultimate Completion Date': 'award_date_raw',    # Raw, to be parsed to Prospect.award_date
                'Estimated Award FY': 'award_fiscal_year',
                'Organization': 'agency', # Maps to Prospect.agency
                'Place of Performance City': 'place_city',
                'Place of Performance State': 'place_state',
                'Place of Performance Country': 'place_country',
                'Contract Type': 'contract_type',
                'Set Aside Type': 'set_aside'
                # 'Summary' is a fallback for 'description' if 'Body' isn't present
            }
            
            # Rename only columns that exist in the input DataFrame
            rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=rename_map_existing, inplace=True)

            # Fallback for description
            if 'description' not in df.columns and 'Summary' in df.columns:
                df.rename(columns={'Summary': 'description'}, inplace=True)

            # Date Parsing
            if 'release_date' in df.columns:
                df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce').dt.date
            else:
                df['release_date'] = None
            
            if 'award_date_raw' in df.columns:
                df['award_date'] = pd.to_datetime(df['award_date_raw'], errors='coerce').dt.date
            else:
                df['award_date'] = None # Ensure column exists if raw version wasn't there

            # Fiscal Year Parsing/Extraction
            if 'award_fiscal_year' in df.columns:
                df['award_fiscal_year'] = pd.to_numeric(df['award_fiscal_year'], errors='coerce')
                if 'award_date' in df.columns: # Fallback for NA fiscal years if award_date is present
                    fallback_mask = df['award_fiscal_year'].isna() & df['award_date'].notna()
                    df.loc[fallback_mask, 'award_fiscal_year'] = df.loc[fallback_mask, 'award_date'].dt.year
            elif 'award_date' in df.columns and df['award_date'].notna().any(): # Only award_date available
                self.logger.warning("'Estimated Award FY' not in source, extracting year from 'Ultimate Completion Date' as fallback for award_fiscal_year.")
                df['award_fiscal_year'] = df['award_date'].dt.year
            else:
                df['award_fiscal_year'] = pd.NA
            
            if 'award_fiscal_year' in df.columns: # Ensure correct type
                df['award_fiscal_year'] = df['award_fiscal_year'].astype('Int64')

            # Estimated Value Parsing
            if 'estimated_value' in df.columns:
                df['estimated_value'] = pd.to_numeric(df['estimated_value'], errors='coerce')
                df['est_value_unit'] = None # AcqG source doesn't seem to have separate units
            else:
                df['estimated_value'] = pd.NA
                df['est_value_unit'] = pd.NA
            # --- End: Logic adapted from acqg_transform.normalize_columns ---

            # Normalize all column names AFTER explicit renaming (lowercase, snake_case)
            # This step is from the original transform script, may not be strictly necessary if mapping directly to Prospect fields
            # but retained for consistency with original transform script's approach to finding 'extra' fields.
            df.columns = df.columns.str.strip().str.lower().str.replace(r'\\s+\\(\\w+\\)', '', regex=True).str.replace(r'\\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)
            df = df.loc[:, ~df.columns.duplicated()] # Remove duplicates after normalization

            # Define Prospect model columns (excluding 'loaded_at' and 'id' initially)
            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name not in ['loaded_at', 'id', 'source_id']]
            
            # Handle 'extra' column for unmapped fields
            current_cols_normalized = df.columns.tolist()
            # Identify unmapped columns based on normalized names not being in prospect_model_fields (after our renaming)
            # The rename_map already targets Prospect model names (or intermediate like award_date_raw)
            # So, we look for columns in df that aren't Prospect fields.
            unmapped_cols = [col for col in current_cols_normalized if col not in prospect_model_fields and col not in ['award_date_raw']] # award_date_raw is intermediate

            if unmapped_cols:
                self.logger.info(f"Found unmapped columns to be included in 'extra': {unmapped_cols}")
                # Create 'extra' from the original DataFrame *before* dropping these columns to preserve original values if needed.
                # This is tricky if names were changed significantly by normalization. Assuming we use the current df state.
                df['extra'] = df[unmapped_cols].to_dict(orient='records')
                # df = df.drop(columns=unmapped_cols) # Not strictly needed if we select only prospect_columns later
            else:
                df['extra'] = None
            
            # Ensure all Prospect model columns exist, fill with None/NA if not
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
            
            # --- Start: ID Generation (adapted from acqg_transform.generate_id) ---
            def generate_prospect_id(row: pd.Series) -> str:
                # Use Prospect field names (which should be columns in df now)
                naics_val = str(row.get('naics', ''))
                title_val = str(row.get('title', ''))
                desc_val = str(row.get('description', ''))
                # Include source_name for uniqueness across different scrapers if native_id is not globally unique
                # However, AcqG's Listing ID (native_id) should be unique for AcqG.
                # The original transform script's ID logic didn't use native_id. Let's stick to title/desc/naics for now for consistency with that.
                unique_string = f"{naics_val}-{title_val}-{desc_val}-{self.source_name}" # Added source_name for cross-source safety
                return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

            df['id'] = df.apply(generate_prospect_id, axis=1)
            # --- End: ID Generation ---

            # Select only columns that exist in the Prospect model for upsert
            final_prospect_columns = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at'] # loaded_at is auto
            df_to_insert = df[[col for col in final_prospect_columns if col in df.columns]]

            # Ensure no completely empty rows are attempted for insertion
            df_to_insert.dropna(how='all', inplace=True)

            if df_to_insert.empty:
                self.logger.info("After processing, no valid data rows to insert.")
                return

            self.logger.info(f"Attempting to insert/update {len(df_to_insert)} records for {self.source_name}.")
            bulk_upsert_prospects(df_to_insert)
            self.logger.info(f"Successfully inserted/updated records for {self.source_name} from {file_path}.")

        except FileNotFoundError:
            self.logger.error(f"CSV file not found at {file_path}")
            raise ScraperError(f"Processing failed: CSV file not found at {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty CSV file at {file_path}")
            # No ScraperError here, just log and return, as it's not a processing failure but empty source data.
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during CSV processing: {e}. This might indicate a change in the CSV format or an issue with mappings.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing file {file_path}: {str(e)}")
    
    def scrape(self):
        """
        Run the scraper to download the file.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        # Simplified call: only setup and extract
        return self.scrape_with_structure(
            setup_func=self.navigate_to_forecast_page,
            extract_func=self.download_csv_file,
            process_func=self.process_func # Add process_func
        )

def check_last_download():
    """
    Check when the last download was performed.
    
    Returns:
        bool: True if a download was performed in the last 24 hours, False otherwise
    """
    # Use the scraper logger
    logger = logger.bind(name="scraper.acquisition_gateway")
    
    try:
        # Check if we should download using the download tracker
        # Removed interval check logic
        # scrape_interval_hours = 24  # Default to 24 hours

        # Removed interval check logic
        # if download_tracker.should_download("Acquisition Gateway", scrape_interval_hours):
        #     logger.info("No recent download found, proceeding with scrape")
        #     return False
        # else:
        #     logger.info(f"Recent download found (within {scrape_interval_hours} hours), skipping scrape")
        #     return True
        # Assume we always want to proceed if called directly, or scheduler handles frequency
        logger.info("Timestamp check logic removed, proceeding with scrape check...")
        return False # Return False to indicate scrape should proceed
    except Exception as e:
        logger.error(f"Error during removed check_last_download logic: {str(e)}")
        return False # Return False to indicate scrape should proceed on error

def run_scraper():
    """
    Run the Acquisition Gateway scraper.
    
    Returns:
        bool: True if scraping was successful, False otherwise
    """
    # Use a local logger from the module-level logger
    local_logger = logger 
    scraper = None
    playwright = None # Add playwright instance for custom setup
    downloaded_path = None
    scraper_success = False
    source_name = "Acquisition Gateway" # Define default source name

    try:
        # Check if we should run the scraper (Timestamp logic removed previously)
        # if not force and check_last_download():
        #     local_logger.info("Skipping scrape due to recent download")
        #     return True

        # Create an instance of the scraper
        scraper = AcquisitionGatewayScraper(debug_mode=False) # debug_mode doesn't control headless here
        source_name = scraper.source_name # Update from instance if needed

        # --- Start Custom Browser Setup for Acquisition Gateway (using Chromium) --- 
        try:
            local_logger.info("Starting custom browser setup for Acq Gateway using Chromium (Headed Mode)...") # Updated log
            playwright = sync_playwright().start()
            scraper.playwright = playwright # Store playwright instance on scraper for cleanup
            
            # Common Chrome User Agent
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36" # Example Chrome UA
            local_logger.info(f"Launching Chromium HEADED with User-Agent: {user_agent}") # Updated log

            # Define Chromium launch arguments for anti-detection
            launch_args = [
                '--disable-blink-features=AutomationControlled'
            ]

            # Launch Chromium browser in HEADED mode with arguments
            scraper.browser = playwright.chromium.launch(
                headless=True, # Set back to headless mode
                args=launch_args # Apply anti-detection arguments
            )
            
            # Create new context with specific user agent and accepting downloads
            scraper.context = scraper.browser.new_context(
                user_agent=user_agent,
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080}
            )
            # Create new page
            scraper.page = scraper.context.new_page()
            
            # --- Apply Stealth Patches --- 
            local_logger.info("Applying playwright-stealth patches...")
            stealth_sync(scraper.page)
            local_logger.info("Stealth patches applied.")
            # --- End Stealth Patches ---
            
            # Re-attach download handler to the new page
            scraper.page.on("download", scraper._handle_download)
             # Re-set default timeout for the page
            scraper.page.set_default_timeout(60000) 
            local_logger.info("Custom Chromium browser setup complete.")

        except Exception as browser_setup_err:
            local_logger.error(f"Failed custom browser setup: {browser_setup_err}", exc_info=True)
            raise ScraperError(f"Failed custom browser setup: {browser_setup_err}") from browser_setup_err
        # --- End Custom Browser Setup --- 
        
        # Check if the URL is accessible (this uses requests, less likely to be blocked)
        if not check_url_accessibility(ACQUISITION_GATEWAY_URL):
            error_msg = f"URL {ACQUISITION_GATEWAY_URL} is not accessible"
            handle_scraper_error(ScraperError(error_msg), source_name)
            raise ScraperError(error_msg)
        
        # Run the scraper steps directly using the custom browser setup
        local_logger.info(f"Running {source_name} scraper steps")
        
        # --- Multi-step Navigation REMOVED ---
        # 1. Navigate to base domain first
        # base_domain = "https://acquisitiongateway.gov"
        # local_logger.info(f"Navigating to base domain: {base_domain}")
        # scraper.navigate_to_url(base_domain) 
        # local_logger.info("Adding a short pause after navigating to base domain...")
        # time.sleep(2) # Short pause
        # 
        # 2. Navigate to the specific forecast page
        # local_logger.info(f"Navigating to forecast page: {ACQUISITION_GATEWAY_URL}")
        # scraper.navigate_to_url(ACQUISITION_GATEWAY_URL) # Use the full forecast URL
        # --- End Multi-step Navigation REMOVED ---
        
        # Navigate directly to the forecast page
        scraper.navigate_to_forecast_page() # Restore direct navigation
        downloaded_path = scraper.download_csv_file() # Then download
        
        # Check if download was successful
        if downloaded_path:
            local_logger.info(f"Scraping successful for {source_name}. File at: {downloaded_path}")
            scraper_success = True
            # Update the ScraperStatus table (commented out)
            # update_scraper_status(source_name, "working", None)
        else:
            # This case might occur if download_csv_file returns None without an exception
            error_msg = "Download function completed but did not return a file path."
            local_logger.error(f"{source_name}: {error_msg}")
            handle_scraper_error(ScraperError(error_msg), source_name, error_msg)
            # update_scraper_status(source_name, "failed", error_msg)
            
        # Return path if successful, None otherwise    
        return downloaded_path if scraper_success else None

    except ImportError as e:
        error_msg = f"Import error: {str(e)}"
        local_logger.error(error_msg)
        # Ensure Playwright installation instructions are clear
        if "playwright" in error_msg.lower():
            local_logger.error("Playwright module not found. Please install it with 'pip install playwright' and run 'playwright install'")
        handle_scraper_error(e, source_name, "Import error")
        raise ScraperError(error_msg) from e # Re-raise as ScraperError
    except ScraperError as e:
        # Log specific scraper errors (already logged deeper)
        local_logger.error(f"ScraperError in run_scraper for {source_name}: {e}")
        # update_scraper_status(source_name, "failed", str(e)) # Update status
        raise # Re-raise the specific scraper error
    except Exception as e:
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
                # Use the base cleanup which should handle the custom setup attributes
                scraper.cleanup_browser() 
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup for {source_name}: {str(cleanup_error)}", exc_info=True)
        # Fallback cleanup if playwright was started but scraper cleanup failed
        elif playwright:
             try:
                  local_logger.warning("Cleaning up Playwright instance directly (fallback)." )
                  playwright.stop()
             except Exception as pw_cleanup_error:
                 local_logger.error(f"Error during fallback playwright cleanup: {pw_cleanup_error}")

if __name__ == "__main__":
    # This block allows the script to be run directly for testing
    print("Running Acquisition Gateway scraper directly...") # Updated print message
    try:
        # Example of running with force flag, adjust as needed
        result_path = run_scraper()
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