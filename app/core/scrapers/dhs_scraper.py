"""
DHS scraper using the consolidated architecture.
Preserves all original DHS-specific functionality.
"""
import json
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
    
    def _dhs_create_extras(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create extras JSON with DHS-specific fields that aren't in core schema.
        Captures 8 additional data points for comprehensive data retention.
        """
        try:
            # Define DHS-specific extras fields mapping
            extras_fields = {
                'contract_number': 'contract_number',
                'contractor': 'contractor',
                'primary_contact_first_name': 'primary_contact_first_name',
                'primary_contact_last_name': 'primary_contact_last_name',
                'primary_contact_phone': 'primary_contact_phone',
                'primary_contact_email': 'primary_contact_email',
                'forecast_published': 'forecast_published',
                'forecast_previously_published': 'forecast_previously_published'
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
            
            # Add the extras JSON column
            df['extras_json'] = [json.dumps(extras) for extras in extras_data]
            
            self.logger.debug(f"Created DHS extras JSON for {len(extras_data)} rows with {len(extras_fields)} potential fields")
                
        except Exception as e:
            self.logger.warning(f"Error in _dhs_create_extras: {e}")
        
        return df
    
    async def scrape(self) -> int:
        """Execute the complete DHS scraping workflow."""
        return await self.scrape_with_structure()


# For backward compatibility
async def run_dhs_scraper() -> int:
    """Run the DHS scraper."""
    scraper = DHSForecastScraper()
    return await scraper.scrape()