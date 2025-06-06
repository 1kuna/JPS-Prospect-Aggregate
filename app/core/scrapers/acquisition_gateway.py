"""Acquisition Gateway scraper."""

# Standard library imports
import os
# import traceback # No longer directly used, BaseScraper handles exc_info logging
from typing import Optional 

# Third-party imports
import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Local application imports
from app.core.specialized_scrapers import PageInteractionScraper 
# from app.models import Prospect # Data model, not directly used by scraper logic itself (mixin handles it)
from app.config import active_config 
from app.exceptions import ScraperError
from app.utils.logger import logger # Base logger, instance logger is self.logger

# Import the specific config for this scraper
from app.core.scrapers.configs.acquisition_gateway_config import AcquisitionGatewayConfig


# Logger for this specific scraper module (can be used for module-level logging if needed)
module_logger = logger.bind(name="module.acquisition_gateway")


class AcquisitionGatewayScraper(PageInteractionScraper):
    """Scraper for the Acquisition Gateway site, refactored to use mixins and configs."""
    
    def __init__(self, config: AcquisitionGatewayConfig, debug_mode: bool = False):
        """
        Initialize the Acquisition Gateway scraper.
        Args:
            config (AcquisitionGatewayConfig): Configuration object for this scraper.
            debug_mode (bool): Runtime override for debug mode.
        """
        if config.base_url is None: # Ensure base_url is set, it's vital.
            config.base_url = active_config.ACQUISITION_GATEWAY_URL 
            module_logger.warning(f"AcquisitionGatewayConfig.base_url was None, set from active_config: {config.base_url}")
            
        super().__init__(config=config, debug_mode=debug_mode)
        # self.logger is initialized by PageInteractionScraper's super() call to BaseScraper.

    def custom_summary_fallback(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Custom transformation: If 'Body' column is missing but 'Summary' exists,
        rename 'Summary' to 'Body'. This runs BEFORE raw_column_rename_map in transform_dataframe.
        """
        self.logger.info("Applying custom_summary_fallback logic...")
        if 'Body' not in df.columns and 'Summary' in df.columns:
            self.logger.info("Found 'Summary' column but no 'Body' column. Renaming 'Summary' to 'Body'.")
            df.rename(columns={'Summary': 'Body'}, inplace=True)
        elif 'Body' in df.columns and 'Summary' in df.columns:
            self.logger.info("'Body' and 'Summary' columns both exist. 'Body' will be preferred by raw_column_rename_map if 'Body' is mapped.")
        elif 'Body' not in df.columns and 'Summary' not in df.columns:
            self.logger.warning("'Body' and 'Summary' columns are both missing. Description might be empty.")
        else: # 'Body' exists, 'Summary' might or might not. 'Body' takes precedence.
            self.logger.info("'Body' column exists. No fallback needed from 'Summary'.")
        return df

    def _setup_method(self) -> None:
        """Navigates to the base URL of the scraper and waits for initial load."""
        self.logger.info(f"Executing setup: Navigating to base URL: {self.config.base_url}")
        if not self.config.base_url: # Should have been set in __init__
            self.logger.error("Base URL is not configured for AcquisitionGatewayScraper.")
            raise ScraperError("Base URL is not configured for AcquisitionGatewayScraper.")
        
        self.navigate_to_url(self.config.base_url) 
        # An initial load wait; specific page interactions might need more granular waits.
        self.wait_for_load_state('load', timeout_ms=self.config.navigation_timeout_ms)


    def _check_page_alive(self) -> bool:
        """Check if the page is still alive and responsive."""
        try:
            # Try to evaluate a simple JavaScript expression
            result = self.page.evaluate("() => true")
            return result == True
        except Exception as e:
            self.logger.warning(f"Page evaluation failed during health check: {e}")
            return False

    def _extract_method(self) -> Optional[str]:
        """
        Downloads the CSV file from the Acquisition Gateway site.
        Returns: Path to the downloaded file, or None if download failed.
        """
        self.logger.info("Starting CSV file download process from Acquisition Gateway.")
        
        # Wait for export button to be visible and clickable
        self.logger.info(f"Waiting for export button '{self.config.export_button_selector}' to be visible...")
        self.wait_for_selector(
            selector=self.config.export_button_selector,
            timeout_ms=30000,  # 30 seconds to wait for button to appear
            visible=True,
            state='visible'
        )
        self.logger.info("Export button is visible.")
        
        # Add natural pause before clicking
        self.logger.info("Waiting 5 seconds before clicking to appear natural...")
        self.wait_for_timeout(5000)
        
        try:
            self._last_download_path = None  # Reset before download attempt
            
            # Try to click and download with extended timeout
            download_timeout = self.config.download_timeout_ms  # Use configured timeout (150 seconds)
            
            with self.page.expect_download(timeout=download_timeout) as download_info:
                self.logger.info("Clicking export button...")
                
                # Get button state before clicking
                button_disabled = self.page.locator(self.config.export_button_selector).is_disabled()
                self.logger.info(f"Button disabled state before click: {button_disabled}")
                
                self.click_element(
                    selector=self.config.export_button_selector,
                    js_click_fallback=True,  # Allow JS click if standard fails
                    timeout_ms=self.config.interaction_timeout_ms
                )
                self.logger.info("Click executed, waiting for download...")
            
            # Wait for the download event to be processed and file to be saved
            self.wait_for_timeout(self.config.default_wait_after_download_ms)
            
            if self._last_download_path and os.path.exists(self._last_download_path):
                self.logger.info(f"Download successful. File at: {self._last_download_path}")
                return self._last_download_path
            else:
                # Download didn't complete properly
                download_obj = download_info.value
                temp_playwright_path = "N/A"
                try:
                    if download_obj: temp_playwright_path = download_obj.path()
                except Exception: pass
                
                error_msg = f"Download failed: _last_download_path ('{self._last_download_path}') is invalid. Playwright temp: '{temp_playwright_path}'"
                self.logger.error(error_msg)
                raise ScraperError("Download did not result in a valid saved file path")
                
        except PlaywrightTimeoutError as e:
            # This is expected if the button loading times out after ~60 seconds
            self.logger.warning(f"Download timeout (expected if site is having issues): {str(e)}")
            if self.config.screenshot_on_error:
                self._save_error_screenshot("acq_gw_timeout")
            
            # Check button state after timeout
            try:
                button_disabled = self.page.locator(self.config.export_button_selector).is_disabled()
                self.logger.info(f"Button disabled state after timeout: {button_disabled}")
            except:
                self.logger.warning("Could not check button state after timeout")
            
            raise ScraperError(f"Acquisition Gateway download timed out: {str(e)}") from e
                    
        except Exception as e:
            self.logger.error(f"Unexpected error during CSV download: {e}", exc_info=True)
            if self.config.screenshot_on_error:
                self._save_error_screenshot("acq_gw_error")
            if self.config.save_html_on_error:
                self._save_error_html("acq_gw_error")
            
            raise ScraperError(f"Acquisition Gateway CSV download failed: {type(e).__name__}") from e
        

    def _process_method(self, file_path: str, data_source=None) -> Optional[int]:
        """
        Processes the downloaded CSV file.
        Args: 
            file_path (str): Path to the downloaded file.
            data_source: DataSource object for setting source_id
        Returns: Optional[int]: Number of prospects loaded, or 0/None on failure.
        """
        self.logger.info(f"Processing Acq Gateway file: {file_path}")
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path '{file_path}' is invalid. Cannot process.")
            return 0

        try:
            df = self.read_file_to_dataframe(file_path, file_type_hint=self.config.file_type_hint)
            if df.empty:
                self.logger.info("DataFrame is empty. Nothing to process.")
                return 0

            # config_params for transform_dataframe and prepare_and_load_data is self.config.data_processing_rules
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty:
                self.logger.info("DataFrame is empty after transformations. Nothing to load.")
                return 0
            
            loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules, data_source=data_source)
            
            self.logger.info(f"Acq Gateway processing complete. Loaded {loaded_count} prospects.")
            return loaded_count

        except ScraperError as e:
            self.logger.error(f"A ScraperError occurred during processing of {file_path}: {e}", exc_info=True)
            raise # Re-raise to be caught by the main error handler
        except Exception as e:
            self.logger.error(f"Unexpected error processing file {file_path}: {e}", exc_info=True)
            raise ScraperError(f"Error processing Acq Gateway file {file_path}: {type(e).__name__}") from e

    def scrape(self):
        """Orchestrates the scraping process for Acquisition Gateway."""
        self.logger.info(f"Starting scrape for {self.config.source_name} using structured approach.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )
