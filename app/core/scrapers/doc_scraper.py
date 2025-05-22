"""Department of Commerce Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
# import sys # Unused
import shutil
import datetime # Added datetime import
from urllib.parse import urljoin

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
import hashlib
# import re # Unused
import json # Added json
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date # Added parsing utils

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect, DataSource, db # Added Prospect, DataSource, db
# from app.database.crud import bulk_upsert_prospects # Unused
from app.exceptions import ScraperError
from app.utils.logger import logger
# from app.utils.db_utils import update_scraper_status, get_data_source_id_by_name # Unused
# We need to add COMMERCE_FORECAST_URL to config.py
from app.config import active_config # Import active_config
from app.utils.scraper_utils import (
    # check_url_accessibility, # Unused
    # download_file, # Unused
    # save_permanent_copy, # Unused
    handle_scraper_error
)

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.doc")

class DocScraper(BaseScraper):
    """Scraper for the Department of Commerce (DOC) Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DOC Forecast scraper."""
        super().__init__(
            source_name="DOC Forecast",
            base_url=active_config.COMMERCE_FORECAST_URL,
            debug_mode=debug_mode
        )
    
    def _find_download_link_locator(self):
        """
        Find the locator for the forecast file download link.
        
        Returns:
            Locator: Playwright Locator object for the download link, or None.
        """
        link_text = "Current Procurement Forecasts"
        selector = f'a:has-text("{link_text}")'
        
        self.logger.info(f"Searching for download link locator with text: '{link_text}'")
        locator = self.page.locator(selector)
        
        if locator.count() > 0:
            try:
                href = locator.first.get_attribute('href')
                if href:
                    absolute_url = urljoin(self.page.url, href)
                    self.logger.info(f"Found download link locator. Href: {href} (Absolute: {absolute_url})")
                    # Optional: Add check if URL looks valid?
                else:
                     self.logger.warning("Found download link locator, but it has no href.")
                return locator.first
            except Exception as e:
                self.logger.error(f"Error getting href from locator: {e}")
                return locator.first
        
        self.logger.error(f"Could not find locator for link with text: '{link_text}'")
        return None
    
    def _save_debug_info(self):
        """Save debug information when the download link is not found."""
        # Save a screenshot for debugging
        screenshot_path = os.path.join(self.download_path, 'page_screenshot.png') # Save in scraper's dir
        self.page.screenshot(path=screenshot_path)
        self.logger.info(f"Saved screenshot to {screenshot_path}")
        
        # Save page content for debugging
        html_path = os.path.join(self.download_path, 'page_content.html') # Save in scraper's dir
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.page.content())
        self.logger.info(f"Saved page content to {html_path}")
    
    def download_forecast_document(self):
        """
        Download the forecast document from the Commerce website.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Attempting to download Commerce forecast document")
        
        try:
            # Navigate to the main forecast page first to establish context/cookies if needed
            self.logger.info(f"Navigating to {self.base_url}")
            self.navigate_to_url()
            
            # Find the locator for the download link
            download_locator = self._find_download_link_locator()
            
            if not download_locator:
                self.logger.error("Could not find the DOC download link locator")
                self._save_debug_info()
                raise ScraperError("Could not find the DOC forecast download link locator")

            # Dispatch click event on the locator and wait for the download
            self.logger.info(f"Dispatching click event on download link locator and waiting for download...")
            with self.page.expect_download(timeout=90000) as download_info:
                 # Use dispatch_event on the located element
                 download_locator.dispatch_event('click')

            _ = download_info.value # Access the download object to ensure the event is processed.

            # Wait a brief moment for the download event to be processed by the callback
            self.page.wait_for_timeout(2000) # Adjust as needed

            if not self._last_download_path or not os.path.exists(self._last_download_path):
                # This block can be further enhanced by trying to get the path from download_info.value if needed
                # For now, strictly relying on _handle_download setting the path.
                self.logger.error(f"BaseScraper._last_download_path not set or invalid. Value: {self._last_download_path}")
                raise ScraperError("Download failed: File not found or path not set by BaseScraper._handle_download.")

            self.logger.info(f"Download process completed. File saved at: {self._last_download_path}")
            return self._last_download_path
            
        except PlaywrightTimeoutError as e:
            handle_scraper_error(e, self.source_name, "Timeout downloading DOC forecast document")
            raise ScraperError(f"Timeout downloading DOC forecast document: {str(e)}")
        except Exception as e:
            # Ensure error is re-raised after handling
            handle_scraper_error(e, self.source_name, "Error downloading DOC forecast document")
            raise ScraperError(f"Failed to download DOC forecast document: {str(e)}")
    
    def process_func(self, file_path: str):
        """
        Process the downloaded Excel file, transform data to Prospect objects, 
        and insert into the database using logic adapted from doc_transform.py.
        """
        self.logger.info(f"Processing downloaded Excel file: {file_path}")
        try:
            # DOC transform script specifics: reads 'Sheet1', header is row 3 (index 2)
            df = pd.read_excel(file_path, sheet_name='Sheet1', header=2)
            self.logger.info(f"Loaded {len(df)} rows from {file_path}")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from doc_transform.normalize_columns_doc ---
            rename_map = {
                # Raw DOC Name: Prospect Model Field Name (or intermediate)
                'Forecast ID': 'native_id',
                'Organization': 'agency', # Maps to Prospect.agency
                'Title': 'title',
                'Description': 'description',
                'Naics Code': 'naics',
                'Place Of Performance City': 'place_city',
                'Place Of Performance State': 'place_state',
                'Place Of Performance Country': 'place_country',
                'Estimated Value Range': 'estimated_value_raw', 
                'Estimated Solicitation Fiscal Year': 'solicitation_fy_raw',
                'Estimated Solicitation Fiscal Quarter': 'solicitation_qtr_raw',
                'Anticipated Set Aside And Type': 'set_aside',
                # Fields for 'extra':
                'Anticipated Action Award Type': 'action_award_type',
                'Competition Strategy': 'competition_strategy',
                'Anticipated Contract Vehicle': 'contract_vehicle'
            }
            rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=rename_map_existing, inplace=True)

            # Derive Solicitation Date (becomes Prospect.release_date)
            if 'solicitation_fy_raw' in df.columns and 'solicitation_qtr_raw' in df.columns:
                df['solicitation_qtr_str'] = df['solicitation_qtr_raw'].astype(str).apply(lambda x: f'Q{x}' if x.isdigit() else x)
                df['solicitation_fyq_raw'] = df['solicitation_fy_raw'].astype(str) + ' ' + df['solicitation_qtr_str']
                # fiscal_quarter_to_date returns (timestamp, fiscal_year)
                parsed_sol_date_info = df['solicitation_fyq_raw'].apply(fiscal_quarter_to_date)
                df['release_date'] = parsed_sol_date_info.apply(lambda x: x[0].date() if pd.notna(x[0]) else None)
                # We could also get solicitation_fiscal_year here if needed, but Prospect model doesn't have it directly.
            else:
                df['release_date'] = None
                self.logger.warning("Could not parse solicitation date for DOC - FY or Quarter column missing.")

            # Parse Estimated Value
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            else:
                df['estimated_value'] = pd.NA
                df['est_value_unit'] = pd.NA
            
            # Initialize missing Prospect fields not in DOC source directly
            df['award_date'] = None # DOC transform initializes with NaT
            df['award_fiscal_year'] = pd.NA
            
            # Default place_country if not present (DOC transform assumes USA)
            if 'place_country' not in df.columns:
                df['place_country'] = 'USA'

            # Drop raw/intermediate columns
            cols_to_drop = ['estimated_value_raw', 'solicitation_fy_raw', 'solicitation_qtr_raw', 
                            'solicitation_qtr_str', 'solicitation_fyq_raw']
            df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore', inplace=True)
            # --- End: Logic adapted from doc_transform.normalize_columns_doc ---
            
            # Define the final column rename map.
            # The keys are current column names in df, values are Prospect model field names.
            # If names are already matching, they still need to be in the map.
            final_column_rename_map = {
                'native_id': 'native_id',
                'agency': 'agency',
                'title': 'title',
                'description': 'description',
                'naics': 'naics',
                'place_city': 'place_city',
                'place_state': 'place_state',
                'place_country': 'place_country',
                'estimated_value': 'estimated_value',
                'est_value_unit': 'est_value_unit',
                'release_date': 'release_date',
                'award_date': 'award_date',
                'award_fiscal_year': 'award_fiscal_year',
                'set_aside': 'set_aside',
                # Raw fields that will go to 'extra' if not explicitly mapped to a model field by _process_and_load_data
                # Ensure these are actual column names in df at this point if they are intended for 'extra'
                'action_award_type': 'action_award_type', 
                'competition_strategy': 'competition_strategy',
                'contract_vehicle': 'contract_vehicle'
            }

            # Ensure all columns in final_column_rename_map exist in df, add them with NA if not.
            # This is important because _process_and_load_data expects keys of final_column_rename_map to be in df.
            for col_name in final_column_rename_map.keys():
                if col_name not in df.columns:
                    df[col_name] = pd.NA
            
            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            # Original ID generation was: unique_string = f"{naics_val}-{title_val}-{desc_val}-{self.source_name}"
            # These correspond to 'naics', 'title', 'description' in the df after initial renaming.
            fields_for_id_hash = ['naics', 'title', 'description']

            return self._process_and_load_data(df, final_column_rename_map, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"DOC Excel file not found: {file_path}")
            raise ScraperError(f"Processing failed: DOC Excel file not found: {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty DOC Excel file: {file_path}")
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during DOC Excel processing: {e}. Check mappings or file format.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing DOC file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing DOC file {file_path}: {str(e)}")

    def scrape(self):
        """
        Run the scraper to download the forecast document.
        
        Returns:
            dict: Result object from scrape_with_structure
        """
        # Use the structured scrape method from the base class - only extract
        return self.scrape_with_structure(
            # Setup is handled within download_forecast_document now
            extract_func=self.download_forecast_document,
            process_func=self.process_func # Add process_func
        )