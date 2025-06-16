"""Department of Homeland Security Opportunity Forecast scraper."""

import os
from typing import Optional

import pandas as pd

from app.core.specialized_scrapers import PageInteractionScraper
from app.config import active_config
from app.core.scrapers.configs.dhs_config import DHSConfig
# fiscal_quarter_to_date and parse_value_range are used by DataProcessingMixin via config

class DHSForecastScraper(PageInteractionScraper):
    """Scraper for the DHS Opportunity Forecast site."""

    def __init__(self, config: DHSConfig, debug_mode: bool = False):
        super().__init__(config=config, debug_mode=debug_mode)
    
    def _get_default_url(self) -> str:
        """Return default URL for DHS scraper."""
        return active_config.DHS_FORECAST_URL

    def _apply_custom_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies DHS-specific transformations."""
        self.logger.info("Applying custom DHS transformations...")
        # Default place_country to 'USA' since DHS data doesn't include country
        if 'place_country' not in df.columns:
            df['place_country'] = 'USA'
            self.logger.debug("Initialized 'place_country' to 'USA' as DHS data doesn't include country.")
        return df

