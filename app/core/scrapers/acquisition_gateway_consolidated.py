"""
Acquisition Gateway scraper using the consolidated architecture.
This replaces the original acquisition_gateway.py with simplified, unified approach.
"""
import pandas as pd
from typing import Optional

from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.config_converter import create_acquisition_gateway_config
from app.config import active_config
from app.utils.logger import logger


class AcquisitionGatewayScraper(ConsolidatedScraperBase):
    """
    Consolidated Acquisition Gateway scraper.
    Preserves all original functionality while using unified architecture.
    """
    
    def __init__(self):
        config = create_acquisition_gateway_config()
        config.base_url = active_config.ACQUISITION_GATEWAY_URL
        super().__init__(config)
    
    def custom_summary_fallback(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Custom transformation: Handle Body/Summary column fallback.
        This preserves the original behavior from the acquisition gateway scraper.
        """
        try:
            # If 'description' (from 'Body') is missing but 'Summary' exists, use Summary
            if 'description' in df.columns and 'Summary' in df.columns:
                # Fill missing descriptions with Summary values
                mask = df['description'].isna() | (df['description'] == '')
                df.loc[mask, 'description'] = df.loc[mask, 'Summary']
                
                self.logger.debug("Applied summary fallback for missing descriptions")
            
            # Remove the Summary column if it exists (no longer needed)
            if 'Summary' in df.columns:
                df = df.drop(columns=['Summary'])
                
        except Exception as e:
            self.logger.warning(f"Error in custom_summary_fallback: {e}")
        
        return df
    
    async def scrape(self) -> int:
        """
        Execute the complete scraping workflow.
        Uses the standard pattern but can be customized if needed.
        """
        return await self.scrape_with_structure()


# For backward compatibility - maintain the same interface
async def run_acquisition_gateway_scraper() -> int:
    """
    Run the Acquisition Gateway scraper.
    Maintains backward compatibility with existing runner scripts.
    """
    scraper = AcquisitionGatewayScraper()
    return await scraper.scrape()


# Testing function
async def test_acquisition_gateway_scraper():
    """Test the consolidated scraper implementation."""
    scraper = AcquisitionGatewayScraper()
    
    try:
        logger.info("Testing Acquisition Gateway consolidated scraper...")
        
        # Test configuration
        assert scraper.source_name == "Acquisition Gateway"
        assert scraper.config.debug_mode == True  # Should be non-headless
        assert scraper.config.download_timeout_ms == 150000  # Extended timeout
        assert scraper.config.export_button_selector == "button#export-0"
        
        # Test custom transform function
        test_df = pd.DataFrame({
            'description': ['Valid desc', None, ''],
            'Summary': ['Summary 1', 'Summary 2', 'Summary 3']
        })
        
        transformed_df = scraper.custom_summary_fallback(test_df)
        
        # Verify fallback behavior
        assert transformed_df.loc[1, 'description'] == 'Summary 2'  # Filled from Summary
        assert transformed_df.loc[2, 'description'] == 'Summary 3'  # Filled from Summary
        assert transformed_df.loc[0, 'description'] == 'Valid desc'  # Unchanged
        assert 'Summary' not in transformed_df.columns  # Summary column removed
        
        logger.info("✓ Acquisition Gateway consolidated scraper test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Acquisition Gateway consolidated scraper test failed: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_acquisition_gateway_scraper())