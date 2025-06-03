"""Department of Justice Opportunity Forecast scraper."""

import os
# import traceback # No longer directly used
from typing import Optional

import pandas as pd
# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError # Handled by mixins

from app.core.specialized_scrapers import PageInteractionScraper
from app.config import active_config
from app.exceptions import ScraperError
from app.core.scrapers.configs.doj_config import DOJConfig
from app.utils.parsing import fiscal_quarter_to_date # For custom award date logic

class DOJForecastScraper(PageInteractionScraper):
    """Scraper for the DOJ Opportunity Forecast site."""

    def __init__(self, config: DOJConfig, debug_mode: bool = False):
        if config.base_url is None:
            config.base_url = active_config.DOJ_FORECAST_URL
            self.logger.warning(f"DOJConfig.base_url was None, set from active_config: {config.base_url}")
        super().__init__(config=config, debug_mode=debug_mode)

    def _setup_method(self) -> None:
        """Navigates to the base URL of the scraper."""
        self.logger.info(f"Executing DOJ setup: Navigating to base URL: {self.config.base_url}")
        if not self.config.base_url:
            self._handle_and_raise_scraper_error(ValueError("Base URL not configured."), "DOJ setup navigation")
        self.navigate_to_url(self.config.base_url)
        self.wait_for_load_state('domcontentloaded') # Ensure basic page structure is ready

    def _extract_method(self) -> Optional[str]:
        """Downloads the forecast Excel document."""
        self.logger.info(f"Starting DOJ Excel document download. Waiting for link: {self.config.download_link_selector}")
        
        self.wait_for_selector(
            self.config.download_link_selector, 
            timeout_ms=self.config.download_link_wait_timeout_ms,
            state='visible' # Ensure link is visible before trying to click
        )
        self.logger.info("Download link is visible.")
        
        try:
            # download_file_via_click from DownloadMixin
            downloaded_file_path = self.download_file_via_click(
                click_selector=self.config.download_link_selector
            )
            return downloaded_file_path
        except ScraperError as e:
            self.logger.error(f"ScraperError during DOJ download: {e}", exc_info=True)
            # Error saving (screenshot/HTML) should have been handled by download_file_via_click
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during DOJ download: {e}", exc_info=True)
            if self.config.screenshot_on_error and self.page: self._save_error_screenshot("doj_extract_error")
            if self.config.save_html_on_error and self.page: self._save_error_html("doj_extract_error")
            self._handle_and_raise_scraper_error(e, "DOJ file extraction")
        return None


    def _custom_doj_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies DOJ-specific transformations. Called by DataProcessingMixin.transform_dataframe
        *after* raw_column_rename_map and *after* declarative parsing defined in date_column_configs etc.
        It expects columns like 'award_date_raw' (from raw_rename).
        It creates 'award_date_final', 'award_fiscal_year_final', 'place_country_final'.
        """
        self.logger.info("Applying custom DOJ transformations...")

        # Award Date Logic (Complex)
        # Column 'award_date_raw' is from raw_column_rename_map
        award_date_col_raw = "award_date_raw" # This is the key from raw_column_rename_map

        if award_date_col_raw in df.columns:
            df['award_date_final'] = pd.to_datetime(df[award_date_col_raw], errors='coerce')
            # Attempt to get year directly, will be float if NaT present, so handle with Int64 later
            df['award_fiscal_year_final'] = df['award_date_final'].dt.year 
            
            needs_fallback_mask = df['award_date_final'].isna() & df[award_date_col_raw].notna()
            if needs_fallback_mask.any():
                self.logger.info(f"Found {needs_fallback_mask.sum()} award dates needing fiscal quarter fallback parsing.")
                parsed_qtr_info = df.loc[needs_fallback_mask, award_date_col_raw].apply(
                    lambda x: fiscal_quarter_to_date(x) if pd.notna(x) else (None, None)
                )
                df.loc[needs_fallback_mask, 'award_date_final'] = parsed_qtr_info.apply(lambda x: x[0])
                df.loc[needs_fallback_mask, 'award_fiscal_year_final'] = parsed_qtr_info.apply(lambda x: x[1])
            
            # Final conversion to date object and Int64 for year
            df['award_date_final'] = pd.to_datetime(df['award_date_final'], errors='coerce').dt.date
            df['award_fiscal_year_final'] = df['award_fiscal_year_final'].astype('Int64') # Handles NaN -> <NA>
            self.logger.debug("Processed 'award_date_final' and 'award_fiscal_year_final' with fallback logic.")
        else:
            df['award_date_final'] = None
            df['award_fiscal_year_final'] = pd.NA
            self.logger.warning(f"'{award_date_col_raw}' not found. Award date fields initialized to None/NA.")

        # Place Country Logic
        # Column 'place_country_raw' is from raw_column_rename_map (original: 'Country')
        place_country_col_raw = "place_country_raw" 
        if place_country_col_raw in df.columns:
            df['place_country_final'] = df[place_country_col_raw].fillna('USA')
            self.logger.debug("Processed 'place_country_final', defaulting NA to USA.")
        else:
            # If 'place_raw' was parsed by declarative 'place_column_configs', a country col might exist.
            # The config maps 'place_raw' to 'place_city_intermediate', 'place_state_intermediate'.
            # It does not create a country column from 'place_raw' declaratively.
            # So, if 'place_country_raw' (from direct 'Country' column) is missing, default to USA.
            df['place_country_final'] = 'USA'
            self.logger.debug(f"'{place_country_col_raw}' not found. Defaulted 'place_country_final' to USA.")
            
        return df

    def _process_method(self, file_path: Optional[str]) -> Optional[int]:
        """Processes the downloaded Excel file."""
        self.logger.info(f"Starting DOJ processing for file: {file_path}")
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path '{file_path}' is invalid. Cannot process.")
            return 0

        try:
            df = self.read_file_to_dataframe(
                file_path, 
                file_type_hint=self.config.file_type_hint,
                read_options=self.config.read_options
            )
            # Initial dropna(how='all') is handled by transform_dataframe via config
            if df.empty:
                self.logger.info("DataFrame is empty after reading. Nothing to process for DOJ.")
                return 0
            
            # transform_dataframe applies raw_rename, then custom_transforms, then declarative parsing
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty:
                self.logger.info("DataFrame is empty after transformations. Nothing to load for DOJ.")
                return 0
            
            loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules)
            
            self.logger.info(f"DOJ processing completed. Loaded {loaded_count} prospects.")
            return loaded_count

        except ScraperError as e:
            self.logger.error(f"ScraperError during DOJ processing of {file_path}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing DOJ file {file_path}: {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, f"processing DOJ file {file_path}")
        return 0


    def scrape(self):
        """Orchestrates the scraping process for DOJ."""
        self.logger.info(f"Starting scrape for {self.config.source_name} using DOJForecastScraper logic.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )
