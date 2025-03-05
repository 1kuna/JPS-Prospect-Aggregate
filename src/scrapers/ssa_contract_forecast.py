"""SSA Contract Forecast scraper."""

# Import from common imports module
from src.utils.imports import (
    os, sys, time, datetime, traceback,
    pd, PlaywrightTimeoutError,
    logging
)

# Import from base scraper
from src.scrapers.base_scraper import BaseScraper

# Import from database
from src.database.db import session_scope

# Import from exceptions
from src.exceptions import ScraperError, ParsingError

# Import from config
from src.config import SSA_CONTRACT_FORECAST_URL

class SSAContractForecastScraper(BaseScraper):
    """Scraper for the SSA Contract Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the SSA Contract Forecast scraper."""
        super().__init__(
            source_name="SSA Contract Forecast",
            base_url=SSA_CONTRACT_FORECAST_URL,
            debug_mode=debug_mode
        )
    
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
            self.page.goto(self.base_url)
            
            # Wait for the page to load
            self.page.wait_for_load_state('networkidle')
            self.logger.info("Page loaded")
            
            # Look for Excel file link
            excel_link = None
            
            # Try different selectors to find the Excel link
            selectors = [
                'a[href$=".xlsx"]',
                'a[href$=".xls"]',
                'a:has-text("Excel")',
                'a:has-text("Forecast")'
            ]
            
            for selector in selectors:
                links = self.page.query_selector_all(selector)
                if links:
                    for link in links:
                        href = link.get_attribute('href')
                        if href and ('.xls' in href.lower() or 'forecast' in href.lower()):
                            excel_link = href
                            self.logger.info(f"Found Excel link: {excel_link}")
                            break
                if excel_link:
                    break
            
            if not excel_link:
                self.logger.error("Could not find Excel link on the page")
                return None
            
            # Download the file
            self.logger.info(f"Downloading file from {excel_link}")
            
            # Start the download
            with self.page.expect_download() as download_info:
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
        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout downloading forecast document: {str(e)}")
            raise ScraperError(f"Timeout downloading forecast document: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error downloading forecast document: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Failed to download forecast document: {str(e)}")
    
    def process_excel(self, excel_file, session, data_source):
        """
        Process the downloaded Excel file and save data to the database.
        
        Args:
            excel_file (str): Path to the Excel file
            session: SQLAlchemy session
            data_source: DataSource object
            
        Returns:
            int: Number of proposals processed
        """
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
            
            # Map the Excel columns to database fields
            field_mapping = {
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
            
            # Create a mapping from Excel columns to database fields
            column_mapping = {}
            for excel_col in df.columns:
                for map_col, db_field in field_mapping.items():
                    if excel_col.lower() == map_col.lower():
                        column_mapping[excel_col] = db_field
                        break
            
            self.logger.info(f"Column mapping: {column_mapping}")
            
            # Process each row
            count = 0
            for _, row in df.iterrows():
                try:
                    # Create a new proposal object
                    proposal_data = {
                        'source_id': data_source.id,
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
                    
                    # Ensure required fields are present
                    if 'title' not in proposal_data or not proposal_data['title']:
                        self.logger.warning(f"Skipping row without title: {row}")
                        continue
                    
                    # Set SSA as the agency if not specified
                    if 'agency' not in proposal_data or not proposal_data['agency']:
                        proposal_data['agency'] = 'Social Security Administration'
                    
                    # Check if this proposal already exists
                    existing = self.get_proposal_query(session, proposal_data)
                    
                    if existing:
                        # Update the existing proposal
                        for key, value in proposal_data.items():
                            setattr(existing, key, value)
                        self.logger.info(f"Updated existing proposal: {proposal_data['title']}")
                    else:
                        # Create a new proposal
                        from src.database.models import Proposal
                        proposal = Proposal(**proposal_data)
                        session.add(proposal)
                        self.logger.info(f"Added new proposal: {proposal_data['title']}")
                    
                    count += 1
                except Exception as e:
                    self.logger.error(f"Error processing row: {str(e)}")
                    self.logger.error(f"Row data: {row}")
                    # Continue with the next row
            
            self.logger.info(f"Processed {count} proposals")
            return count
        except Exception as e:
            self.logger.error(f"Error processing Excel file: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ParsingError(f"Failed to process Excel file: {str(e)}")
    
    def get_proposal_query(self, session, proposal_data):
        """
        Get a query to find an existing proposal.
        
        Args:
            session: SQLAlchemy session
            proposal_data (dict): Proposal data
            
        Returns:
            Query: SQLAlchemy query
        """
        from src.database.models import Proposal
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
        self.logger.info("Starting SSA Contract Forecast scraper")
        
        try:
            # Set up the browser
            self.setup_browser()
            
            # Download the forecast document
            excel_file = self.download_forecast_document()
            
            if not excel_file:
                self.logger.error("Failed to download forecast document")
                return False
            
            # Process the data and save to the database
            with session_scope() as session:
                # Get or create the data source
                data_source = self.get_or_create_data_source(session)
                
                # Process the Excel file
                count = self.process_excel(excel_file, session, data_source)
                
                # Update the last_scraped timestamp
                data_source.last_scraped = datetime.datetime.utcnow()
                session.commit()
            
            self.logger.info(f"Scraper completed successfully, processed {count} proposals")
            return True
        except Exception as e:
            self.logger.error(f"Error running scraper: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
        finally:
            # Clean up resources
            self.cleanup_browser()
            self.cleanup_downloads()

def run_scraper(force=False):
    """
    Run the SSA Contract Forecast scraper.
    
    Args:
        force (bool): Whether to force the scraper to run even if it ran recently
        
    Returns:
        bool: True if scraping was successful, False otherwise
    """
    logger = logging.getLogger("scraper.ssa_contract_forecast")
    
    try:
        # Create and run the scraper
        scraper = SSAContractForecastScraper(debug_mode=False)
        return scraper.scrape()
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        logger.error(traceback.format_exc())
        return False 