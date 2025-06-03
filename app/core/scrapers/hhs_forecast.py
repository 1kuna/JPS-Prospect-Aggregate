"""Department of Health and Human Services Opportunity Forecast scraper."""

import os
# import traceback # No longer directly used
from typing import Optional

import pandas as pd
# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError # Handled by mixins

from app.core.specialized_scrapers import PageInteractionScraper
from app.config import active_config
from app.exceptions import ScraperError
from app.core.scrapers.configs.hhs_config import HHSConfig

class HHSForecastScraper(PageInteractionScraper):
    """Scraper for the HHS Opportunity Forecast site."""

    def __init__(self, config: HHSConfig, debug_mode: bool = False):
        if config.base_url is None:
            config.base_url = active_config.HHS_FORECAST_URL
            # self.logger not available yet
            print(f"Warning: HHSConfig.base_url was None, set from active_config: {config.base_url}")
        super().__init__(config=config, debug_mode=debug_mode)

    def _setup_method(self) -> None:
        """Navigates to the base URL and clicks the 'View All' button."""
        self.logger.info(f"Executing HHS setup: Navigating to base URL: {self.config.base_url}")
        if not self.config.base_url:
            self._handle_and_raise_scraper_error(ValueError("Base URL not configured."), "HHS setup navigation")
        
        self.navigate_to_url(self.config.base_url)
        # Wait for page to be generally ready before clicking "View All"
        self.wait_for_load_state('domcontentloaded', timeout_ms=self.config.navigation_timeout_ms)

        self.logger.info(f"Clicking 'View All' button: {self.config.view_all_button_selector}")
        self.click_element(self.config.view_all_button_selector, timeout_ms=self.config.interaction_timeout_ms)
        
        self.logger.info(f"Waiting {self.config.pre_export_click_wait_ms}ms for page to update after 'View All' click.")
        self.wait_for_timeout(self.config.pre_export_click_wait_ms)
        # Potentially add a wait_for_selector for the export button to be ready if needed,
        # but download_file_via_click also has a wait for the selector.

    def _extract_method(self) -> Optional[str]:
        """Downloads the forecast CSV by clicking the export button."""
        self.logger.info(f"Attempting to download by clicking export button: {self.config.export_button_selector}")
        try:
            # download_file_via_click from DownloadMixin will handle expect_download and calling _handle_download_event
            # It also uses click_element from NavigationMixin which can handle JS fallback if needed,
            # though HHSConfig doesn't specify js_click_fallback=True for this button.
            downloaded_file_path = self.download_file_via_click(
                click_selector=self.config.export_button_selector,
                # No pre_click_selector here as it's handled in _setup_method
                # expect_download_timeout can be set in config if default is not enough
            )
            return downloaded_file_path
        except ScraperError as e:
            self.logger.error(f"ScraperError during HHS download: {e}", exc_info=True)
            # Error saving (screenshot/HTML) should have been handled by download_file_via_click's internal call to click_element
            raise # Re-raise to be caught by scrape_with_structure
        except Exception as e:
            self.logger.error(f"Unexpected error during HHS download: {e}", exc_info=True)
            if self.config.screenshot_on_error and self.page: self._save_error_screenshot("hhs_extract_error")
            if self.config.save_html_on_error and self.page: self._save_error_html("hhs_extract_error")
            self._handle_and_raise_scraper_error(e, "HHS file extraction")
        return None


    def _custom_hhs_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies HHS-specific transformations. Called by DataProcessingMixin.transform_dataframe
        *after* raw_column_rename_map.
        """
        self.logger.info("Applying custom HHS transformations...")

        # Add row_index for unique ID generation (HHS data noted to have duplicates)
        df.reset_index(drop=True, inplace=True) # Ensure clean index
        df['row_index'] = df.index
        self.logger.debug("Added 'row_index'.")

        # Standardize 'place_country'
        # raw_column_rename_map maps source 'Place of Performance Country' to 'place_country_raw'.
        # This transform creates 'place_country_final' which db_column_rename_map maps to 'place_country'.
        if 'place_country_raw' in df.columns:
            df['place_country_final'] = df['place_country_raw'].fillna('USA')
            self.logger.debug("Processed 'place_country_raw' into 'place_country_final', defaulting NA to USA.")
        else:
            df['place_country_final'] = 'USA'
            self.logger.debug("Column 'place_country_raw' not found. Initialized 'place_country_final' to 'USA'.")
            
        return df

    def _process_method(self, file_path: Optional[str]) -> Optional[int]:
        """Processes the downloaded CSV file."""
        self.logger.info(f"Starting HHS processing for file: {file_path}")
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path '{file_path}' is invalid. Cannot process.")
            return 0

        try:
            df = self.read_file_to_dataframe(
                file_path, 
                file_type_hint=self.config.file_type_hint,
                read_options=self.config.read_options # e.g., {'on_bad_lines': 'skip'}
            )
            
            # Initial dropna(how='all') is now part of DataProcessingMixin.transform_dataframe,
            # controlled by config_params.dropna_how_all (defaulting to True).
            # So, no need to call it explicitly here if that default is used.
            # df.dropna(how='all', inplace=True) # This was in old scraper, now handled by mixin.

            if df.empty: # Check after read, before transform call.
                self.logger.info("DataFrame is empty after reading. Nothing to process for HHS.")
                return 0
            
            # transform_dataframe applies raw_rename, then custom_transforms, then declarative parsing
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty:
                self.logger.info("DataFrame is empty after transformations. Nothing to load for HHS.")
                return 0
            
            loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules)
            
            self.logger.info(f"HHS processing completed. Loaded {loaded_count} prospects.")
            return loaded_count

        except ScraperError as e:
            self.logger.error(f"ScraperError during HHS processing of {file_path}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing HHS file {file_path}: {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, f"processing HHS file {file_path}")
        return 0


    def scrape(self):
        """Orchestrates the scraping process for HHS."""
        self.logger.info(f"Starting scrape for {self.config.source_name} using HHSForecastScraper logic.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )
