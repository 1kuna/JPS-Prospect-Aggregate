"""Social Security Administration Opportunity Forecast scraper."""

# Standard library imports
import os
import traceback
import sys
import shutil
import datetime

# Third-party imports
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import pandas as pd
import hashlib
import traceback
import re
from datetime import datetime
import json

# Local application imports
from app.core.base_scraper import BaseScraper
from app.database.models import Prospect, DataSource, ScraperStatus, db
from app.database.crud import bulk_upsert_prospects
from app.exceptions import ScraperError
from app.utils.logger import logger
from app.utils.db_utils import update_scraper_status
from app.config import active_config # Import active_config
from app.utils.scraper_utils import (
    check_url_accessibility,
    download_file,
    save_permanent_copy,
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

            download = download_info.value

            # --- Start modification for timestamped filename ---
            original_filename = download.suggested_filename
            if not original_filename:
                self.logger.warning("Download suggested_filename is empty, using default 'ssa_download.xlsx'")
                original_filename = "ssa_download.xlsx"

            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.xlsx' # Default extension
                self.logger.warning(f"Original filename '{original_filename}' had no extension, defaulting to '{ext}'")

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use hardcoded identifier 'ssa'
            final_filename = f"ssa_{timestamp_str}{ext}"
            final_path = os.path.join(self.download_path, final_filename)
            self.logger.info(f"Original suggested filename: {original_filename}")
            self.logger.info(f"Saving with standardized filename: {final_filename} to {final_path}")
            # --- End modification ---

            # The file is saved by the _handle_download callback in BaseScraper or manually below
            self.logger.info(f"Download complete. File expected at: {final_path}")

            # Verify the file exists (saved by _handle_download or manually) using the new final_path
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                self.logger.error(f"Verification failed: File not found or empty at {final_path}")
                # Attempt to save manually first
                try:
                    download.save_as(final_path)
                    self.logger.warning(f"Manually saved file to {final_path}")
                    if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                        raise ScraperError(f"Download failed even after manual save: File missing or empty at {final_path}")
                except Exception as save_err:
                    # If save_as failed, try moving from playwright temp path
                    try:
                        fallback_path = download.path()
                        if fallback_path and os.path.exists(fallback_path):
                            shutil.move(fallback_path, final_path)
                            self.logger.warning(f"Manually moved file from {fallback_path} to {final_path}")
                            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                                raise ScraperError(f"Download failed after fallback move: File missing or empty at {final_path}")
                        else:
                            raise ScraperError(f"Download failed: File missing/empty at {final_path}, manual save failed ({save_err}), and Playwright temp path unavailable.")
                    except Exception as move_err:
                        raise ScraperError(f"Download failed: File missing/empty at {final_path}. Manual save failed: {save_err}. Fallback move failed: {move_err}")

            # Return the path within the scraper's download directory
            return final_path
            
            # Removed old download_file and save_permanent_copy logic
            # temp_path = download_file(self.page, f'a[href="{excel_link}"]')
            # return save_permanent_copy(temp_path, self.source_name, 'xlsx')
            
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

            # Standardize column names
            df.columns = df.columns.str.strip().str.lower().str.replace(r'\\s+\\(.*?\\)', '', regex=True).str.replace(r'\\s+', '_', regex=True).str.replace(r'[^a-z0-9_]', '', regex=True)
            df = df.loc[:, ~df.columns.duplicated()]

            prospect_model_fields = [col.name for col in Prospect.__table__.columns if col.name not in ['loaded_at', 'id', 'source_id']]
            current_cols_normalized = df.columns.tolist()
            # Ensure 'requirement_type' from source (if exists after rename) is handled by extra if not in prospect_model_fields
            # The original ssa_transform script includes 'requirement_type' in its explicit rename_map for source columns.
            # If this normalized to 'requirement_type' and is not a Prospect field, it will be in unmapped_cols.
            unmapped_cols = [col for col in current_cols_normalized if col not in prospect_model_fields]

            if unmapped_cols:
                self.logger.info(f"Found unmapped columns for 'extra' for SSA: {unmapped_cols}")
                def row_to_extra_json(row):
                    extra_dict = {}
                    for col_name in unmapped_cols:
                        val = row.get(col_name)
                        if pd.isna(val):
                            extra_dict[col_name] = None
                        elif pd.api.types.is_datetime64_any_dtype(val) or isinstance(val, (datetime, pd.Timestamp)):
                            extra_dict[col_name] = pd.to_datetime(val).isoformat()
                        elif isinstance(val, (int, float, bool, str)):
                            extra_dict[col_name] = val
                        else:
                            try: extra_dict[col_name] = str(val)
                            except Exception: extra_dict[col_name] = "CONVERSION_ERROR"
                    try: return json.dumps(extra_dict)
                    except TypeError: return str(extra_dict)
                df['extra'] = df.apply(row_to_extra_json, axis=1)
            else:
                df['extra'] = None

            for col in prospect_model_fields:
                if col not in df.columns:
                    df[col] = pd.NA

            data_source_obj = db.session.query(DataSource).filter_by(name=self.source_name).first()
            df['source_id'] = data_source_obj.id if data_source_obj else None

            # --- ID Generation (adapted from ssa_transform.generate_id) ---
            # Transform uses: naics, requirement_title (now mapped to description), requirement_description (not present after mapping)
            # Adjusting to use Prospect.naics, Prospect.description, Prospect.agency for uniqueness and consistency.
            def generate_prospect_id(row: pd.Series) -> str:
                naics_val = str(row.get('naics', ''))
                # title_val = str(row.get('title', '')) # Using description for title, as per current mapping
                desc_val = str(row.get('description', ''))
                agency_val = str(row.get('agency', '')) # Adding agency for better uniqueness
                unique_string = f"{naics_val}-{desc_val}-{agency_val}-{self.source_name}" # Consistent with other fallback IDs
                return hashlib.md5(unique_string.encode('utf-8')).hexdigest()
            df['id'] = df.apply(generate_prospect_id, axis=1)
            # --- End: ID Generation ---

            final_prospect_columns = [col.name for col in Prospect.__table__.columns if col.name != 'loaded_at']
            df_to_insert = df[[col for col in final_prospect_columns if col in df.columns]]

            df_to_insert.dropna(how='all', inplace=True)
            if df_to_insert.empty:
                self.logger.info("After SSA processing, no valid data rows to insert.")
                return

            self.logger.info(f"Attempting to insert/update {len(df_to_insert)} SSA records.")
            bulk_upsert_prospects(df_to_insert)
            self.logger.info(f"Successfully inserted/updated SSA records from {file_path}.")

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

def run_scraper(force=False):
    """
    Run the SSA Forecast scraper.
    
    Args:
        force (bool): Whether to force scraping even if recently run
        
    Returns:
        bool: True if scraping was successful
        
    Raises:
        ScraperError: If an error occurs during scraping
        ImportError: If required dependencies are not installed
    """
    scraper = None
    source_name = "SSA Forecast"
    
    try:
        # Check if we should run the scraper
        # Removed interval check logic
        # if not force and download_tracker.should_download(source_name):
        #     logger.info(f"Skipping scrape for {source_name} due to recent download")
        #     return True

        # Create an instance of the scraper
        scraper = SsaScraper(debug_mode=False)
        
        # Run the scraper
        logger.info(f"Running {source_name} scraper")
        success = scraper.scrape()
        
        # If scraper.scrape() returns False, it means an error occurred
        if not success:
            error_msg = "Scraper failed without specific error"
            handle_scraper_error(ScraperError(error_msg), source_name)
            raise ScraperError(error_msg)
        
        # Update the download tracker with the current time
        # Removed: download_tracker.set_last_download_time(source_name)
        # logger.info(f"Updated download tracker for {source_name}")
        
        # Update the ScraperStatus table to indicate success
        # --> Temporarily skip this during direct script execution <---
        # update_scraper_status(source_name, "working", None)
            
        return True
    except ImportError as e:
        error_msg = f"Import error: {str(e)}"
        logger.error(error_msg)
        logger.error("Playwright module not found. Please install it with 'pip install playwright'")
        logger.error("Then run 'playwright install' to install the browsers")
        handle_scraper_error(e, source_name, "Import error")
        raise
    except ScraperError as e:
        handle_scraper_error(e, source_name)
        raise
    except Exception as e:
        # Ensure error_msg is defined or handled appropriately
        error_msg = f"Error running scraper: {str(e)}"
        handle_scraper_error(e, source_name, "Error running scraper")
        raise ScraperError(error_msg)
    finally:
        if scraper:
            try:
                logger.info("Cleaning up scraper resources")
                scraper.cleanup_browser() # Correct method name
            except Exception as cleanup_error:
                logger.error(f"Error during scraper cleanup: {str(cleanup_error)}")

if __name__ == "__main__":
    # This block allows the script to be run directly for testing
    source_name = "SSA Forecast" # Define source_name here
    try:
        run_scraper(force=True)
        print(f"{source_name} scraper finished successfully (DB operations skipped).")
    except Exception as e:
        print(f"{source_name} scraper failed: {e}")