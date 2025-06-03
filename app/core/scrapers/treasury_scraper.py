"""Department of Treasury Forecast scraper."""

import os
# import traceback # No longer directly used
from typing import Optional

import pandas as pd
# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError # Handled by mixins

from app.core.specialized_scrapers import PageInteractionScraper
from app.config import active_config 
from app.exceptions import ScraperError
from app.core.scrapers.configs.treasury_config import TreasuryConfig


class TreasuryScraper(PageInteractionScraper):
    """Scraper for the Department of Treasury Forecast site."""
    
    def __init__(self, config: TreasuryConfig, debug_mode: bool = False):
        if config.base_url is None:
            config.base_url = active_config.TREASURY_FORECAST_URL
            print(f"Warning: TreasuryConfig.base_url was None, set from active_config: {config.base_url}")
        super().__init__(config=config, debug_mode=debug_mode)

    def _setup_method(self) -> None:
        """Navigates to the base URL and waits for page load."""
        self.logger.info(f"Executing Treasury setup: Navigating to base URL: {self.config.base_url}")
        if not self.config.base_url:
            self._handle_and_raise_scraper_error(ValueError("Base URL not configured."), "Treasury setup navigation")
        
        self.navigate_to_url(self.config.base_url)
        # Default wait_until in navigate_to_url is 'domcontentloaded'. 
        # Treasury scraper originally waited for 'load'.
        self.wait_for_load_state('load', timeout_ms=self.config.navigation_timeout_ms)
        self.logger.info("Page 'load' state reached.")

    def _extract_method(self) -> Optional[str]:
        """Downloads the Opportunity Data file from the Treasury Forecast site."""
        self.logger.info("Starting Treasury data file download process.")
        
        # Wait for the download button to be visible first
        self.wait_for_selector(
            self.config.download_button_xpath_selector, 
            timeout_ms=self.config.interaction_timeout_ms,
            state='visible' # Ensure it's visible, not just attached
        )
        self.logger.info(f"Download button '{self.config.download_button_xpath_selector}' is visible.")

        # download_file_via_click uses click_element internally, which handles js_click_fallback
        # However, the js_click_fallback is a parameter to click_element, not download_file_via_click.
        # For Treasury, a JS click fallback was specifically needed.
        # So, we'll replicate the logic of download_file_via_click but ensure click_element gets the fallback flag.
        
        self._last_download_path = None # Reset before download
        operation_desc = f"clicking download button (XPath: {self.config.download_button_xpath_selector})"
        self.logger.info(f"Attempting {operation_desc} and expecting download.")

        try:
            with self.page.expect_download(timeout=self.config.download_timeout_ms) as download_info:
                self.click_element(
                    selector=self.config.download_button_xpath_selector,
                    js_click_fallback=self.config.js_click_fallback_for_download, # Pass the flag
                    timeout_ms=self.config.interaction_timeout_ms 
                )
            
            download = download_info.value
            # Manually call the handler from the mixin, as BaseScraper's _handle_download is a placeholder
            # and DownloadMixin._handle_download_event is the actual implementation.
            self._handle_download_event(download) 

            self.wait_for_timeout(self.config.default_wait_after_download_ms)

            if self._last_download_path and os.path.exists(self._last_download_path):
                self.logger.info(f"Download successful. File at: {self._last_download_path}")
                return self._last_download_path
            else:
                self.logger.error(f"Download attempt for Treasury finished, but _last_download_path ('{self._last_download_path}') is not valid.")
                raise ScraperError("Failed to download file or _last_download_path not set correctly after Treasury download.")
        
        except ScraperError as e: # Re-raise if already a ScraperError (e.g. from click_element)
            self.logger.error(f"A ScraperError occurred during Treasury download: {e}", exc_info=True)
            raise
        except Exception as e: # Catch other errors (e.g. from expect_download timeout)
            self.logger.error(f"Unexpected error during Treasury download: {e}", exc_info=True)
            if self.config.screenshot_on_error: self._save_error_screenshot("treasury_extract_error")
            if self.config.save_html_on_error: self._save_error_html("treasury_extract_error")
            self._handle_and_raise_scraper_error(e, operation_desc) # Standardized handler
        return None # Should be unreachable

    def _custom_treasury_pre_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies Treasury-specific transformations *before* the main DataProcessingMixin.transform_dataframe.
        Handles native_id selection and row_index addition.
        """
        self.logger.info("Applying Treasury pre-transformations...")
        
        # Handle alternative native_id fields
        # raw_column_rename_map has already mapped these to intermediate names.
        # Config has: 'Specific Id': 'native_id_intermediate', 'ShopCart/req': 'shopcart_req_intermediate', 'Contract Number': 'contract_num_intermediate'
        if 'native_id_intermediate' in df.columns:
            df['native_id_final'] = df['native_id_intermediate']
        elif 'shopcart_req_intermediate' in df.columns:
            df['native_id_final'] = df['shopcart_req_intermediate']
            self.logger.info("Used 'shopcart_req_intermediate' as native_id_final.")
        elif 'contract_num_intermediate' in df.columns:
            df['native_id_final'] = df['contract_num_intermediate']
            self.logger.info("Used 'contract_num_intermediate' as native_id_final.")
        else:
            df['native_id_final'] = None # Ensure column exists
            self.logger.warning("No primary or fallback native ID column found. 'native_id_final' set to None.")

        # Add row_index for unique ID generation, as Treasury data may have duplicates
        df.reset_index(drop=True, inplace=True) # Ensure index is clean if multiple files were concatenated (not here, but good practice)
        df['row_index'] = df.index 
        self.logger.debug("Added 'row_index' to DataFrame.")
        
        return df

    def _custom_treasury_transforms_in_mixin_flow(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies Treasury-specific transformations that fit within the DataProcessingMixin.transform_dataframe flow
        (i.e., after raw_column_rename_map, before specific parsers if needed).
        Mainly for initializing description.
        """
        self.logger.info("Applying Treasury transforms within mixin flow (description init)...")
        # Initialize Prospect.description as None (Treasury source lacks detailed description)
        # This will be picked up by db_column_rename_map
        df['description_final'] = None 
        self.logger.debug("Initialized 'description_final' to None.")
        return df

    def _process_method(self, file_path: Optional[str]) -> Optional[int]:
        """Processes the downloaded Treasury file."""
        self.logger.info(f"Starting Treasury processing for file: {file_path}")
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path '{file_path}' is invalid. Cannot process.")
            return 0

        try:
            df = None
            if self.config.file_read_strategy == "html_then_excel":
                self.logger.info(f"Using 'html_then_excel' strategy for {file_path}.")
                try:
                    # header=0 is now in self.config.read_options for the excel fallback
                    df_list = pd.read_html(file_path, **(self.config.read_options or {})) # Pass read_options for html too
                    if not df_list:
                        self._handle_and_raise_scraper_error(ScraperError(f"No tables found in HTML file: {file_path}"), "reading HTML file")
                    df = df_list[0] 
                    self.logger.info(f"Successfully read HTML table from {file_path}. Shape: {df.shape}")
                except ValueError as ve: # pandas raises ValueError if HTML parsing fails
                    self.logger.warning(f"Could not read {file_path} as HTML table ({ve}), attempting pd.read_excel...")
                    try:
                        df = pd.read_excel(file_path, **(self.config.read_options or {}))
                        self.logger.info(f"Successfully read as Excel file {file_path}. Shape: {df.shape}")
                    except Exception as ex_err:
                        self._handle_and_raise_scraper_error(ex_err, f"parsing file {file_path} as HTML or Excel fallback")
            else: # Fallback to default mixin reading behavior
                df = self.read_file_to_dataframe(file_path, read_options=self.config.read_options)
            
            if df is None or df.empty: # Should be caught by error handlers if read failed
                self.logger.info("DataFrame is empty after reading attempts. Nothing to process.")
                return 0
            
            # Initial cleanup
            df.dropna(how='all', inplace=True)
            if df.empty:
                self.logger.info("DataFrame is empty after initial dropna. Nothing to process.")
                return 0

            # Apply pre-transformations (native_id selection, row_index)
            df = self._custom_treasury_pre_transforms(df)

            # Apply main transformations via DataProcessingMixin
            # This will call _custom_treasury_transforms_in_mixin_flow for description init
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty:
                self.logger.info("DataFrame is empty after transformations. Nothing to load.")
                return 0
            
            loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules)
            
            self.logger.info(f"Treasury processing completed. Loaded {loaded_count} prospects.")
            return loaded_count

        except ScraperError as e:
            self.logger.error(f"ScraperError during Treasury processing of {file_path}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing Treasury file {file_path}: {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, f"processing Treasury file {file_path}")
        return 0


    def scrape(self):
        """Orchestrates the scraping process for Treasury."""
        self.logger.info(f"Starting scrape for {self.config.source_name} using TreasuryScraper logic.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )

```
