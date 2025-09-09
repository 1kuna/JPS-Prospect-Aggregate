"""DOC scraper using the consolidated architecture.
Preserves all original DOC-specific functionality including link text finding and fiscal quarter processing.
"""

import pandas as pd

from app.config import active_config
from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.scraper_configs import get_scraper_config


class DocScraper(ConsolidatedScraperBase):
    """Consolidated DOC scraper.
    Preserves all original functionality including link text finding and custom transforms.
    """

    def __init__(self):
        config = get_scraper_config("doc")
        config.base_url = active_config.COMMERCE_FORECAST_URL
        super().__init__(config)

    def _custom_doc_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Custom DOC transformations preserving the original logic.
        Derives release date from fiscal year/quarter and handles place country standardization.
        """
        try:
            self.logger.info("Applying custom DOC transformations...")

            # Date derivation from FY/Q now handled via transform_params

            # Initialize award dates as None (DOC source doesn't provide them)
            df["award_date_final"] = None
            df["award_fiscal_year_final"] = (
                pd.NA
            )  # Use pandas NA for Int64 compatibility
            self.logger.debug(
                "Initialized 'award_date_final' and 'award_fiscal_year_final' to None/NA."
            )

            # Default country now handled via transform_params

            # Ensure agency is present (DOC sometimes treats Organization as agency)
            if "agency" not in df.columns and "Organization" in df.columns:
                df["agency"] = df["Organization"]
                self.logger.debug("Mapped 'Organization' to 'agency' (DOC).")

        except Exception as e:
            self.logger.warning(f"Error in _custom_doc_transforms: {e}")

        return df


    async def doc_setup(self) -> bool:
        """DOC-specific setup: simple navigation to base URL."""
        if not self.base_url:
            self.logger.error("Base URL not configured.")
            return False

        self.logger.info(f"DOC setup: Navigating to {self.base_url}")
        return await self.navigate_to_url(self.base_url)

    async def doc_extract(self) -> str | None:
        """DOC-specific extraction: find link by text and download via browser click.
        Uses interactive download to avoid 403 errors with direct downloads.
        """
        self.logger.info(
            f"Starting DOC data file download process. Looking for link text: '{self.config.download_link_text}'"
        )

        # First, dismiss the newsletter popup if it appears
        popup_selector = "#prefix-dismissButton"
        try:
            popup_exists = await self.wait_for_selector(
                popup_selector, state="visible", timeout=5000
            )
            if popup_exists:
                self.logger.info("Newsletter popup detected, dismissing...")
                await self.click_element(popup_selector)
                await self.wait_for_timeout(2000)  # Wait for popup to close
                self.logger.info("Newsletter popup dismissed")
            else:
                self.logger.info("No newsletter popup detected, proceeding...")
        except Exception as e:
            self.logger.info(
                f"No popup found or error dismissing popup: {e}, proceeding with download..."
            )

        # Create selector for the link containing the specific text
        link_selector = f'a:has-text("{self.config.download_link_text}")'

        # Verify the link exists and is visible
        link_exists = await self.wait_for_selector(
            link_selector, state="visible", timeout=self.config.interaction_timeout_ms
        )
        if not link_exists:
            await self.capture_error_info(
                Exception("Download link not found"), "doc_link_not_found"
            )
            self.logger.error(
                f"Download link with text '{self.config.download_link_text}' not found on page."
            )
            return None

        self.logger.info(
            "Found download link, attempting interactive download via click"
        )

        # Download by clicking the link with fallback (avoids 403 errors)
        return await self.download_with_fallback(
            selector=link_selector, timeout=self.config.download_timeout_ms
        )

    async def scrape(self) -> int:
        """Execute the complete DOC scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.doc_setup,
            extract_method=self.doc_extract,
            # Uses standard_process by default
        )
