"""Department of Transportation (DOT) Forecast scraper."""

import os
import time # For custom navigation delays
import shutil # For fallback file copy
from typing import Optional

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.core.specialized_scrapers import PageInteractionScraper
from app.config import active_config
from app.exceptions import ScraperError
from app.core.scrapers.configs.dot_config import DOTConfig
from app.utils.parsing import fiscal_quarter_to_date, parse_value_range, split_place # Used by mixin/custom

class DotScraper(PageInteractionScraper):
    """Scraper for the DOT Forecast site."""

    def __init__(self, config: DOTConfig, debug_mode: bool = False):
        super().__init__(config=config, debug_mode=debug_mode)
    
    def _get_default_url(self) -> str:
        """Return default URL for DOT scraper."""
        return active_config.DOT_FORECAST_URL

    def _setup_method(self) -> None:
        """Navigates to the DOT forecast page using custom retry logic and clicks 'Apply'."""
        self.logger.info(f"Navigating to {self.config.base_url} with custom retry logic (DOT).")
        if not self.page:
            self._handle_and_raise_scraper_error(ScraperError("Page not initialized before navigation."), "DOT custom navigation setup")
        
        time.sleep(2) # Initial 2s delay from original scraper

        for i, params in enumerate(self.config.navigation_retry_attempts, 1):
            operation_desc = f"DOT custom navigation attempt {i}/{len(self.config.navigation_retry_attempts)} to {self.config.base_url} with params {params}"
            try:
                self.logger.info(f"Starting {operation_desc}")
                delay_before_s = params.get('delay_before_next_s', 0)
                if i > 1 and delay_before_s > 0:
                    self.logger.info(f"Waiting {delay_before_s}s before attempt {i}...")
                    time.sleep(delay_before_s)
                
                current_nav_timeout = params.get('timeout', self.config.navigation_timeout_ms)
                # navigate_to_url is from NavigationMixin, but we are doing custom goto here
                response = self.page.goto(
                    self.config.base_url, 
                    wait_until=params['wait_until'], 
                    timeout=current_nav_timeout
                )
                
                if response and not response.ok:
                    self.logger.warning(f"Navigation attempt {i} resulted in status {response.status}. URL: {response.url}")
                    if i == len(self.config.navigation_retry_attempts):
                        self._handle_and_raise_scraper_error(ScraperError(f"Navigation failed with status {response.status} after all attempts."), operation_desc)
                    continue # Try next attempt configuration
                
                self.logger.info(f"Successfully navigated on attempt {i}. Page URL: {self.page.url}")
                
                # Ensure page is stable after goto before further actions
                self.wait_for_load_state('load', timeout_ms=current_nav_timeout) 
                
                self.logger.info(f"Clicking 'Apply' button: {self.config.apply_button_selector}")
                self.click_element(self.config.apply_button_selector, timeout_ms=self.config.interaction_timeout_ms) 
                
                self.logger.info(f"Waiting {self.config.wait_after_apply_ms}ms after 'Apply' click.")
                self.wait_for_timeout(self.config.wait_after_apply_ms)
                return # Successful setup
                
            except PlaywrightTimeoutError as e:
                self.logger.warning(f"Attempt {i} timed out: {str(e)}")
                if i == len(self.config.navigation_retry_attempts):
                    self._handle_and_raise_scraper_error(e, f"DOT custom navigation (all attempts timed out for {self.config.base_url})")
                
                retry_delay_s = params.get('retry_delay_on_timeout_s', 0)
                if retry_delay_s > 0:
                     self.logger.info(f"Waiting {retry_delay_s}s before timeout retry...")
                     time.sleep(retry_delay_s)
                continue
            except Exception as e: # Catch other errors like protocol errors
                error_str = str(e).upper()
                # Simplified error checking from original scraper
                if "ERR_HTTP2_PROTOCOL_ERROR" in error_str or "ERR_TIMED_OUT" in error_str or "NS_ERROR_NETTIMEOUT" in error_str:
                    self.logger.warning(f"Network/Protocol error on attempt {i}: {error_str}")
                    if i == len(self.config.navigation_retry_attempts):
                        self._handle_and_raise_scraper_error(e, f"DOT custom navigation ({error_str} after all attempts for {self.config.base_url})")
                    
                    # Use a progressive delay based on attempt number for these errors
                    delay = params.get('delay_before_next_s', 5) * i 
                    self.logger.info(f"Waiting {delay}s before retrying due to {error_str}...")
                    time.sleep(delay)
                    continue
                else: # Other unexpected errors
                    self._handle_and_raise_scraper_error(e, f"DOT custom navigation (unexpected error: {self.config.base_url})")
        
        # Should not be reached if all attempts fail, as errors are raised.
        self.logger.error("All navigation attempts failed for DOT scraper setup.")
        raise ScraperError("Exhausted all navigation retry attempts for DOT scraper.")


    def _extract_method(self) -> Optional[str]:
        """Downloads the CSV file after navigating to a new page."""
        self.logger.info(f"Starting DOT CSV download. Waiting for link: {self.config.download_csv_link_selector}")
        
        self.wait_for_selector(
            self.config.download_csv_link_selector, 
            timeout_ms=self.config.interaction_timeout_ms, 
            state='visible'
        )
        self.logger.info("Download CSV link is visible.")

        self._last_download_path = None # Reset before download attempt
        downloaded_file_path: Optional[str] = None
        new_page = None # Ensure new_page is defined for finally block

        operation_desc = f"DOT CSV download via new page from selector '{self.config.download_csv_link_selector}'"
        try:
            # This is similar to DownloadMixin.download_with_new_tab but more specific to DOT's flow
            with self.context.expect_page(timeout=self.config.new_page_download_expect_timeout_ms) as new_page_info:
                self.click_element(self.config.download_csv_link_selector, timeout_ms=self.config.interaction_timeout_ms)
            
            new_page = new_page_info.value
            self.logger.info(f"New page opened for download, URL (may be temporary): {new_page.url}")

            # Register the download handler from DownloadMixin for the new page
            new_page.on("download", self._handle_download_event)
            
            with new_page.expect_download(timeout=self.config.new_page_download_initiation_wait_ms) as download_info_new_page:
                self.logger.info("Waiting for download to initiate on new page...")
                # Original scraper had no specific action here, just waited. Add a small explicit wait.
                new_page.wait_for_timeout(self.config.new_page_initial_load_wait_ms) 
            
            download_event_data = download_info_new_page.value
            # _handle_download_event should have been triggered and set self._last_download_path
            
            self.wait_for_timeout(self.config.default_wait_after_download_ms) # Allow event processing

            if self._last_download_path and os.path.exists(self._last_download_path):
                downloaded_file_path = self._last_download_path
                self.logger.info(f"Download successfully handled by event. File at: {downloaded_file_path}")
            else:
                # Fallback: Manually save if _handle_download_event didn't set the path or failed silently
                self.logger.warning("_last_download_path not set by event or file missing. Attempting manual save from Playwright temp path.")
                temp_playwright_path = download_event_data.path()
                if not temp_playwright_path or not os.path.exists(temp_playwright_path):
                     self._handle_and_raise_scraper_error(ScraperError("Playwright temporary download path is invalid."), operation_desc + " - fallback save")

                suggested_filename = download_event_data.suggested_filename or f"{self.source_name_short}_download.csv"
                _, ext = os.path.splitext(suggested_filename)
                ext = ext if ext else '.csv' # Ensure extension
                
                final_filename = f"{self.source_name_short}_{time.strftime('%Y%m%d_%H%M%S')}{ext}"
                final_save_path = os.path.join(self.download_path, final_filename)
                ensure_directory(self.download_path)
                
                shutil.copy2(temp_playwright_path, final_save_path)
                self.logger.info(f"Manually copied download from '{temp_playwright_path}' to '{final_save_path}'.")
                self._last_download_path = final_save_path
                downloaded_file_path = final_save_path
            
            if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                 self._handle_and_raise_scraper_error(ScraperError("Download path not resolved or file does not exist after all attempts."), operation_desc)

            return downloaded_file_path

        except Exception as e: # Catch any error, including PlaywrightTimeoutError from expect_page/expect_download
            self.logger.error(f"Error during {operation_desc}: {e}", exc_info=True)
            if self.config.screenshot_on_error and self.page: self._save_error_screenshot("dot_extract_error_main_page")
            if self.config.save_html_on_error and self.page: self._save_error_html("dot_extract_error_main_page")
            if new_page and not new_page.is_closed() and self.config.screenshot_on_error : 
                try: # Try to get debug info from new_page if it exists
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    np_ss_path = os.path.join(active_config.ERROR_SCREENSHOTS_DIR, f"dot_extract_error_newpage_{timestamp}.png")
                    new_page.screenshot(path=np_ss_path)
                    self.logger.info(f"Saved screenshot of new_page to {np_ss_path}")
                except Exception as np_err: self.logger.error(f"Failed to get screenshot from new_page: {np_err}")
            self._handle_and_raise_scraper_error(e, operation_desc)
        finally:
            if new_page and not new_page.is_closed():
                new_page.close()
                self.logger.info("Closed the new page used for download.")
        return None # Should be unreachable

    def _custom_dot_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies DOT-specific transformations."""
        self.logger.info("Applying custom DOT transformations...")

        # Complex Award Date Parsing (handle multiple formats, then flexible fallback)
        # Column 'award_date_raw_custom' is from raw_column_rename_map
        award_date_col = "award_date_raw_custom"
        df['award_date_final'] = None
        df['award_fiscal_year_final'] = pd.NA

        if award_date_col in df.columns:
            date_formats_to_try = ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y'] # From original scraper
            for fmt in date_formats_to_try:
                try:
                    parsed_dates = pd.to_datetime(df[award_date_col], format=fmt, errors='coerce')
                    # Fill only where current 'award_date_final' is still NaT but parsed_dates is not
                    fill_mask = df['award_date_final'].isna() & parsed_dates.notna()
                    if fill_mask.any():
                        df.loc[fill_mask, 'award_date_final'] = parsed_dates[fill_mask]
                except Exception: # Catch errors during a specific format attempt
                    continue 
            
            # Fallback for any remaining NaNs using infer_datetime_format
            fallback_mask = df['award_date_final'].isna() & df[award_date_col].notna()
            if fallback_mask.any():
                df.loc[fallback_mask, 'award_date_final'] = pd.to_datetime(
                    df.loc[fallback_mask, award_date_col], 
                    errors='coerce', 
                    infer_datetime_format=True 
                )
            
            # Extract date and fiscal year
            valid_dates_mask = df['award_date_final'].notna()
            if valid_dates_mask.any():
                df.loc[valid_dates_mask, 'award_fiscal_year_final'] = pd.to_datetime(df.loc[valid_dates_mask, 'award_date_final']).dt.year
                df.loc[valid_dates_mask, 'award_date_final'] = pd.to_datetime(df.loc[valid_dates_mask, 'award_date_final']).dt.date
            
            df['award_fiscal_year_final'] = df['award_fiscal_year_final'].astype('Int64')
            self.logger.debug("Processed 'award_date_final' and 'award_fiscal_year_final' with custom logic.")
        else:
            self.logger.warning(f"'{award_date_col}' not found for custom award date parsing.")

        # Contract Type Fallback
        # Expects 'contract_type_raw' (from raw_rename if 'Contract Type' exists) and 'action_award_type_extra'
        if 'contract_type_raw' in df.columns and df['contract_type_raw'].notna().any():
            df['contract_type_final'] = df['contract_type_raw']
            self.logger.debug("Used 'contract_type_raw' for 'contract_type_final'.")
        elif 'action_award_type_extra' in df.columns:
            df['contract_type_final'] = df['action_award_type_extra']
            self.logger.info("Used 'action_award_type_extra' as fallback for 'contract_type_final'.")
        else:
            df['contract_type_final'] = None
            self.logger.warning("No source for 'contract_type_final'.")
            
        return df

    def _process_method(self, file_path: Optional[str], data_source=None) -> Optional[int]:
        """Processes the downloaded CSV file."""
        self.logger.info(f"Starting DOT processing for file: {file_path}")
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path '{file_path}' is invalid. Cannot process.")
            return 0
        try:
            df = self.read_file_to_dataframe(
                file_path, 
                file_type_hint=self.config.file_type_hint,
                read_options=self.config.read_options # e.g., {"on_bad_lines": "skip", "header": 0}
            )
            if df.empty: self.logger.info("DataFrame empty after reading."); return 0
            
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty: self.logger.info("DataFrame empty after transforms."); return 0
            
            loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules, data_source=data_source)
            self.logger.info(f"DOT processing completed. Loaded {loaded_count} prospects.")
            return loaded_count
        except ScraperError as e: self.logger.error(f"ScraperError: {e}", exc_info=True); raise
        except Exception as e: self._handle_and_raise_scraper_error(e, f"processing DOT file {file_path}")
        return 0

    def scrape(self):
        """Orchestrates the scraping process for DOT."""
        self.logger.info(f"Starting scrape for {self.config.source_name} using DotScraper logic.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )
