"""SSA Contract Forecast scraper."""

# Standard library imports
import os
import traceback

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Proposal
from app.database.download_tracker import DownloadTracker
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.utils.db_utils import update_scraper_status
from app.config import SSA_CONTRACT_FORECAST_URL
from app.utils.scraper_utils import (
    check_url_accessibility,
    download_file,
    wait_for_download,
    wait_for_element,
    wait_for_selector,
    wait_for_network_idle,
    wait_for_load_state,
    save_permanent_copy,
    read_dataframe,
    transform_dataframe,
    handle_scraper_error
)

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.ssa_contract_forecast")

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
        """Save debug information when Excel link is not found."""
        # Save a screenshot for debugging
        screenshot_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'downloads', 'page_screenshot.png')
        self.page.screenshot(path=screenshot_path)
        self.logger.info(f"Saved screenshot to {screenshot_path}")
        
        # Save page content for debugging
        html_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'downloads', 'page_content.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.page.content())
        self.logger.info(f"Saved page content to {html_path}")
    
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
            temp_path = download_file(self.page, f'a[href="{excel_link}"]')
            return save_permanent_copy(temp_path, self.source_name, 'xlsx')
            
        except PlaywrightTimeoutError as e:
            handle_scraper_error(e, self.source_name, "Timeout downloading forecast document")
            raise ScraperError(f"Timeout downloading forecast document: {str(e)}")
        except Exception as e:
            handle_scraper_error(e, self.source_name, "Error downloading forecast document")
            raise ScraperError(f"Failed to download forecast document: {str(e)}")
    
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
            df = read_dataframe(excel_file, 'xlsx')
            
            # Get field mapping
            field_mapping = self._get_field_mapping()
            
            # Transform the data
            transformed_data = transform_dataframe(
                df=df,
                column_mapping=field_mapping,
                date_columns=['release_date', 'response_date', 'award_date'],
                value_columns=['estimated_value'],
                parse_funcs={
                    'date': self.parse_date,
                    'value': self.parse_value
                }
            )
            
            # Process each row
            count = 0
            for item in transformed_data:
                try:
                    # Add source_id
                    item['source_id'] = data_source.id
                    
                    # Get or create proposal
                    proposal_query = self.get_proposal_query(session, item)
                    if proposal_query:
                        count += 1
                except Exception as e:
                    self.logger.error(f"Error processing row: {str(e)}")
                    continue
            
            return count
            
        except Exception as e:
            handle_scraper_error(e, self.source_name, "Failed to process Excel file")
            raise ScraperError(f"Failed to process Excel file: {str(e)}")
    
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
            handle_scraper_error(ScraperError(error_msg), "SSA Contract Forecast")
            raise ScraperError(error_msg)
        
        # Run the scraper
        local_logger.info("Running SSA Contract Forecast scraper")
        success = scraper.scrape()
        
        # If scraper.scrape() returns False, it means an error occurred
        if not success:
            error_msg = "Scraper failed without specific error"
            handle_scraper_error(ScraperError(error_msg), "SSA Contract Forecast")
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
        handle_scraper_error(e, "SSA Contract Forecast", "Import error")
        raise
    except ScraperError as e:
        handle_scraper_error(e, "SSA Contract Forecast")
        raise
    except Exception as e:
        handle_scraper_error(e, "SSA Contract Forecast", "Error running scraper")
        raise ScraperError(error_msg)
    finally:
        if scraper:
            try:
                local_logger.info("Cleaning up scraper resources")
                scraper.cleanup()
            except Exception as cleanup_error:
                local_logger.error(f"Error during scraper cleanup: {str(cleanup_error)}") 