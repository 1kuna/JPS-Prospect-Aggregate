import os
import sys
import time
import datetime
import logging
from logging.handlers import RotatingFileHandler
import requests
import csv
import tempfile
from io import StringIO
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import glob
import pathlib
import re

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db import get_session, close_session, session_scope
from src.database.models import Proposal, DataSource
from src.database.download_tracker import download_tracker
from src.config import (
    LOGS_DIR, DOWNLOADS_DIR, 
    PAGE_NAVIGATION_TIMEOUT, PAGE_ELEMENT_TIMEOUT, TABLE_LOAD_TIMEOUT, DOWNLOAD_TIMEOUT,
    CSV_ENCODINGS, FILE_FRESHNESS_SECONDS, ACQUISITION_GATEWAY_URL,
    LOG_FORMAT, LOG_FILE_MAX_BYTES, LOG_FILE_BACKUP_COUNT
)

# Set up logging with a rotating file handler
log_file = os.path.join(LOGS_DIR, 'acquisition_gateway.log')
# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Create handlers
# RotatingFileHandler will rotate log files when they reach the configured size
file_handler = RotatingFileHandler(log_file, maxBytes=LOG_FILE_MAX_BYTES, backupCount=LOG_FILE_BACKUP_COUNT)
console_handler = logging.StreamHandler()
# Create formatters and add them to handlers
formatter = logging.Formatter(LOG_FORMAT)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info(f"Logging to {log_file}")

