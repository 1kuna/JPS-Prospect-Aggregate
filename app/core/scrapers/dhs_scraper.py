"""
DHS scraper using the consolidated architecture.
Preserves all original DHS-specific functionality.
"""
import pandas as pd
from typing import Optional

from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.config_converter import create_dhs_config
from app.config import active_config


class DHSForecastScraper(ConsolidatedScraperBase):
    """
    Consolidated DHS Opportunity Forecast scraper.
    Preserves all original functionality while using unified architecture.
    """
    
    def __init__(self):
        config = create_dhs_config()
        config.base_url = active_config.DHS_FORECAST_URL
        super().__init__(config)
    
    def _custom_dhs_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Custom DHS transformations: set place_country to 'USA'.
        This preserves the original behavior from the DHS scraper.
        """
        try:
            # Default place_country to 'USA' since DHS data doesn't include country
            if 'place_country' not in df.columns:
                df['place_country'] = 'USA'
                self.logger.debug("Initialized 'place_country' to 'USA' as DHS data doesn't include country.")
            
        except Exception as e:
            self.logger.warning(f"Error in _custom_dhs_transforms: {e}")
        
        return df
    
    async def scrape(self) -> int:
        """Execute the complete DHS scraping workflow."""
        return await self.scrape_with_structure()


# For backward compatibility
async def run_dhs_scraper() -> int:
    """Run the DHS scraper."""
    scraper = DHSForecastScraper()
    return await scraper.scrape()