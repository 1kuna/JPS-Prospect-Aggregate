"""
This module contains specialized base scraper classes that combine BaseScraper
with one or more mixins to provide a tailored starting point for specific
types of scraping tasks.
"""

import os
from typing import Optional
import pandas as pd

from app.core.base_scraper import BaseScraper
from app.core.mixins.navigation_mixin import NavigationMixin
from app.core.mixins.download_mixin import DownloadMixin
from app.core.mixins.data_processing_mixin import DataProcessingMixin
from app.utils.logger import logger
from app.core.configs.base_config import BaseScraperConfig
from app.exceptions import ScraperError

class PageInteractionScraper(NavigationMixin, DownloadMixin, DataProcessingMixin, BaseScraper):
    """
    Enhanced scraper base class with common patterns extracted from all scrapers.
    
    This class combines mixins with common scraper operations that were duplicated
    across multiple scraper implementations:
    - Standard setup method with navigation and wait
    - Standard extract method with download handling  
    - Standard process method with file reading and data processing
    - Common error handling patterns
    
    It inherits functionalities from:
    - NavigationMixin: For common page navigation tasks
    - DownloadMixin: For handling file downloads
    - DataProcessingMixin: For processing downloaded data
    - BaseScraper: For core browser setup, logging, and overall structure
    """
    
    def __init__(self, config: BaseScraperConfig, debug_mode: Optional[bool] = None):
        """Initialize the PageInteractionScraper with config and optional debug mode."""
        # Ensure base_url is set from active_config if not provided
        url_was_none = config.base_url is None
        if url_was_none and hasattr(self, '_get_default_url'):
            config.base_url = self._get_default_url()
        
        super().__init__(config=config, debug_mode=debug_mode)
        
        # Log warning after super().__init__ when logger is available
        if url_was_none and config.base_url:
            self.logger.warning(f"{self.__class__.__name__} base_url was None, set from active_config: {config.base_url}")
    
    def _get_default_url(self) -> Optional[str]:
        """
        Override this method in subclasses to provide default URL from active_config.
        
        Returns:
            str: Default URL for this scraper type
        """
        return None
    
    def _setup_method(self) -> None:
        """
        Standard setup method used by most scrapers.
        Navigates to base URL and waits for page load.
        """
        self.logger.info(f"Executing setup: Navigating to base URL: {self.config.base_url}")
        if not self.config.base_url:
            self._handle_and_raise_scraper_error(
                ValueError("Base URL not configured."), 
                f"{self.__class__.__name__} setup navigation"
            )
        
        self.navigate_to_url(self.config.base_url)
        self.wait_for_load_state('domcontentloaded', timeout_ms=self.config.navigation_timeout_ms)
        
        # Apply any pre-download wait if configured
        if hasattr(self.config, 'explicit_wait_ms_before_download') and self.config.explicit_wait_ms_before_download:
            self.logger.info(f"Waiting {self.config.explicit_wait_ms_before_download}ms before proceeding.")
            self.wait_for_timeout(self.config.explicit_wait_ms_before_download)
    
    def _extract_method(self) -> Optional[str]:
        """
        Standard extract method for downloading files via button click.
        
        Returns:
            str: Path to downloaded file, or None if download failed
        """
        button_selector = getattr(self.config, 'download_button_selector', None) or \
                         getattr(self.config, 'csv_button_selector', None) or \
                         getattr(self.config, 'export_button_selector', None)
        
        if not button_selector:
            raise ScraperError(f"No download button selector configured for {self.__class__.__name__}")
        
        self.logger.info(f"Attempting to download file using button: {button_selector}")
        
        try:
            downloaded_file_path = self.download_file_via_click(click_selector=button_selector)
            return downloaded_file_path
        except ScraperError as e:
            self.logger.error(f"ScraperError during download: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during download: {e}", exc_info=True)
            if self.config.screenshot_on_error and self.page:
                self._save_error_screenshot(f"{self.__class__.__name__.lower()}_extract_error")
            if self.config.save_html_on_error and self.page:
                self._save_error_html(f"{self.__class__.__name__.lower()}_extract_error")
            self._handle_and_raise_scraper_error(e, f"{self.__class__.__name__} file extraction")
    
    def _process_method(self, file_path: Optional[str], data_source=None) -> Optional[int]:
        """
        Standard process method for reading and loading data.
        
        Args:
            file_path: Path to the downloaded file
            data_source: DataSource object for setting source_id
            
        Returns:
            int: Number of prospects loaded, or 0 on failure
        """
        self.logger.info(f"Starting processing for file: {file_path}")
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path '{file_path}' is invalid. Cannot process.")
            return 0
        
        try:
            # Read file using configured strategy or default
            df = self._read_file_with_strategy(file_path)
            
            if df is None or df.empty:
                self.logger.info("DataFrame is empty after reading. Nothing to process.")
                return 0
            
            # Apply custom transformations if the subclass defines them
            if hasattr(self, '_apply_custom_transforms'):
                df = self._apply_custom_transforms(df)
            
            # Transform using mixin
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty:
                self.logger.info("DataFrame is empty after transformations. Nothing to load.")
                return 0
            
            # Load data using mixin
            loaded_count = self.prepare_and_load_data(
                df, 
                config_params=self.config.data_processing_rules, 
                data_source=data_source
            )
            
            self.logger.info(f"Processing completed. Loaded {loaded_count} prospects.")
            return loaded_count
            
        except ScraperError as e:
            self.logger.error(f"ScraperError during processing of {file_path}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing file {file_path}: {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, f"processing file {file_path}")
        
        return 0
    
    def _read_file_with_strategy(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Read file using configured strategy or intelligent fallback.
        
        Args:
            file_path: Path to file to read
            
        Returns:
            pd.DataFrame: Loaded dataframe or None if failed
        """
        strategy = getattr(self.config, 'file_read_strategy', 'auto')
        
        if strategy == "csv_then_excel":
            return self._read_csv_then_excel(file_path)
        elif strategy == "excel_then_csv":
            return self._read_excel_then_csv(file_path)
        else:
            # Default: use mixin's intelligent file reading
            return self.read_file_to_dataframe(file_path, 
                                             file_type_hint=getattr(self.config, 'file_type_hint', None))
    
    def _read_csv_then_excel(self, file_path: str) -> Optional[pd.DataFrame]:
        """Try CSV first, then Excel if CSV fails."""
        self.logger.info(f"Using 'csv_then_excel' strategy for {file_path}")
        try:
            csv_options = getattr(self.config, 'csv_read_options', {}) or {}
            df = pd.read_csv(file_path, **csv_options)
            self.logger.info(f"Successfully read as CSV. Shape: {df.shape}")
            return df
        except Exception as csv_error:
            self.logger.warning(f"Failed to read as CSV ({csv_error}), trying Excel")
            try:
                excel_options = getattr(self.config, 'excel_read_options', {}) or {}
                df = pd.read_excel(file_path, **excel_options)
                self.logger.info(f"Successfully read as Excel. Shape: {df.shape}")
                return df
            except Exception as excel_error:
                self._handle_and_raise_scraper_error(
                    excel_error, 
                    f"parsing file as CSV then Excel: {file_path}"
                )
        return None
    
    def _read_excel_then_csv(self, file_path: str) -> Optional[pd.DataFrame]:
        """Try Excel first, then CSV if Excel fails."""
        self.logger.info(f"Using 'excel_then_csv' strategy for {file_path}")
        try:
            excel_options = getattr(self.config, 'excel_read_options', {}) or {}
            df = pd.read_excel(file_path, **excel_options)
            self.logger.info(f"Successfully read as Excel. Shape: {df.shape}")
            return df
        except Exception as excel_error:
            self.logger.warning(f"Failed to read as Excel ({excel_error}), trying CSV")
            try:
                csv_options = getattr(self.config, 'csv_read_options', {}) or {}
                df = pd.read_csv(file_path, **csv_options)
                self.logger.info(f"Successfully read as CSV. Shape: {df.shape}")
                return df
            except Exception as csv_error:
                self._handle_and_raise_scraper_error(
                    csv_error, 
                    f"parsing file as Excel then CSV: {file_path}"
                )
        return None
    
    def scrape(self):
        """
        Standard scrape orchestration used by all scrapers.
        """
        self.logger.info(f"Starting scrape for {self.config.source_name} using structured approach.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )
