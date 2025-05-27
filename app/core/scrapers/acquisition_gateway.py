"""Acquisition Gateway scraper."""

# Standard library imports
import traceback # Keep one traceback

# Third-party imports
import pandas as pd # Add pandas
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
from app.core.base_scraper import BaseScraper
from app.models import Prospect # Removed ScraperStatus
from app.config import active_config # Import active_config
from app.exceptions import ScraperError
# from app.utils.file_utils import ensure_directory # Removed ensure_directory
from app.utils.logger import logger
# from app.utils.scraper_utils import handle_scraper_error # Removed unused import
# import hashlib # No longer needed here

# Set up logging
logger = logger.bind(name="scraper.acquisition_gateway")

# Removed local check_url_accessibility function. Use self.check_url_accessibility() from BaseScraper.

class AcquisitionGatewayScraper(BaseScraper):
    """Scraper for the Acquisition Gateway site."""
    
    def __init__(self, debug_mode=False):
        """Initialize the Acquisition Gateway scraper."""
        super().__init__(
            source_name="Acquisition Gateway",
            base_url=active_config.ACQUISITION_GATEWAY_URL,
            debug_mode=debug_mode,
            use_stealth=True # Enable stealth mode for this scraper
        )
    
    def navigate_to_forecast_page(self):
        """Navigate to the forecast page."""
        return self.navigate_to_url()
    
    def download_csv_file(self):
        """
        Download the CSV file from the Acquisition Gateway site.
        Saves the file directly to the scraper's download directory.
        
        Returns:
            str: Path to the downloaded file.
        
        Raises:
            ScraperError: If the download process fails.
        """
        self.logger.info("Attempting to download CSV file using _click_and_download.")
        try:
            # The navigate_to_forecast_page in setup_func handles initial page load.
            # _click_and_download handles waiting for the selector and the download itself.
            downloaded_file_path = self._click_and_download(
                download_trigger_selector='button#export-0',
                click_method="click_then_js",
                wait_for_trigger_timeout_ms=60000, # Matches original explicit wait for button visibility
                download_timeout_ms=120000 # Matches original download timeout
            )
            
            self.logger.info(f"CSV file download successful. Path: {downloaded_file_path}")
            return downloaded_file_path

        except ScraperError as e: # Catch ScraperError from _click_and_download or other steps
            # Logged already by _click_and_download or other base methods if it's a ScraperError
            # Re-raise to be handled by scrape_with_structure
            raise 
        except Exception as e:
            # For any other unexpected errors during this specific download sequence
            error_message = f"An unexpected error occurred in download_csv_file: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(traceback.format_exc())
            raise ScraperError(error_message, error_type="download_error") from e
    
    def process_func(self, file_path: str):
        """
        Process the downloaded CSV file, transform data to Prospect objects, 
        and insert into the database using logic adapted from acqg_transform.py.
        """
        self.logger.info(f"Processing downloaded CSV file: {file_path}")
        try:
            df = pd.read_csv(file_path, header=0, on_bad_lines='skip')
            self.logger.info(f"Loaded {len(df)} rows from {file_path}")

            if df.empty:
                self.logger.info("Downloaded file is empty. Nothing to process.")
                return 0 # Return 0 as no records processed

            # Scraper-specific parsing (before common processing)
            # Fallback for description (already handled by rename_map if 'Body' exists)
            if 'Body' not in df.columns and 'Summary' in df.columns:
                 df.rename(columns={'Summary': 'Body'}, inplace=True) # Rename Summary to Body so map picks it up

            # Date Parsing
            if 'Estimated Solicitation Date' in df.columns:
                df['Estimated Solicitation Date'] = pd.to_datetime(df['Estimated Solicitation Date'], errors='coerce').dt.date
            
            if 'Ultimate Completion Date' in df.columns: # This is for 'award_date_raw'
                df['Ultimate Completion Date'] = pd.to_datetime(df['Ultimate Completion Date'], errors='coerce').dt.date

            # Fiscal Year Parsing/Extraction - simplified as common logic will handle this if column exists
            if 'Estimated Award FY' in df.columns:
                df['Estimated Award FY'] = pd.to_numeric(df['Estimated Award FY'], errors='coerce')
                # Fallback for NA fiscal years if award_date (from Ultimate Completion Date) is present
                if 'Ultimate Completion Date' in df.columns:
                    fallback_mask = df['Estimated Award FY'].isna() & df['Ultimate Completion Date'].notna()
                    df.loc[fallback_mask, 'Estimated Award FY'] = df.loc[fallback_mask, 'Ultimate Completion Date'].dt.year
            elif 'Ultimate Completion Date' in df.columns and df['Ultimate Completion Date'].notna().any():
                self.logger.warning("'Estimated Award FY' not in source, extracting year from 'Ultimate Completion Date' as fallback for award_fiscal_year.")
                df['Estimated Award FY'] = df['Ultimate Completion Date'].dt.year # Create the column
            
            # Ensure 'Estimated Award FY' is Int64 if it exists
            if 'Estimated Award FY' in df.columns:
                 df['Estimated Award FY'] = df['Estimated Award FY'].astype('Int64')


            # Estimated Value Parsing
            if 'Estimated Contract Value' in df.columns:
                df['Estimated Contract Value'] = pd.to_numeric(df['Estimated Contract Value'], errors='coerce')
            # est_value_unit is None for AcqG, so no specific parsing needed here for it.

            # Define mappings and call the common processing method
            column_rename_map = {
                'Listing ID': 'native_id',
                'Title': 'title',
                'Body': 'description', # Renamed 'Summary' to 'Body' above if 'Body' was missing
                'NAICS Code': 'naics',
                'Estimated Contract Value': 'estimated_value',
                'Estimated Solicitation Date': 'release_date',
                'Ultimate Completion Date': 'award_date', # Directly map to award_date after parsing
                'Estimated Award FY': 'award_fiscal_year',
                'Organization': 'agency',
                'Place of Performance City': 'place_city',
                'Place of Performance State': 'place_state',
                'Place of Performance Country': 'place_country',
                'Contract Type': 'contract_type',
                'Set Aside Type': 'set_aside'
            }
            
            # Ensure all mapped source columns exist in df before passing to _process_and_load_data
            # This is implicitly handled by how rename works (only existing columns are renamed)
            # and how _process_and_load_data handles missing fields later.

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            fields_for_id_hash = ['naics', 'title', 'description'] # After renaming

            return self._process_and_load_data(df, column_rename_map, prospect_model_fields, fields_for_id_hash)

        except FileNotFoundError:
            self.logger.error(f"CSV file not found at {file_path}")
            raise ScraperError(f"Processing failed: CSV file not found at {file_path}")
        except pd.errors.EmptyDataError:
            self.logger.error(f"No data or empty CSV file at {file_path}")
            # No ScraperError here, just log and return, as it's not a processing failure but empty source data.
            return
        except KeyError as e:
            self.logger.error(f"Missing expected column during CSV processing: {e}. This might indicate a change in the CSV format or an issue with mappings.")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Processing failed due to missing column: {e}")
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ScraperError(f"Error processing file {file_path}: {str(e)}")
    
    def scrape(self):
        """
        Run the scraper to download the file.
        
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        # Simplified call: only setup and extract
        return self.scrape_with_structure(
            setup_func=self.navigate_to_forecast_page,
            extract_func=self.download_csv_file,
            process_func=self.process_func # Add process_func
        )

# Removed check_last_download function as it's obsolete.