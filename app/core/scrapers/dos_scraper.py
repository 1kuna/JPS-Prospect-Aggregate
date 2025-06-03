"""Department Of State Opportunity Forecast scraper."""

import os
# import traceback # No longer directly used
from typing import Optional

import pandas as pd
# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError # Handled by mixins

from app.core.specialized_scrapers import PageInteractionScraper
from app.config import active_config
from app.exceptions import ScraperError
from app.core.scrapers.configs.dos_config import DOSConfig
from app.utils.parsing import fiscal_quarter_to_date, parse_value_range # For custom transforms

class DOSForecastScraper(PageInteractionScraper):
    """Scraper for the DOS Opportunity Forecast site."""
    
    def __init__(self, config: DOSConfig, debug_mode: bool = False):
        if config.base_url is None: # Though not used for navigation, good to have for reference
            config.base_url = active_config.DOS_FORECAST_URL 
            print(f"Warning: DOSConfig.base_url was None, set from active_config: {config.base_url}")
        super().__init__(config=config, debug_mode=debug_mode)

    def _setup_method(self) -> None:
        """Minimal setup for DOS scraper as it's a direct download."""
        self.logger.info(f"DOS Scraper setup initiated for direct download from: {self.config.direct_download_url}")
        # No browser navigation to a base_url is needed for the page itself.
        # BaseScraper.setup_browser() is still called by scrape_with_structure,
        # which initializes playwright, context, etc., needed for download_file_directly.
        pass

    def _extract_method(self) -> Optional[str]:
        """Downloads the forecast document directly using the URL from config."""
        self.logger.info(f"Attempting direct download for DOS from URL: {self.config.direct_download_url}")
        try:
            # download_file_directly is from DownloadMixin
            downloaded_path = self.download_file_directly(url=self.config.direct_download_url)
            return downloaded_path
        except ScraperError as e:
            self.logger.error(f"ScraperError during DOS direct download: {e}", exc_info=True)
            # _handle_and_raise_scraper_error is not called again if download_file_directly already did it
            raise 
        except Exception as e:
            self.logger.error(f"Unexpected error during DOS direct download: {e}", exc_info=True)
            # No page context for screenshot here as it's a direct download error.
            self._handle_and_raise_scraper_error(e, "DOS direct download unexpected error")
        return None # Should be unreachable

    def _custom_dos_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies DOS-specific transformations. Called by DataProcessingMixin.transform_dataframe
        *after* raw_column_rename_map. Expects columns like 'award_date_raw', 'estimated_value_raw1', etc.
        Creates 'final' columns that db_column_rename_map will then map to DB fields.
        """
        self.logger.info("Applying custom DOS transformations...")

        # Add row_index first for unique ID generation
        df.reset_index(drop=False, inplace=True)
        df['row_index'] = df.index
        self.logger.debug("Added 'row_index'.")

        # Date Parsing (Award Date/Year with priority)
        # Columns expected from raw_column_rename_map: award_fiscal_year_raw, award_date_raw, award_qtr_raw
        df['award_date_final'] = None 
        df['award_fiscal_year_final'] = pd.NA

        if 'award_fiscal_year_raw' in df.columns:
            df['award_fiscal_year_final'] = pd.to_numeric(df['award_fiscal_year_raw'], errors='coerce')

        if 'award_date_raw' in df.columns:
            parsed_direct_award_date = pd.to_datetime(df['award_date_raw'], errors='coerce')
            # Fill award_date if it's still None (it is)
            df['award_date_final'] = df['award_date_final'].fillna(parsed_direct_award_date.dt.date)
            
            # Fill fiscal year from this date if fiscal year is still NA
            needs_fy_from_date_mask = df['award_fiscal_year_final'].isna() & parsed_direct_award_date.notna()
            if needs_fy_from_date_mask.any():
                df.loc[needs_fy_from_date_mask, 'award_fiscal_year_final'] = parsed_direct_award_date[needs_fy_from_date_mask].dt.year

        if 'award_qtr_raw' in df.columns:
            # Only parse quarter if both date and fiscal year are still missing
            needs_qtr_parse_mask = df['award_date_final'].isna() & df['award_fiscal_year_final'].isna() & df['award_qtr_raw'].notna()
            if needs_qtr_parse_mask.any():
                parsed_qtr_info = df.loc[needs_qtr_parse_mask, 'award_qtr_raw'].apply(
                    lambda x: fiscal_quarter_to_date(x) if pd.notna(x) else (None, None)
                )
                df.loc[needs_qtr_parse_mask, 'award_date_final'] = parsed_qtr_info.apply(lambda x: x[0].date() if x[0] else None)
                df.loc[needs_qtr_parse_mask, 'award_fiscal_year_final'] = parsed_qtr_info.apply(lambda x: x[1])
        
        if 'award_fiscal_year_final' in df.columns: # Ensure Int64 type
             df['award_fiscal_year_final'] = df['award_fiscal_year_final'].astype('Int64')
        self.logger.debug("Processed award date and fiscal year columns with priority logic.")

        # Estimated Value Parsing (Priority: raw1 then raw2)
        # Columns expected: estimated_value_raw1, estimated_value_raw2
        df['estimated_value_final'] = pd.NA
        df['est_value_unit_final'] = pd.NA
        if 'estimated_value_raw1' in df.columns and df['estimated_value_raw1'].notna().any():
            parsed_vals = df['estimated_value_raw1'].apply(lambda x: parse_value_range(x) if pd.notna(x) else (None,None))
            df['estimated_value_final'] = parsed_vals.apply(lambda x: x[0])
            df['est_value_unit_final'] = parsed_vals.apply(lambda x: x[1])
        elif 'estimated_value_raw2' in df.columns: # Fallback to raw2 if raw1 was empty/not present
            # Assuming raw2 is numeric or simple string convertible to numeric, not a range
            df['estimated_value_final'] = pd.to_numeric(df['estimated_value_raw2'], errors='coerce')
            # est_value_unit_final remains NA if only raw2 is used and it's just a number
        self.logger.debug("Processed estimated value columns with priority logic.")

        # Solicitation Date (Release Date)
        # Column expected: release_date_raw
        if 'release_date_raw' in df.columns:
            df['release_date_final'] = pd.to_datetime(df['release_date_raw'], errors='coerce').dt.date
        else:
            df['release_date_final'] = None
        self.logger.debug("Processed release date column.")
            
        # Initialize NAICS (not in DOS source)
        df['naics_final'] = pd.NA
        self.logger.debug("Initialized 'naics_final' to NA.")
        
        # Initialize Place columns if missing after raw rename, default country USA
        # Columns expected: place_city_raw, place_state_raw, place_country_raw
        df['place_city_final'] = df['place_city_raw'] if 'place_city_raw' in df.columns else None
        df['place_state_final'] = df['place_state_raw'] if 'place_state_raw' in df.columns else None
        df['place_country_final'] = df['place_country_raw'] if 'place_country_raw' in df.columns else 'USA'
        df.loc[df['place_country_final'].isna(), 'place_country_final'] = 'USA' # Default NA to USA
        self.logger.debug("Processed place columns, defaulting country to USA if needed.")
        
        return df

    def _process_method(self, file_path: Optional[str]) -> Optional[int]:
        """Processes the downloaded Excel file."""
        self.logger.info(f"Starting DOS processing for file: {file_path}")
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File path '{file_path}' is invalid. Cannot process.")
            return 0

        try:
            df = self.read_file_to_dataframe(
                file_path, 
                file_type_hint=self.config.file_type_hint,
                read_options=self.config.read_options
            )
            if getattr(self.config.data_processing_rules, 'dropna_how_all', True) and df.empty:
                 # If dropna_how_all is true (default in mixin) and initial read is empty,
                 # it means the sheet itself might be empty or only headers.
                 self.logger.info("DataFrame is empty after reading (or was all NA rows if dropna applied in read_file_to_dataframe). Nothing to process for DOS.")
                 return 0
            # DataProcessingMixin.transform_dataframe applies raw_column_rename_map, then custom_transform_functions
            df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)
            if df.empty:
                self.logger.info("DataFrame is empty after transformations. Nothing to load for DOS.")
                return 0
            
            loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules)
            
            self.logger.info(f"DOS processing completed. Loaded {loaded_count} prospects.")
            return loaded_count

        except ScraperError as e:
            self.logger.error(f"ScraperError during DOS processing of {file_path}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error processing DOS file {file_path}: {e}", exc_info=True)
            self._handle_and_raise_scraper_error(e, f"processing DOS file {file_path}")
        return 0


    def scrape(self):
        """Orchestrates the scraping process for DOS."""
        self.logger.info(f"Starting scrape for {self.config.source_name} using DOSForecastScraper logic.")
        return self.scrape_with_structure(
            setup_func=self._setup_method,
            extract_func=self._extract_method,
            process_func=self._process_method
        )
