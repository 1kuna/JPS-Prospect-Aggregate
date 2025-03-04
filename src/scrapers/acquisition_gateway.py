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
log_file = os.path.join(logs_dir, f'acquisition_gateway_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
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

class AcquisitionGatewayScraper:
    """Scraper for the Acquisition Gateway Forecast site"""
    
    def __init__(self, debug_mode=False):
        self.base_url = "https://acquisitiongateway.gov/forecast"
        self.source_name = "Acquisition Gateway Forecast"
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
            "browser.helperApps.neverAsk.saveToDisk": "text/csv,application/csv,application/vnd.ms-excel,application/excel,application/x-excel,application/x-msexcel,text/comma-separated-values,application/octet-stream",
            "browser.download.manager.useWindow": False,
            "browser.download.manager.focusWhenStarting": False,
            "browser.download.manager.closeWhenDone": True,
            "browser.download.manager.showAlertOnComplete": False,
            "browser.download.manager.useWindow": False,
            "browser.helperApps.alwaysAsk.force": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Disable the "Save As" dialog for downloads
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        
        try:
            # Try using ChromeDriverManager
            logging.info("Attempting to use ChromeDriverManager")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set download behavior for headless mode
            if not self.debug_mode:
                params = {
                    'behavior': 'allow',
                    'downloadPath': download_dir_abs
                }
                try:
                    driver.execute_cdp_cmd('Page.setDownloadBehavior', params)
                    logger.info("Set download behavior for headless mode")
                except Exception as e:
                    logger.warning(f"Could not set CDP download behavior: {e}")
            
            return driver
        except Exception as e:
            logging.error(f"Error with ChromeDriverManager: {str(e)}")
            try:
                # Fallback to default Chrome installation
                logging.info("Falling back to default Chrome installation")
                driver = webdriver.Chrome(options=chrome_options)
                
                # Set download behavior for headless mode
                if not self.debug_mode:
                    params = {
                        'behavior': 'allow',
                        'downloadPath': download_dir_abs
                    }
                    try:
                        driver.execute_cdp_cmd('Page.setDownloadBehavior', params)
                        logger.info("Set download behavior for headless mode")
                    except Exception as e:
                        logger.warning(f"Could not set CDP download behavior: {e}")
                
                return driver
            except Exception as e2:
                logging.error(f"Error with default Chrome installation: {str(e2)}")
                # Log error and return None to handle in the calling method
                logging.error("Could not initialize Chrome WebDriver. Please ensure Chrome is installed and up to date.")
                return None
    
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
    
    def download_csv(self, driver):
        """Click the Export CSV button and download the file"""
        try:
            # Wait for the page to fully load
            logger.info("Waiting for page to fully load")
            time.sleep(10)  # Give the page more time to stabilize
            
            # Clear any existing CSV files in the downloads directory
            downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
            existing_csv_files = glob.glob(os.path.join(downloads_dir, "*.csv"))
            for file in existing_csv_files:
                try:
                    logger.info(f"Removing existing CSV file: {file}")
                    os.remove(file)
                except Exception as e:
                    logger.warning(f"Could not remove existing CSV file {file}: {e}")
            
            # Take a screenshot before looking for the button
            screenshot_path = os.path.join(downloads_dir, "before_export_button.png")
            driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot before export button saved to {screenshot_path}")
            
            # Save page source for analysis
            source_path = os.path.join(downloads_dir, "page_source_before_export.html")
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.info(f"Page source saved to {source_path}")
            
            # Try to find any table data on the page first
            logger.info("Looking for table data on the page")
            tables = driver.find_elements(By.TAG_NAME, "table")
            if tables:
                logger.info(f"Found {len(tables)} tables on the page")
                
                # Try to find a direct download link first
                logger.info("Looking for direct download links")
                download_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.csv') or contains(@href, 'download') or contains(@href, 'export')]")
                if download_links:
                    logger.info(f"Found {len(download_links)} potential download links")
                    for link in download_links:
                        try:
                            href = link.get_attribute('href')
                            logger.info(f"Found download link with href: {href}")
                            
                            # Try to download directly
                            logger.info(f"Navigating to download link: {href}")
                            
                            # Open in a new tab to avoid losing the main page
                            driver.execute_script("window.open(arguments[0]);", href)
                            
                            # Switch back to the main tab
                            driver.switch_to.window(driver.window_handles[0])
                            
                            # Wait a bit for the download to start
                            time.sleep(5)
                            
                            # Check if any files were downloaded
                            csv_files = glob.glob(os.path.join(downloads_dir, "*.csv"))
                            if csv_files:
                                new_file = max(csv_files, key=os.path.getmtime)
                                logger.info(f"Successfully downloaded file via direct link: {new_file}")
                                
                                # Update the download tracker
                                download_tracker.set_last_download_time(self.source_name)
                                logger.info(f"Updated download timestamp for {self.source_name}")
                                
                                return new_file
                        except Exception as e:
                            logger.warning(f"Error trying download link: {e}")
            
            # Based on our analysis, we know the exact button to target
            export_button = None
            
            # Try multiple approaches to find the export button
            button_finders = [
                # Method 1: By ID
                lambda: driver.find_element(By.ID, "export-0"),
                
                # Method 2: By class and text
                lambda: next((b for b in driver.find_elements(By.CLASS_NAME, "ag-button") if "Export CSV" in b.text), None),
                
                # Method 3: By XPath containing Export CSV text
                lambda: driver.find_element(By.XPATH, "//button[contains(text(), 'Export CSV')]"),
                
                # Method 4: By XPath for any button containing Export
                lambda: driver.find_element(By.XPATH, "//button[contains(text(), 'Export')]"),
                
                # Method 5: By XPath for any element containing Export CSV
                lambda: driver.find_element(By.XPATH, "//*[contains(text(), 'Export CSV')]"),
                
                # Method 6: By XPath for any link containing Export
                lambda: driver.find_element(By.XPATH, "//a[contains(text(), 'Export')]"),
                
                # Method 7: By XPath for any element with download attribute
                lambda: driver.find_element(By.XPATH, "//*[@download]"),
                
                # Method 8: By XPath for any element with href containing csv
                lambda: driver.find_element(By.XPATH, "//a[contains(@href, 'csv')]")
            ]
            
            # Try each method until we find the button
            for i, finder in enumerate(button_finders):
                try:
                    logger.info(f"Trying button finder method {i+1}")
                    result = finder()
                    if result:
                        export_button = result
                        logger.info(f"Found Export button using method {i+1}")
                        
                        # Take a screenshot with the button highlighted
                        try:
                            driver.execute_script("arguments[0].style.border='3px solid red'", export_button)
                            screenshot_path = os.path.join(downloads_dir, f"export_button_found_method_{i+1}.png")
                            driver.save_screenshot(screenshot_path)
                            logger.info(f"Screenshot with highlighted button saved to {screenshot_path}")
                        except:
                            pass
                        
                        break
                except Exception as e:
                    logger.info(f"Button finder method {i+1} failed: {str(e)}")
            
            # If we still couldn't find the button, take a screenshot for debugging
            if not export_button:
                logger.error("Could not find Export CSV button")
                screenshot_path = os.path.join(downloads_dir, "acquisition_gateway_page.png")
                driver.save_screenshot(screenshot_path)
                logger.info(f"Page screenshot saved to {screenshot_path}")
                
                # Save page source for debugging
                source_path = os.path.join(downloads_dir, "acquisition_gateway_page.html")
                with open(source_path, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                logger.info(f"Page source saved to {source_path}")
                
                # Try a last resort approach - look for any table and try to extract data directly
                try:
                    logger.info("Attempting to extract table data directly as CSV")
                    tables = driver.find_elements(By.TAG_NAME, "table")
                    if tables:
                        largest_table = None
                        max_rows = 0
                        
                        for table in tables:
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            if len(rows) > max_rows:
                                max_rows = len(rows)
                                largest_table = table
                        
                        if largest_table and max_rows > 1:
                            logger.info(f"Found table with {max_rows} rows, extracting to CSV")
                            
                            # Extract headers
                            headers = []
                            header_row = largest_table.find_elements(By.TAG_NAME, "th")
                            if not header_row:
                                # Try first row as header if no th elements
                                rows = largest_table.find_elements(By.TAG_NAME, "tr")
                                if rows:
                                    header_row = rows[0].find_elements(By.TAG_NAME, "td")
                            
                            for header in header_row:
                                headers.append(header.text.strip())
                            
                            # Extract data rows
                            data_rows = []
                            rows = largest_table.find_elements(By.TAG_NAME, "tr")
                            
                            for row_idx, row in enumerate(rows):
                                # Skip header row
                                if row_idx == 0:
                                    continue
                                
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if cells:
                                    row_data = []
                                    for cell in cells:
                                        row_data.append(cell.text.strip())
                                    data_rows.append(row_data)
                            
                            # Create a CSV file from the extracted data
                            csv_path = os.path.join(downloads_dir, f"extracted_table_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                writer.writerow(headers)
                                writer.writerows(data_rows)
                            
                            logger.info(f"Created CSV file from table data: {csv_path}")
                            
                            # Update the download tracker
                            download_tracker.set_last_download_time(self.source_name)
                            logger.info(f"Updated download timestamp for {self.source_name}")
                            
                            return csv_path
                except Exception as e:
                    logger.error(f"Error extracting table data: {e}")
                
                return None
            
            # Check if the button is a link with href
            href = None
            try:
                href = export_button.get_attribute('href')
                if href:
                    logger.info(f"Export button is a link with href: {href}")
            except:
                pass
            
            # If it's a link with href, try to download directly
            if href:
                try:
                    logger.info(f"Navigating to download link: {href}")
                    
                    # Open in a new tab to avoid losing the main page
                    driver.execute_script("window.open(arguments[0]);", href)
                    
                    # Switch back to the main tab
                    driver.switch_to.window(driver.window_handles[0])
                    
                    # Wait a bit for the download to start
                    time.sleep(5)
                    
                    # Check if any files were downloaded
                    csv_files = glob.glob(os.path.join(downloads_dir, "*.csv"))
                    if csv_files:
                        new_file = max(csv_files, key=os.path.getmtime)
                        logger.info(f"Successfully downloaded file via href: {new_file}")
                        
                        # Update the download tracker
                        download_tracker.set_last_download_time(self.source_name)
                        logger.info(f"Updated download timestamp for {self.source_name}")
                        
                        return new_file
                except Exception as e:
                    logger.warning(f"Error navigating to href: {e}")
            
            # Click the export button
            logger.info("Clicking Export CSV button")
            try:
                # Scroll the button into view
                driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
                time.sleep(2)
                
                # Try regular click
                export_button.click()
                logger.info("Clicked Export CSV button")
                
                # Take a screenshot after clicking
                screenshot_path = os.path.join(downloads_dir, "after_button_click.png")
                driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot after button click saved to {screenshot_path}")
            except ElementClickInterceptedException:
                logger.info("Click intercepted, trying JavaScript click")
                driver.execute_script("arguments[0].click();", export_button)
                logger.info("Used JavaScript to click Export CSV button")
                
                # Take a screenshot after JS click
                screenshot_path = os.path.join(downloads_dir, "after_js_click.png")
                driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot after JS click saved to {screenshot_path}")
            except Exception as e:
                logger.error(f"Error clicking Export CSV button: {str(e)}")
                return None
            
            # Wait for the download to complete
            logger.info("Waiting for download to complete")
            time.sleep(10)  # Give time for the download to start
            
            # Check the downloads directory for new CSV files
            downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
            
            # Wait for new files to appear (up to 60 seconds)
            max_wait = 60
            wait_time = 0
            new_file = None
            
            while wait_time < max_wait:
                # Get current list of CSV files
                csv_files = glob.glob(os.path.join(downloads_dir, "*.csv"))
                
                if csv_files:
                    # Get the most recently modified file
                    new_file = max(csv_files, key=os.path.getmtime)
                    logger.info(f"Found CSV file: {new_file}")
                    break
                
                # Wait and check again
                time.sleep(5)
                wait_time += 5
                logger.info(f"Waiting for download... ({wait_time}s)")
            
            if not new_file:
                # Check for other file types that might have been downloaded instead
                for ext in ['.xlsx', '.xls', '.txt']:
                    other_files = glob.glob(os.path.join(downloads_dir, f"*{ext}"))
                    if other_files:
                        new_file = max(other_files, key=os.path.getmtime)
                        logger.info(f"Found non-CSV file: {new_file}")
                        
                        # If it's an Excel file, we can convert it to CSV
                        if ext in ['.xlsx', '.xls']:
                            try:
                                import pandas as pd
                                logger.info(f"Converting Excel file to CSV: {new_file}")
                                df = pd.read_excel(new_file)
                                csv_path = os.path.splitext(new_file)[0] + '.csv'
                                df.to_csv(csv_path, index=False)
                                logger.info(f"Converted Excel file to CSV: {csv_path}")
                                new_file = csv_path
                            except Exception as e:
                                logger.error(f"Error converting Excel to CSV: {e}")
                        break
            
            if not new_file:
                logger.error("No files found in downloads directory after export attempt")
                
                # As a last resort, try to extract table data directly
                try:
                    logger.info("Attempting to extract table data directly as CSV")
                    tables = driver.find_elements(By.TAG_NAME, "table")
                    if tables:
                        largest_table = None
                        max_rows = 0
                        
                        for table in tables:
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            if len(rows) > max_rows:
                                max_rows = len(rows)
                                largest_table = table
                        
                        if largest_table and max_rows > 1:
                            logger.info(f"Found table with {max_rows} rows, extracting to CSV")
                            
                            # Extract headers
                            headers = []
                            header_row = largest_table.find_elements(By.TAG_NAME, "th")
                            if not header_row:
                                # Try first row as header if no th elements
                                rows = largest_table.find_elements(By.TAG_NAME, "tr")
                                if rows:
                                    header_row = rows[0].find_elements(By.TAG_NAME, "td")
                            
                            for header in header_row:
                                headers.append(header.text.strip())
                            
                            # Extract data rows
                            data_rows = []
                            rows = largest_table.find_elements(By.TAG_NAME, "tr")
                            
                            for row_idx, row in enumerate(rows):
                                # Skip header row
                                if row_idx == 0:
                                    continue
                                
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if cells:
                                    row_data = []
                                    for cell in cells:
                                        row_data.append(cell.text.strip())
                                    data_rows.append(row_data)
                            
                            # Create a CSV file from the extracted data
                            csv_path = os.path.join(downloads_dir, f"extracted_table_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                writer.writerow(headers)
                                writer.writerows(data_rows)
                            
                            logger.info(f"Created CSV file from table data: {csv_path}")
                            
                            # Update the download tracker
                            download_tracker.set_last_download_time(self.source_name)
                            logger.info(f"Updated download timestamp for {self.source_name}")
                            
                            return csv_path
                except Exception as e:
                    logger.error(f"Error extracting table data: {e}")
                
                return None
            
            # Verify the file is not empty
            if os.path.getsize(new_file) == 0:
                logger.error(f"Downloaded file is empty: {new_file}")
                return None
            
            # Update the download tracker
            download_tracker.set_last_download_time(self.source_name)
            logger.info(f"Updated download timestamp for {self.source_name}")
            
            return new_file
            
        except Exception as e:
            logger.error(f"Error downloading CSV: {str(e)}")
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
            # Try different encodings if needed
            encodings = ['utf-8', 'latin-1', 'cp1252']
            csv_data = None
            
            for encoding in encodings:
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
                    
                    # Check if this is a duplicate (same data as existing record)
                    is_duplicate = False
                    if existing_proposal:
                        # Compare relevant fields to see if data has changed
                        fields_to_compare = [
                            "title", "agency", "office", "description", "naics_code", 
                            "estimated_value", "release_date", "response_date", 
                            "contact_info", "url", "status"
                        ]
                        
                        # Count how many fields are different
                        different_fields = 0
                        for field in fields_to_compare:
                            existing_value = getattr(existing_proposal, field)
                            new_value = proposal_data[field]
                            
                            # Skip None values
                            if existing_value is None and new_value is None:
                                continue
                                
                            # Compare values, accounting for different types
                            if isinstance(existing_value, datetime.datetime) and isinstance(new_value, datetime.datetime):
                                # For dates, compare only the date part
                                if existing_value.date() != new_value.date():
                                    different_fields += 1
                            elif existing_value != new_value:
                                different_fields += 1
                        
                        # If no fields are different, it's a duplicate
                        if different_fields == 0:
                            is_duplicate = True
                            duplicate_count += 1
                            logger.debug(f"Duplicate record found for external_id: {external_id}")
                            continue
                        
                        # If we get here, the data has changed, so we need to create a new record
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
                        
                        # Check if this is a duplicate (same data as existing record)
                        is_duplicate = False
                        if existing_proposal:
                            # Compare relevant fields to see if data has changed
                            fields_to_compare = [
                                "title", "agency", "office", "description", "naics_code", 
                                "estimated_value", "release_date", "response_date", 
                                "contact_info", "url", "status"
                            ]
                            
                            # Count how many fields are different
                            different_fields = 0
                            for field in fields_to_compare:
                                existing_value = getattr(existing_proposal, field)
                                new_value = proposal_data[field]
                                
                                # Skip None values
                                if existing_value is None and new_value is None:
                                    continue
                                    
                                # Compare values, accounting for different types
                                if isinstance(existing_value, datetime.datetime) and isinstance(new_value, datetime.datetime):
                                    # For dates, compare only the date part
                                    if existing_value.date() != new_value.date():
                                        different_fields += 1
                                elif existing_value != new_value:
                                    different_fields += 1
                            
                            # If no fields are different, it's a duplicate
                            if different_fields == 0:
                                is_duplicate = True
                                duplicate_count += 1
                                logger.debug(f"Duplicate record found for external_id: {external_id}")
                                continue
                            
                            # If we get here, the data has changed, so we need to create a new record
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
                    description="Acquisition Gateway data source"
                )
                session.add(data_source)
                session.commit()
            
            # Download the CSV
            csv_file = self.download_csv(driver)
            
            if not csv_file:
                logger.error("Failed to download CSV")
                close_session(session)
                if driver:
                    driver.quit()
                return False
            
            # Process the CSV
            proposals_added = self.process_csv(csv_file, session, data_source)
            
            # Update the last scraped timestamp
            data_source.last_scraped = datetime.datetime.utcnow()
            session.commit()
            
            # Update the download tracker
            download_tracker.set_last_download_time(self.source_name)
            
            logger.info(f"Scrape completed. Added {proposals_added} proposals.")
            
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
        downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'downloads')
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