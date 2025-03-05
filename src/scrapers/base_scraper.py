"""Base scraper class with common functionality for all scrapers."""

# Import from common imports module
from src.utils.imports import (
    os, sys, time, datetime, traceback, glob, pathlib, re,
    requests, BeautifulSoup, sync_playwright, PlaywrightTimeoutError,
    logging, RotatingFileHandler
)

from src.database.db import session_scope
from src.database.models import DataSource
from src.exceptions import ScraperError, ParsingError
from src.config import LOGS_DIR, DOWNLOADS_DIR, LOG_FORMAT, LOG_FILE_MAX_BYTES, LOG_FILE_BACKUP_COUNT

# Create logs directory if it doesn't exist
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

# Create downloads directory if it doesn't exist
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

class BaseScraper:
    """Base scraper class with common functionality for all scrapers."""
    
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
    
    def setup_logging(self):
        """
        Set up logging for the scraper.
        
        Returns:
            logging.Logger: Configured logger
        """
        # Create a logger
        logger = logging.getLogger(f"scraper.{self.source_name.lower().replace(' ', '_')}")
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        if logger.handlers:
            logger.handlers.clear()
        
        # Set up log file
        log_file = os.path.join(LOGS_DIR, f"{self.source_name.lower().replace(' ', '_')}.log")
        
        # Create handlers
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=LOG_FILE_MAX_BYTES, 
            backupCount=LOG_FILE_BACKUP_COUNT
        )
        console_handler = logging.StreamHandler()
        
        # Create formatters and add them to handlers
        formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logger.info(f"Logging to {log_file}")
        return logger
    
    def setup_browser(self):
        """
        Set up and configure the Playwright browser.
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        self.logger.info("Setting up Playwright browser")
        
        # Get the downloads directory
        download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
        # Ensure the download directory exists
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        self.logger.info(f"Setting download directory to {download_dir}")
        
        # Convert to absolute path
        download_dir_abs = os.path.abspath(download_dir)
        self.logger.info(f"Absolute download path: {download_dir_abs}")
        
        try:
            # Start Playwright
            self.playwright = sync_playwright().start()
            self.logger.info("Started Playwright")
            
            # Set browser options
            browser_type = self.playwright.chromium
            
            # Launch the browser with appropriate options
            self.browser = browser_type.launch(
                headless=not self.debug_mode,
                downloads_path=download_dir_abs,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-popup-blocking",
                    "--window-size=1920,1080"
                ]
            )
            self.logger.info("Launched browser")
            
            # Create a new context with download options
            self.context = self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.logger.info("Created browser context")
            
            # Create a new page
            self.page = self.context.new_page()
            self.logger.info("Created page")
            
            # Set default timeout
            self.page.set_default_timeout(60000)  # 60 seconds
            
            self.logger.info("Playwright browser setup complete")
            return True
        except Exception as e:
            self.logger.error(f"Error setting up Playwright browser: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.cleanup_browser()
            return False
    
    def cleanup_browser(self):
        """Clean up Playwright resources."""
        self.logger.info("Cleaning up Playwright resources")
        try:
            if self.page:
                self.logger.info("Closing page")
                self.page.close()
                self.page = None
        except Exception as e:
            self.logger.error(f"Error closing page: {str(e)}")
        
        try:
            if self.context:
                self.logger.info("Closing context")
                self.context.close()
                self.context = None
        except Exception as e:
            self.logger.error(f"Error closing context: {str(e)}")
        
        try:
            if self.browser:
                self.logger.info("Closing browser")
                self.browser.close()
                self.browser = None
        except Exception as e:
            self.logger.error(f"Error closing browser: {str(e)}")
        
        try:
            if self.playwright:
                self.logger.info("Stopping playwright")
                self.playwright.stop()
                self.playwright = None
        except Exception as e:
            self.logger.error(f"Error stopping playwright: {str(e)}")
    
    def cleanup_downloads(self, file_pattern=None):
        """
        Remove temporary download files.
        
        Args:
            file_pattern (str, optional): Glob pattern to match files to delete
        """
        try:
            download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
            
            if file_pattern:
                files = glob.glob(os.path.join(download_dir, file_pattern))
            else:
                # Find files modified in the last hour
                current_time = time.time()
                one_hour_ago = current_time - 3600  # 1 hour in seconds
                
                files = []
                for file_path in glob.glob(os.path.join(download_dir, "*")):
                    if os.path.getmtime(file_path) > one_hour_ago:
                        # Only include temporary files
                        if "_temp_" in os.path.basename(file_path) or "download-" in os.path.basename(file_path):
                            files.append(file_path)
            
            for file_path in files:
                self.logger.info(f"Removing temporary file: {file_path}")
                try:
                    os.remove(file_path)
                except Exception as e:
                    self.logger.error(f"Error removing file {file_path}: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    def parse_date(self, date_str):
        """
        Parse a date string into a datetime object.
        
        Args:
            date_str (str): Date string to parse
            
        Returns:
            datetime.datetime: Parsed date, or None if parsing failed
        """
        if date_str is None:
            return None
        
        # Convert to string if it's a numeric type
        if isinstance(date_str, (int, float)):
            date_str = str(date_str)
        
        # If it's empty after conversion, return None
        if not date_str or str(date_str).strip() == "":
            return None
        
        # Try different date formats
        date_formats = [
            "%m/%d/%Y",
            "%m/%d/%y",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%m-%d-%Y",
            "%m-%d-%y"
        ]
        
        # Clean up the date string
        date_str = str(date_str).strip()
        
        # Try each format
        for date_format in date_formats:
            try:
                return datetime.datetime.strptime(date_str, date_format)
            except ValueError:
                continue
        
        # If we get here, none of the formats worked
        self.logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def parse_value(self, value_str):
        """
        Parse a value string into a float.
        
        Args:
            value_str (str): Value string to parse
            
        Returns:
            float: Parsed value, or None if parsing failed
        """
        if value_str is None:
            return None
        
        # If it's already a numeric type, return it
        if isinstance(value_str, (int, float)):
            return float(value_str)
        
        # Convert to string if needed
        value_str = str(value_str)
        
        # If it's empty after conversion, return None
        if not value_str or value_str.strip() == "":
            return None
        
        # Remove any non-numeric characters except for decimal points
        value_str = re.sub(r'[^\d.]', '', value_str)
        
        # Try to convert to float
        try:
            return float(value_str)
        except ValueError:
            self.logger.warning(f"Could not parse value: {value_str}")
            return None
    
    def get_or_create_data_source(self, session):
        """
        Get or create a data source record in the database.
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            DataSource: Data source record
        """
        # Check if the data source exists
        data_source = session.query(DataSource).filter(DataSource.name == self.source_name).first()
        
        # If the data source doesn't exist, create it
        if not data_source:
            self.logger.info(f"Creating new data source: {self.source_name}")
            data_source = DataSource(
                name=self.source_name,
                url=self.base_url,
                description=f"{self.source_name} data source"
            )
            session.add(data_source)
            session.commit()
        
        return data_source
    
    def scrape(self):
        """
        Abstract method to be implemented by subclasses.
        
        This method should contain the scraping logic for the specific data source.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement the scrape method") 