"""Department of Homeland Security Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
# import sys # Unused
# import shutil # Unused
# import datetime # Unused at top level, `from datetime import datetime` is used

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
# import hashlib # No longer needed here
# import re # Unused

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.utils.parsing import parse_value_range, fiscal_quarter_to_date
from app.config import active_config # Import active_config
from app.utils.scraper_utils import handle_scraper_error

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.dhs_forecast")

class DHSForecastScraper(BaseScraper):
    """Scraper for the DHS Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the DHS Forecast scraper."""
        super().__init__(
            source_name="DHS Forecast",
            base_url=active_config.DHS_FORECAST_URL,
            debug_mode=debug_mode
        )
    
    def download_forecast_document(self):
        """
        Download the forecast CSV document from the DHS APFS website.
        Requires waiting, then clicking the 'CSV' button.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Attempting to download DHS forecast document")
        
        # Selector for the CSV download button
        csv_button_selector = 'button.buttons-csv' 
        
        try:
            # Navigate to the main forecast page
            self.logger.info(f"Navigating to {self.base_url}")
            self.navigate_to_url()
            self.logger.info("Page loaded.")

            # Explicit wait for 10 seconds
            self.logger.info("Waiting for 10 seconds before interacting...")
            self.page.wait_for_timeout(10000) # 10 seconds explicit wait
            self.logger.info("Wait finished.")
            
            # Use the new helper method to click and download
            # The helper will handle waiting for the selector, clicking, and managing the download.
            # It also includes the _last_download_path check.
            return self._click_and_download(
                download_trigger_selector=csv_button_selector
                # Default timeouts from helper: wait_for_trigger_timeout_ms=30000, download_timeout_ms=90000
            )
            
        except PlaywrightTimeoutError as e: # This might catch timeouts from navigate_to_url or the explicit wait
            self.logger.error(f"Timeout error during DHS forecast download process: {e}")
            handle_scraper_error(e, self.source_name, "Timeout during DHS download process")
            raise ScraperError(f"Timeout during DHS forecast download process: {str(e)}") from e
        except ScraperError as se: # Catch ScraperErrors raised by _click_and_download or elsewhere
            self.logger.error(f"ScraperError during DHS forecast download: {se}")
            # handle_scraper_error is not strictly needed here if ScraperError is already logged by helper/source
            # For consistency, ensure handle_scraper_error is called if not already done by the source of error.
            # The _click_and_download helper logs its errors but doesn't call handle_scraper_error.
            # So, it's good to call it here.
            handle_scraper_error(se, self.source_name, "DHS download operation")
            raise # Re-raise the ScraperError
        except Exception as e: # Catch any other general exceptions
            self.logger.error(f"General error during DHS forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Error downloading DHS forecast document")
            if not isinstance(e, ScraperError): # Wrap if it's not already a ScraperError
                 raise ScraperError(f"Failed to download DHS forecast document: {str(e)}") from e
            else:
                 raise # Re-raise if it's already a ScraperError (though previous block should catch it)
    
    def process_func(self, file_path: str):
        """
        Process the downloaded Excel file, transform data to Prospect objects, 
        and insert into the database using logic adapted from dhs_transform.py.
        """
        self.logger.info(f"Processing downloaded Excel file: {file_path}")
        try:
            df = pd.read_excel(file_path, sheet_name=0, header=0) 
            self.logger.info(f"Loaded {len(df)} rows from {file_path}")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return 0 # Return 0 as no records processed

            # --- Scraper-specific pre-processing ---
            # Initial rename to standardized intermediate names, some of which might be final
            # Prospect field names.
            initial_rename_map = {
                'APFS Number': 'native_id', # Final Prospect field
                'NAICS': 'naics',           # Final Prospect field
                'Component': 'agency',      # Final Prospect field
                'Title': 'title',           # Final Prospect field
                'Contract Type': 'contract_type', # Final Prospect field
                'Contract Vehicle': 'contract_vehicle_raw', # Will go to extra
                'Dollar Range': 'estimated_value_raw',      # Needs parsing
                'Small Business Set-Aside': 'set_aside',     # Final Prospect field
                'Small Business Program': 'small_business_program_raw', # Will go to extra
                'Contract Status': 'contract_status_raw',        # Will go to extra
                'Place of Performance City': 'place_city',    # Final Prospect field
                'Place of Performance State': 'place_state',   # Final Prospect field
                'Description': 'description', # Final Prospect field
                'Estimated Solicitation Release': 'release_date_raw', # Needs parsing
                'Award Quarter': 'award_date_raw'           # Needs parsing
            }
            df.rename(columns=initial_rename_map, inplace=True)

            # Date Parsing (Solicitation/Release Date)
            df['release_date'] = pd.to_datetime(df.get('release_date_raw'), errors='coerce').dt.date if 'release_date_raw' in df.columns else None
            
            # Award Date and Fiscal Year Parsing
            if 'award_date_raw' in df.columns:
                parsed_award_info = df['award_date_raw'].apply(fiscal_quarter_to_date)
                df['award_date'] = parsed_award_info.apply(lambda x: x[0].date() if pd.notna(x[0]) else None)
                df['award_fiscal_year'] = parsed_award_info.apply(lambda x: x[1])
            else: 
                df['award_date'] = None
                df['award_fiscal_year'] = pd.NA
            if 'award_fiscal_year' in df.columns:
                df['award_fiscal_year'] = df['award_fiscal_year'].astype('Int64')

            # Estimated Value Parsing
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            else:
                df['estimated_value'] = pd.NA 
                df['est_value_unit'] = pd.NA

            # Initialize Place Country (DHS transform assumes USA)
            df['place_country'] = 'USA'
            
            # Columns that were raw and have been parsed can be dropped if desired,
            # or let _process_and_load_data handle them via 'extra' if they are not in final rename map.
            # For clarity, we might drop them here if they are truly intermediate.
            # df.drop(columns=['release_date_raw', 'award_date_raw', 'estimated_value_raw'], errors='ignore', inplace=True)
            # However, if we want them in 'extra', we should keep them and ensure they are not in the final_rename_map's values.

            # --- Define mappings for _process_and_load_data ---
            # These are the columns that are now ready to be mapped to final Prospect model fields
            # or are already named as such.
            final_column_rename_map = {
                # Source (already renamed or parsed) : Prospect Model Field
                'native_id': 'native_id',
                'naics': 'naics',
                'agency': 'agency',
                'title': 'title',
                'description': 'description',
                'contract_type': 'contract_type',
                'release_date': 'release_date', # Parsed from release_date_raw
                'award_date': 'award_date',       # Parsed from award_date_raw
                'award_fiscal_year': 'award_fiscal_year', # Parsed from award_date_raw
                'estimated_value': 'estimated_value', # Parsed from estimated_value_raw
                'est_value_unit': 'est_value_unit', # Parsed from estimated_value_raw
                'set_aside': 'set_aside',
                'place_city': 'place_city',
                'place_state': 'place_state',
                'place_country': 'place_country',
                # Raw fields that will go to 'extra' if not explicitly mapped to a model field
                'contract_vehicle_raw': 'contract_vehicle_raw', 
                'small_business_program_raw': 'small_business_program_raw',
                'contract_status_raw': 'contract_status_raw',
                # Also include original raw fields if they are needed in 'extra' and not dropped
                'release_date_raw': 'release_date_raw', 
                'award_date_raw': 'award_date_raw', 
                'estimated_value_raw': 'estimated_value_raw'
            }
            
            # Filter map for only columns present in df to avoid errors during rename
            final_column_rename_map_existing = {k: v for k, v in final_column_rename_map.items() if k in df.columns}

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            fields_for_id_hash = ['naics', 'title', 'description'] # Use final Prospect field names

            return self._process_and_load_data(df, final_column_rename_map_existing, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"Excel file not found at {file_path}")
            raise ScraperError(f"Processing failed: Excel file not found at {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty Excel file at {file_path}")
            return # Not a ScraperError, just empty source.
        except KeyError as e:
            self.logger.error(f"Missing expected column during Excel processing: {e}. Check mappings or file format.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing file {file_path}: {str(e)}")

    def scrape(self):
        """
        Run the scraper to download the forecast document.
        Returns a result dict from scrape_with_structure.
        """
        return self.scrape_with_structure(
            extract_func=self.download_forecast_document,
            process_func=self.process_func
        )
