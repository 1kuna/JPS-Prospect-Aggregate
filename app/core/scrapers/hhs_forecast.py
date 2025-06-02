"""Department of Health and Human Services Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
# import sys # Unused

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
# import traceback # Redundant
# import re # Unused

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect
# from app.database.crud import bulk_upsert_prospects # Unused
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.config import active_config # Import active_config
from app.utils.scraper_utils import handle_scraper_error
from app.utils.parsing import parse_value_range

# Set up logging using the centralized utility
logger = logger.bind(name="scraper.hhs_forecast")

class HHSForecastScraper(BaseScraper):
    """Scraper for the HHS Opportunity Forecast site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the HHS Forecast scraper."""
        super().__init__(
            source_name="Health and Human Services",
            base_url=active_config.HHS_FORECAST_URL,
            debug_mode=debug_mode
        )
    
    def download_forecast_document(self):
        """
        Download the forecast document from the HHS website.
        Requires clicking 'View All' then 'Export'.
        Saves the file directly to the scraper's download directory.

        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        self.logger.info("Attempting to download HHS forecast document")
        
        view_all_selector = 'button[data-cy="viewAllBtn"]' 
        export_button_selector = 'button:has-text("Export")'
        
        try:
            # Navigate to the main forecast page
            self.logger.info(f"Navigating to {self.base_url}")
            self.navigate_to_url()
            self.logger.info("Page loaded.")

            # Use the new helper method to handle pre-click, main click, and download
            return self._click_and_download(
                download_trigger_selector=export_button_selector,
                pre_click_selector=view_all_selector,
                # Wait 10 seconds after clicking "View All" for the page to update
                # and the Export button to become available/interactive.
                pre_click_wait_ms=10000 
            )
            
        except PlaywrightTimeoutError as e: # This might catch timeouts from navigate_to_url
            self.logger.error(f"Timeout error during HHS forecast download process: {e}")
            handle_scraper_error(e, self.source_name, "Timeout during HHS download process")
            raise ScraperError(f"Timeout during HHS forecast download process: {str(e)}") from e
        except ScraperError as se: # Catch ScraperErrors raised by _click_and_download or elsewhere
            self.logger.error(f"ScraperError during HHS forecast download: {se}")
            handle_scraper_error(se, self.source_name, "HHS download operation")
            raise # Re-raise the ScraperError
        except Exception as e: # Catch any other general exceptions
            self.logger.error(f"General error during HHS forecast download: {e}")
            handle_scraper_error(e, self.source_name, "Error downloading HHS forecast document")
            if not isinstance(e, ScraperError): # Wrap if it's not already a ScraperError
                 raise ScraperError(f"Failed to download HHS forecast document: {str(e)}") from e
            else:
                 raise # Re-raise if it's already a ScraperError
    
    def process_func(self, file_path: str):
        """
        Process the downloaded CSV file, transform data to Prospect objects,
        and insert into the database using logic adapted from hhs_transform.py.
        """
        self.logger.info(f"Processing downloaded CSV file: {file_path}")
        try:
            df = pd.read_csv(file_path, header=0, on_bad_lines='skip')
            df.dropna(how='all', inplace=True) # Pre-processing from transform script
            self.logger.info(f"Loaded {len(df)} rows from {file_path} after initial dropna.")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return

            # --- Start: Logic adapted from hhs_transform.normalize_columns_hhs ---
            rename_map = {
                # Raw HHS Name: Prospect Model Field Name (or intermediate)
                'Procurement Number': 'native_id',
                'Operating Division': 'agency', # Maps to Prospect.agency
                'Requirement Title': 'title',
                'Requirement Description': 'description',
                'NAICS Code': 'naics',
                'Contract Vehicle': 'contract_vehicle', # To extra
                'Contract Type': 'contract_type',
                'Estimated Contract Value': 'estimated_value_raw',
                'Anticipated Award Date': 'award_date_raw',
                'Anticipated Solicitation Release Date': 'release_date_raw',
                'Small Business Set-Aside': 'set_aside',
                'Place of Performance City': 'place_city',
                'Place of Performance State': 'place_state',
                'Place of Performance Country': 'place_country'
                # 'Contact Name', 'Contact Email', 'Contact Phone' -> To extra
            }
            
            # Rename only columns that exist
            rename_map_existing = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=rename_map_existing, inplace=True)

            # Date Parsing
            if 'award_date_raw' in df.columns:
                df['award_date'] = pd.to_datetime(df['award_date_raw'], errors='coerce').dt.date
                df['award_fiscal_year'] = pd.to_datetime(df['award_date_raw'], errors='coerce').dt.year.astype('Int64')
            else:
                df['award_date'] = None
                df['award_fiscal_year'] = pd.NA

            if 'release_date_raw' in df.columns:
                df['release_date'] = pd.to_datetime(df['release_date_raw'], errors='coerce').dt.date
            else:
                df['release_date'] = None

            # Estimated Value Parsing
            if 'estimated_value_raw' in df.columns:
                parsed_values = df['estimated_value_raw'].apply(parse_value_range)
                df['estimated_value'] = parsed_values.apply(lambda x: x[0])
                df['est_value_unit'] = parsed_values.apply(lambda x: x[1])
            else:
                df['estimated_value'] = pd.NA
                df['est_value_unit'] = pd.NA

            # Default place_country if not present (HHS transform assumes USA)
            if 'place_country' not in df.columns:
                 df['place_country'] = 'USA'
            elif 'place_country' in df.columns: # Ensure consistent handling of empty/NaN
                 df['place_country'] = df['place_country'].fillna('USA')


            # Drop raw/intermediate columns
            cols_to_drop = ['award_date_raw', 'release_date_raw', 'estimated_value_raw']
            df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore', inplace=True)
            # --- End: Logic adapted from hhs_transform.normalize_columns_hhs ---

            # Define the final column rename map.
            final_column_rename_map = {
                'native_id': 'native_id',
                'agency': 'agency',
                'title': 'title',
                'description': 'description',
                'naics': 'naics',
                'contract_vehicle': 'contract_vehicle', # This will go to extra
                'contract_type': 'contract_type',
                'estimated_value': 'estimated_value',
                'est_value_unit': 'est_value_unit',
                'award_date': 'award_date',
                'award_fiscal_year': 'award_fiscal_year',
                'release_date': 'release_date',
                'set_aside': 'set_aside',
                'place_city': 'place_city',
                'place_state': 'place_state',
                'place_country': 'place_country',
                'row_index': 'row_index', # Include row_index for uniqueness
                # Columns like 'Contact Name', 'Contact Email', 'Contact Phone'
                # will be handled by _process_and_load_data if they exist in df
                # and are not in prospect_model_fields, so they don't need explicit map here
                # unless renaming them.
                # Assuming they are already named e.g., 'contact_name' from initial rename or direct from source.
                # If their original names are 'Contact Name', they should be included in the initial rename_map.
            }
            
            # Ensure all columns in final_column_rename_map exist in df.
            for col_name in final_column_rename_map.keys():
                if col_name not in df.columns:
                    df[col_name] = pd.NA

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            # Original ID generation: native_id if available, else title, desc, agency
            # Using native_id as primary, common logic in _process_and_load_data will use fields_for_id_hash
            # if 'id' column isn't already populated. Here, we assume 'native_id' is the preferred unique key.
            # If 'native_id' is consistently present and unique, this is fine.
            # Otherwise, a composite key might be better.
            # For now, let's use the more robust composite key as per original logic.
            # The _process_and_load_data will generate 'id' if not present.
            # We need to ensure the columns for the hash are correctly named.
            # The original hash logic was:
            #   if native_id_val: unique_string = f"{native_id_val}-{self.source_name}"
            #   else: unique_string = f"{title_val}-{desc_val}-{agency_val}-{self.source_name}"
            # This conditional logic is not directly supported by fields_for_id_hash.
            # We will rely on a consistent set of fields for hashing.
            # If native_id is present, it should be part of the hash.
            # HHS data contains true duplicates, so we need to add row index for uniqueness
            # First, add a unique row identifier to distinguish true duplicates
            df.reset_index(drop=False, inplace=True)
            df['row_index'] = df.index
            
            # Include comprehensive fields plus row index to ensure uniqueness
            fields_for_id_hash = ['native_id', 'naics', 'title', 'description', 'agency', 'place_city', 'place_state', 'contract_type', 'set_aside', 'estimated_value', 'award_date', 'release_date', 'row_index']


            return self._process_and_load_data(df, final_column_rename_map, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"HHS CSV file not found: {file_path}")
            raise ScraperError(f"Processing failed: HHS CSV file not found: {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty HHS CSV file: {file_path}")
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during HHS CSV processing: {e}.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing HHS file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing HHS file {file_path}: {str(e)}")

    def scrape(self):
        """
        Run the scraper to download the forecast document.
        Returns a result dict from scrape_with_structure.
        """
        return self.scrape_with_structure(
            extract_func=self.download_forecast_document,
            process_func=self.process_func
        )