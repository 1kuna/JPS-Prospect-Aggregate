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
from app.models import DataSource, db, Prospect # Added db for potential direct use, Prospect
import pandas as pd # Add pandas import for type hinting
import json # Add json import for 'extra' field serialization
from app.database.crud import bulk_upsert_prospects # Import for loading data
from app.exceptions import ScraperError
from app.config import active_config # Import active_config
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
        source_name (str): Name of the data source
        base_url (str): Base URL for the data source
        debug_mode (bool): Whether to run in debug mode
        logger: Logger instance for this scraper
        playwright (Playwright): Playwright instance
        browser (Browser): Browser instance
        context (BrowserContext): Browser context
        page (Page): Browser page
        download_path (str): Path to download directory for this scraper
    """
    
    def __init__(self, source_name, base_url, debug_mode=False, use_stealth=False):
        """
        Initialize the base scraper.
        
        Args:
            source_name (str): Name of the data source
            base_url (str): Base URL for the data source
            debug_mode (bool): Whether to run in debug mode
            use_stealth (bool): Whether to apply playwright-stealth patches
        """
        self.source_name = source_name
        self.base_url = base_url
        self.debug_mode = debug_mode
        self.use_stealth = use_stealth # Add use_stealth attribute
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        # Use the specific directory for this scraper within RAW_DATA_DIR
        self.download_path = os.path.join(active_config.RAW_DATA_DIR, source_name.lower().replace(' ', '_'))
        ensure_directory(self.download_path) # Ensure it exists
        self._last_download_path: Optional[str] = None # Initialize _last_download_path
        self.logger = logger.bind(name=f"scraper.{source_name.lower().replace(' ', '_')}")
        self.logger.info(f"Initialized {source_name} scraper. Debug mode: {debug_mode}")
    
    # -------------------------------------------------------------------------
    # Logging and Setup Methods
    # -------------------------------------------------------------------------
    
    def setup_logging(self):
        """
        Set up logging for this scraper.
        """
        # Use the centralized Loguru logger with scraper-specific context
        self.logger = logger.bind(name=f"scraper.{self.source_name.lower().replace(' ', '_')}")
        self.logger.info(f"Initialized {self.source_name} scraper")
        if self.debug_mode:
            self.logger.debug("Debug mode enabled")
    
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
            
            # Launch browser (chromium by default)
            self.browser = self.playwright.chromium.launch(
                headless=not self.debug_mode
            )
            
            # Create a browser context
            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                accept_downloads=True
            )
            
            # Create a page
            self.page = self.context.new_page()

            if self.use_stealth:
                self.logger.info("Applying playwright-stealth patches...")
                try:
                    from playwright_stealth import stealth_sync
                    stealth_sync(self.page)
                    self.logger.info("Stealth patches applied.")
                except ImportError:
                    self.logger.warning("playwright-stealth not installed. Skipping stealth application.")
                except Exception as e:
                    self.logger.error(f"Error applying playwright-stealth: {e}")
            
            # Set default timeout
            self.page.set_default_timeout(60000)  # 60 seconds
            
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
        """Callback function to handle downloads initiated by Playwright."""
        try:
            suggested_filename = download.suggested_filename
            if not suggested_filename:
                self.logger.warning(f"Download suggested_filename is empty. Using default.")
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
            file_pattern = f"{self.source_name.lower().replace(' ', '_')}*.csv"
        
        download_dir = os.path.join(active_config.RAW_DATA_DIR, self.source_name.lower().replace(' ', '_'))
        
        if not os.path.exists(download_dir):
            logger.warning(f"Download directory doesn't exist: {download_dir}")
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

    def _generate_prospect_id(self, data_row: pd.Series, fields_to_hash: list[str], source_name_override: str = None) -> str:
        """
        Generate a unique prospect ID based on specified fields and source name.

        Args:
            data_row (pd.Series): A row of data.
            fields_to_hash (list[str]): List of column names from data_row to use for hashing.
            source_name_override (str, optional): Override for self.source_name. Defaults to None.

        Returns:
            str: MD5 hash string.
        """
        unique_string_parts = []
        for field in fields_to_hash:
            value = data_row.get(field, '') # Get value or default to empty string
            unique_string_parts.append(str(value) if pd.notna(value) and value is not None else '')

        current_source_name = source_name_override if source_name_override else self.source_name
        unique_string_parts.append(current_source_name)
        
        unique_string = "-".join(unique_string_parts)
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

    def _process_and_load_data(self, df: pd.DataFrame, column_rename_map: dict, prospect_model_fields: list[str], fields_for_id_hash: list[str]):
        """
        Centralized method to process a DataFrame and load it into the Prospect table.
        """
        self.logger.info(f"Starting common data processing for {self.source_name}")

        # 1. Rename Columns
        df.rename(columns=column_rename_map, inplace=True)
        self.logger.debug(f"Columns after rename: {df.columns.tolist()}")

        # 2. Normalize Column Names
        # Ensure this regex handles various cases robustly, including stripping leading/trailing underscores if any appear post-regex.
        df.columns = (df.columns.str.strip()
                      .str.lower()
                      .str.replace(r'[\s\W]+', '_', regex=True) # Replace whitespace and non-alphanumeric with single underscore
                      .str.replace(r'_+', '_', regex=True)      # Replace multiple underscores with single
                      .str.replace(r'^_|_$', '', regex=True))   # Remove leading/trailing underscores
        df = df.loc[:, ~df.columns.duplicated()] # Remove duplicate columns
        self.logger.debug(f"Columns after normalization: {df.columns.tolist()}")

        # 3. Handle 'extra' Column
        # Define actual model fields (excluding 'extra' itself for this check)
        # 'id' and 'loaded_at' are auto-generated or handled separately. 'source_id' is added by this func.
        core_model_fields_for_extra_check = [f for f in prospect_model_fields if f not in ['extra', 'id', 'loaded_at', 'source_id']]
        
        unmapped_cols = [col for col in df.columns if col not in core_model_fields_for_extra_check]
        
        if unmapped_cols:
            self.logger.info(f"Unmapped columns for '{self.source_name}' to be included in 'extra': {unmapped_cols}")
            
            def create_extra_json(row):
                extra_dict = {}
                for col_name in unmapped_cols:
                    val = row.get(col_name)
                    if pd.isna(val):
                        extra_dict[col_name] = None
                    elif isinstance(val, (datetime.datetime, datetime.date, pd.Timestamp)):
                        extra_dict[col_name] = pd.to_datetime(val).isoformat()
                    elif isinstance(val, (int, float, bool, str)):
                        extra_dict[col_name] = val
                    else:
                        try:
                            extra_dict[col_name] = str(val)
                        except Exception:
                            self.logger.warning(f"Could not convert value for extra field {col_name} to string. Type: {type(val)}")
                            extra_dict[col_name] = "CONVERSION_ERROR"
                try:
                    return json.dumps(extra_dict)
                except TypeError as e:
                    self.logger.error(f"JSON serialization error for 'extra' data: {e}. Dict: {extra_dict}")
                    return json.dumps({"serialization_error": str(e)}) # Store error in JSON
            
            df['extra'] = df.apply(create_extra_json, axis=1)
        else:
            df['extra'] = None # Initialize with None if no unmapped columns

        # 4. Add source_id
        # Assuming db.session is available and managed by the application context (e.g., in scrape_with_structure)
        data_source_obj = db.session.query(DataSource).filter_by(name=self.source_name).first()
        if data_source_obj:
            df['source_id'] = data_source_obj.id
        else:
            self.logger.error(f"DataSource '{self.source_name}' not found. 'source_id' cannot be set.")
            # Depending on strictness, could raise error or allow None if Prospect.source_id is nullable
            df['source_id'] = None 

        # 5. Generate id
        df['id'] = df.apply(lambda row: self._generate_prospect_id(row, fields_for_id_hash), axis=1)

        # 6. Ensure All Model Fields exist in DataFrame
        for field in prospect_model_fields:
            if field not in df.columns:
                df[field] = pd.NA # Use pd.NA for consistency, converts to None for object types

        # 7. Select Final Columns (ensure 'id' is included if not in prospect_model_fields list initially)
        # prospect_model_fields should ideally contain all columns for the final table including 'id', 'source_id', 'extra'
        # but excluding 'loaded_at'
        final_columns_for_db = [col for col in prospect_model_fields if col in df.columns]
        # Ensure 'id' is present if it was generated
        if 'id' not in final_columns_for_db and 'id' in df.columns:
             final_columns_for_db.append('id')
        
        df_to_insert = df[final_columns_for_db]

        # 8. Data Cleaning: Drop rows that are entirely NA (after selecting final columns)
        df_to_insert.dropna(how='all', inplace=True)

        if df_to_insert.empty:
            self.logger.info(f"After all processing, no valid data rows to insert for {self.source_name}.")
            return 0 # No records processed

        # 9. Load Data
        self.logger.info(f"Attempting to insert/update {len(df_to_insert)} records for {self.source_name}.")
        try:
            bulk_upsert_prospects(df_to_insert)
            self.logger.info(f"Successfully inserted/updated records for {self.source_name}.")
            return len(df_to_insert)
        except Exception as e:
            self.logger.error(f"Error during bulk_upsert_prospects for {self.source_name}: {e}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Database loading failed for {self.source_name}: {e}") from e

    # -------------------------------------------------------------------------
    # Browser Interaction Methods
    # -------------------------------------------------------------------------
    
    def check_url_accessibility(self, url=None):
        """
        Check if a URL is accessible.
        
        Args:
            url (str, optional): URL to check. If None, the base URL is used.
        
        Returns:
            bool: True if the URL is accessible, False otherwise
        """
        url = url or self.base_url
        
        try:
            self.logger.info(f"Checking accessibility of URL: {url}")
            
            # Send a HEAD request to check if the URL is accessible
            response = requests.head(url, timeout=10)
            
            # Check if the response is successful
            is_accessible = response.status_code < 400
            
            self.logger.info(f"URL {url} is {'accessible' if is_accessible else 'not accessible'} (status code: {response.status_code})")
            
            return is_accessible
        except Exception as e:
            self.logger.error(f"Error checking URL accessibility: {str(e)}")
            return False
    
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
        url = url or self.base_url
        
        try:
            self.logger.info(f"Navigating to URL: {url}")
            
            if not self.page:
                raise ScraperError("Page object is not initialized. Call setup_browser first.")

            # Navigate to the URL
            response = self.page.goto(url, timeout=timeout, wait_until='domcontentloaded')
            
            # Check if navigation response is generally okay (ignore strict 404 for now if content loaded)
            # We will rely on subsequent element waits to confirm page validity
            if response and not response.ok:
                self.logger.warning(f"Navigation to {url} resulted in status {response.status}. URL: {response.url}")
                # Consider raising an error or returning False depending on desired strictness
            
            # Optional: Wait for a specific load state if needed after goto, but goto usually handles it.
            # try:
            #     self.page.wait_for_load_state("load", timeout=timeout) 
            # except PlaywrightTimeoutError:
            #     self.logger.warning(f"wait_for_load_state('load') timed out for {url}, proceeding anyway.")
            
            # Handle any popups (if implemented in subclass)
            self.handle_popups()
            
            self.logger.info(f"Navigation attempted for URL: {url}. Subsequent checks will verify content.")
            
            return True # Indicate navigation attempt was made
        except PlaywrightTimeoutError as e:
            error_msg = f"Timeout navigating to URL: {url}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            raise ScraperError(error_msg) from e
        except Exception as e:
            error_msg = f"Error navigating to URL {url}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            raise ScraperError(error_msg) from e
    
    def handle_popups(self):
        """
        Handle common popups that might appear on a page.
        
        This method should be overridden by subclasses to handle
        site-specific popups.
        """
        # This is a placeholder method that can be overridden by subclasses
        pass
    
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
                raw_data = extract_func()
                result["data"] = raw_data
            
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
                
                # Call process_func without session and data_source arguments
                processed_data = process_func(result["data"]) 
                result["data"] = processed_data
            
            result["success"] = True
            self.logger.info(f"Structured scraping for {self.source_name} completed successfully")
            
        except Exception as e:
            error_msg = f"Error during structured scraping: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            result["error"] = error_msg
            
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