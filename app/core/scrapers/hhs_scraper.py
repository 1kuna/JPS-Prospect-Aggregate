"""HHS scraper using the consolidated architecture.
Preserves all original HHS-specific functionality including View All workflow.
"""

import pandas as pd

from app.config import active_config
from app.core.scraper_base import ConsolidatedScraperBase
from app.core.scraper_configs import get_scraper_config


class HHSForecastScraper(ConsolidatedScraperBase):
    """Consolidated HHS Opportunity Forecast scraper.
    Preserves all original functionality including View All button workflow.
    """

    def __init__(self):
        config = get_scraper_config("hhs")
        config.base_url = active_config.HHS_FORECAST_URL
        super().__init__(config)

    def _custom_hhs_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Custom HHS transformations for the new CSV format.
        Creates native_id, handles contact names, and place_country.
        """
        try:
            self.logger.info("Applying custom HHS transformations...")

            # Row index is now added via transform_params

            # Create native_id from title and row_index
            df["native_id"] = "HHS-" + df["row_index"].astype(str).str.zfill(5)
            self.logger.debug("Created native_id from row_index.")

            # Name combining now handled via transform_params

            # Default country now handled via transform_params

        except Exception as e:
            self.logger.warning(f"Error in _custom_hhs_transforms: {e}")

        return df


    async def hhs_setup(self) -> bool:
        """HHS-specific setup: navigate and click 'View All' button.
        Enhanced for JavaScript-heavy HHS site with multi-step navigation.
        """
        if not self.base_url:
            self.logger.error("Base URL not configured.")
            return False

        # Try alternative approach - first go to main HHS OSDBU site
        self.logger.info("Trying alternative navigation approach for HHS...")

        # First navigate to the main OSDBU page
        main_url = "https://osdbu.hhs.gov/"
        self.logger.info(f"Step 1: Navigating to main OSDBU site: {main_url}")
        success = await self.navigate_to_url(main_url, wait_until="networkidle")
        if not success:
            self.logger.error("Failed to navigate to main HHS OSDBU site")
            # Try direct navigation as fallback
            self.logger.info(f"Fallback: Direct navigation to {self.base_url}")
            success = await self.navigate_to_url(
                self.base_url, wait_until="domcontentloaded"
            )
            if not success:
                return False
        else:
            # Now navigate to the forecast page
            self.logger.info(f"Step 2: Navigating to forecast page: {self.base_url}")
            success = await self.navigate_to_url(
                self.base_url, wait_until="networkidle"
            )
            if not success:
                self.logger.error("Failed to navigate to HHS forecast URL")
                return False

        # Additional wait for JavaScript to fully initialize
        self.logger.info("Waiting for JavaScript to initialize...")
        await self.wait_for_timeout(5000)

        # Wait for the specific View All button to be available
        self.logger.info(
            f"Waiting for View All button: {self.config.pre_export_click_selector}"
        )
        try:
            await self.wait_for_selector(
                self.config.pre_export_click_selector, timeout=30000
            )
        except Exception as e:
            self.logger.error(f"View All button not found: {e}")
            return False

        # Click "View All" button
        self.logger.info(
            f"Clicking 'View All' button: {self.config.pre_export_click_selector}"
        )
        success = await self.click_element(self.config.pre_export_click_selector)
        if not success:
            self.logger.error("Failed to click 'View All' button")
            return False

        # Wait for page to update after 'View All' click
        self.logger.info(
            f"Waiting {self.config.pre_export_click_wait_ms}ms for page to update after 'View All' click."
        )
        await self.wait_for_timeout(self.config.pre_export_click_wait_ms)

        return True

    async def hhs_extract(self) -> str | None:
        """HHS-specific extraction: download via CSV button.
        Preserves original HHS download behavior.
        """
        self.logger.info(
            f"Attempting to download by clicking export button: {self.config.csv_button_selector}"
        )

        return await self.download_with_fallback(
            selector=self.config.csv_button_selector,
            wait_after_click=self.config.default_wait_after_download_ms,
        )

    async def scrape(self) -> int:
        """Execute the complete HHS scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.hhs_setup,
            extract_method=self.hhs_extract,
            # Uses standard_process by default
        )
