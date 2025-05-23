"""
Base scraper class with common functionality for all scrapers.

This module provides a foundation for all web scrapers in the application,
with common functionality for browser management, logging, error handling,
and data processing.
"""

# Standard library imports
import os
import sys
import time
import datetime
import traceback
import glob
import pathlib
import re
import logging
from abc import ABC
from typing import Optional, Any, Dict

# Third-party imports
import requests
from playwright.sync_api import sync_playwright, Browser, Page, Playwright, BrowserContext, Download
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
# from app.database.connection import get_db, session_scope # Removed dead import
from app.models import DataSource, db # Added db for potential direct use
from app.exceptions import ScraperError
from app.config import LOGS_DIR, RAW_DATA_DIR, LOG_FORMAT, LOG_FILE_MAX_BYTES, LOG_FILE_BACKUP_COUNT
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
    
    def __init__(self, source_name, base_url, debug_mode=False):
        """
        Initialize the base scraper.
        
        Args:
            source_name (str): Name of the data source
            base_url (str): Base URL for the data source
            debug_mode (bool): Whether to run in debug mode
        """
        self.source_name = source_name
        self.base_url = base_url
        self.debug_mode = debug_mode
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        # Use the specific directory for this scraper within RAW_DATA_DIR
        self.download_path = os.path.join(RAW_DATA_DIR, source_name.lower().replace(' ', '_'))
        ensure_directory(self.download_path) # Ensure it exists
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
        suggested_filename = download.suggested_filename
        # Ensure the target download directory for this scraper exists
        download_dir = os.path.join(RAW_DATA_DIR, self.source_name.lower().replace(' ', '_')) # Use RAW_DATA_DIR
        ensure_directory(download_dir)
        # save_path = os.path.join(download_dir, suggested_filename) # Path calculation no longer needed here
        self.logger.info(f"Download event triggered: {suggested_filename}")
        # Removed the automatic save_as call. Scraper-specific methods will handle saving/moving.
        self.logger.info(f"BaseScraper._handle_download: Letting scraper-specific method handle saving/moving of {suggested_filename}.")
        # try:
            # Save the file
            # download.save_as(save_path) # REMOVED THIS LINE
            
            # self.logger.info(f"Downloaded file: {suggested_filename}")
        # except Exception as e:
        #     self.logger.error(f"Failed to handle download: {str(e)}")
    
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
        
        download_dir = os.path.join(RAW_DATA_DIR, self.source_name.lower().replace(' ', '_'))
        
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
                    url=self.base_url,
                    last_scraped=datetime.datetime.now()
                )
                session.add(data_source)
                session.flush()
            else:
                # Update the last_scraped timestamp
                data_source.last_scraped = datetime.datetime.now()
            
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
                from app.models import DataSource # db is already imported at the top
                
                # Flask-SQLAlchemy's db.session is typically managed by the app context,
                # so a 'with' block for the session itself isn't usually needed here.
                # Operations will be part of the current session.
                session = db.session
                data_source = self.get_or_create_data_source(session)
                if not data_source:
                    raise ScraperError(f"Could not find or create DataSource for {self.source_name}")
                
                # Pass session and data_source to process_func
                processed_data = process_func(result["data"], session, data_source)
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