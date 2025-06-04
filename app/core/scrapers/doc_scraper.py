"""Department of Commerce Opportunity Forecast scraper."""

import os
# import traceback # No longer directly used
from typing import Optional
from urllib.parse import urljoin 

import pandas as pd
# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError # Handled by mixins
# from playwright.sync_api import ElementHandle # No longer directly used

from app.core.specialized_scrapers import PageInteractionScraper
from app.config import active_config
from app.exceptions import ScraperError
from app.core.scrapers.configs.doc_config import DOCConfig
from app.utils.parsing import fiscal_quarter_to_date # For custom transforms

class DocScraper(PageInteractionScraper):
    """Scraper for the Department of Commerce (DOC) Forecast site."""
    
    def __init__(self, config: DOCConfig, debug_mode: bool = False):
        if config.base_url is None:
            config.base_url = active_config.COMMERCE_FORECAST_URL
            print(f"Warning: DOCConfig.base_url was None, set from active_config: {config.base_url}")
        super().__init__(config=config, debug_mode=debug_mode)

    def _setup_method(self) -> None:
        """Navigates to the base URL of the scraper."""
        self.logger.info(f"Executing DOC setup: Navigating to base URL: {self.config.base_url}")
        if not self.config.base_url:
            self._handle_and_raise_scraper_error(ValueError("Base URL not configured."), "DOC setup navigation")
        self.navigate_to_url(self.config.base_url)
        # Additional wait for load state can be added if needed, e.g., self.wait_for_load_state('networkidle')

    def _extract_method(self) -> Optional[str]:
        """Finds the download link by text, resolves its URL, and downloads the file directly."""
        self.logger.info(f"Starting DOC data file download process. Looking for link text: '{self.config.download_link_text}'")
        
        link_selector = f'a:has-text("{self.config.download_link_text}")'
        
        # Wait for selector ensures the link is at least attached, visible is better if no immediate click
        self.wait_for_selector(link_selector, state='visible', timeout_ms=self.config.interaction_timeout_ms)
        
        # Using .first because has-text can sometimes match multiple if text is not unique enough, though unlikely here.
        link_locator = self.page.locator(link_selector).first 
        
        href = link_locator.get_attribute('href')
        if not href:
            # Error saving (screenshot/HTML) will be done by _handle_and_raise_scraper_error via BaseScraper
            self._handle_and_raise_scraper_error(
                ScraperError("Download link found but has no href attribute."), 
                f"finding href for download link '{self.config.download_link_text}'"
            )
            return None # Unreachable

        # Resolve the potentially relative URL from href against the current page's URL
        absolute_url = urljoin(self.page.url, href)
        self.logger.info(f"Resolved download URL: {absolute_url}")

        try:
            # download_file_directly is from DownloadMixin
            downloaded_path = self.download_file_directly(url=absolute_url)
            return downloaded_path
        except ScraperError as e:
            self.logger.error(f"ScraperError during DOC direct download from '{absolute_url}': {e}", exc_info=True)
            raise # Re-raise
        except Exception as e:
            self.logger.error(f"Unexpected error during DOC direct download from '{absolute_url}': {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, f"DOC direct download from {absolute_url}")
        return None # Unreachable


    def _custom_doc_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies DOC-specific transformations. Called by DataProcessingMixin.transform_dataframe
        *after* raw_column_rename_map.
        """
        self.logger.info("Applying custom DOC transformations...")

        # Derive Solicitation Date (release_date_final) from FY/Quarter
        # Expects 'solicitation_fy_raw' and 'solicitation_qtr_raw' from raw_column_rename_map
        if 'solicitation_fy_raw' in df.columns and 'solicitation_qtr_raw' in df.columns:
            # fiscal_quarter_to_date needs strings like "Q1", "Q2" etc.
            # Ensure quarter column is formatted correctly.
            df['solicitation_qtr_fmt'] = df['solicitation_qtr_raw'].astype(str).apply(
                lambda x: f'Q{x.split(".")[0]}' if pd.notna(x) and x else None
            )
            df['solicitation_fyq_combined'] = df['solicitation_fy_raw'].astype(str).fillna('') + ' ' + df['solicitation_qtr_fmt'].fillna('')
            
            parsed_sol_date_info = df['solicitation_fyq_combined'].apply(
                lambda x: fiscal_quarter_to_date(x.strip()) if pd.notna(x) and x.strip() else (None, None)
            )
            df['release_date_final'] = parsed_sol_date_info.apply(lambda x: x[0].date() if x[0] else None)
            # df['solicitation_fiscal_year_final'] = parsed_sol_date_info.apply(lambda x: x[1]).astype('Int64') # If needed
            self.logger.debug("Derived 'release_date_final' from fiscal year and quarter.")
        else:
            df['release_date_final'] = None
            self.logger.warning("Could not derive 'release_date_final'; 'solicitation_fy_raw' or 'solicitation_qtr_raw' missing.")

        # Initialize award dates as None (DOC source doesn't provide them)
        df['award_date_final'] = None
        df['award_fiscal_year_final'] = pd.NA # Use pandas NA for Int64 compatibility
        self.logger.debug("Initialized 'award_date_final' and 'award_fiscal_year_final' to None/NA.")
            
        # Default place_country_final to 'USA' if not present or NaN
        # Expects 'place_country_raw' from raw_column_rename_map
        if 'place_country_raw' in df.columns:
            df['place_country_final'] = df['place_country_raw'].fillna('USA')
        else:
            df['place_country_final'] = 'USA'
        self.logger.debug("Processed 'place_country_final', defaulting to USA if needed.")
        
        return df

    def _process_method(self, file_path: Optional[str], data_source=None) -> Optional[int]:
        """Processes the downloaded Excel file."""
        self.logger.info(f"Starting DOC processing for file: {file_path}")
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
                self.logger.info("DataFrame is empty after reading. Nothing to process for DOC.")
                return 0
            
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty:
                self.logger.info("DataFrame is empty after transformations. Nothing to load for DOC.")
                return 0
            
            loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules, data_source=data_source)
            
            self.logger.info(f"DOC processing completed. Loaded {loaded_count} prospects.")
            return loaded_count

        except ScraperError as e:
            self.logger.error(f"ScraperError during DOC processing of {file_path}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing DOC file {file_path}: {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, f"processing DOC file {file_path}")
        return 0


    def scrape(self):
        """Orchestrates the scraping process for DOC."""
        self.logger.info(f"Starting scrape for {self.config.source_name} using DocScraper logic.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )
