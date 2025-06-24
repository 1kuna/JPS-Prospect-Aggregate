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
        Custom DHS transformations: set place_country to 'USA' and combine contact names.
        This preserves the original behavior from the DHS scraper.
        """
        try:
            # Default place_country to 'USA' since DHS data doesn't include country
            if 'place_country' not in df.columns:
                df['place_country'] = 'USA'
                self.logger.debug("Initialized 'place_country' to 'USA' as DHS data doesn't include country.")
            
            # Combine contact first and last names into primary_contact_name
            first_name_col = 'primary_contact_first_name'
            last_name_col = 'primary_contact_last_name'
            if first_name_col in df.columns and last_name_col in df.columns:
                df['primary_contact_name'] = df[first_name_col].fillna('') + ' ' + df[last_name_col].fillna('')
                df['primary_contact_name'] = df['primary_contact_name'].str.strip()
                # Clean up empty combinations (just spaces)
                df['primary_contact_name'] = df['primary_contact_name'].replace('', None)
                self.logger.debug("Combined DHS primary contact first and last names.")
            
        except Exception as e:
            self.logger.warning(f"Error in _custom_dhs_transforms: {e}")
        
        return df
    
    def _dhs_create_extras(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create extras JSON with DHS-specific fields that aren't in core schema.
        Captures 8 additional data points for comprehensive data retention.
        """
        try:
            # Define DHS-specific extras fields mapping (using original CSV column names)
            extras_fields = {
                'Contract Number': 'contract_number',
                'Contractor': 'contractor',
                'Primary Contact First Name': 'primary_contact_first_name',
                'Primary Contact Last Name': 'primary_contact_last_name',
                'Primary Contact Phone': 'primary_contact_phone',
                'Primary Contact Email': 'primary_contact_email',
                'Forecast Published': 'forecast_published',
                'Forecast Previously Published': 'forecast_previously_published'
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