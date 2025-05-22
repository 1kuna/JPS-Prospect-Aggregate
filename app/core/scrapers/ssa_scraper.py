"""Social Security Administration Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
# import sys # Unused
import shutil
import datetime # Used for datetime.datetime

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
import hashlib
# import traceback # Redundant
# import re # Unused
from datetime import datetime # Used for type hinting and direct use
import json

# Local application imports
from app.core.base_scraper import BaseScraper
from app.database.models import Prospect, DataSource, db # Removed ScraperStatus
# from app.database.crud import bulk_upsert_prospects # Unused
from app.exceptions import ScraperError
from app.utils.logger import logger
# from app.utils.db_utils import update_scraper_status # Unused
from app.config import active_config # Import active_config
from app.utils.scraper_utils import (
    # check_url_accessibility, # Unused
    # download_file, # Unused
    # save_permanent_copy, # Unused
    handle_scraper_error
)
from app.utils.parsing import parse_value_range, split_place

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.ssa")

class SsaScraper(BaseScraper):
    """Scraper for the Social Security Administration (SSA) Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the SSA Forecast scraper."""
        super().__init__(
            source_name="SSA Forecast",
            base_url=active_config.SSA_CONTRACT_FORECAST_URL,
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
        # Prioritize the specific link text observed
        selectors.insert(0, 'a:has-text("FY25 SSA Contract Forecast")') 

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
    
    def download_forecast_document(self):
        """
        Download the forecast document from the SSA website.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Downloading forecast document")
        
        try:
            # Navigate to the forecast page
            self.logger.info(f"Navigating to {self.base_url}")
            try:
                # Assuming navigate_to_url sets up self.page correctly
                self.navigate_to_url() 
            except Exception as e:
                self.logger.error(f"Error navigating to forecast page: {str(e)}")
                self.logger.error(traceback.format_exc())
                raise # Re-raise the navigation error
            
            # Find the Excel link
            excel_link_href = self._find_excel_link()
            
            if not excel_link_href:
                self.logger.error("Could not find Excel link on the page")
                self._save_debug_info() # Save debug info if link not found
                raise ScraperError("Could not find Excel download link on the page")
            
            # Click the link and wait for the download
            self.logger.info(f"Clicking link '{excel_link_href}' and waiting for download...")
            # Use the specific link found
            link_selector = f'a[href="{excel_link_href}"]'
            with self.page.expect_download(timeout=60000) as download_info:
                 self.page.click(link_selector)

            _ = download_info.value # Access the download object

            # Wait a brief moment for the download event to be processed by the callback
            self.page.wait_for_timeout(2000) # Adjust as needed

            if not self._last_download_path or not os.path.exists(self._last_download_path):
                self.logger.error(f"BaseScraper._last_download_path not set or invalid. Value: {self._last_download_path}")
                # Fallback or detailed error logging
                try:
                    download_obj_for_debug = download_info.value 
                    temp_playwright_path = download_obj_for_debug.path()
                    self.logger.warning(f"Playwright temp download path for debugging: {temp_playwright_path}")
                except Exception as path_err:
                    self.logger.error(f"Could not retrieve Playwright temp download path for debugging: {path_err}")
                raise ScraperError("Download failed: File not found or path not set by BaseScraper._handle_download.")

            self.logger.info(f"Download process completed. File saved at: {self._last_download_path}")
            return self._last_download_path
            
        except PlaywrightTimeoutError as e:
            handle_scraper_error(e, self.source_name, "Timeout downloading forecast document")
            raise ScraperError(f"Timeout downloading forecast document: {str(e)}")
        except Exception as e:
            handle_scraper_error(e, self.source_name, "Error downloading forecast document")
            raise ScraperError(f"Failed to download forecast document: {str(e)}")
    
    def process_func(self, file_path: str):
        """
        Process the downloaded Excel file (.xlsm), transform data to Prospect objects,
        and insert into the database using logic adapted from ssa_transform.py.
        """
        self.logger.info(f"Processing downloaded Excel file: {file_path}")
        try:
            # SSA transform: reads 'Sheet1', header is row 5 (index 4), engine='openpyxl' for .xlsm
            df = pd.read_excel(file_path, sheet_name='Sheet1', header=4, engine='openpyxl')
            df.dropna(how='all', inplace=True) # Pre-processing from transform script
            self.logger.info(f"Loaded {len(df)} rows from {file_path} after initial dropna.")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from ssa_transform.normalize_columns_ssa ---
            rename_map = {
                'APP #': 'native_id',
                'SITE Type': 'agency', # Mapped to Prospect.agency (was 'office' in transform)
                'DESCRIPTION': 'description', # Mapped to Prospect.description (was 'requirement_title' in transform)
                # 'REQUIREMENT TYPE': 'requirement_type', # This will go to extra
                'EST COST PER FY': 'estimated_value_raw',
                'PLANNED AWARD DATE': 'award_date_raw',
                'CONTRACT TYPE': 'contract_type',
                'NAICS': 'naics',
                'TYPE OF COMPETITION': 'set_aside',
                'PLACE OF PERFORMANCE': 'place_raw'
            }
            # Rename only columns that exist in the input DataFrame
            rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=rename_map_existing, inplace=True)

            # Place of Performance Parsing
            if 'place_raw' in df.columns:
                split_places_data = df['place_raw'].apply(split_place)
                df['place_city'] = split_places_data.apply(lambda x: x[0])
                df['place_state'] = split_places_data.apply(lambda x: x[1])
                df['place_country'] = 'USA'  # Assume USA
            else:
                df['place_city'], df['place_state'], df['place_country'] = pd.NA, pd.NA, 'USA'

            # Estimated Value Parsing
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                # Add " (Per FY)" to unit as per transform script logic if unit is present
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
                unit_mask = df['est_value_unit'].notna()
                df.loc[unit_mask, 'est_value_unit'] = df.loc[unit_mask, 'est_value_unit'].astype(str) + ' (Per FY)'
                df['est_value_unit'].fillna('Per FY', inplace=True) # Default if no unit parsed
            else:
                df['estimated_value'], df['est_value_unit'] = pd.NA, pd.NA

            # Award Date and Fiscal Year Parsing
            if 'award_date_raw' in df.columns:
                df['award_date'] = pd.to_datetime(df['award_date_raw'], errors='coerce').dt.date
                df['award_fiscal_year'] = pd.to_datetime(df['award_date_raw'], errors='coerce').dt.year.astype('Int64')
            else:
                df['award_date'] = None
                df['award_fiscal_year'] = pd.NA

            # Initialize missing Prospect fields
            df['title'] = df.get('description', pd.NA) # Using description as title for SSA as per initial thought, or set to NA
                                                      # The original transform maps 'DESCRIPTION' source to 'requirement_title'.
                                                      # If 'title' is a distinct concept, it might be empty for SSA.
                                                      # For now, let's use description for title. If a dedicated title field appears, adjust.
            df['release_date'] = None # SSA transform has solicitation_date = pd.NaT

            # Drop raw/intermediate columns
            cols_to_drop = ['place_raw', 'estimated_value_raw', 'award_date_raw']
            df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore', inplace=True)
            # --- End: Logic adapted from ssa_transform.normalize_columns_ssa ---

            # Define the final column rename map.
            final_column_rename_map = {
                'native_id': 'native_id',
                'agency': 'agency',
                'description': 'description', # Mapped from 'DESCRIPTION'
                'title': 'title', # Initialized from 'description'
                'estimated_value': 'estimated_value',
                'est_value_unit': 'est_value_unit',
                'award_date': 'award_date',
                'award_fiscal_year': 'award_fiscal_year',
                'contract_type': 'contract_type',
                'naics': 'naics',
                'set_aside': 'set_aside',
                'place_city': 'place_city',
                'place_state': 'place_state',
                'place_country': 'place_country',
                'release_date': 'release_date', # Initialized as None
                # 'REQUIREMENT TYPE' was in original source, if renamed to 'requirement_type',
                # it will be handled by 'extra' if not in prospect_model_fields.
                # No explicit mapping here means it should be picked by extra logic if present.
            }

            # Ensure all columns in final_column_rename_map exist in df.
            for col_name in final_column_rename_map.keys():
                if col_name not in df.columns:
                    df[col_name] = pd.NA
            
            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            # Original ID generation: naics, description (as requirement_title), agency
            fields_for_id_hash = ['naics', 'description', 'agency']


            return self._process_and_load_data(df, final_column_rename_map, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"SSA Excel file not found: {file_path}")
            raise ScraperError(f"Processing failed: SSA Excel file not found: {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty SSA Excel file: {file_path}")
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during SSA Excel processing: {e}.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing SSA file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing SSA file {file_path}: {str(e)}")

    def scrape(self):
        """
        Run the scraper to download the forecast document.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        # Use the structured scrape method from the base class - only extract
        return self.scrape_with_structure(
            # No setup_func needed if navigation happens in extract
            extract_func=self.download_forecast_document,
            process_func=self.process_func
        )