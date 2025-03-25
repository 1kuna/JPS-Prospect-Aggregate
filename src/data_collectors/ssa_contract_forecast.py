"""SSA Contract Forecast scraper."""

# Standard library imports
import os
import datetime
import traceback

# Third-party imports
import pandas as pd
import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
from src.data_collectors.base_scraper import BaseScraper
from src.database.models import Proposal
from src.database.download_tracker import DownloadTracker
from src.exceptions import ScraperError
from src.utils.logger import logger
from src.utils.db_utils import update_scraper_status
from src.config import SSA_CONTRACT_FORECAST_URL

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.ssa_contract_forecast")

def check_url_accessibility(url):
    """
    Check if a URL is accessible.
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if the URL is accessible, False otherwise
    """
    logger.info(f"Checking accessibility of {url}")
    
    try:
        # Set a reasonable timeout
        response = requests.head(url, timeout=10)
        
        # Check if the response is successful
        if response.status_code < 400:
            logger.info(f"URL {url} is accessible (status code: {response.status_code})")
            return True
        
        logger.error(f"URL {url} returned status code {response.status_code}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking URL {url}: {str(e)}")
        return False

class SSAContractForecastScraper(BaseScraper):
    """Scraper for the SSA Contract Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the SSA Contract Forecast scraper."""
        super().__init__(
            source_name="SSA Contract Forecast",
            base_url=SSA_CONTRACT_FORECAST_URL,
            debug_mode=debug_mode
        )
    
    def _find_excel_link(self):
        """
        Find the Excel file link on the page.
        
        Returns:
            str: URL of the Excel file, or None if not found
        """
        # Try different selectors to find the Excel link
        selectors = [
            'a[href$=".xlsx"]',
            'a[href$=".xls"]',
            'a:has-text("Excel")',
            'a:has-text("Forecast")'
        ]
        
        self.logger.info("Searching for Excel link...")
        for selector in selectors:
            self.logger.info(f"Trying selector: {selector}")
            links = self.page.query_selector_all(selector)
            if links:
                self.logger.info(f"Found {len(links)} links with selector {selector}")
                for link in links:
                    href = link.get_attribute('href')
                    if href and ('.xls' in href.lower() or 'forecast' in href.lower()):
                        self.logger.info(f"Found Excel link: {href}")
                        return href
        return None
    
    def _save_debug_info(self):
        """
        Save debug information when Excel link is not found.
        """
        # Save a screenshot for debugging
        screenshot_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'downloads', 'page_screenshot.png')
        self.page.screenshot(path=screenshot_path)
        self.logger.info(f"Saved screenshot to {screenshot_path}")
        
        # Save page content for debugging
        html_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'downloads', 'page_content.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.page.content())
        self.logger.info(f"Saved page content to {html_path}")
    
    def _download_file(self, excel_link):
        """
        Download the Excel file from the given link.
        
        Args:
            excel_link (str): URL of the Excel file
            
        Returns:
            str: Path to the downloaded file
            
        Raises:
            ScraperError: If download fails
        """
        self.logger.info(f"Downloading file from {excel_link}")
        
        try:
            # Start the download
            with self.page.expect_download(timeout=60000) as download_info:
                # Click the link
                self.page.click(f'a[href="{excel_link}"]')
            
            # Wait for the download to complete
            download = download_info.value
            self.logger.info(f"Download started: {download.suggested_filename}")
            
            # Wait for the download to complete and save the file
            download_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'downloads', download.suggested_filename)
            download.save_as(download_path)
            self.logger.info(f"File downloaded to: {download_path}")
            
            return download_path
        except Exception as e:
            self.logger.error(f"Error during download: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Failed to download forecast document: {str(e)}")
    
    def download_forecast_document(self):
        """
        Download the forecast document from the SSA website.
        
        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Downloading forecast document")
        
        try:
            # Navigate to the forecast page
            self.logger.info(f"Navigating to {self.base_url}")
            try:
                self.navigate_to_url()
            except Exception as e:
                self.logger.error(f"Error navigating to forecast page: {str(e)}")
                self.logger.error(traceback.format_exc())
                raise
            
            # Find the Excel link
            excel_link = self._find_excel_link()
            
            if not excel_link:
                self.logger.error("Could not find Excel link on the page")
                self._save_debug_info()
                return None
            
            # Download the file
            return self._download_file(excel_link)
            
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout downloading forecast document: {str(e)}")
            raise ScraperError(f"Timeout downloading forecast document: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error downloading forecast document: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Failed to download forecast document: {str(e)}")
    
    def _get_field_mapping(self):
        """
        Get the mapping of Excel columns to database fields.
        
        Returns:
            dict: Mapping of Excel column names to database field names
        """
        return {
            'Title': 'title',
            'Project Title': 'title',
            'Description': 'description',
            'Agency': 'agency',
            'Office': 'office',
            'NAICS': 'naics_code',
            'NAICS Code': 'naics_code',
            'Estimated Value': 'estimated_value',
            'Estimated Contract Value': 'estimated_value',
            'Release Date': 'release_date',
            'Solicitation Date': 'release_date',
            'Response Date': 'response_date',
            'Due Date': 'response_date',
            'Contact': 'contact_info',
            'Point of Contact': 'contact_info',
            'URL': 'url',
            'Status': 'status',
            'Contract Type': 'contract_type',
            'Set-Aside': 'set_aside',
            'Competition Type': 'competition_type',
            'Solicitation Number': 'solicitation_number',
            'Award Date': 'award_date',
            'Place of Performance': 'place_of_performance',
            'Incumbent': 'incumbent'
        }
    
    def _create_column_mapping(self, df_columns):
        """
        Create a mapping from Excel columns to database fields.
        
        Args:
            df_columns: DataFrame columns
            
        Returns:
            dict: Mapping of Excel columns to database fields
        """
        field_mapping = self._get_field_mapping()
        column_mapping = {}
        
        for excel_col in df_columns:
            for map_col, db_field in field_mapping.items():
                if excel_col.lower() == map_col.lower():
                    column_mapping[excel_col] = db_field
                    break
        
        self.logger.info(f"Column mapping: {column_mapping}")
        return column_mapping
    
    def _transform_row_data(self, row, column_mapping):
        """
        Transform a row of Excel data into proposal data.
        
        Args:
            row: DataFrame row
            column_mapping: Mapping of Excel columns to database fields
            
        Returns:
            dict: Transformed proposal data
        """
        proposal_data = {
            'is_latest': True
        }
        
        # Map the fields
        for excel_col, db_field in column_mapping.items():
            value = row[excel_col]
            
            # Handle NaN values
            if pd.isna(value):
                value = None
            
            # Parse dates
            if db_field in ['release_date', 'response_date', 'award_date'] and value is not None:
                value = self.parse_date(str(value))
            
            # Parse monetary values
            elif db_field == 'estimated_value' and value is not None:
                value = self.parse_value(str(value))
            
            proposal_data[db_field] = value
        
        return proposal_data
    
    def process_excel(self, excel_file, session, data_source):
        """
        Process the downloaded Excel file and save data to the database.
        
        Args:
            excel_file (list or str): Path to the Excel file or list containing the path
            session: SQLAlchemy session
            data_source: DataSource object
            
        Returns:
            int: Number of proposals processed
            
        Raises:
            ScraperError: If processing fails
        """
        # If excel_file is a list (from extract_func), get the first element
        if isinstance(excel_file, list):
            excel_file = excel_file[0]
            
        self.logger.info(f"Processing Excel file: {excel_file}")
        
        try:
            # Read the Excel file
            df = pd.read_excel(excel_file)
            
            # Check if dataframe is empty
            if df.empty:
                self.logger.error("Excel file is empty")
                return 0
            
            # Log the columns
            self.logger.info(f"Excel columns: {df.columns.tolist()}")
            
            # Create column mapping
            column_mapping = self._create_column_mapping(df.columns)
            
            # Process each row
            count = 0
            for _, row in df.iterrows():
                try:
                    # Transform row data
                    proposal_data = self._transform_row_data(row, column_mapping)
                    proposal_data['source_id'] = data_source.id
                    
                    # Get or create proposal
                    proposal_query = self.get_proposal_query(session, proposal_data)
                    if proposal_query:
                        count += 1
                except Exception as e:
                    self.logger.error(f"Error processing row: {str(e)}")
                    continue
            
            return count
            
        except Exception as e:
            error_msg = f"Failed to process Excel file: {str(e)}"
            self.logger.error(error_msg)
            raise ScraperError(error_msg)
    
    def get_proposal_query(self, session, proposal_data):
        """
        Get a query to find an existing proposal.
        
        Args:
            session: SQLAlchemy session
            proposal_data (dict): Proposal data containing at least source_id and title
            
        Returns:
            Proposal or None: Existing proposal if found, None otherwise
        """
        query = session.query(Proposal).filter(
            Proposal.source_id == proposal_data['source_id'],
            Proposal.title == proposal_data['title']
        )
        
        # Add additional filters if available
        if 'agency' in proposal_data and proposal_data['agency']:
            query = query.filter(Proposal.agency == proposal_data['agency'])
        
        if 'solicitation_number' in proposal_data and proposal_data['solicitation_number']:
            query = query.filter(Proposal.solicitation_number == proposal_data['solicitation_number'])
        
        return query.first()
    
    def scrape(self):
        """
        Run the scraper to extract and process data.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        # Use the structured scrape method from the base class
        return self.scrape_with_structure(
            extract_func=self.download_forecast_document,
            process_func=self.process_excel
        )

