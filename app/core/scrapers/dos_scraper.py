"""DOS scraper using the consolidated architecture.
Preserves all original DOS-specific functionality including direct download and complex value processing.
"""

import pandas as pd

from app.config import active_config
from app.core.scraper_base import ConsolidatedScraperBase
from app.core.scraper_configs import get_scraper_config


class DOSForecastScraper(ConsolidatedScraperBase):
    """Consolidated DOS scraper.
    Preserves all original functionality including direct download and complex data processing.
    """

    def __init__(self):
        config = get_scraper_config("dos")
        config.base_url = active_config.DOS_FORECAST_URL  # For reference
        super().__init__(config)

    def _custom_dos_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Custom DOS transformations preserving the original complex logic.
        Handles priority-based date parsing, value range processing, and place standardization.
        """
        try:
            self.logger.info("Applying custom DOS transformations...")

            # Row index is now added via transform_params

            # Award date priority logic now handled via transform_params

            # Value parsing with priority now handled via transform_params

            # Solicitation Date (Release Date)
            if "release_date_raw" in df.columns:
                df["release_date_final"] = pd.to_datetime(
                    df["release_date_raw"], errors="coerce"
                ).dt.date
            else:
                df["release_date_final"] = None
            self.logger.debug("Processed release date column.")

            # Initialize NAICS (not in DOS source)
            df["naics_final"] = pd.NA
            self.logger.debug("Initialized 'naics_final' to NA.")

            # Place country default now handled via transform_params
            # Handle place columns that need renaming from raw
            if "place_city_raw" in df.columns:
                df["place_city_final"] = df["place_city_raw"]
            if "place_state_raw" in df.columns:
                df["place_state_final"] = df["place_state_raw"]
            if "place_country_raw" in df.columns:
                df["place_country_final"] = df["place_country_raw"]

        except Exception as e:
            self.logger.warning(f"Error in _custom_dos_transforms: {e}")

        return df

    async def dos_setup(self) -> bool:
        """DOS-specific setup: minimal setup for direct download.
        No browser navigation needed since it's a direct download.
        """
        self.logger.info(
            f"DOS Scraper setup initiated for direct download from: {self.config.direct_download_url}"
        )
        # No actual navigation needed, browser is set up by the base class
        return True

    async def dos_extract(self) -> str | None:
        """DOS-specific extraction: direct download from configured URL.
        Preserves original DOS direct download behavior.
        """
        self.logger.info(
            f"Attempting direct download for DOS from URL: {self.config.direct_download_url}"
        )

        # Download directly from the configured URL
        return await self.download_file_directly(self.config.direct_download_url)

    async def scrape(self) -> int:
        """Execute the complete DOS scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.dos_setup,
            extract_method=self.dos_extract,
            # Uses standard_process by default
        )
