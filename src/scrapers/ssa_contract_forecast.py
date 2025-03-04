import os
import sys
import time
import datetime
import logging
import requests
import csv
import tempfile
from io import StringIO
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import glob
import pathlib
import re
import pandas as pd

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db import get_session, close_session
from src.database.models import Proposal, DataSource
from src.database.download_tracker import download_tracker

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Create downloads directory if it doesn't exist
downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
if not os.path.exists(downloads_dir):
    os.makedirs(downloads_dir)

# Set up logging
log_file = os.path.join(logs_dir, f'ssa_contract_forecast_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to {log_file}")

class SSAContractForecastScraper:
    """Scraper for the SSA Contract Forecast site"""
    
    def __init__(self, debug_mode=False):
        self.base_url = "https://www.ssa.gov/osdbu/contract-forecast-intro.html"
        self.source_name = "SSA Contract Forecast"
        self.debug_mode = debug_mode
        logger.info(f"Initializing scraper with debug_mode={debug_mode}")
    
    def setup_driver(self):
        """Set up and configure the Chrome WebDriver"""
        logging.info("Setting up Chrome WebDriver")
        chrome_options = webdriver.ChromeOptions()
        
        # Enable headless mode to prevent browser window from appearing
        if not self.debug_mode:
            chrome_options.add_argument("--headless")
        
        # Add these arguments to make Chrome more stable
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--window-size=1920,1080")  # Set a specific window size
        
        # Set download preferences
        download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
        # Ensure the download directory exists
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        logger.info(f"Setting download directory to {download_dir}")
        
        # Convert to absolute path
        download_dir_abs = os.path.abspath(download_dir)
        logger.info(f"Absolute download path: {download_dir_abs}")
        
        # More aggressive download preferences
        prefs = {
            "download.default_directory": download_dir_abs,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,
            "browser.download.manager.showWhenStarting": False,
            "browser.download.folderList": 2,  # Use custom folder
            "browser.helperApps.neverAsk.saveToDisk": "text/csv,application/csv,application/vnd.ms-excel,application/excel,application/x-excel,application/x-msexcel,text/comma-separated-values,application/octet-stream,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "browser.download.manager.useWindow": False,
            "browser.download.manager.focusWhenStarting": False,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            # Try to use the ChromeDriverManager to get the driver
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            logger.info("Successfully created Chrome WebDriver using ChromeDriverManager")
        except Exception as e:
            logger.error(f"Error creating Chrome WebDriver using ChromeDriverManager: {e}")
            # Fallback to using the system Chrome driver
            try:
                driver = webdriver.Chrome(options=chrome_options)
                logger.info("Successfully created Chrome WebDriver using system Chrome driver")
            except Exception as e:
                logger.error(f"Error creating Chrome WebDriver using system Chrome driver: {e}")
                raise
        
        # Set page load timeout
        driver.set_page_load_timeout(60)
        
        return driver
    
    def parse_date(self, date_str):
        """Parse a date string into a datetime object"""
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
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def parse_value(self, value_str):
        """Parse a value string into a float"""
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
            logger.warning(f"Could not parse value: {value_str}")
            return None
    
    def download_forecast_document(self, driver):
        """Download the FY25 SSA Contract Forecast document"""
        logger.info("Attempting to download the FY25 SSA Contract Forecast document")
        
        # Check if we have a valid file using the download tracker
        if download_tracker.verify_file_exists("SSA Contract Forecast", "*01072025*.xls*"):
            # Get the downloads directory
            download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
            
            # Find the matching files
            matching_files = list(pathlib.Path(download_dir).glob("*01072025*.xls*"))
            
            if matching_files:
                # Sort by modification time (most recent first)
                matching_files.sort(key=os.path.getmtime, reverse=True)
                latest_file = str(matching_files[0])
                logger.info(f"Found existing 2025 file, using it instead of downloading again: {latest_file}")
                return latest_file
        
        try:
            # Navigate to the base URL
            logger.info(f"Navigating to {self.base_url}")
            driver.get(self.base_url)
            
            # Wait for the page to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for the FY25 SSA Contract Forecast link
            logger.info("Looking for the FY25 SSA Contract Forecast link")
            forecast_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'FY25 SSA Contract Forecast')]")
            
            if not forecast_links:
                logger.warning("Could not find the FY25 SSA Contract Forecast link")
                # Try looking for it in the main menu
                forecast_links = driver.find_elements(By.XPATH, "//div[contains(@class, 'mainMenu')]//a[contains(text(), 'FY25 SSA Contract Forecast')]")
            
            if not forecast_links:
                logger.error("Could not find the FY25 SSA Contract Forecast link")
                return None
            
            # Click the link
            logger.info("Clicking the FY25 SSA Contract Forecast link")
            forecast_links[0].click()
            
            # Wait for the page to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for the download link specifically for the 2025 file
            logger.info("Looking for the 2025 download link")
            # First try to find links with 01072025 in the text or href
            download_links = driver.find_elements(By.XPATH, "//a[contains(text(), '01072025') or contains(@href, '01072025')]")
            
            # If not found, look for links with 2025 in the text or href
            if not download_links:
                logger.info("No links with '01072025' found, looking for links with '2025'")
                download_links = driver.find_elements(By.XPATH, "//a[contains(text(), '2025') or contains(@href, '2025')]")
            
            # If still not found, fall back to any Excel/PDF links
            if not download_links:
                logger.warning("No 2025 links found, falling back to any Excel/PDF links")
                download_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.xlsx') or contains(@href, '.xls') or contains(@href, '.pdf') or contains(@href, '.csv') or contains(@href, '.xlsm')]")
            
            if not download_links:
                logger.error("Could not find any download links")
                return None
            
            # Log all available download links for debugging
            logger.info(f"Found {len(download_links)} download links:")
            for i, link in enumerate(download_links):
                href = link.get_attribute('href')
                text = link.text
                logger.info(f"Link {i+1}: Text='{text}', Href='{href}'")
            
            # Click the first download link
            logger.info(f"Clicking the download link: {download_links[0].get_attribute('href')}")
            download_links[0].click()
            
            # Wait for the download to complete
            logger.info("Waiting for the download to complete")
            time.sleep(5)  # Initial wait
            
            # Get the most recent file in the downloads directory
            download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
            files = glob.glob(os.path.join(download_dir, "*"))
            if not files:
                logger.error("No files found in the downloads directory")
                return None
            
            # Sort by modification time (most recent first)
            files.sort(key=os.path.getmtime, reverse=True)
            
            # Get the most recent file
            latest_file = files[0]
            logger.info(f"Most recent file: {latest_file}")
            
            # Check if the file was just downloaded (within the last minute)
            if os.path.getmtime(latest_file) > time.time() - 60:
                # Check if the file contains 2025 in the name
                if "01072025" in os.path.basename(latest_file) or "2025" in os.path.basename(latest_file):
                    logger.info(f"Successfully downloaded 2025 file: {latest_file}")
                    # Update the download tracker
                    download_tracker.set_last_download_time("SSA Contract Forecast")
                    return latest_file
                else:
                    logger.warning(f"Downloaded file does not appear to be the 2025 file: {latest_file}")
                    # We'll still return it for now, but log a warning
                    return latest_file
            else:
                logger.warning("The most recent file is not from this download session")
                return None
            
        except Exception as e:
            logger.error(f"Error downloading forecast document: {e}")
            return None
    
    def process_excel(self, excel_file, session, data_source):
        """Process the Excel file and extract proposal data"""
        logger.info(f"Processing Excel file: {excel_file}")
        
        try:
            # Read the Excel file
            df = pd.read_excel(excel_file)
            
            # Check if the DataFrame is empty
            if df.empty:
                logger.error("Excel file is empty")
                return 0
            
            # Log the column names
            logger.info(f"Column names: {df.columns.tolist()}")
            
            # Based on examination, the SSA Excel file has headers at row 3 (0-indexed)
            header_row_idx = 3
            logger.info(f"Using header row at index {header_row_idx}")
            
            # Get the header row values
            header_values = df.iloc[header_row_idx].values
            
            # Create a mapping of column indices to header names
            col_mapping = {}
            for i, val in enumerate(header_values):
                if pd.notna(val) and str(val).strip():
                    col_mapping[i] = str(val).strip()
            
            # Create a new DataFrame with the data below the header row
            data_df = df.iloc[header_row_idx+1:].reset_index(drop=True)
            
            # Rename columns based on the mapping
            new_columns = [col_mapping.get(i, f"Unnamed_{i}") for i in range(len(data_df.columns))]
            data_df.columns = new_columns
            
            # Log the new column names
            logger.info(f"New column names: {data_df.columns.tolist()}")
            
            # Count of proposals added
            proposals_added = 0
            
            # Process each row
            for index, row in data_df.iterrows():
                try:
                    # Skip rows with no data
                    if pd.isna(row.iloc[0]) and pd.isna(row.iloc[1]):
                        continue
                    
                    # Extract values safely using iloc for positional access
                    # This avoids the ambiguity with duplicate column names
                    site_type = row.iloc[0] if pd.notna(row.iloc[0]) else None
                    app_num = row.iloc[1] if pd.notna(row.iloc[1]) else None
                    requirement_type = row.iloc[2] if pd.notna(row.iloc[2]) else None
                    description = row.iloc[3] if pd.notna(row.iloc[3]) else None
                    est_cost = row.iloc[4] if pd.notna(row.iloc[4]) else None
                    award_date_str = row.iloc[5] if pd.notna(row.iloc[5]) else None
                    existing_award = row.iloc[6] if pd.notna(row.iloc[6]) else None
                    contract_type = row.iloc[7] if pd.notna(row.iloc[7]) else None
                    incumbent = row.iloc[8] if pd.notna(row.iloc[8]) else None
                    naics_code = row.iloc[9] if pd.notna(row.iloc[9]) else None
                    naics_desc = row.iloc[10] if pd.notna(row.iloc[10]) else None
                    competition_type = row.iloc[11] if pd.notna(row.iloc[11]) else None
                    obligated_amt = row.iloc[12] if pd.notna(row.iloc[12]) else None
                    place_of_performance = row.iloc[13] if pd.notna(row.iloc[13]) else None
                    completion_date = row.iloc[14] if pd.notna(row.iloc[14]) else None
                    
                    # Skip rows without a description
                    if not description:
                        continue
                    
                    # Parse dates
                    release_date = None
                    response_date = None
                    award_date = self.parse_date(award_date_str) if award_date_str else None
                    
                    # Parse estimated value
                    estimated_value = self.parse_value(est_cost) if est_cost else None
                    
                    # Create a unique external ID
                    external_id = f"SSA_{app_num}" if app_num else None
                    
                    # Check if this proposal already exists
                    existing_proposal = None
                    if external_id:
                        existing_proposal = session.query(Proposal).filter(
                            Proposal.external_id == external_id,
                            Proposal.source_id == data_source.id
                        ).first()
                    
                    if not existing_proposal:
                        # Create a new proposal
                        proposal = Proposal(
                            source_id=data_source.id,
                            external_id=external_id,
                            title=description,
                            agency="Social Security Administration",
                            office=site_type,
                            description=description,
                            naics_code=naics_code,
                            estimated_value=estimated_value,
                            release_date=release_date,
                            response_date=response_date,
                            contact_info=None,
                            url=self.base_url,
                            status=None,
                            contract_type=contract_type,
                            set_aside=None,
                            competition_type=competition_type,
                            solicitation_number=app_num,
                            award_date=award_date,
                            place_of_performance=place_of_performance,
                            incumbent=incumbent,
                            is_latest=True
                        )
                        
                        session.add(proposal)
                        proposals_added += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {index}: {e}")
                    continue
            
            # Commit the changes
            session.commit()
            logger.info(f"Added {proposals_added} proposals from Excel file")
            
            return proposals_added
            
        except Exception as e:
            logger.error(f"Error processing Excel file: {e}")
            return 0
    
    def process_pdf(self, pdf_file, session, data_source):
        """Process the PDF file and extract proposal data"""
        logger.info(f"Processing PDF file: {pdf_file}")
        
        try:
            # For PDF processing, we would need to use a library like PyPDF2 or pdfplumber
            # This is a placeholder for now
            logger.warning("PDF processing is not implemented yet")
            return 0
            
        except Exception as e:
            logger.error(f"Error processing PDF file: {e}")
            return 0
    
    def cleanup_downloads(self):
        """Remove any non-2025 files from the downloads directory"""
        try:
            download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
            files = glob.glob(os.path.join(download_dir, "*"))
            
            # Find files that specifically contain "11042024" in their name (the non-2025 files)
            # and were modified in the last hour
            current_time = time.time()
            one_hour_ago = current_time - 3600  # 1 hour in seconds
            
            for file_path in files:
                file_name = os.path.basename(file_path)
                file_mod_time = os.path.getmtime(file_path)
                
                # Check if the file was modified in the last hour and contains "11042024" in the name
                if file_mod_time > one_hour_ago and "11042024" in file_name:
                    # Check if it's an Excel or PDF file (to avoid deleting other important files)
                    if file_path.endswith('.xlsx') or file_path.endswith('.xls') or file_path.endswith('.xlsm') or file_path.endswith('.pdf') or file_path.endswith('.csv'):
                        logger.info(f"Removing non-2025 file: {file_path}")
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            logger.error(f"Error removing file {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def scrape(self):
        """Main scraping function"""
        logger.info("Starting scrape")
        
        # Set up the driver
        driver = None
        try:
            driver = self.setup_driver()
            
            # Get a database session
            session = get_session()
            
            # Check if the data source exists
            data_source = session.query(DataSource).filter(DataSource.name == self.source_name).first()
            
            # If the data source doesn't exist, create it
            if not data_source:
                logger.info(f"Creating new data source: {self.source_name}")
                data_source = DataSource(
                    name=self.source_name,
                    url=self.base_url,
                    description="SSA Contract Forecast data source"
                )
                session.add(data_source)
                session.commit()
            
            # Download the forecast document
            forecast_file = self.download_forecast_document(driver)
            
            if not forecast_file:
                logger.error("Failed to download forecast document")
                close_session(session)
                if driver:
                    driver.quit()
                return False
            
            # Check if the downloaded file is the 2025 file
            if not ("01072025" in os.path.basename(forecast_file) or "2025" in os.path.basename(forecast_file)):
                logger.warning(f"Downloaded file does not appear to be the 2025 file: {forecast_file}")
                
                # Try to find a 2025 file in the downloads directory
                download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
                files = glob.glob(os.path.join(download_dir, "*"))
                
                # Filter for files with 01072025 or 2025 in the name
                year_2025_files = [f for f in files if "01072025" in os.path.basename(f) or "2025" in os.path.basename(f)]
                
                if year_2025_files:
                    # Sort by modification time (most recent first)
                    year_2025_files.sort(key=os.path.getmtime, reverse=True)
                    forecast_file = year_2025_files[0]
                    logger.info(f"Found 2025 file in downloads directory: {forecast_file}")
                else:
                    logger.warning("Could not find any 2025 files in the downloads directory")
            
            # Process the forecast document based on its type
            proposals_added = 0
            if forecast_file.endswith('.xlsx') or forecast_file.endswith('.xls') or forecast_file.endswith('.xlsm'):
                proposals_added = self.process_excel(forecast_file, session, data_source)
            elif forecast_file.endswith('.pdf'):
                proposals_added = self.process_pdf(forecast_file, session, data_source)
            else:
                logger.error(f"Unsupported file type: {forecast_file}")
            
            # Update the last scraped timestamp
            data_source.last_scraped = datetime.datetime.utcnow()
            session.commit()
            
            # Update the download tracker
            download_tracker.set_last_download_time(self.source_name)
            
            logger.info(f"Scrape completed. Added {proposals_added} proposals.")
            
            # Clean up any non-2025 files
            self.cleanup_downloads()
            
            # Close the session
            close_session(session)
            
            return True
            
        except Exception as e:
            logger.error(f"Error during scrape: {e}")
            return False
            
        finally:
            # Clean up
            if driver:
                driver.quit()

def run_scraper(force=False):
    """Run the scraper if it's time or if forced"""
    try:
        # Get the scrape interval from environment or use default (24 hours)
        scrape_interval_hours = int(os.getenv("SCRAPE_INTERVAL_HOURS", 24))
        
        # Check if we should run the scraper using the download tracker
        if force or download_tracker.should_download("SSA Contract Forecast", scrape_interval_hours):
            logger.info(f"Running scraper (force={force})")
            
            # Create and run the scraper
            scraper = SSAContractForecastScraper(debug_mode=os.getenv("DEBUG", "False").lower() == "true")
            return scraper.scrape()
        else:
            logger.info(f"Skipping scrape (interval={scrape_interval_hours} hours)")
            return True
            
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        return False

if __name__ == "__main__":
    # Run the scraper with force=True to run regardless of when it was last run
    run_scraper(force=True) 