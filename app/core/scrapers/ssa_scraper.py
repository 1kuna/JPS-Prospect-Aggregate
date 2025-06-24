"""
SSA scraper using the consolidated architecture.
Preserves all original SSA-specific functionality including Excel link finding and direct downloads.
"""
import pandas as pd
from typing import Optional

from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.config_converter import create_ssa_config
from app.config import active_config


class SsaScraper(ConsolidatedScraperBase):
    """
    Consolidated SSA scraper.
    Preserves all original functionality including Excel link finding and custom transforms.
    """
    
    def __init__(self):
        config = create_ssa_config()
        config.base_url = active_config.SSA_CONTRACT_FORECAST_URL
        super().__init__(config)
    
    def _custom_ssa_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Custom SSA transformations preserving the original logic.
        Maps description to title and handles value unit adjustments.
        """
        try:
            self.logger.info("Applying SSA custom transformations...")
            
            # Create title and description from description_raw (SSA uses description as title)
            if 'description_raw' in df.columns:
                df['title_final'] = df['description_raw']
                df['description_final'] = df['description_raw']  # Keep original desc as well
                self.logger.debug("Created 'title_final' and 'description_final' from 'description_raw'.")
            else:
                df['title_final'] = None
                df['description_final'] = None
                self.logger.warning("'description_raw' not found to create 'title_final'/'description_final'.")
            
            # Initialize release_date_final
            df['release_date_final'] = None 
            self.logger.debug("Initialized 'release_date_final' to None.")
            
            # Value unit adjustment (Per FY notation)
            if 'est_value_unit' in df.columns:
                df['est_value_unit_final'] = df['est_value_unit'].apply(
                    lambda x: f"{x} (Per FY)" if pd.notna(x) and x else "Per FY"
                )
                self.logger.debug("Adjusted 'est_value_unit' to 'est_value_unit_final'.")
            else:
                df['est_value_unit_final'] = "Per FY"
                self.logger.warning("'est_value_unit' column not found. Defaulting 'est_value_unit_final' to 'Per FY'.")
            
        except Exception as e:
            self.logger.warning(f"Error in _custom_ssa_transforms: {e}")
        
        return df
    
    def _ssa_create_extras(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create extras JSON with SSA-specific fields that aren't in core schema.
        Captures 9 additional data points for comprehensive data retention.
        """
        try:
            # Define SSA-specific extras fields mapping (using original CSV column names)
            extras_fields = {
                'REQUIREMENT TYPE': 'requirement_type',
                'EST COST PER FY': 'est_cost_per_fy',
                'PLANNED AWARD DATE': 'planned_award_date',
                'EXISTING AWD #': 'existing_award_number',
                'INCUMBENT VENDOR': 'incumbent_vendor',
                'NAICS DESCRIPTION': 'naics_description',
                'TYPE OF COMPETITION': 'type_of_competition',
                'NET VIEW TOTAL OBLIGATED AMT': 'net_view_total_obligated_amount',
                'ULTIMATE COMPLETION DATE': 'ultimate_completion_date'
            }
            
            # Create extras JSON column
            extras_data = []
            for _, row in df.iterrows():
                extras = {}
                for df_col, extra_key in extras_fields.items():
                    if df_col in df.columns:
                        value = row[df_col]
                        if pd.notna(value) and value != '':
                            extras[extra_key] = str(value)
                extras_data.append(extras if extras else {})
            
            # Add the extras JSON column (as dict, not JSON string)
            df['extras_json'] = extras_data
            
            self.logger.debug(f"Created SSA extras JSON for {len(extras_data)} rows with {len(extras_fields)} potential fields")
                
        except Exception as e:
            self.logger.warning(f"Error in _ssa_create_extras: {e}")
        
        return df
    
    async def ssa_setup(self) -> bool:
        """
        SSA-specific setup: simple navigation to base URL.
        """
        if not self.base_url:
            self.logger.error("Base URL not configured.")
            return False
        
        self.logger.info(f"SSA setup: Navigating to {self.base_url}")
        return await self.navigate_to_url(self.base_url)
    
    async def ssa_extract(self) -> Optional[str]:
        """
        SSA-specific extraction: find Excel link and download directly.
        Preserves original SSA download behavior.
        """
        self.logger.info("Starting Excel document download process for SSA.")
        
        # Find the Excel link using configured selectors
        excel_link_href = await self.find_excel_link()
        
        if not excel_link_href:
            await self.capture_error_info(Exception("Excel link not found"), "ssa_excel_link_not_found")
            self.logger.error("Excel download link not found on page.")
            return None
        
        self.logger.info(f"Attempting direct download from resolved link: {excel_link_href}")
        
        # Download directly from the URL
        return await self.download_file_directly(excel_link_href)
    
    def ssa_process(self, file_path: str) -> int:
        """
        SSA-specific processing with Excel-specific read options.
        """
        if not file_path:
            # Try to get most recent download
            file_path = self.get_last_downloaded_path()
            if not file_path:
                self.logger.error("No file available for processing")
                return 0
        
        self.logger.info(f"Starting SSA processing for file: {file_path}")
        
        # Read Excel file with specific options (header at row 4)
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
        """Execute the complete SSA scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.ssa_setup,
            extract_method=self.ssa_extract,
            process_method=self.ssa_process
        )


# For backward compatibility
async def run_ssa_scraper() -> int:
    """Run the SSA scraper."""
    scraper = SsaScraper()
    return await scraper.scrape()