"""Department of Homeland Security Opportunity Forecast scraper."""

import os
# import traceback # No longer directly used
from typing import Optional

import pandas as pd
# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError # Handled by mixins

from app.core.specialized_scrapers import PageInteractionScraper
from app.config import active_config
from app.exceptions import ScraperError
from app.core.scrapers.configs.dhs_config import DHSConfig
# fiscal_quarter_to_date and parse_value_range are used by DataProcessingMixin via config

class DHSForecastScraper(PageInteractionScraper):
    """Scraper for the DHS Opportunity Forecast site."""

    def __init__(self, config: DHSConfig, debug_mode: bool = False):
        if config.base_url is None:
            config.base_url = active_config.DHS_FORECAST_URL
            print(f"Warning: DHSConfig.base_url was None, set from active_config: {config.base_url}")
        super().__init__(config=config, debug_mode=debug_mode)

    def _setup_method(self) -> None:
        """Navigates to the base URL and applies an explicit wait."""
        self.logger.info(f"Executing DHS setup: Navigating to base URL: {self.config.base_url}")
        if not self.config.base_url:
            self._handle_and_raise_scraper_error(ValueError("Base URL not configured."), "DHS setup navigation")
        
        self.navigate_to_url(self.config.base_url)
        # Wait for page to be generally ready
        self.wait_for_load_state('domcontentloaded', timeout_ms=self.config.navigation_timeout_ms)

        self.logger.info(f"Waiting {self.config.explicit_wait_ms_before_download}ms before download attempt.")
        self.wait_for_timeout(self.config.explicit_wait_ms_before_download)

    def _extract_method(self) -> Optional[str]:
        """Downloads the forecast CSV by clicking the CSV button."""
        self.logger.info(f"Attempting to download by clicking CSV button: {self.config.csv_button_selector}")
        try:
            # download_file_via_click from DownloadMixin
            downloaded_file_path = self.download_file_via_click(
                click_selector=self.config.csv_button_selector
            )
            return downloaded_file_path
        except ScraperError as e:
            self.logger.error(f"ScraperError during DHS download: {e}", exc_info=True)
            # Error saving (screenshot/HTML) should have been handled by download_file_via_click
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during DHS download: {e}", exc_info=True)
            if self.config.screenshot_on_error and self.page: self._save_error_screenshot("dhs_extract_error")
            if self.config.save_html_on_error and self.page: self._save_error_html("dhs_extract_error")
            self._handle_and_raise_scraper_error(e, "DHS file extraction")
        return None


    def _custom_dhs_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies DHS-specific transformations. Called by DataProcessingMixin.transform_dataframe
        *after* raw_column_rename_map.
        """
        self.logger.info("Applying custom DHS transformations...")
        # Default place_country_final to 'USA'
        # Assumes raw_column_rename_map did *not* create a 'place_country_raw' if source doesn't have it.
        # If it did (e.g. from a non-existent col), it would be all NA.
        # This transform creates 'place_country_final' which db_column_rename_map maps to 'place_country'.
        if 'place_country_raw' in df.columns: # If source might sometimes provide country
            df['place_country_final'] = df['place_country_raw'].fillna('USA')
            self.logger.debug("Processed 'place_country_raw' into 'place_country_final', defaulting NA to USA.")
        else:
            df['place_country_final'] = 'USA' # If source never provides country
            self.logger.debug("Initialized 'place_country_final' to 'USA' as 'place_country_raw' not found.")
        return df

    def _process_method(self, file_path: Optional[str]) -> Optional[int]:
        """Processes the downloaded CSV/Excel file."""
        self.logger.info(f"Starting DHS processing for file: {file_path}")
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path '{file_path}' is invalid. Cannot process.")
            return 0

        df: Optional[pd.DataFrame] = None
        try:
            if self.config.file_read_strategy == "csv_then_excel":
                self.logger.info(f"Using 'csv_then_excel' strategy for {file_path}.")
                try:
                    df = pd.read_csv(file_path, **(self.config.csv_read_options or {}))
                    self.logger.info(f"Successfully read as CSV: {file_path}. Shape: {df.shape if df is not None else 'None'}")
                except Exception as csv_error:
                    self.logger.warning(f"Failed to read as CSV ({csv_error}), trying Excel: {file_path}")
                    try:
                        df = pd.read_excel(file_path, **(self.config.excel_read_options or {}))
                        self.logger.info(f"Successfully read as Excel: {file_path}. Shape: {df.shape if df is not None else 'None'}")
                    except Exception as excel_error:
                        # If both fail, use the standard error handler from BaseScraper
                        self._handle_and_raise_scraper_error(excel_error, f"parsing file as CSV then Excel: {file_path}")
            else: # Fallback to default mixin reading behavior
                df = self.read_file_to_dataframe(file_path) # No specific read_options from config for this path yet
            
            if df is None or df.empty: # Should be caught by error handlers if read failed and raised
                self.logger.info("DataFrame is empty after reading attempts. Nothing to process for DHS.")
                return 0
            
            # DataProcessingMixin.transform_dataframe handles initial dropna(how='all') via config_params.dropna_how_all
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty:
                self.logger.info("DataFrame is empty after transformations. Nothing to load for DHS.")
                return 0
            
            loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules)
            
            self.logger.info(f"DHS processing completed. Loaded {loaded_count} prospects.")
            return loaded_count

        except ScraperError as e:
            self.logger.error(f"ScraperError during DHS processing of {file_path}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing DHS file {file_path}: {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, f"processing DHS file {file_path}")
        return 0


    def scrape(self):
        """Orchestrates the scraping process for DHS."""
        self.logger.info(f"Starting scrape for {self.config.source_name} using DHSForecastScraper logic.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )

```
