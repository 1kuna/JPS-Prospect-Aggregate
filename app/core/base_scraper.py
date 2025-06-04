"""
Base scraper class with common functionality for all scrapers.

This module provides a foundation for all web scrapers in the application,
with common functionality for browser management, logging, error handling,
and data processing.
"""

# Standard library imports
import os
import datetime
import traceback
import re
from abc import ABC
from typing import Optional #, Any, Dict # Any, Dict were not used
import hashlib # Add hashlib import

# Third-party imports
import requests
from playwright.sync_api import sync_playwright, Browser, Page, Playwright, BrowserContext, Download
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
# from app.database.connection import get_db, session_scope # Removed dead import
from app.models import DataSource, db # Added db for potential direct use, Prospect
import pandas as pd # Add pandas import for type hinting
import json # Add json import for 'extra' field serialization
from app.database.crud import bulk_upsert_prospects # Import for loading data
from app.exceptions import ScraperError
from app.config import active_config # Import active_config
# Import BaseScraperConfig
from app.core.configs.base_config import BaseScraperConfig
from app.utils.file_utils import clean_old_files, ensure_directory
from app.utils.logger import logger

# Directory creation is now centralized in config.py, no need to create them here


class BaseScraper(ABC):
    """
    Base scraper class with common functionality for all scrapers.
    
    This class provides a foundation for all web scrapers in the application,
    with common functionality for browser management, logging, error handling,
    and data processing.
    
    Attributes:
        config (BaseScraperConfig): Configuration object for the scraper.
        source_name (str): Name of the data source (derived from config).
        base_url (Optional[str]): Base URL for the data source (derived from config).
        debug_mode (bool): Whether to run in debug mode (derived from config, though typically set at runtime).
        logger: Logger instance for this scraper.
        playwright (Playwright): Playwright instance.
        browser (Browser): Browser instance.
        context (BrowserContext): Browser context.
        page (Page): Browser page.
        download_path (str): Path to download directory for this scraper.
    """
    
    def __init__(self, config: BaseScraperConfig, debug_mode: Optional[bool] = None):
        """
        Initialize the base scraper.
        
        Args:
            config (BaseScraperConfig): The configuration object for this scraper.
            debug_mode (Optional[bool]): Runtime override for debug mode. If None, uses config's setting (or a default).
        """
        self.config = config
        self.source_name = self.config.source_name
        self.base_url = self.config.base_url # Can be None
        
        # Debug mode can be set by runtime parameter, falling back to a default if not in config.
        # Assuming BaseScraperConfig might not have debug_mode, or it's a runtime concern.
        # For now, let's assume debug_mode is primarily a runtime flag passed to the scraper instance.
        self.debug_mode = debug_mode if debug_mode is not None else False
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Use a shortened, filesystem-safe version of the source name for paths/logging keys
        self.source_name_short = self.config.source_name.lower().replace(' ', '_').replace('.', '_')
        
        self.download_path = os.path.join(active_config.RAW_DATA_DIR, self.source_name_short)
        ensure_directory(self.download_path) # Ensure it exists
        self._last_download_path: Optional[str] = None # Initialize _last_download_path
        
        # Logger setup using the potentially modified source_name_short
        self.logger = logger.bind(name=f"scraper.{self.source_name_short}")
        self.logger.info(f"Initialized {self.config.source_name} scraper. Debug mode: {self.debug_mode}. Base URL: {self.base_url}")
    
    def get_most_recent_download(self) -> Optional[str]:
        """
        Find the most recent download file for this scraper.
        Returns: Path to the most recent file, or None if no files exist.
        """
        try:
            # List all files in the download directory
            files = []
            if os.path.exists(self.download_path):
                for filename in os.listdir(self.download_path):
                    filepath = os.path.join(self.download_path, filename)
                    if os.path.isfile(filepath):
                        # Get file modification time
                        mtime = os.path.getmtime(filepath)
                        files.append((filepath, mtime))
            
            if not files:
                self.logger.warning(f"No previous downloads found in {self.download_path}")
                return None
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x[1], reverse=True)
            most_recent_file = files[0][0]
            
            # Get file age
            file_age_seconds = datetime.datetime.now().timestamp() - files[0][1]
            file_age_days = file_age_seconds / (24 * 3600)
            
            self.logger.info(f"Found most recent download: {most_recent_file} (age: {file_age_days:.1f} days)")
            return most_recent_file
            
        except Exception as e:
            self.logger.error(f"Error finding most recent download: {e}", exc_info=True)
            return None

    # -------------------------------------------------------------------------
    # Logging and Setup Methods
    # -------------------------------------------------------------------------
    
    def setup_logging(self):
        """
        Set up logging for this scraper.
        NOTE: Logger is now initialized in __init__. This method can be kept for compatibility
              or removed if __init__ handles all necessary logger setup.
        """
        # self.logger = logger.bind(name=f"scraper.{self.source_name_short}")
        # self.logger.info(f"Logger re-bound for {self.config.source_name} scraper via setup_logging.")
        if self.debug_mode: # self.debug_mode is already set in __init__
            self.logger.debug(f"Debug mode confirmed enabled for {self.config.source_name}.")
        pass # Logger is set in __init__
    
    def setup_browser(self):
        """
        Set up the browser for scraping.
        
        This method initializes Playwright, launches a browser, creates a context,
        and opens a page.
        
        Raises:
            ScraperError: If browser setup fails
        """
        try:
            self.logger.info("Setting up browser...")
            
            # Initialize Playwright
            self.playwright = sync_playwright().start()
            
            # Launch browser (chromium by default) with additional args to handle HTTP/2 issues
            launch_args = []
            if hasattr(self, 'source_name') and 'Transportation' in self.source_name:
                # Add specific args for DOT scraper to handle HTTP/2 protocol errors and timeouts
                launch_args.extend([
                    '--disable-http2',
                    '--disable-features=VizDisplayCompositor',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--disable-translate',
                    '--mute-audio',
                    '--no-first-run',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ])
            elif hasattr(self, 'source_name') and 'Acquisition Gateway' in self.source_name:
                # Add specific args for Acquisition Gateway to prevent timeouts
                launch_args.extend([
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--unlimited-storage',
                    '--disable-hang-monitor',
                    '--disable-prompt-on-repost',
                    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ])
            
            self.browser = self.playwright.chromium.launch(
                headless=not self.debug_mode,
                args=launch_args if launch_args else None
            )
            
            # Create a browser context with enhanced settings for HTTP/2 issues
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "accept_downloads": True,
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            if hasattr(self, 'source_name') and 'Transportation' in self.source_name:
                # Add specific settings for DOT scraper
                context_options.update({
                    "extra_http_headers": {
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1"
                    },
                    "ignore_https_errors": True
                })
            
            self.context = self.browser.new_context(**context_options)
            
            # Create a page
            self.page = self.context.new_page()

            if self.config.use_stealth: # Use config for stealth
                self.logger.info("Applying playwright-stealth patches as per config...")
                try:
                    from playwright_stealth import stealth_sync
                    stealth_sync(self.page)
                    self.logger.info("Stealth patches applied.")
                except ImportError:
                    self.logger.warning("playwright-stealth not installed. Skipping stealth application despite config.")
                except Exception as e:
                    self.logger.error(f"Error applying playwright-stealth: {e}")
            
            # Set default timeout from config
            self.page.set_default_timeout(self.config.navigation_timeout_ms) 
            self.logger.info(f"Default page timeout set to {self.config.navigation_timeout_ms}ms from config.")
            
            # Set up download behavior
            self.page.on("download", self._handle_download)
            
            # Set up console logging if in debug mode
            if self.debug_mode:
                self.page.on("console", lambda msg: self.logger.debug(f"BROWSER: {msg.text}"))
            
            self.logger.info("Browser setup complete")
        except Exception as e:
            error_msg = f"Failed to set up browser: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            raise ScraperError(error_msg)
    
    def _handle_download(self, download: Download) -> None:
        """
        Callback function to handle downloads initiated by Playwright.
        This method delegates to DownloadMixin if available, otherwise implements basic functionality.
        """
        # Check if this instance has the DownloadMixin's method
        if hasattr(self, '_handle_download_event'):
            # Use the mixin's implementation
            self._handle_download_event(download)
        else:
            # Fallback implementation for scrapers that don't use DownloadMixin
            try:
                suggested_filename = download.suggested_filename
                if not suggested_filename:
                    self.logger.warning("Download suggested_filename is empty. Using default.")
                    suggested_filename = f"{self.source_name.lower().replace(' ', '_')}_download.dat"

                file_name_part, ext = os.path.splitext(suggested_filename)
                if not ext:
                    self.logger.warning(f"Filename '{suggested_filename}' has no extension. Defaulting to '.dat'.")
                    ext = '.dat'

                timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                final_filename = f"{self.source_name.lower().replace(' ', '_')}_{timestamp_str}{ext}"
                
                # Ensure self.download_path (scraper's specific download dir) exists
                ensure_directory(self.download_path) 
                
                final_save_path = os.path.join(self.download_path, final_filename)

                download.save_as(final_save_path)
                self.logger.info(f"Successfully saved download to: {final_save_path}")
                self._last_download_path = final_save_path
            except Exception as e:
                self.logger.error(f"Error in _handle_download: {str(e)}")
                self.logger.error(traceback.format_exc())
                self._last_download_path = None # Ensure path is None on error
    
    def cleanup_browser(self):
        """
        Clean up browser resources.
        
        This method closes the page, context, browser, and stops Playwright.
        """
        try:
            self.logger.info("Cleaning up browser resources...")
            
            # Close page if it exists
            if self.page:
                self.page.close()
                self.page = None
            
            # Close context if it exists
            if self.context:
                self.context.close()
                self.context = None
            
            # Close browser if it exists
            if self.browser:
                self.browser.close()
                self.browser = None
            
            # Stop Playwright if it exists
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
            
            self.logger.info("Browser cleanup complete")
        except Exception as e:
            self.logger.error(f"Error during browser cleanup: {str(e)}")
    
    # -------------------------------------------------------------------------
    # File and Data Management Methods
    # -------------------------------------------------------------------------
    
    def cleanup_downloads(self, file_pattern=None):
        """
        Clean up old download files for this scraper, keeping the most recent ones.
        
        Args:
            file_pattern (str, optional): Pattern to match files (default: scraper's name + "*.csv")
        
        Returns:
            int: Number of files deleted
        """
        # Use default pattern if not specified
        if file_pattern is None:
            file_pattern = f"{self.source_name_short}*.csv" # Use source_name_short
        
        # download_dir is self.download_path, which already uses source_name_short
        if not os.path.exists(self.download_path):
            logger.warning(f"Download directory doesn't exist: {self.download_path}")
            return 0
        
        # Keep the 2 most recent files
        deleted = clean_old_files(download_dir, file_pattern, keep_count=2)
        logger.info(f"Cleaned up {deleted} old download files for {self.source_name}")
        return deleted
    
    def get_or_create_data_source(self, session):
        """
        Get or create a data source record in the database.
        
        Args:
            session: SQLAlchemy session
        
        Returns:
            DataSource: Data source record
        """
        try:
            # Try to get the data source
            data_source = session.query(DataSource).filter_by(name=self.source_name).first()
            
            # If it doesn't exist, create it
            if not data_source:
                self.logger.info(f"Creating new data source: {self.source_name}")
                data_source = DataSource(
                    name=self.source_name,
                    url=self.base_url
                    # last_scraped is intentionally not set here.
                    # It will be set by ScraperService upon successful scrape.
                )
                session.add(data_source)
                session.flush() # Flush to get the ID if needed, though not strictly necessary here.
            # else:
                # Do not update last_scraped here for existing records.
                # This will be handled by ScraperService upon successful scrape.
            
            return data_source
        except Exception as e:
            self.logger.error(f"Error getting or creating data source: {str(e)}")
            raise
    
    # -------------------------------------------------------------------------
    # Data Parsing Methods
    # -------------------------------------------------------------------------
    
    def parse_date(self, date_str):
        """
        Parse a date string into a datetime object.
        
        Args:
            date_str (str): String representation of a date
            
        Returns:
            datetime: Parsed datetime object
            
        Raises:
            ScraperError: If the date string cannot be parsed
        """
        if not date_str or not isinstance(date_str, str):
            return None
            
        date_str = date_str.strip()
        if not date_str:
            return None
            
        # Try common date formats
        date_formats = [
            "%m/%d/%Y",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
            "%m/%d/%y",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
        ]
        
        for fmt in date_formats:
            try:
                return datetime.datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
                
        # If none of the formats match, try parsing with dateutil
        try:
            from dateutil import parser
            return parser.parse(date_str).date()
        except Exception as e:
            logger.warning(f"Failed to parse date: {date_str}, error: {str(e)}")
            
        # If all attempts fail
        raise ScraperError(f"Could not parse date: {date_str}", error_type="parsing_error")
    
    def parse_value(self, value_str):
        """
        Parse a string into a numeric value.
        
        Args:
            value_str (str): String to parse
        
        Returns:
            float: Parsed value, or None if parsing fails
        """
        if not value_str or value_str.strip() == "":
            return None
        
        # Remove extra whitespace
        value_str = value_str.strip()
        
        # Remove currency symbols and commas
        value_str = re.sub(r'[$,]', '', value_str)
        
        # Try to convert to float
        try:
            return float(value_str)
        except ValueError:
            self.logger.warning(f"Failed to parse value: {value_str}")
            return None
    
    def get_proposal_query(self, session, proposal_data):
        """
        Get a query for a proposal based on its data.
        
        This method is used to check if a proposal already exists in the database.
        
        Args:
            session: SQLAlchemy session
            proposal_data (dict): Proposal data
        
        Returns:
            Query: SQLAlchemy query for the proposal
        """
        # This method should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement get_proposal_query")

    def _generate_prospect_id(self, data_row: pd.Series, fields_to_hash: list[str]) -> str:
        """
        Generate a unique prospect ID based on specified fields and source name (from config).

        Args:
            data_row (pd.Series): A row of data.
            fields_to_hash (list[str]): List of column names from data_row to use for hashing.

        Returns:
            str: MD5 hash string.
        """
        unique_string_parts = []
        for field in fields_to_hash:
            value = data_row.get(field, '') # Get value or default to empty string
            unique_string_parts.append(str(value) if pd.notna(value) and value is not None else '')

        # Always use the source_name from the config for consistency in ID generation
        unique_string_parts.append(self.config.source_name) 
        
        unique_string = "-".join(unique_string_parts)
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

    def _process_and_load_data(self, df: pd.DataFrame, column_rename_map: dict, prospect_model_fields: list[str], fields_for_id_hash: list[str]):
        """
        Centralized method to process a DataFrame and load it into the Prospect table.
        NOTE: The core logic of this method is intended to be moved to DataProcessingMixin.
        This method in BaseScraper will likely be removed or become a simple wrapper/placeholder.
        """
        # self.logger.info(f"Starting common data processing for {self.source_name}")

        # # 1. Rename Columns
        # df.rename(columns=column_rename_map, inplace=True)
        # self.logger.debug(f"Columns after rename: {df.columns.tolist()}")

        # # 2. Normalize Column Names
        # # Ensure this regex handles various cases robustly, including stripping leading/trailing underscores if any appear post-regex.
        # df.columns = (df.columns.str.strip()
        #               .str.lower()
        #               .str.replace(r'[\s\W]+', '_', regex=True) # Replace whitespace and non-alphanumeric with single underscore
        #               .str.replace(r'_+', '_', regex=True)      # Replace multiple underscores with single
        #               .str.replace(r'^_|_$', '', regex=True))   # Remove leading/trailing underscores
        # df = df.loc[:, ~df.columns.duplicated()] # Remove duplicate columns
        # self.logger.debug(f"Columns after normalization: {df.columns.tolist()}")

        # # 3. Handle 'extra' Column
        # # Define actual model fields (excluding 'extra' itself for this check)
        # # 'id' and 'loaded_at' are auto-generated or handled separately. 'source_id' is added by this func.
        # core_model_fields_for_extra_check = [f for f in prospect_model_fields if f not in ['extra', 'id', 'loaded_at', 'source_id']]
        
        # unmapped_cols = [col for col in df.columns if col not in core_model_fields_for_extra_check]
        
        # if unmapped_cols:
        #     self.logger.info(f"Unmapped columns for '{self.source_name}' to be included in 'extra': {unmapped_cols}")
            
        #     def create_extra_json(row):
        #         extra_dict = {}
        #         for col_name in unmapped_cols:
        #             val = row.get(col_name)
        #             if pd.isna(val):
        #                 extra_dict[col_name] = None
        #             elif isinstance(val, (datetime.datetime, datetime.date, pd.Timestamp)):
        #                 extra_dict[col_name] = pd.to_datetime(val).isoformat()
        #             elif isinstance(val, (int, float, bool, str)):
        #                 extra_dict[col_name] = val
        #             else:
        #                 try:
        #                     extra_dict[col_name] = str(val)
        #                 except Exception:
        #                     self.logger.warning(f"Could not convert value for extra field {col_name} to string. Type: {type(val)}")
        #                     extra_dict[col_name] = "CONVERSION_ERROR"
        #         try:
        #             return json.dumps(extra_dict)
        #         except TypeError as e:
        #             self.logger.error(f"JSON serialization error for 'extra' data: {e}. Dict: {extra_dict}")
        #             return json.dumps({"serialization_error": str(e)}) # Store error in JSON
            
        #     df.loc[:, 'extra'] = df.apply(create_extra_json, axis=1)
        # else:
        #     df.loc[:, 'extra'] = None # Initialize with None if no unmapped columns

        # # 4. Add source_id
        # # Assuming db.session is available and managed by the application context (e.g., in scrape_with_structure)
        # data_source_obj = db.session.query(DataSource).filter_by(name=self.source_name).first()
        # if data_source_obj:
        #     df.loc[:, 'source_id'] = data_source_obj.id
        # else:
        #     self.logger.error(f"DataSource '{self.source_name}' not found. 'source_id' cannot be set.")
        #     # Depending on strictness, could raise error or allow None if Prospect.source_id is nullable
        #     df.loc[:, 'source_id'] = None 

        # # 5. Generate id
        # df.loc[:, 'id'] = df.apply(lambda row: self._generate_prospect_id(row, fields_for_id_hash), axis=1)

        # # 6. Ensure All Model Fields exist in DataFrame
        # for field in prospect_model_fields:
        #     if field not in df.columns:
        #         df.loc[:, field] = pd.NA # Use pd.NA for consistency, converts to None for object types

        # # 7. Normalize NAICS codes
        # if 'naics' in df.columns:
        #     from app.utils.parsing import normalize_naics_code
        #     df['naics'] = df['naics'].apply(normalize_naics_code)
        #     self.logger.info(f"Normalized NAICS codes for {self.source_name}")

        # # 8. Select Final Columns (ensure 'id' is included if not in prospect_model_fields list initially)
        # # prospect_model_fields should ideally contain all columns for the final table including 'id', 'source_id', 'extra'
        # # but excluding 'loaded_at'
        # final_columns_for_db = [col for col in prospect_model_fields if col in df.columns]
        # # Ensure 'id' is present if it was generated
        # if 'id' not in final_columns_for_db and 'id' in df.columns:
        #      final_columns_for_db.append('id')
        
        # df_to_insert = df[final_columns_for_db].copy()

        # # 9. Data Cleaning: Drop rows that are entirely NA (after selecting final columns)
        # df_to_insert = df_to_insert.dropna(how='all')

        # if df_to_insert.empty:
        #     self.logger.info(f"After all processing, no valid data rows to insert for {self.source_name}.")
        #     return 0 # No records processed

        # # 10. Load Data
        # self.logger.info(f"Attempting to insert/update {len(df_to_insert)} records for {self.source_name}.")
        # try:
        #     bulk_upsert_prospects(df_to_insert)
        #     self.logger.info(f"Successfully inserted/updated records for {self.source_name}.")
        #     return len(df_to_insert)
        # except Exception as e:
        #     self.logger.error(f"Error during bulk_upsert_prospects for {self.source_name}: {e}")
        #     self.logger.error(traceback.format_exc())
        #     raise ScraperError(f"Database loading failed for {self.source_name}: {e}") from e
        self.logger.info("BaseScraper._process_and_load_data called. Logic to be moved to DataProcessingMixin.")
        # Example of how it might call a mixin method:
        # if hasattr(super(), '_process_and_load_data'): # Check if mixin method exists
        #     return super()._process_and_load_data(df, column_rename_map, prospect_model_fields, fields_for_id_hash)
        # else:
        #     self.logger.warning("DataProcessingMixin._process_and_load_data not found.")
        #     return 0
        pass # Placeholder
        return 0 # Placeholder return

    # -------------------------------------------------------------------------
    # Browser Interaction Methods
    # -------------------------------------------------------------------------

    def _click_and_download(self,
                            download_trigger_selector: str,
                            pre_click_selector: Optional[str] = None,
                            pre_click_wait_ms: int = 0,
                            wait_for_trigger_timeout_ms: int = 30000,
                            download_timeout_ms: int = 90000,
                            click_method: str = "click" # "click", "dispatch_event", "js_click"
                            ) -> str:
        """
        Helper to handle common download patterns:
        (Optionally) click a preparatory element, then click a download trigger.
        Returns the path to the downloaded file.
        """
        if pre_click_selector:
            self.logger.info(f"Attempting pre-click on selector: {pre_click_selector}")
            pre_click_element = self.page.locator(pre_click_selector)
            pre_click_element.wait_for(state='visible', timeout=wait_for_trigger_timeout_ms) # Use wait_for_trigger_timeout_ms for consistency
            pre_click_element.click() # Standard click for pre-click
            if pre_click_wait_ms > 0:
                self.logger.info(f"Waiting for {pre_click_wait_ms}ms after pre-click.")
                self.page.wait_for_timeout(pre_click_wait_ms)

        self.logger.info(f"Locating download trigger: {download_trigger_selector}")
        trigger_element = self.page.locator(download_trigger_selector)
        try:
            trigger_element.wait_for(state='visible', timeout=wait_for_trigger_timeout_ms)
            self.logger.info(f"Download trigger '{download_trigger_selector}' is visible.")
        except PlaywrightTimeoutError as e: # Ensure PlaywrightTimeoutError is imported
            self.logger.error(f"Timeout waiting for download trigger '{download_trigger_selector}' to be visible.")
            raise ScraperError(f"Download trigger '{download_trigger_selector}' not visible: {str(e)}") from e

        self.logger.info(f"Attempting to {click_method} on download trigger and waiting for download...")
        with self.page.expect_download(timeout=download_timeout_ms) as download_info:
            if click_method == "dispatch_event":
                trigger_element.dispatch_event('click')
            elif click_method == "js_click":
                # Ensure page.evaluate can find the selector if it's complex; might need refinement
                self.page.evaluate(f"document.querySelector('{download_trigger_selector.replace("'", "\\'")}').click();") # Make sure querySelector is robust
            else: # Default "click"
                trigger_element.click()

        download_event_obj = download_info.value # Access the download object

        # Use default_wait_after_download_ms from config
        self.page.wait_for_timeout(self.config.default_wait_after_download_ms) 

        if not self._last_download_path or not os.path.exists(self.last_download_path):
            self.logger.warning(f"Download check: _last_download_path ('{self._last_download_path}') not set or invalid after click. This might indicate an issue with _handle_download or event timing if it wasn't called via a mixin that sets it directly.")
            # If _handle_download is now a placeholder, this check might always fail unless a mixin updates _last_download_path.
            # For now, we assume _handle_download (even as placeholder) or a mixin would set _last_download_path.
            # If it is not set, it's an error condition.
            raise ScraperError(f"Download failed for '{download_trigger_selector}': File path not established by download handler.")

        self.logger.info(f"Download process completed. File saved at: {self._last_download_path}")
        return self._last_download_path
    
    def navigate_to_url(self, url=None, timeout=60000):
        """
        Navigate to a URL.
        
        Args:
            url (str, optional): URL to navigate to. If None, the base URL is used.
            timeout (int, optional): Timeout in milliseconds
        
        Returns:
            bool: True if navigation was successful, False otherwise
        
        Raises:
            ScraperError: If navigation fails
        """
        target_url = url or self.base_url # Use self.base_url which is from config
        if not target_url:
            self.logger.error("Navigation failed: No URL provided and base_url is not set in config.")
            raise ScraperError("No URL available for navigation.")

        effective_timeout = timeout if timeout is not None else self.config.navigation_timeout_ms
        
        try:
            self.logger.info(f"Navigating to URL: {target_url} with timeout {effective_timeout}ms")
            
            if not self.page:
                raise ScraperError("Page object is not initialized. Call setup_browser first.")

            response = self.page.goto(target_url, timeout=effective_timeout, wait_until='domcontentloaded')
            
            if response and not response.ok:
                self.logger.warning(f"Navigation to {target_url} resulted in status {response.status}. URL: {response.url}")
            
            self.handle_popups() # Assumes self.handle_popups exists
            
            self.logger.info(f"Navigation to {target_url} attempt completed.")
            return True
        except PlaywrightTimeoutError as e:
            error_msg = f"Timeout navigating to URL: {target_url} after {effective_timeout}ms: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            if self.config.screenshot_on_error and self.page:
                self._save_error_screenshot("navigation_timeout")
            if self.config.save_html_on_error and self.page:
                self._save_error_html("navigation_timeout")
            raise ScraperError(error_msg) from e
        except Exception as e:
            error_msg = f"Error navigating to URL {target_url}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            if self.config.screenshot_on_error and self.page:
                self._save_error_screenshot("navigation_error")
            if self.config.save_html_on_error and self.page:
                self._save_error_html("navigation_error")
            raise ScraperError(error_msg) from e
    
    def handle_popups(self):
        """
        Handle common popups that might appear on a page.
        This method should be overridden by subclasses to handle site-specific popups.
        """
        self.logger.debug("Base handle_popups called. No default popup handling implemented.")
        pass

    def _save_error_screenshot(self, prefix: str = "error"):
        """Saves a screenshot of the current page state."""
        if not self.page or not hasattr(self, 'source_name_short'):
            self.logger.warning("Cannot save error screenshot: Page or source_name_short not available.")
            return
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{self.source_name_short}_{timestamp}.png"
            path = os.path.join(active_config.ERROR_SCREENSHOTS_DIR, filename)
            ensure_directory(active_config.ERROR_SCREENSHOTS_DIR)
            self.page.screenshot(path=path, full_page=True)
            self.logger.info(f"Error screenshot saved to: {path}")
        except Exception as e:
            self.logger.error(f"Failed to save error screenshot: {e}", exc_info=True)

    def _save_error_html(self, prefix: str = "error"):
        """Saves the HTML content of the current page state."""
        if not self.page or not hasattr(self, 'source_name_short'):
            self.logger.warning("Cannot save error HTML: Page or source_name_short not available.")
            return
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{self.source_name_short}_{timestamp}.html"
            path = os.path.join(active_config.ERROR_HTML_DIR, filename)
            ensure_directory(active_config.ERROR_HTML_DIR)
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.page.content())
            self.logger.info(f"Error HTML saved to: {path}")
        except Exception as e:
            self.logger.error(f"Failed to save error HTML: {e}", exc_info=True)

    def _handle_and_raise_scraper_error(self, error: Exception, operation_description: str) -> None:
        """
        Logs an error and raises a ScraperError, standardizing error reporting.
        Screenshot/HTML saving should be handled by the caller if page-specific.
        """
        # The logger is already bound with scraper name, so the context is there.
        # exc_info=True will include the stack trace of the original error.
        detailed_error_message = f"Error during '{operation_description}': {error}"
        self.logger.error(detailed_error_message, exc_info=True)
        # Raise a new ScraperError, chaining the original exception for full context.
        raise ScraperError(f"Operation failed: '{operation_description}'. Original error: {type(error).__name__} - {error}") from error
    
    # -------------------------------------------------------------------------
    # Main Scraping Methods
    # -------------------------------------------------------------------------
    
    def scrape_with_structure(self, setup_func=None, extract_func=None, process_func=None):
        """
        Scrape data using a structured approach.
        
        This method provides a structured way to scrape data by breaking the process
        into three phases: setup, extraction, and processing.
        
        Args:
            setup_func (callable, optional): Function to set up the scraping process
            extract_func (callable, optional): Function to extract data
            process_func (callable, optional): Function to process extracted data
        
        Returns:
            dict: Result of the scraping process
        
        Raises:
            ScraperError: If any phase of the scraping process fails
        """
        result = {
            "success": False,
            "data": None,
            "error": None
        }
        
        try:
            self.logger.info(f"Starting structured scraping for {self.source_name}")
            
            # Set up the browser
            self.setup_browser()
            
            # Run the setup phase
            if setup_func:
                self.logger.info("Running setup phase")
                setup_func()
            
            # Run the extraction phase
            if extract_func:
                self.logger.info("Running extraction phase")
                try:
                    raw_data = extract_func()
                    result["data"] = raw_data
                except Exception as extract_error:
                    self.logger.error(f"Extraction failed: {extract_error}")
                    
                    # Try fallback to most recent download
                    self.logger.info("Attempting to use most recent download as fallback...")
                    fallback_file = self.get_most_recent_download()
                    
                    if fallback_file:
                        self.logger.warning(f"Using fallback file: {fallback_file}")
                        result["data"] = fallback_file
                        result["used_fallback"] = True
                        result["fallback_reason"] = str(extract_error)
                    else:
                        # No fallback available, re-raise the original error
                        raise
            
            # Run the processing phase
            if process_func and result["data"]:
                self.logger.info("Running processing phase")
                # Use db.session directly
                # from app.database.connection import session_scope # Removed
                # from app.models import DataSource # db is already imported at the top 
                # -> This import is at the top of the file.

                # Flask-SQLAlchemy's db.session is typically managed by the app context.
                # Get or create the data source - this ensures the source exists in DB.
                # self.get_or_create_data_source uses db.session directly.
                data_source = self.get_or_create_data_source(db.session) 
                if not data_source:
                    # This check is important to ensure data source exists before processing.
                    raise ScraperError(f"Could not find or create DataSource for {self.source_name}")
                
                # Call process_func and pass the data_source for source_id
                processed_data = process_func(result["data"], data_source) 
                result["data"] = processed_data
            
            result["success"] = True
            self.logger.info(f"Structured scraping for {self.source_name} completed successfully")
            
        except Exception as e:
            error_msg = f"Error during structured scraping: {str(e)}"
            self.logger.error(error_msg, exc_info=True) # Ensure stack trace is logged
            # self.logger.error(traceback.format_exc()) # Already covered by exc_info=True
            result["error"] = error_msg
            # Save screenshot/HTML on error if configured and page is available
            if self.config.screenshot_on_error and self.page and not self.page.is_closed():
                self._save_error_screenshot("scrape_structure_exception")
            if self.config.save_html_on_error and self.page and not self.page.is_closed():
                self._save_error_html("scrape_structure_exception")
            
        finally:
            # Clean up browser resources
            self.cleanup_browser()
        
        return result
    
    def scrape(self):
        """
        Scrape data from the source.
        
        This method should be implemented by subclasses to perform the actual scraping.
        
        Returns:
            dict: Result of the scraping process
        
        Raises:
            NotImplementedError: If the method is not implemented by a subclass
        """
        raise NotImplementedError("Subclasses must implement scrape method")

    def run(self):
        """
        Run the scraper.

        This method is a simple wrapper around the scrape method.
        """
        return self.scrape()