"""Acquisition Gateway scraper."""

# Import from common imports module
from src.utils.imports import (
    os, sys, time, datetime, traceback,
    requests, BeautifulSoup, PlaywrightTimeoutError,
    logging
)

# Import from base scraper
from src.scrapers.base_scraper import BaseScraper

# Import from database
from src.database.db import session_scope
from src.database.models import Proposal
from src.database.download_tracker import download_tracker

# Import from exceptions
from src.exceptions import ScraperError

# Import from config
from src.config import ACQUISITION_GATEWAY_URL

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
    
    def extract_table_data(self):
        """Extract data from the forecast table."""
        self.logger.info("Extracting table data")
        
        # Wait for the table to load
        self.page.wait_for_selector('table', state='visible')
        
        # Extract the table HTML
        table_html = self.page.query_selector('table').inner_html()
        
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(f"<table>{table_html}</table>", 'html.parser')
        
        # Extract the table rows
        rows = soup.find_all('tr')
        
        # Extract the headers
        headers = [th.text.strip() for th in rows[0].find_all('th')]
        
        # Extract the data rows
        data = []
        for row in rows[1:]:
            cells = row.find_all('td')
            if cells:
                row_data = {headers[i]: cell.text.strip() for i, cell in enumerate(cells) if i < len(headers)}
                data.append(row_data)
        
        self.logger.info(f"Extracted {len(data)} rows from table")
        return data
    
    def process_table_data(self, table_data, session, data_source):
        """
        Process the extracted table data and save to the database.
        
        Args:
            table_data (list): List of dictionaries containing the table data
            session: SQLAlchemy session
            data_source: DataSource object
            
        Returns:
            int: Number of proposals processed
        """
        self.logger.info(f"Processing {len(table_data)} rows of table data")
        
        count = 0
        for row in table_data:
            try:
                # Extract the data from the row
                title = row.get('Title', '')
                agency = row.get('Agency', '')
                description = row.get('Description', '')
                naics_code = row.get('NAICS', '')
                estimated_value = self.parse_value(row.get('Estimated Value', ''))
                release_date = self.parse_date(row.get('Release Date', ''))
                response_date = self.parse_date(row.get('Response Date', ''))
                contact_info = row.get('Contact', '')
                
                # Skip rows without a title
                if not title:
                    continue
                
                # Create a proposal data dictionary
                proposal_data = {
                    'source_id': data_source.id,
                    'title': title,
                    'agency': agency,
                    'description': description,
                    'naics_code': naics_code,
                    'estimated_value': estimated_value,
                    'release_date': release_date,
                    'response_date': response_date,
                    'contact_info': contact_info,
                    'url': self.base_url,
                    'is_latest': True
                }
                
                # Use the base class method to check for existing proposals
                existing = self.get_proposal_query(session, proposal_data)
                
                if existing:
                    # Update the existing proposal
                    for key, value in proposal_data.items():
                        setattr(existing, key, value)
                    self.logger.info(f"Updated existing proposal: {title}")
                else:
                    # Create a new proposal
                    proposal = Proposal(**proposal_data)
                    session.add(proposal)
                    self.logger.info(f"Added new proposal: {title}")
                
                count += 1
            except Exception as e:
                self.logger.error(f"Error processing row: {str(e)}")
                self.logger.error(f"Row data: {row}")
                # Continue with the next row
        
        self.logger.info(f"Processed {count} proposals")
        return count
    
    def scrape(self):
        """
        Run the scraper to extract and process data.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        return self.scrape_with_structure(
            setup_func=self.navigate_to_forecast_page,
            extract_func=self.extract_table_data,
            process_func=self.process_table_data
        )

def check_last_download():
    """
    Check when the last download was performed.
    
    Returns:
        bool: True if a download was performed in the last 24 hours, False otherwise
    """
    logger = logging.getLogger("scraper.acquisition_gateway")
    
    try:
        # Check if we should download using the download tracker
        scrape_interval_hours = 24  # Default to 24 hours
        
        if download_tracker.should_download("Acquisition Gateway", scrape_interval_hours):
            logger.info("No recent download found, proceeding with scrape")
            return False
        else:
            logger.info(f"Recent download found (within {scrape_interval_hours} hours), skipping scrape")
            return True
    except Exception as e:
        logger.error(f"Error checking last download: {str(e)}")
        return False

def run_scraper(force=False):
    """
    Run the Acquisition Gateway scraper.
    
    Args:
        force (bool): Whether to force the scraper to run even if it ran recently
        
    Returns:
        bool: True if scraping was successful, False otherwise
    """
    logger = logging.getLogger("scraper.acquisition_gateway")
    
    try:
        # Check if we should run the scraper
        if not force and check_last_download():
            logger.info("Skipping scrape due to recent download")
            return True
        
        # Create an instance of the scraper to use its methods
        scraper = AcquisitionGatewayScraper(debug_mode=False)
        
        # Check if the URL is accessible using the scraper's method
        if not scraper.check_url_accessibility():
            logger.error(f"URL {ACQUISITION_GATEWAY_URL} is not accessible")
            return False
        
        # Check if Playwright is installed
        try:
            from playwright.sync_api import sync_playwright
            logger.info("Playwright module found")
        except ImportError:
            logger.error("Playwright module not found. Please install it with 'pip install playwright'")
            logger.error("Then run 'playwright install' to install the browsers")
            return False
        
        # Run the scraper
        logger.info("Running Acquisition Gateway scraper")
        return scraper.scrape()
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    run_scraper() 