"""SSA scraper using the consolidated architecture.
Preserves all original SSA-specific functionality including Excel link finding and direct downloads.
"""

import pandas as pd

from app.config import active_config
from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.scraper_configs import get_scraper_config


class SsaScraper(ConsolidatedScraperBase):
    """Consolidated SSA scraper.
    Preserves all original functionality including Excel link finding and custom transforms.
    """

    def __init__(self):
        config = get_scraper_config("ssa")
        config.base_url = active_config.SSA_CONTRACT_FORECAST_URL
        super().__init__(config)

    def _custom_ssa_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Custom SSA transformations preserving the original logic.
        Maps description to title and handles value unit adjustments.
        """
        try:
            self.logger.info("Applying SSA custom transformations...")

            # Create title from description (SSA uses description as title)
            if "description" in df.columns:
                df["title"] = df["description"]
                self.logger.debug(
                    "Created 'title' from 'description' (SSA convention)."
                )
            else:
                df["title"] = None
                self.logger.warning("'description' not found to create 'title'.")

            # Initialize release_date_final
            df["release_date_final"] = None
            self.logger.debug("Initialized 'release_date_final' to None.")

            # Value unit adjustment (Per FY notation)
            if "est_value_unit" in df.columns:
                df["est_value_unit_final"] = df["est_value_unit"].apply(
                    lambda x: f"{x} (Per FY)" if pd.notna(x) and x else "Per FY"
                )
                self.logger.debug(
                    "Adjusted 'est_value_unit' to 'est_value_unit_final'."
                )
            else:
                df["est_value_unit_final"] = "Per FY"
                self.logger.warning(
                    "'est_value_unit' column not found. Defaulting 'est_value_unit_final' to 'Per FY'."
                )

            # Normalize set_aside variants to unified 'set_aside'
            if "set_aside" not in df.columns:
                for variant in ["TYPE OF COMPETITION", "SET ASIDE"]:
                    if variant in df.columns and df[variant].notna().any():
                        df["set_aside"] = df[variant]
                        break

            # Normalize estimated value variants to 'estimated_value_text'
            if "estimated_value_text" not in df.columns:
                for variant in ["EST COST PER FY", "ESTIMATED VALUE"]:
                    if variant in df.columns and df[variant].notna().any():
                        df["estimated_value_text"] = df[variant]
                        break

            # Parse place_raw to extract city and state
            if "place_raw" in df.columns:
                # SSA typically has format like "Baltimore, MD" or just city name
                df[["place_city", "place_state"]] = df["place_raw"].str.extract(
                    r"^([^,]+)(?:,\s*([A-Z]{2}))?$", expand=True
                )
                df["place_city"] = df["place_city"].str.strip()
                df["place_state"] = df["place_state"].str.strip()
                df["place_country"] = "USA"  # Default for SSA data
                self.logger.debug("Parsed place_raw into city, state, and country.")

        except Exception as e:
            self.logger.warning(f"Error in _custom_ssa_transforms: {e}")

        return df


    async def ssa_setup(self) -> bool:
        """SSA-specific setup: simple navigation to base URL."""
        if not self.base_url:
            self.logger.error("Base URL not configured.")
            return False

        self.logger.info(f"SSA setup: Navigating to {self.base_url}")
        return await self.navigate_to_url(self.base_url)

    async def ssa_extract(self) -> str | None:
        """SSA-specific extraction: find Excel link and download directly.
        Preserves original SSA download behavior.
        """
        self.logger.info("Starting Excel document download process for SSA.")

        # Find the Excel link using configured selectors
        excel_link_href = await self.find_excel_link()

        if not excel_link_href:
            await self.capture_error_info(
                Exception("Excel link not found"), "ssa_excel_link_not_found"
            )
            self.logger.error("Excel download link not found on page.")
            return None

        self.logger.info(
            f"Attempting direct download from resolved link: {excel_link_href}"
        )

        # Download directly from the URL
        return await self.download_file_directly(excel_link_href)

    async def scrape(self) -> int:
        """Execute the complete SSA scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.ssa_setup,
            extract_method=self.ssa_extract,
            # Uses standard_process by default
        )
