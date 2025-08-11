"""DHS scraper using the consolidated architecture.
Preserves all original DHS-specific functionality.
"""

import pandas as pd

from app.config import active_config
from app.core.consolidated_scraper_base import ConsolidatedScraperBase
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
            # Default place_country to 'USA' since DHS data doesn't include country
            if "place_country" not in df.columns:
                df["place_country"] = "USA"
                self.logger.debug(
                    "Initialized 'place_country' to 'USA' as DHS data doesn't include country."
                )

            # Combine contact first and last names into primary_contact_name
            first_name_col = "primary_contact_first_name"
            last_name_col = "primary_contact_last_name"
            if first_name_col in df.columns and last_name_col in df.columns:
                df["primary_contact_name"] = (
                    df[first_name_col].fillna("") + " " + df[last_name_col].fillna("")
                )
                df["primary_contact_name"] = df["primary_contact_name"].str.strip()
                # Clean up empty combinations (just spaces)
                df["primary_contact_name"] = df["primary_contact_name"].replace(
                    "", None
                )
                self.logger.debug("Combined DHS primary contact first and last names.")

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

    def _dhs_create_extras(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create extras JSON with DHS-specific fields that aren't in core schema.
        Captures additional data points for comprehensive data retention and metadata.
        """
        try:
            # Define DHS-specific extras fields mapping (using original CSV column names)
            extras_fields = {
                "Contract Number": "contract_number",
                "Contractor": "contractor",
                "Primary Contact First Name": "primary_contact_first_name",
                "Primary Contact Last Name": "primary_contact_last_name",
                "Primary Contact Phone": "primary_contact_phone",
                "Primary Contact Email": "primary_contact_email",
                "Forecast Published": "forecast_published",
                "Forecast Previously Published": "forecast_previously_published",
            }

            # Create extras JSON column
            extras_data = []
            for _, row in df.iterrows():
                extras = {}

                # Add standard extras fields
                for df_col, extra_key in extras_fields.items():
                    if df_col in df.columns:
                        value = row[df_col]
                        if pd.notna(value) and value != "":
                            extras[extra_key] = str(value)

                # Add metadata about award date if it was derived from quarter
                if "award_qtr_raw" in df.columns:
                    award_quarter = row.get("award_qtr_raw")
                    if pd.notna(award_quarter) and str(award_quarter).strip():
                        extras["award_quarter_original"] = str(award_quarter).strip()
                        extras["award_date_is_tentative"] = True
                        extras["award_date_note"] = (
                            "Date derived from fiscal quarter - represents tentative start of quarter"
                        )

                # Preserve original small business program value
                if "small_business_program" in df.columns:
                    sb_program = row.get("small_business_program")
                    if pd.notna(sb_program) and str(sb_program).strip() not in [
                        "",
                        "None",
                        "N/A",
                        "TBD",
                    ]:
                        extras["original_small_business_program"] = str(
                            sb_program
                        ).strip()

                extras_data.append(extras if extras else {})

            # Add the extras JSON column (as dict, not JSON string)
            df["extras_json"] = extras_data

            self.logger.debug(
                f"Created DHS extras JSON for {len(extras_data)} rows with enhanced metadata"
            )

        except Exception as e:
            self.logger.warning(f"Error in _dhs_create_extras: {e}")

        return df

    async def scrape(self) -> int:
        """Execute the complete DHS scraping workflow."""
        return await self.scrape_with_structure()
