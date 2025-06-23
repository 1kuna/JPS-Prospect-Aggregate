"""
DOC scraper using the consolidated architecture.
Preserves all original DOC-specific functionality including link text finding and fiscal quarter processing.
"""
import pandas as pd
from typing import Optional
from app.utils.value_and_date_parsing import fiscal_quarter_to_date

from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.config_converter import create_doc_config
from app.config import active_config


class DocScraper(ConsolidatedScraperBase):
    """
    Consolidated DOC scraper.
    Preserves all original functionality including link text finding and custom transforms.
    """
    
    def __init__(self):
        config = create_doc_config()
        config.base_url = active_config.COMMERCE_FORECAST_URL
        super().__init__(config)
    
    def _custom_doc_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Custom DOC transformations preserving the original logic.
        Derives release date from fiscal year/quarter and handles place country standardization.
        """
        try:
            self.logger.info("Applying custom DOC transformations...")
            
            # Derive Solicitation Date (release_date_final) from FY/Quarter
            if 'solicitation_fy_raw' in df.columns and 'solicitation_qtr_raw' in df.columns:
                # Format quarter column correctly for fiscal_quarter_to_date
                df['solicitation_qtr_fmt'] = df['solicitation_qtr_raw'].astype(str).apply(
                    lambda x: f'Q{x.split(".")[0]}' if pd.notna(x) and x else None
                )
                df['solicitation_fyq_combined'] = df['solicitation_fy_raw'].astype(str).fillna('') + ' ' + df['solicitation_qtr_fmt'].fillna('')
                
                parsed_sol_date_info = df['solicitation_fyq_combined'].apply(
                    lambda x: fiscal_quarter_to_date(x.strip()) if pd.notna(x) and x.strip() else (None, None)
                )
                df['release_date_final'] = parsed_sol_date_info.apply(lambda x: x[0].date() if x[0] else None)
                self.logger.debug("Derived 'release_date_final' from fiscal year and quarter.")
            else:
                df['release_date_final'] = None
                self.logger.warning("Could not derive 'release_date_final'; 'solicitation_fy_raw' or 'solicitation_qtr_raw' missing.")

            # Initialize award dates as None (DOC source doesn't provide them)
            df['award_date_final'] = None
            df['award_fiscal_year_final'] = pd.NA  # Use pandas NA for Int64 compatibility
            self.logger.debug("Initialized 'award_date_final' and 'award_fiscal_year_final' to None/NA.")
                
            # Default place_country_final to 'USA' if not present or NaN
            if 'place_country_raw' in df.columns:
                df['place_country_final'] = df['place_country_raw'].fillna('USA')
            else:
                df['place_country_final'] = 'USA'
            self.logger.debug("Processed 'place_country_final', defaulting to USA if needed.")
            
        except Exception as e:
            self.logger.warning(f"Error in _custom_doc_transforms: {e}")
        
        return df
    
    async def doc_setup(self) -> bool:
        """
        DOC-specific setup: simple navigation to base URL.
        """
        if not self.base_url:
            self.logger.error("Base URL not configured.")
            return False
        
        self.logger.info(f"DOC setup: Navigating to {self.base_url}")
        return await self.navigate_to_url(self.base_url)
    
    async def doc_extract(self) -> Optional[str]:
        """
        DOC-specific extraction: find link by text and download directly.
        Preserves original DOC download behavior.
        """
        self.logger.info(f"Starting DOC data file download process. Looking for link text: '{self.config.download_link_text}'")
        
        # Find the download link by text
        download_url = await self.find_link_by_text(
            self.config.download_link_text, 
            timeout_ms=self.config.interaction_timeout_ms
        )
        
        if not download_url:
            await self.capture_error_info(Exception("Download link not found"), "doc_link_not_found")
            self.logger.error(f"Download link with text '{self.config.download_link_text}' not found on page.")
            return None
        
        self.logger.info(f"Attempting direct download from resolved link: {download_url}")
        
        # Download directly from the URL
        return await self.download_file_directly(download_url)
    
    def doc_process(self, file_path: str) -> int:
        """
        DOC-specific processing with Excel-specific read options.
        """
        if not file_path:
            # Try to get most recent download
            file_path = self.get_last_downloaded_path()
            if not file_path:
                self.logger.error("No file available for processing")
                return 0
        
        self.logger.info(f"Starting DOC processing for file: {file_path}")
        
        # Read Excel file with specific options (header at row 2)
        df = self.read_file_to_dataframe(file_path)
        if df is None or df.empty:
            self.logger.info("DataFrame is empty after reading. Nothing to process.")
            return 0
        
        # Apply transformations
        df = self.transform_dataframe(df)
        if df.empty:
            self.logger.info("DataFrame is empty after transformations. Nothing to load.")
            return 0
        
        # Load to database
        return self.prepare_and_load_data(df)
    
    async def scrape(self) -> int:
        """Execute the complete DOC scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.doc_setup,
            extract_method=self.doc_extract,
            process_method=self.doc_process
        )


# For backward compatibility
async def run_doc_scraper() -> int:
    """Run the DOC scraper."""
    scraper = DocScraper()
    return await scraper.scrape()