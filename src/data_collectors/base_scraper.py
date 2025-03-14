"""
Base scraper class with common functionality for all scrapers.

This module provides a foundation for all web scrapers in the application,
with common functionality for browser management, logging, error handling,
and data processing.
"""

# Import from common imports module
from src.utils.imports import (
    os, sys, time, datetime, traceback, glob, pathlib, re,
    requests, BeautifulSoup, sync_playwright, PlaywrightTimeoutError,
    logging, RotatingFileHandler
)

from src.database.db_session_manager import session_scope
from src.database.models import DataSource
from src.exceptions import ScraperError, ParsingError
from src.config import LOGS_DIR, DOWNLOADS_DIR, LOG_FORMAT, LOG_FILE_MAX_BYTES, LOG_FILE_BACKUP_COUNT

# Create required directories
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class BaseScraper:
    """
    Base scraper class with common functionality for all scrapers.
    
    This class provides a foundation for all web scrapers in the application,
    with common functionality for browser management, logging, error handling,
    and data processing.
    
    Attributes:
        source_name (str): Name of the data source
        base_url (str): Base URL for the data source
        debug_mode (bool): Whether to run in debug mode
        logger (logging.Logger): Logger for this scraper
        playwright (Playwright): Playwright instance
        browser (Browser): Browser instance
        context (BrowserContext): Browser context
        page (Page): Browser page
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
        
        # Set up logging
        self.logger = self.setup_logging()
        self.logger.info(f"Initializing {source_name} scraper with debug_mode={debug_mode}")
        
        # Initialize browser components
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    # -------------------------------------------------------------------------
    # Logging and Setup Methods
    # -------------------------------------------------------------------------
    
    def setup_logging(self):
        """
        Set up logging for this scraper.
        
        Returns:
            logging.Logger: Configured logger
        """
        # Create a logger for this scraper
        logger = logging.getLogger(f"scraper.{self.source_name}")
        logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        if logger.handlers:
            logger.handlers.clear()
        
        # Create log file path
        log_file = os.path.join(LOGS_DIR, f"{self.source_name.lower().replace(' ', '_')}_scraper.log")
        
        # Create file handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT
        )
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Set log level for handlers
        file_handler.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(LOG_FORMAT)
        
        # Add formatter to handlers
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
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
    
    def _handle_download(self, download):
        """
        Handle file downloads from the browser.
        
        Args:
            download: Playwright download object
        """
        try:
            # Get the suggested filename
            filename = download.suggested_filename
            
            # Create the download path
            download_path = os.path.join(DOWNLOADS_DIR, filename)
            
            # Save the file
            download.save_as(download_path)
            
            self.logger.info(f"Downloaded file: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to handle download: {str(e)}")
    
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
        Clean up downloaded files.
        
        Args:
            file_pattern (str, optional): Glob pattern for files to clean up.
                If None, all files in the downloads directory will be removed.
        
        Returns:
            int: Number of files removed
        """
        try:
            # If no pattern is provided, use a pattern that matches all files
            if file_pattern is None:
                file_pattern = "*"
            
            # Create the full pattern
            full_pattern = os.path.join(DOWNLOADS_DIR, file_pattern)
            
            # Get a list of files matching the pattern
            files = glob.glob(full_pattern)
            
            # Remove each file
            count = 0
            for file_path in files:
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to remove file {file_path}: {str(e)}")
            
            self.logger.info(f"Removed {count} files from downloads directory")
            return count
        except Exception as e:
            self.logger.error(f"Error cleaning up downloads: {str(e)}")
            return 0
    
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
            date_str (str): Date string to parse
        
        Returns:
            datetime.datetime: Parsed date, or None if parsing fails
        
        Raises:
            ParsingError: If date parsing fails
        """
        if not date_str or date_str.strip() == "":
            return None
        
        # Remove extra whitespace
        date_str = date_str.strip()
        
        # Try different date formats
        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
            "%m/%d/%y",
            "%m-%d-%y"
        ]
        
        for fmt in formats:
            try:
                return datetime.datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # If we get here, none of the formats worked
        error_msg = f"Failed to parse date: {date_str}"
        self.logger.error(error_msg)
        raise ParsingError(error_msg)
    
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
            
            # Navigate to the URL
            response = self.page.goto(url, timeout=timeout)
            
            # Check if navigation was successful
            if response.status >= 400:
                error_msg = f"Failed to navigate to URL {url}: status code {response.status}"
                self.logger.error(error_msg)
                raise ScraperError(error_msg)
            
            # Wait for the page to load
            self.page.wait_for_load_state("networkidle", timeout=timeout)
            
            # Handle any popups
            self.handle_popups()
            
            self.logger.info(f"Successfully navigated to URL: {url}")
            
            return True
        except PlaywrightTimeoutError:
            error_msg = f"Timeout navigating to URL: {url}"
            self.logger.error(error_msg)
            raise ScraperError(error_msg)
        except Exception as e:
            error_msg = f"Error navigating to URL {url}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            raise ScraperError(error_msg)
    
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