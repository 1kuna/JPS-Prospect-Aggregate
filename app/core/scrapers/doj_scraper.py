"""DOJ scraper using the consolidated architecture.
Preserves all original DOJ-specific functionality including complex award date processing.
"""

import pandas as pd

from app.config import active_config
from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.scraper_configs import get_scraper_config
from app.utils.value_and_date_parsing import fiscal_quarter_to_date


class DOJForecastScraper(ConsolidatedScraperBase):
    """Consolidated DOJ scraper.
    Preserves all original functionality including complex award date logic and place country handling.
    """

    def __init__(self):
        config = get_scraper_config("doj")
        config.base_url = active_config.DOJ_FORECAST_URL
        super().__init__(config)

    def _custom_doj_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Custom DOJ transformations preserving the original complex logic.
        Handles award date with fiscal quarter fallback and place country standardization.
        """
        try:
            self.logger.info("Applying custom DOJ transformations...")

            # Award Date Logic (Complex)
            award_date_col_raw = "award_date_raw"  # From raw_column_rename_map

            if award_date_col_raw in df.columns:
                df["award_date_final"] = pd.to_datetime(
                    df[award_date_col_raw], errors="coerce"
                )
                # Attempt to get year directly, will be float if NaT present, so handle with Int64 later
                df["award_fiscal_year_final"] = df["award_date_final"].dt.year

                needs_fallback_mask = (
                    df["award_date_final"].isna() & df[award_date_col_raw].notna()
                )
                if needs_fallback_mask.any():
                    self.logger.info(
                        f"Found {needs_fallback_mask.sum()} award dates needing fiscal quarter fallback parsing."
                    )
                    parsed_qtr_info = df.loc[
                        needs_fallback_mask, award_date_col_raw
                    ].apply(
                        lambda x: fiscal_quarter_to_date(x)
                        if pd.notna(x)
                        else (None, None)
                    )
                    df.loc[needs_fallback_mask, "award_date_final"] = (
                        parsed_qtr_info.apply(lambda x: x[0])
                    )
                    df.loc[needs_fallback_mask, "award_fiscal_year_final"] = (
                        parsed_qtr_info.apply(lambda x: x[1])
                    )

                # Final conversion to date object and Int64 for year
                df["award_date_final"] = pd.to_datetime(
                    df["award_date_final"], errors="coerce"
                ).dt.date
                df["award_fiscal_year_final"] = df["award_fiscal_year_final"].astype(
                    "Int64"
                )  # Handles NaN -> <NA>
                self.logger.debug(
                    "Processed 'award_date_final' and 'award_fiscal_year_final' with fallback logic."
                )
            else:
                df["award_date_final"] = None
                df["award_fiscal_year_final"] = pd.NA
                self.logger.warning(
                    f"'{award_date_col_raw}' not found. Award date fields initialized to None/NA."
                )

            # Contact Selection Logic - prioritize requirement POC over small business POC
            req_poc_name = "doj_req_poc_name"
            req_poc_email = "doj_req_poc_email"
            sb_poc_name = "doj_sb_poc_name"
            sb_poc_email = "doj_sb_poc_email"

            # Initialize primary contact fields
            df["primary_contact_name"] = None
            df["primary_contact_email"] = None

            # Prioritize requirement POC
            if req_poc_name in df.columns and req_poc_email in df.columns:
                df["primary_contact_name"] = df[req_poc_name].fillna("")
                df["primary_contact_email"] = df[req_poc_email].fillna("")

                # Fall back to small business POC where requirement POC is missing
                if sb_poc_name in df.columns and sb_poc_email in df.columns:
                    df["primary_contact_name"] = df["primary_contact_name"].where(
                        df["primary_contact_name"] != "", df[sb_poc_name].fillna("")
                    )
                    df["primary_contact_email"] = df["primary_contact_email"].where(
                        df["primary_contact_email"] != "", df[sb_poc_email].fillna("")
                    )

                # Clean up empty values
                df["primary_contact_name"] = df["primary_contact_name"].replace(
                    "", None
                )
                df["primary_contact_email"] = df["primary_contact_email"].replace(
                    "", None
                )
                self.logger.debug(
                    "Selected primary contacts from DOJ requirement POC with small business POC fallback."
                )

            # Default country now handled via transform_params
            # Handle alternate column name for country if needed
            if "Country" in df.columns and "place_country_raw" not in df.columns:
                df["place_country"] = df["Country"]

            # Parse place_raw to extract city and state if available
            if "place_raw" in df.columns:
                # DOJ typically has format like "Quantico, VA" or just city name
                df[["place_city", "place_state"]] = df["place_raw"].str.extract(
                    r"^([^,]+)(?:,\s*([A-Z]{2}))?$", expand=True
                )
                df["place_city"] = df["place_city"].str.strip()
                df["place_state"] = df["place_state"].str.strip()
                self.logger.debug("Parsed place_raw into city and state.")

        except Exception as e:
            self.logger.warning(f"Error in _custom_doj_transforms: {e}")

        return df


    async def doj_setup(self) -> bool:
        """DOJ-specific setup: navigate to URL and wait for DOM to load."""
        if not self.base_url:
            self.logger.error("Base URL not configured.")
            return False

        self.logger.info(f"DOJ setup: Navigating to {self.base_url}")

        success = await self.navigate_to_url(self.base_url)
        if not success:
            return False

        # Ensure basic page structure is ready
        await self.wait_for_load_state("domcontentloaded")
        return True

    async def doj_extract(self) -> str | None:
        """DOJ-specific extraction: wait for download link and click to download.
        Preserves original DOJ download behavior.
        """
        self.logger.info(
            f"Starting DOJ Excel document download. Waiting for link: {self.config.export_button_selector}"
        )

        # Wait for the download link to be visible
        await self.wait_for_selector(
            self.config.export_button_selector,
            timeout=self.config.interaction_timeout_ms,
            state="visible",
        )
        self.logger.info("Download link is visible.")

        # Download via click with fallback
        return await self.download_with_fallback(
            selector=self.config.export_button_selector
        )

    async def scrape(self) -> int:
        """Execute the complete DOJ scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.doj_setup,
            extract_method=self.doj_extract,
            # Uses standard_process by default
        )