def run_scraper(force=False):
    """
    Run the SSA Contract Forecast scraper.
    
    Args:
        force (bool): Whether to force scraping even if recently run
        
    Returns:
        bool: True if scraping was successful
        
    Raises:
        ScraperError: If an error occurs during scraping
        ImportError: If required dependencies are not installed
    """
    local_logger = logger
    scraper = None
    download_tracker = DownloadTracker()
    
    try:
        # Check if we should run the scraper
        if not force and download_tracker.check_last_download("SSA Contract Forecast"):
            local_logger.info("Skipping scrape due to recent download")
            return True
        
        # Create an instance of the scraper
        scraper = SSAContractForecastScraper(debug_mode=False)
        
        # Check if the URL is accessible
        if not check_url_accessibility(SSA_CONTRACT_FORECAST_URL):
            error_msg = f"URL {SSA_CONTRACT_FORECAST_URL} is not accessible"
            local_logger.error(error_msg)
            update_scraper_status("SSA Contract Forecast", "error", error_msg)
            raise ScraperError(error_msg)
        
        # Run the scraper
        local_logger.info("Running SSA Contract Forecast scraper")
        success = scraper.scrape()
        
        # If scraper.scrape() returns False, it means an error occurred
        if not success:
            error_msg = "Scraper failed without specific error"
            local_logger.error(error_msg)
            update_scraper_status("SSA Contract Forecast", "error", error_msg)
            raise ScraperError(error_msg)
        
        # Update the download tracker with the current time
        download_tracker.set_last_download_time("SSA Contract Forecast")
        local_logger.info("Updated download tracker with current time")
        
        # Update the ScraperStatus table to indicate success
        update_scraper_status("SSA Contract Forecast", "working", None)
            
        return True
    except ImportError as e:
        error_msg = f"Import error: {str(e)}"
        local_logger.error(error_msg)
        local_logger.error("Playwright module not found. Please install it with 'pip install playwright'")
        local_logger.error("Then run 'playwright install' to install the browsers")
        update_scraper_status("SSA Contract Forecast", "error", error_msg)
        raise
    except ScraperError as e:
        update_scraper_status("SSA Contract Forecast", "error", str(e))
        raise
    except Exception as e:
        error_msg = f"Error running scraper: {str(e)}"
        local_logger.error(error_msg)
        update_scraper_status("SSA Contract Forecast", "error", error_msg)
        raise ScraperError(error_msg)
    finally:
        if scraper:
            try:
                local_logger.info("Cleaning up scraper resources")
                scraper.cleanup()
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup: {str(cleanup_error)}") 