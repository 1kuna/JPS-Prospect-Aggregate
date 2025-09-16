"""DHS scraper using the consolidated architecture.
Preserves all original DHS-specific functionality.
"""

import pandas as pd

from app.config import active_config
from app.core.scraper_base import ConsolidatedScraperBase
from app.core.scraper_configs import get_scraper_config


class DHSForecastScraper(ConsolidatedScraperBase):
    """Consolidated DHS Opportunity Forecast scraper.
    Preserves all original functionality while using unified architecture.
    """

    def __init__(self):
        config = get_scraper_config("dhs")
        config.base_url = active_config.DHS_FORECAST_URL
        super().__init__(config)

    def _custom_dhs_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Custom DHS transformations: set place_country to 'USA', combine contact names,
        and consolidate set-aside and small business program fields.
        """
        try:
            # Default country now handled via transform_params

            # Name combining now handled via transform_params

            # Consolidate set_aside and small_business_program fields
            if "set_aside" in df.columns and "small_business_program" in df.columns:
                df["consolidated_set_aside"] = df.apply(
                    self._consolidate_set_aside_fields, axis=1
                )
                # Replace the original set_aside column with the consolidated value
                df["set_aside"] = df["consolidated_set_aside"]
                # Drop the temporary column
                df.drop("consolidated_set_aside", axis=1, inplace=True, errors="ignore")
                self.logger.debug(
                    "Consolidated DHS set-aside and small business program fields."
                )

        except Exception as e:
            self.logger.warning(f"Error in _custom_dhs_transforms: {e}")

        return df

    def _consolidate_set_aside_fields(self, row) -> str:
        """Consolidate set_aside and small_business_program into a single meaningful value.
        Prioritizes small_business_program when it contains specific program information.
        """
        set_aside = str(row.get("set_aside", "")).strip()
        small_business_program = str(row.get("small_business_program", "")).strip()

        # Define values that should be treated as empty/meaningless
        empty_values = {"", "None", "N/A", "TBD", "nan", "NaN"}

        # Normalize empty values
        if set_aside in empty_values:
            set_aside = ""
        if small_business_program in empty_values:
            small_business_program = ""

        # If we have a specific small business program, prioritize it
        if small_business_program:
            # If we also have meaningful set-aside info, combine them
            if set_aside and set_aside.lower() not in ["full", "partial", "sb"]:
                return f"{set_aside} - {small_business_program}"
            # For generic set-aside values or when set_aside is empty, just use the program
            return small_business_program

        # If only set_aside has meaningful value, use it
        if set_aside:
            return set_aside

        # If both are empty, return None
        return None

    async def scrape(self) -> int:
        """Execute the complete DHS scraping workflow."""
        return await self.scrape_with_structure()
