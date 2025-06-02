"""Social Security Administration Opportunity Forecast scraper."""

import os
# import traceback # No longer directly used
from typing import Optional, List 

import pandas as pd
# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError # Handled by mixins
from playwright.sync_api import ElementHandle # Used in _find_excel_link

from app.core.specialized_scrapers import PageInteractionScraper
# from app.models import Prospect # Data model, not directly used by scraper logic itself
from app.config import active_config 
from app.exceptions import ScraperError
# Logger instance is self.logger from BaseScraper
from app.core.scrapers.configs.ssa_config import SSAConfig


class SsaScraper(PageInteractionScraper):
    """Scraper for the Social Security Administration (SSA) Forecast site."""
    
    def __init__(self, config: SSAConfig, debug_mode: bool = False):
        """Initialize the SSA Forecast scraper."""
        if config.base_url is None:
            config.base_url = active_config.SSA_CONTRACT_FORECAST_URL
            # self.logger is not available yet, use module logger or print for this rare case
            # Using print as logger might not be configured if this is very early.
            print(f"Warning: SSAConfig.base_url was None, set from active_config: {config.base_url}")
            
        super().__init__(config=config, debug_mode=debug_mode)

    def _find_excel_link(self) -> Optional[str]:
        """
        Find the Excel file link on the page using configured selectors.
        Returns: URL of the Excel file, or None if not found.
        """
        self.logger.info("Searching for Excel download link...")
        
        if not self.page:
            self.logger.error("Page object is not available in _find_excel_link.")
            return None 

        for selector in self.config.excel_link_selectors:
            self.logger.debug(f"Trying selector for Excel link: {selector}")
            try:
                links: List[ElementHandle] = self.page.query_selector_all(selector)
                if links:
                    self.logger.debug(f"Found {len(links)} links with selector '{selector}'. Checking hrefs.")
                    for link_element in links:
                        href = link_element.get_attribute('href')
                        if href and ('.xls' in href.lower() or 'forecast' in href.lower() or '.xlsx' in href.lower()):
                            absolute_href = self.page.urljoin(href) 
                            self.logger.info(f"Found Excel link: {absolute_href} (from original href: {href})")
                            return absolute_href
            except Exception as e:
                self.logger.warning(f"Error while querying selector '{selector}' or getting attribute: {e}", exc_info=True)
                continue 
        
        self.logger.warning("Could not find any Excel download link using configured selectors.")
        return None

    def _setup_method(self) -> None:
        """Navigates to the base URL of the scraper."""
        self.logger.info(f"Executing SSA setup: Navigating to base URL: {self.config.base_url}")
        if not self.config.base_url:
            self._handle_and_raise_scraper_error(ValueError("Base URL is not configured."), "SSA setup navigation")
        self.navigate_to_url(self.config.base_url) 

    def _extract_method(self) -> Optional[str]:
        """
        Finds the Excel link and downloads the file.
        Returns: Path to the downloaded file, or None if download failed.
        """
        self.logger.info("Starting Excel document download process for SSA.")
        excel_link_href = self._find_excel_link()

        if not excel_link_href:
            if self.page and self.config.screenshot_on_error: self._save_error_screenshot("ssa_excel_link_not_found")
            if self.page and self.config.save_html_on_error: self._save_error_html("ssa_excel_link_not_found")
            self._handle_and_raise_scraper_error(ScraperError("Excel download link not found on page."), "SSA finding Excel link")
            # The above line raises, so return None is for logical completeness but won't be hit.
            return None 

        self.logger.info(f"Attempting direct download from resolved link: {excel_link_href}")
        try:
            downloaded_path = self.download_file_directly(url=excel_link_href)
            return downloaded_path
        except ScraperError as e:
            self.logger.error(f"ScraperError during direct download for SSA: {e}", exc_info=True)
            raise 
        except Exception as e: 
            self.logger.error(f"Unexpected error during direct download attempt for SSA: {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, "SSA direct download unexpected error")
        return None


    def _custom_ssa_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies SSA-specific transformations to the DataFrame.
        Called by DataProcessingMixin.transform_dataframe *after* raw_column_rename_map.
        The column names here are those resulting from raw_column_rename_map.
        """
        self.logger.info("Applying SSA custom transformations...")

        # Target names based on what db_column_rename_map expects as input
        # Example: if raw_column_rename_map was {'DESCRIPTION': 'description_intermediate_custom'}
        # then here you'd use 'description_intermediate_custom'.
        # The config uses 'description_raw', 'agency_raw' etc. from raw_column_rename_map.
        # And 'title_final', 'description_final' etc. for db_column_rename_map.
        # This function needs to bridge that gap if necessary, or config needs to be precise.

        # For SSA, config is:
        # raw_map: {'DESCRIPTION': 'description_raw', ...}
        # db_map:  {'description_final': 'description', 'title_final': 'title', ...}
        # So, this function should create 'title_final', 'description_final', etc.

        if 'description_raw' in df.columns:
            df['title_final'] = df['description_raw']
            df['description_final'] = df['description_raw'] # Keep original desc as well
            self.logger.debug("Created 'title_final' and 'description_final' from 'description_raw'.")
        else:
            df['title_final'] = None
            df['description_final'] = None
            self.logger.warning("'description_raw' not found to create 'title_final'/'description_final'.")
        
        df['release_date_final'] = None 
        self.logger.debug("Initialized 'release_date_final' to None.")

        # Value parsing in transform_dataframe (DataProcessingMixin) creates 'estimated_value' and 'est_value_unit'.
        # We need to create 'est_value_unit_final' based on 'est_value_unit'.
        if 'est_value_unit' in df.columns:
            df['est_value_unit_final'] = df['est_value_unit'].apply(
                lambda x: f"{x} (Per FY)" if pd.notna(x) and x else "Per FY"
            )
            self.logger.debug("Adjusted 'est_value_unit' to 'est_value_unit_final'.")
        else:
            df['est_value_unit_final'] = "Per FY"
            self.logger.warning("'est_value_unit' column not found. Defaulting 'est_value_unit_final' to 'Per FY'.")
            
        return df

    def _process_method(self, file_path: Optional[str]) -> Optional[int]:
        """
        Processes the downloaded Excel file using DataProcessingMixin methods.
        """
        self.logger.info(f"Starting SSA processing for file: {file_path}")
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path '{file_path}' is invalid or file does not exist. Skipping.")
            return 0

        try:
            df = self.read_file_to_dataframe(
                file_path, 
                file_type_hint=self.config.file_type_hint,
                read_options=self.config.read_options
            )
            if df.empty:
                self.logger.info("DataFrame is empty after reading. Nothing to process for SSA.")
                return 0

            # DataProcessingMixin.transform_dataframe will call _custom_ssa_transforms
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty:
                self.logger.info("DataFrame is empty after transformations. Nothing to load for SSA.")
                return 0
            
            loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules)
            
            self.logger.info(f"SSA processing completed. Loaded {loaded_count} prospects.")
            return loaded_count

        except ScraperError as e: 
            self.logger.error(f"ScraperError during SSA processing of {file_path}: {e}", exc_info=True)
            raise
        except Exception as e: 
            self.logger.error(f"Unexpected error processing SSA file {file_path}: {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, f"processing SSA file {file_path}")
        return 0 

    def scrape(self):
        """Orchestrates the scraping process for SSA."""
        self.logger.info(f"Starting scrape for {self.config.source_name} using SsaScraper logic.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )
```