class AcquisitionGatewayScraper:
    """Scraper for the Acquisition Gateway Forecast site"""
    
    def __init__(self, debug_mode=False):
        self.base_url = ACQUISITION_GATEWAY_URL
        self.source_name = "Acquisition Gateway Forecast"
        self.debug_mode = debug_mode
        logger.info(f"Initializing scraper with debug_mode={debug_mode}")
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def setup_browser(self):
        """Set up and configure the Playwright browser"""
        logging.info("Setting up Playwright browser")
        
        # Get the downloads directory
        download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
        # Ensure the download directory exists
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        logger.info(f"Setting download directory to {download_dir}")
        
        # Convert to absolute path
        download_dir_abs = os.path.abspath(download_dir)
        logger.info(f"Absolute download path: {download_dir_abs}")
        
        try:
            # Start Playwright
            self.playwright = sync_playwright().start()
            logger.info("Started Playwright")
            
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
            logger.info("Launched browser")
            
            # Create a new context with download options
            self.context = self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            logger.info("Created browser context")
            
            # Create a new page
            self.page = self.context.new_page()
            logger.info("Created page")
            
            # Set default timeout
            self.page.set_default_timeout(60000)  # 60 seconds
            
            logger.info("Playwright browser setup complete")
            return True
        except Exception as e:
            logger.error(f"Error setting up Playwright browser: {e}")
            self.cleanup_browser()
            return False
    
    def cleanup_browser(self):
        """Clean up Playwright resources"""
        logger.info("Cleaning up Playwright resources")
        try:
            if self.page:
                logger.info("Closing page")
                self.page.close()
                self.page = None
        except Exception as e:
            logger.error(f"Error closing page: {e}")
        
        try:
            if self.context:
                logger.info("Closing context")
                self.context.close()
                self.context = None
        except Exception as e:
            logger.error(f"Error closing context: {e}")
        
        try:
            if self.browser:
                logger.info("Closing browser")
                self.browser.close()
                self.browser = None
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
        
        try:
            if self.playwright:
                logger.info("Stopping playwright")
                self.playwright.stop()
                self.playwright = None
        except Exception as e:
            logger.error(f"Error stopping playwright: {e}")
    
    def parse_date(self, date_str):
        """Parse date string into datetime object"""
        if not date_str or date_str.strip() == "":
            return None
        
        try:
            # Clean up the date string
            date_str = date_str.strip()
            
            # Handle fiscal year quarter format (e.g., "4th (July 1 - September 30)")
            if "1st" in date_str and "October" in date_str:
                # 1st quarter (Oct-Dec)
                return datetime.datetime(int(date_str.split()[-1].strip(")")), 10, 1)
            elif "2nd" in date_str and "January" in date_str:
                # 2nd quarter (Jan-Mar)
                return datetime.datetime(int(date_str.split()[-1].strip(")")), 1, 1)
            elif "3rd" in date_str and "April" in date_str:
                # 3rd quarter (Apr-Jun)
                return datetime.datetime(int(date_str.split()[-1].strip(")")), 4, 1)
            elif "4th" in date_str and "July" in date_str:
                # 4th quarter (Jul-Sep)
                return datetime.datetime(int(date_str.split()[-1].strip(")")), 7, 1)
            
            # Try to extract year from parentheses if present
            if "(" in date_str and ")" in date_str:
                year_match = re.search(r'\(.*?(\d{4}).*?\)', date_str)
                if year_match:
                    year = int(year_match.group(1))
                    # If we have a month name in the string, try to parse it
                    month_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)', date_str, re.IGNORECASE)
                    if month_match:
                        month_name = month_match.group(1)
                        month_num = {
                            'january': 1, 'february': 2, 'march': 3, 'april': 4,
                            'may': 5, 'june': 6, 'july': 7, 'august': 8,
                            'september': 9, 'october': 10, 'november': 11, 'december': 12
                        }[month_name.lower()]
                        return datetime.datetime(year, month_num, 1)
            
            # If it's just a year, return January 1st of that year
            if re.match(r'^\d{4}$', date_str):
                return datetime.datetime(int(date_str), 1, 1)
            
            # Try different date formats
            for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d-%b-%Y", "%d/%m/%Y"]:
                try:
                    return datetime.datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
        
        return None
    
    def parse_value(self, value_str):
        """Parse estimated value string into float"""
        if not value_str or value_str.strip() == "":
            return None
        
        try:
            # Remove currency symbols and commas
            clean_value = value_str.replace("$", "").replace(",", "").strip()
            
            # Check for ranges (e.g., "$1M - $5M")
            if "-" in clean_value:
                parts = clean_value.split("-")
                # Take the average of the range
                return (self.convert_to_number(parts[0]) + self.convert_to_number(parts[1])) / 2
            
            return self.convert_to_number(clean_value)
        except Exception as e:
            logger.error(f"Error parsing value {value_str}: {e}")
        
        return None
    
    def convert_to_number(self, value_str):
        """Convert string with K, M, B suffixes to number"""
        value_str = value_str.strip().upper()
        
        multiplier = 1
        if value_str.endswith("K"):
            multiplier = 1000
            value_str = value_str[:-1]
        elif value_str.endswith("M"):
            multiplier = 1000000
            value_str = value_str[:-1]
        elif value_str.endswith("B"):
            multiplier = 1000000000
            value_str = value_str[:-1]
        
        try:
            return float(value_str) * multiplier
        except ValueError:
            return 0
    
    def download_csv(self):
        """Download the CSV file from the Acquisition Gateway Forecast site"""
        logger.info("Attempting to download the CSV file from the Acquisition Gateway Forecast site")
        
        # Check if we have a valid file using the download tracker
        if download_tracker.verify_file_exists("Acquisition Gateway Forecast", "*.csv"):
            # Get the downloads directory
            download_dir = DOWNLOADS_DIR
            
            # Find the matching files
            matching_files = list(pathlib.Path(download_dir).glob("*.csv"))
            
            if matching_files:
                # Sort by modification time (most recent first)
                matching_files.sort(key=os.path.getmtime, reverse=True)
                latest_file = str(matching_files[0])
                
                # Check if the file is recent enough (within the configured freshness period)
                if os.path.getmtime(latest_file) > time.time() - FILE_FRESHNESS_SECONDS:
                    logger.info(f"Found existing CSV file, using it instead of downloading again: {latest_file}")
                    return latest_file
        
        try:
            # Navigate to the base URL
            logger.info(f"Navigating to {self.base_url}")
            self.page.goto(self.base_url, wait_until="networkidle", timeout=PAGE_NAVIGATION_TIMEOUT)
            
            # Wait for the page to load
            logger.info("Waiting for page to load")
            self.page.wait_for_selector("body", state="visible", timeout=PAGE_ELEMENT_TIMEOUT)
            
            # Take a screenshot for debugging
            screenshot_path = os.path.join(LOGS_DIR, f'acquisition_gateway_initial_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            self.page.screenshot(path=screenshot_path)
            logger.info(f"Initial page screenshot saved to {screenshot_path}")
            
            # Wait for the table to load
            logger.info("Waiting for the table to load")
            try:
                self.page.wait_for_selector("table", timeout=TABLE_LOAD_TIMEOUT, state="visible")
                logger.info("Table loaded successfully")
            except PlaywrightTimeoutError:
                logger.warning("Table did not load within timeout, continuing anyway")
            
            # Save the page HTML for analysis
            html_path = os.path.join(LOGS_DIR, f'acquisition_gateway_page_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.page.content())
            logger.info(f"Saved page HTML to {html_path} for analysis")
            
            # Look specifically for the "Export CSV" button
            logger.info("Looking for the 'Export CSV' button")
            
            # Try various selectors that might match the Export CSV button
            export_selectors = [
                "button:has-text('Export CSV')",
                "button:has-text('Export')",
                "button.usa-button:has-text('Export')",
                "button.export-button",
                "[aria-label='Export CSV']",
                "[aria-label='Export']",
                "[title='Export CSV']",
                "[title='Export']",
                "button.usa-button",  # Try any USA button
                "button.ag-button",   # Try any AG button
                "button.download-button",
                "button.csv-button"
            ]
            
            export_button = None
            for selector in export_selectors:
                logger.info(f"Trying selector: {selector}")
                buttons = self.page.query_selector_all(selector)
                for button in buttons:
                    text = button.inner_text().strip()
                    logger.info(f"Found button with text: '{text}'")
                    if "export" in text.lower() or "csv" in text.lower() or "download" in text.lower():
                        export_button = button
                        logger.info(f"Found export button with text: '{text}'")
                        break
                if export_button:
                    break
            
            if not export_button:
                # Try to find any buttons on the page and log their text
                logger.info("No export button found with specific selectors, checking all buttons")
                all_buttons = self.page.query_selector_all("button")
                logger.info(f"Found {len(all_buttons)} buttons on the page")
                for i, button in enumerate(all_buttons):
                    try:
                        text = button.inner_text().strip()
                        logger.info(f"Button {i+1}: '{text}'")
                        if "export" in text.lower() or "csv" in text.lower() or "download" in text.lower():
                            export_button = button
                            logger.info(f"Found potential export button with text: '{text}'")
                            break
                    except Exception as e:
                        logger.warning(f"Could not get text for button {i+1}: {e}")
            
            if not export_button:
                # Take a screenshot for debugging
                screenshot_path = os.path.join(LOGS_DIR, f'acquisition_gateway_no_export_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                self.page.screenshot(path=screenshot_path)
                logger.error(f"Could not find any export buttons. Screenshot saved to {screenshot_path}")
                return None
            
            # Click the export button and wait for download
            logger.info(f"Clicking the export button")
            
            # Get the downloads directory
            download_dir = DOWNLOADS_DIR
            
            # Start waiting for the download with the configured timeout
            with self.page.expect_download(timeout=DOWNLOAD_TIMEOUT) as download_info:
                try:
                    # Click the export button
                    export_button.click()
                    logger.info("Clicked export button, waiting for download to start")
                except Exception as e:
                    logger.error(f"Error clicking export button: {e}")
                    return None
            
            try:
                # Get the download object
                download = download_info.value
                logger.info(f"Download started: {download.suggested_filename}")
                
                # Wait for the download to complete and save to the downloads directory
                download_path = os.path.join(download_dir, download.suggested_filename)
                download.save_as(download_path)
                logger.info(f"Download completed and saved to: {download_path}")
                
                # Update the download tracker
                download_tracker.set_last_download_time("Acquisition Gateway Forecast")
                
                # Return the path to the downloaded file
                return download_path
            except Exception as e:
                logger.error(f"Error handling download: {e}")
                
                # Try a fallback approach if the download fails
                logger.info("Trying fallback approach to detect downloaded file")
                
                # Get list of files before and after a short wait
                before_files = set(os.listdir(download_dir))
                time.sleep(10)  # Wait a bit more for any potential downloads
                after_files = set(os.listdir(download_dir))
                new_files = after_files - before_files
                
                if new_files:
                    new_file = os.path.join(download_dir, list(new_files)[0])
                    logger.info(f"Found new file using fallback method: {new_file}")
                    
                    # Update the download tracker
                    download_tracker.set_last_download_time("Acquisition Gateway Forecast")
                    
                    return new_file
                
                logger.error("No download detected even with fallback method")
                return None
            
        except Exception as e:
            logger.error(f"Error downloading CSV file: {e}")
            
            # Take a screenshot for debugging
            try:
                screenshot_path = os.path.join(LOGS_DIR, f'acquisition_gateway_error_screenshot_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                self.page.screenshot(path=screenshot_path)
                logger.error(f"Error screenshot saved to {screenshot_path}")
            except Exception as screenshot_error:
                logger.error(f"Could not take error screenshot: {screenshot_error}")
                
            return None
    
    def process_csv(self, csv_file, session, data_source):
        """Process the downloaded CSV file and update the database
        
        Returns:
            int: Number of new proposals added to the database
        """
        try:
            logger.info(f"Processing file: {csv_file}")
            
            # Check if file exists
            if not os.path.exists(csv_file):
                logger.error(f"File does not exist: {csv_file}")
                return 0
            
            # Check file size
            file_size = os.path.getsize(csv_file)
            logger.info(f"File size: {file_size} bytes")
            
            if file_size == 0:
                logger.error("File is empty")
                return 0
            
            # Check file extension
            file_ext = os.path.splitext(csv_file)[1].lower()
            
            # Process based on file type
            if file_ext in ['.xlsx', '.xls']:
                # Process Excel file
                return self.process_excel(csv_file, session, data_source)
            
            # Process CSV file
            # Try different encodings from the configuration
            csv_data = None
            
            for encoding in CSV_ENCODINGS:
                try:
                    with open(csv_file, 'r', encoding=encoding) as f:
                        # Read the first few lines to check the format
                        sample = f.read(1024)
                        f.seek(0)  # Reset file pointer
                        
                        logger.info(f"CSV sample with {encoding} encoding: {sample[:100]}...")
                        
                        # Try to parse the CSV
                        csv_reader = csv.DictReader(f)
                        field_names = csv_reader.fieldnames
                        
                        if not field_names:
                            logger.warning(f"No field names found with {encoding} encoding")
                            continue
                        
                        logger.info(f"CSV fields: {field_names}")
                        
                        # Store the data for processing
                        csv_data = list(csv_reader)
                        logger.info(f"Found {len(csv_data)} rows in CSV")
                        break
                        
                except Exception as e:
                    logger.warning(f"Error reading CSV with {encoding} encoding: {e}")
            
            if not csv_data:
                logger.error("Could not parse CSV file with any encoding")
                return 0
            
            # Get the current import timestamp
            import_timestamp = datetime.datetime.utcnow()
            
            # Track statistics
            new_count = 0
            duplicate_count = 0
            error_count = 0
            
            # Process each row in the CSV
            for row in csv_data:
                try:
                    # Extract data from the row
                    external_id = row.get("ID", "")
                    
                    # If no ID column, try to find an alternative
                    if not external_id:
                        # Look for common ID field names
                        for field in ["id", "Id", "ID", "identifier", "Identifier", "Number", "number"]:
                            if field in row:
                                external_id = row[field]
                                break
                    
                    # If still no ID, generate one from other fields
                    if not external_id:
                        # Create a composite ID from title and agency if available
                        title = row.get("Title", row.get("title", ""))
                        agency = row.get("Agency", row.get("agency", ""))
                        if title and agency:
                            import hashlib
                            external_id = hashlib.md5(f"{title}:{agency}".encode()).hexdigest()
                        else:
                            logger.warning(f"Could not determine ID for row: {row}")
                            error_count += 1
                            continue
                    
                    # Map CSV columns to database fields with flexible field name matching
                    def get_field_value(field_names):
                        for field in field_names:
                            for key in row.keys():
                                if field.lower() == key.lower():
                                    return row[key]
                        return None
                    
                    # Parse dates with flexible field names
                    release_date_value = get_field_value(["Release Date", "release date", "releaseDate", "release_date", "Date Released", "Start Date", "Estimated Solicitation Date"])
                    response_date_value = get_field_value(["Response Date", "response date", "responseDate", "response_date", "Due Date", "End Date"])
                    
                    # For award date, try to combine Estimated Award FY-QTR and Estimated Award FY if available
                    award_date_value = get_field_value(["Award Date", "award date", "awardDate", "award_date", "Date Awarded"])
                    if not award_date_value:
                        award_fy_qtr = get_field_value(["Estimated Award FY-QTR"])
                        award_fy = get_field_value(["Estimated Award FY"])
                        if award_fy:
                            # Create a date from the fiscal year
                            if award_fy_qtr and "1st" in award_fy_qtr:
                                award_date_value = f"10/01/{award_fy}"  # 1st quarter starts Oct 1
                            elif award_fy_qtr and "2nd" in award_fy_qtr:
                                award_date_value = f"01/01/{award_fy}"  # 2nd quarter starts Jan 1
                            elif award_fy_qtr and "3rd" in award_fy_qtr:
                                award_date_value = f"04/01/{award_fy}"  # 3rd quarter starts Apr 1
                            elif award_fy_qtr and "4th" in award_fy_qtr:
                                award_date_value = f"07/01/{award_fy}"  # 4th quarter starts Jul 1
                            else:
                                award_date_value = f"01/01/{award_fy}"  # Default to beginning of year
                    
                    # Parse value with flexible field names
                    value_str = get_field_value(["Estimated Value", "estimated value", "estimatedValue", "estimated_value", "Value", "Amount", "Budget", "Estimated Contract Value", "Basic Exercised Value"])
                    
                    proposal_data = {
                        "title": get_field_value(["Title", "title", "Name", "name", "Project", "project"]) or "Unknown",
                        "agency": get_field_value(["Agency", "agency", "Department", "department"]),
                        "office": get_field_value(["Office", "office", "Bureau", "bureau", "Division", "division", "Organization"]),
                        "description": get_field_value(["Description", "description", "Details", "details", "Summary", "summary", "Body"]),
                        "naics_code": get_field_value(["NAICS", "naics", "NAICS Code", "naics code", "naics_code"]),
                        "estimated_value": self.parse_value(value_str),
                        "release_date": self.parse_date(release_date_value),
                        "response_date": self.parse_date(response_date_value),
                        "contact_info": get_field_value(["Contact", "contact", "Contact Info", "contact info", "POC", "poc", "Point of Contact (Name) For", "Point of Contact (Email)"]),
                        "url": get_field_value(["URL", "url", "Link", "link", "Website", "website", "Solicitation Link"]),
                        "status": get_field_value(["Status", "status", "State", "state", "Phase", "phase", "Requirement Status", "Acquisition Phase"]),
                        "last_updated": import_timestamp,
                        "imported_at": import_timestamp,
                        
                        # Additional fields
                        "contract_type": get_field_value(["Contract Type", "contract type", "contractType", "contract_type", "Type"]),
                        "set_aside": get_field_value(["Set Aside", "set aside", "setAside", "set_aside", "Set Aside Type"]),
                        "competition_type": get_field_value(["Competition Type", "competition type", "competitionType", "competition_type", "Procurement Method", "Extent Competed"]),
                        "solicitation_number": get_field_value(["Solicitation Number", "solicitation number", "solicitationNumber", "solicitation_number", "Sol #", "Sol Num", "Listing ID"]),
                        "award_date": self.parse_date(award_date_value),
                        "place_of_performance": get_field_value(["Place of Performance", "place of performance", "placeOfPerformance", "place_of_performance", "Location", "location", "Place of Performance City", "Place of Performance State", "Place of Performance Country"]),
                        "incumbent": get_field_value(["Incumbent", "incumbent", "Current Contractor", "current contractor", "currentContractor", "Contractor Name"])
                    }
                    
                    # Check if proposal already exists
                    existing_proposal = session.query(Proposal).filter_by(
                        source_id=data_source.id,
                        external_id=external_id,
                        is_latest=True
                    ).first()
                    
                    # Check if this is a duplicate or if we need to update with new information
                    is_duplicate = False
                    needs_update = False
                    
                    if existing_proposal:
                        # Compare relevant fields to see if data has changed
                        fields_to_compare = [
                            "title", "agency", "office", "description", "naics_code", 
                            "estimated_value", "release_date", "response_date", 
                            "contact_info", "url", "status", "contract_type", "set_aside",
                            "competition_type", "solicitation_number", "award_date",
                            "place_of_performance", "incumbent"
                        ]
                        
                        # Count how many fields are different
                        different_fields = 0
                        fields_updated = []
                        
                        for field in fields_to_compare:
                            existing_value = getattr(existing_proposal, field)
                            new_value = proposal_data[field]
                            
                            # Skip None values
                            if existing_value is None and new_value is None:
                                continue
                                
                            # Check if we're updating from empty/N/A to a valid value
                            is_empty_or_na = (
                                existing_value is None or 
                                existing_value == "" or 
                                (isinstance(existing_value, str) and existing_value.lower() in ["n/a", "na", "not available", "not applicable", "tbd", "to be determined"])
                            )
                            
                            has_new_value = (
                                new_value is not None and 
                                new_value != "" and 
                                (not isinstance(new_value, str) or new_value.lower() not in ["n/a", "na", "not available", "not applicable", "tbd", "to be determined"])
                            )
                            
                            # Compare values, accounting for different types
                            if isinstance(existing_value, datetime.datetime) and isinstance(new_value, datetime.datetime):
                                # For dates, compare only the date part
                                if existing_value.date() != new_value.date():
                                    different_fields += 1
                                    # If we're updating from a null-like date to a valid date
                                    if existing_value.year < 1900 and new_value.year >= 1900:
                                        setattr(existing_proposal, field, new_value)
                                        fields_updated.append(field)
                                        needs_update = True
                            elif existing_value != new_value:
                                different_fields += 1
                                # If we're updating from empty/N/A to a valid value
                                if is_empty_or_na and has_new_value:
                                    setattr(existing_proposal, field, new_value)
                                    fields_updated.append(field)
                                    needs_update = True
                        
                        # If no fields are different, it's a duplicate
                        if different_fields == 0:
                            is_duplicate = True
                            duplicate_count += 1
                            logger.debug(f"Duplicate record found for external_id: {external_id}")
                            continue
                        
                        # If we updated fields but didn't create a new record
                        if needs_update:
                            # Update the last_updated timestamp
                            existing_proposal.last_updated = import_timestamp
                            session.add(existing_proposal)
                            logger.info(f"Updated existing record for external_id: {external_id} - Fields updated: {fields_updated}")
                            continue
                        
                        # If we get here, the data has changed significantly, so we need to create a new record
                        # First, mark the existing record as not latest
                        existing_proposal.is_latest = False
                        session.add(existing_proposal)
                    
                    # Create new proposal
                    new_proposal = Proposal(
                        source_id=data_source.id,
                        external_id=external_id,
                        is_latest=True,
                        **proposal_data
                    )
                    session.add(new_proposal)
                    new_count += 1
                    
                    # Commit in batches to avoid memory issues
                    if new_count % 100 == 0:
                        session.commit()
                        logger.info(f"Committed batch of 100 records. New: {new_count}, Duplicates: {duplicate_count}")
                    
                except Exception as e:
                    logger.error(f"Error processing row: {e}")
                    error_count += 1
            
            # Final commit
            session.commit()
            logger.info(f"CSV processing complete. New: {new_count}, Duplicates: {duplicate_count}, Errors: {error_count}")
            
            # Keep the CSV file for reference
            # Rename it with timestamp to avoid overwriting
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{os.path.splitext(csv_file)[0]}_{timestamp_str}{os.path.splitext(csv_file)[1]}"
            try:
                os.rename(csv_file, new_filename)
                logger.info(f"Renamed CSV file to: {new_filename}")
            except Exception as e:
                logger.warning(f"Could not rename CSV file: {e}")
            
            # Update last_scraped timestamp with UTC time only if new proposals were collected
            if new_count > 0:
                data_source.last_scraped = datetime.datetime.utcnow()
                session.commit()
                logger.info(f"Updated last_scraped timestamp for {self.source_name} - {new_count} new proposals collected")
            else:
                logger.info(f"No new proposals collected, not updating last_scraped timestamp")
            
            return new_count
            
        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            session.rollback()
            return 0
    
    def process_excel(self, excel_file, session, data_source):
        """Process the downloaded Excel file and update the database
        
        Returns:
            int: Number of new proposals added to the database
        """
        try:
            logger.info(f"Processing Excel file: {excel_file}")
            
            try:
                import pandas as pd
                
                # Read the Excel file
                logger.info("Reading Excel file with pandas")
                df = pd.read_excel(excel_file)
                
                # Check if dataframe is empty
                if df.empty:
                    logger.error("Excel file is empty")
                    return 0
                
                # Log the columns
                logger.info(f"Excel columns: {df.columns.tolist()}")
                
                # Get the current import timestamp
                import_timestamp = datetime.datetime.utcnow()
                
                # Track statistics
                new_count = 0
                duplicate_count = 0
                error_count = 0
                
                # Process each row in the dataframe
                for _, row in df.iterrows():
                    try:
                        # Convert row to dict
                        row_dict = row.to_dict()
                        
                        # Extract data from the row
                        external_id = None
                        
                        # Look for common ID field names
                        for field in ["ID", "Id", "id", "identifier", "Identifier", "Number", "number"]:
                            if field in row_dict:
                                external_id = str(row_dict[field])
                                break
                        
                        # If still no ID, generate one from other fields
                        if not external_id:
                            # Create a composite ID from title and agency if available
                            title = None
                            agency = None
                            
                            for title_field in ["Title", "title", "Name", "name", "Project", "project"]:
                                if title_field in row_dict:
                                    title = str(row_dict[title_field])
                                    break
                            
                            for agency_field in ["Agency", "agency", "Department", "department"]:
                                if agency_field in row_dict:
                                    agency = str(row_dict[agency_field])
                                    break
                            
                            if title and agency:
                                import hashlib
                                external_id = hashlib.md5(f"{title}:{agency}".encode()).hexdigest()
                            else:
                                logger.warning(f"Could not determine ID for row: {row_dict}")
                                error_count += 1
                                continue
                        
                        # Map Excel columns to database fields with flexible field name matching
                        def get_field_value(field_names):
                            for field in field_names:
                                for key in row_dict.keys():
                                    if field.lower() == str(key).lower():
                                        value = row_dict[key]
                                        # Handle NaN values
                                        if pd.isna(value):
                                            return None
                                        return value
                        return None
                        
                        # Parse dates with flexible field names
                        release_date_value = get_field_value(["Release Date", "release date", "releaseDate", "release_date", "Date Released", "Start Date", "Estimated Solicitation Date"])
                        response_date_value = get_field_value(["Response Date", "response date", "responseDate", "response_date", "Due Date", "End Date"])
                        
                        # For award date, try to combine Estimated Award FY-QTR and Estimated Award FY if available
                        award_date_value = get_field_value(["Award Date", "award date", "awardDate", "award_date", "Date Awarded"])
                        if not award_date_value:
                            award_fy_qtr = get_field_value(["Estimated Award FY-QTR"])
                            award_fy = get_field_value(["Estimated Award FY"])
                            if award_fy:
                                # Create a date from the fiscal year
                                if award_fy_qtr and "1st" in award_fy_qtr:
                                    award_date_value = f"10/01/{award_fy}"  # 1st quarter starts Oct 1
                                elif award_fy_qtr and "2nd" in award_fy_qtr:
                                    award_date_value = f"01/01/{award_fy}"  # 2nd quarter starts Jan 1
                                elif award_fy_qtr and "3rd" in award_fy_qtr:
                                    award_date_value = f"04/01/{award_fy}"  # 3rd quarter starts Apr 1
                                elif award_fy_qtr and "4th" in award_fy_qtr:
                                    award_date_value = f"07/01/{award_fy}"  # 4th quarter starts Jul 1
                                else:
                                    award_date_value = f"01/01/{award_fy}"  # Default to beginning of year
                        
                        # Parse value with flexible field names
                        value_str = get_field_value(["Estimated Value", "estimated value", "estimatedValue", "estimated_value", "Value", "Amount", "Budget", "Estimated Contract Value", "Basic Exercised Value"])
                        
                        proposal_data = {
                            "title": get_field_value(["Title", "title", "Name", "name", "Project", "project"]) or "Unknown",
                            "agency": get_field_value(["Agency", "agency", "Department", "department"]),
                            "office": get_field_value(["Office", "office", "Bureau", "bureau", "Division", "division", "Organization"]),
                            "description": get_field_value(["Description", "description", "Details", "details", "Summary", "summary", "Body"]),
                            "naics_code": get_field_value(["NAICS", "naics", "NAICS Code", "naics code", "naics_code"]),
                            "estimated_value": self.parse_value(value_str),
                            "release_date": self.parse_date(release_date_value),
                            "response_date": self.parse_date(response_date_value),
                            "contact_info": get_field_value(["Contact", "contact", "Contact Info", "contact info", "POC", "poc", "Point of Contact (Name) For", "Point of Contact (Email)"]),
                            "url": get_field_value(["URL", "url", "Link", "link", "Website", "website", "Solicitation Link"]),
                            "status": get_field_value(["Status", "status", "State", "state", "Phase", "phase", "Requirement Status", "Acquisition Phase"]),
                            "last_updated": import_timestamp,
                            "imported_at": import_timestamp,
                            
                            # Additional fields
                            "contract_type": get_field_value(["Contract Type", "contract type", "contractType", "contract_type", "Type"]),
                            "set_aside": get_field_value(["Set Aside", "set aside", "setAside", "set_aside", "Set Aside Type"]),
                            "competition_type": get_field_value(["Competition Type", "competition type", "competitionType", "competition_type", "Procurement Method", "Extent Competed"]),
                            "solicitation_number": get_field_value(["Solicitation Number", "solicitation number", "solicitationNumber", "solicitation_number", "Sol #", "Sol Num", "Listing ID"]),
                            "award_date": self.parse_date(award_date_value),
                            "place_of_performance": get_field_value(["Place of Performance", "place of performance", "placeOfPerformance", "place_of_performance", "Location", "location", "Place of Performance City", "Place of Performance State", "Place of Performance Country"]),
                            "incumbent": get_field_value(["Incumbent", "incumbent", "Current Contractor", "current contractor", "currentContractor", "Contractor Name"])
                        }
                        
                        # Check if proposal already exists
                        existing_proposal = session.query(Proposal).filter_by(
                            source_id=data_source.id,
                            external_id=external_id,
                            is_latest=True
                        ).first()
                        
                        # Check if this is a duplicate or if we need to update with new information
                        is_duplicate = False
                        needs_update = False
                        
                        if existing_proposal:
                            # Compare relevant fields to see if data has changed
                            fields_to_compare = [
                                "title", "agency", "office", "description", "naics_code", 
                                "estimated_value", "release_date", "response_date", 
                                "contact_info", "url", "status", "contract_type", "set_aside",
                                "competition_type", "solicitation_number", "award_date",
                                "place_of_performance", "incumbent"
                            ]
                            
                            # Count how many fields are different
                            different_fields = 0
                            fields_updated = []
                            
                            for field in fields_to_compare:
                                existing_value = getattr(existing_proposal, field)
                                new_value = proposal_data[field]
                                
                                # Skip None values
                                if existing_value is None and new_value is None:
                                    continue
                                    
                                # Check if we're updating from empty/N/A to a valid value
                                is_empty_or_na = (
                                    existing_value is None or 
                                    existing_value == "" or 
                                    (isinstance(existing_value, str) and existing_value.lower() in ["n/a", "na", "not available", "not applicable", "tbd", "to be determined"])
                                )
                                
                                has_new_value = (
                                    new_value is not None and 
                                    new_value != "" and 
                                    (not isinstance(new_value, str) or new_value.lower() not in ["n/a", "na", "not available", "not applicable", "tbd", "to be determined"])
                                )
                                
                                # Compare values, accounting for different types
                                if isinstance(existing_value, datetime.datetime) and isinstance(new_value, datetime.datetime):
                                    # For dates, compare only the date part
                                    if existing_value.date() != new_value.date():
                                        different_fields += 1
                                        # If we're updating from a null-like date to a valid date
                                        if existing_value.year < 1900 and new_value.year >= 1900:
                                            setattr(existing_proposal, field, new_value)
                                            fields_updated.append(field)
                                            needs_update = True
                                elif existing_value != new_value:
                                    different_fields += 1
                                    # If we're updating from empty/N/A to a valid value
                                    if is_empty_or_na and has_new_value:
                                        setattr(existing_proposal, field, new_value)
                                        fields_updated.append(field)
                                        needs_update = True
                            
                            # If no fields are different, it's a duplicate
                            if different_fields == 0:
                                is_duplicate = True
                                duplicate_count += 1
                                logger.debug(f"Duplicate record found for external_id: {external_id}")
                                continue
                            
                            # If we updated fields but didn't create a new record
                            if needs_update:
                                # Update the last_updated timestamp
                                existing_proposal.last_updated = import_timestamp
                                session.add(existing_proposal)
                                logger.info(f"Updated existing record for external_id: {external_id} - Fields updated: {fields_updated}")
                                continue
                            
                            # If we get here, the data has changed significantly, so we need to create a new record
                            # First, mark the existing record as not latest
                            existing_proposal.is_latest = False
                            session.add(existing_proposal)
                        
                        # Create new proposal
                        new_proposal = Proposal(
                            source_id=data_source.id,
                            external_id=external_id,
                            is_latest=True,
                            **proposal_data
                        )
                        session.add(new_proposal)
                        new_count += 1
                        
                        # Commit in batches to avoid memory issues
                        if new_count % 100 == 0:
                            session.commit()
                            logger.info(f"Committed batch of 100 records. New: {new_count}, Duplicates: {duplicate_count}")
                        
                    except Exception as e:
                        logger.error(f"Error processing Excel row: {e}")
                        error_count += 1
                
                # Final commit
                session.commit()
                logger.info(f"Excel processing complete. New: {new_count}, Duplicates: {duplicate_count}, Errors: {error_count}")
                
                # Keep the Excel file for reference
                # Rename it with timestamp to avoid overwriting
                timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"{os.path.splitext(excel_file)[0]}_{timestamp_str}{os.path.splitext(excel_file)[1]}"
                try:
                    os.rename(excel_file, new_filename)
                    logger.info(f"Renamed Excel file to: {new_filename}")
                except Exception as e:
                    logger.warning(f"Could not rename Excel file: {e}")
                
                # Update last_scraped timestamp with UTC time only if new proposals were collected
                if new_count > 0:
                    data_source.last_scraped = datetime.datetime.utcnow()
                    session.commit()
                    logger.info(f"Updated last_scraped timestamp for {self.source_name} - {new_count} new proposals collected")
                else:
                    logger.info(f"No new proposals collected, not updating last_scraped timestamp")
                
                return new_count
                
            except Exception as e:
                logger.error(f"Error reading Excel file: {e}")
                return 0
                
        except Exception as e:
            logger.error(f"Error processing Excel: {e}")
            session.rollback()
            return 0
    
    def scrape(self):
        """Scrape the Acquisition Gateway Forecast site"""
        logger.info("Starting Acquisition Gateway Forecast scraper")
        
        try:
            # Set up the browser
            if not self.setup_browser():
                logger.error("Failed to set up browser")
                return False
            
            # Use the session context manager to ensure proper cleanup
            with session_scope() as session:
                # Get or create the data source
                data_source = session.query(DataSource).filter_by(name=self.source_name).first()
                if not data_source:
                    data_source = DataSource(name=self.source_name)
                    session.add(data_source)
                    session.commit()
                
                # Download the CSV file
                csv_file = self.download_csv()
                
                if not csv_file:
                    logger.warning("Could not download CSV file from the website. This might be due to authentication requirements or site issues.")
                    
                    # Check if we have any existing CSV files we can use
                    download_dir = DOWNLOADS_DIR
                    csv_files = list(pathlib.Path(download_dir).glob("*.csv"))
                    
                    if csv_files:
                        # Sort by modification time (most recent first)
                        csv_files.sort(key=os.path.getmtime, reverse=True)
                        latest_file = str(csv_files[0])
                        logger.info(f"Using most recent CSV file: {latest_file}")
                        
                        # Process the CSV file
                        logger.info(f"Processing CSV file: {latest_file}")
                        self.process_csv(latest_file, session, data_source)
                        
                        # Clean up the browser
                        self.cleanup_browser()
                        
                        return True
                    else:
                        logger.error("No CSV files found in the downloads directory")
                        self.cleanup_browser()
                        return False
                
                # Process the CSV file
                logger.info(f"Processing CSV file: {csv_file}")
                self.process_csv(csv_file, session, data_source)
                
                # Update the last scraped timestamp
                data_source.last_scraped = datetime.datetime.utcnow()
            
            # Clean up the browser
            self.cleanup_browser()
            
            return True
        except Exception as e:
            logger.error(f"Error scraping Acquisition Gateway Forecast: {e}")
            
            # Clean up
            self.cleanup_browser()
            
            return False

def check_last_download():
    """Check if a CSV file has been downloaded within the last 24 hours"""
    try:
        # Get the scrape interval from environment or use default (24 hours)
        scrape_interval_hours = int(os.getenv("SCRAPE_INTERVAL_HOURS", 24))
        
        # Use the download tracker to check if we should download
        if download_tracker.should_download("Acquisition Gateway", scrape_interval_hours):
            logger.info(f"No recent download found or download interval ({scrape_interval_hours} hours) exceeded, should download")
            return False
        
        # Also verify that we have valid CSV files
        downloads_dir = DOWNLOADS_DIR
        csv_files = glob.glob(os.path.join(downloads_dir, "*.csv"))
        
        if not csv_files:
            logger.info("No CSV files found in downloads directory, should download")
            return False
        
        # Check if any of the CSV files are valid (not empty)
        for csv_file in csv_files:
            if os.path.getsize(csv_file) > 0:
                logger.info(f"Found valid CSV file: {csv_file}, no need to download")
                return True
        
        logger.info("No valid CSV files found, should download")
        return False
        
    except Exception as e:
        logger.error(f"Error checking last download: {e}")
        return False  # If there's an error, we'll download to be safe

def run_scraper(force=False):
    """Run the scraper if it's time or if forced"""
    try:
        # Check if we should run the scraper
        if force or check_last_download() == False:
            logger.info(f"Running scraper (force={force})")
            
            # Create and run the scraper
            scraper = AcquisitionGatewayScraper(debug_mode=os.getenv("DEBUG", "False").lower() == "true")
            return scraper.scrape()
        else:
            logger.info("Skipping scrape (recent download exists)")
            return True
            
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        return False

if __name__ == "__main__":
    run_scraper() 