"""
Acquisition Gateway scraper using the consolidated architecture.
This replaces the original acquisition_gateway.py with simplified, unified approach.
"""
import pandas as pd

from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.scraper_configs import get_scraper_config
from app.config import active_config
from app.utils.logger import logger


class AcquisitionGatewayScraper(ConsolidatedScraperBase):
    """
    Consolidated Acquisition Gateway scraper.
    Preserves all original functionality while using unified architecture.
    """

    def __init__(self):
        config = get_scraper_config("acquisition_gateway")
        config.base_url = active_config.ACQUISITION_GATEWAY_URL
        super().__init__(config)

    def custom_summary_fallback(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Custom transformation: Handle Description/Body column fallback and create extras JSON.
        Uses Description as primary, falls back to Body if Description is empty.
        Also collects acquisition gateway-specific fields into extras JSON.
        """
        try:
            # Handle Description/Body fallback robustly (pre- and post-rename cases)
            # Case 1: Pre-rename headers
            if "Description" in df.columns and "Body" in df.columns:
                mask = df["Description"].isna() | (df["Description"].astype(str).str.strip() == "")
                df.loc[mask, "Description"] = df.loc[mask, "Body"]
                self.logger.debug("Applied Body fallback for missing descriptions (pre-rename)")
            
            # Case 2: Post-rename 'description' + still-present 'Body'
            if "description" in df.columns and "Body" in df.columns:
                mask = df["description"].isna() | (df["description"].astype(str).str.strip() == "")
                df.loc[mask, "description"] = df.loc[mask, "Body"]
                self.logger.debug("Applied Body fallback for missing descriptions (post-rename)")

            # Create extras JSON with acquisition gateway-specific fields
            extras_fields = {
                "Node_ID": "node_id",
                # Preserve full body separately for traceability
                "Body": "body",
                "Organization": "organization",
                "Requirement Status": "requirement_status",
                "Basic Exercised Value": "basic_exercised_value",
                "Basic Exercised Options": "basic_exercised_options",
                "Acquisition Phase": "acquisition_phase",
                "Delivery Order Value": "delivery_order_value",
                "Current Fiscal Year Projected Obligation": "current_fy_projected_obligation",
                "Funding Source": "funding_source",
                "Estimated Award FY-QTR": "estimated_award_fy_qtr",
                "Solicitation Link": "solicitation_link",
                "Period of Performance": "period_of_performance",
                "Procurement Method": "procurement_method",
                "Extent Competed": "extent_competed",
                "Additional Information": "additional_information",
                "Contractor Name": "contractor_name",
                "Type of Awardee": "type_of_awardee",
                "Award Type": "award_type",
                "Region": "region",
                "Awarded Contract Order": "awarded_contract_order",
                "Content: Point of Contact (Name) For": "poc_name",
                "Point of Contact (Email)": "poc_email",
                "Current Completion Date": "current_completion_date",
                "Content: Small Business Specialist Info (Email)": "sbs_email",
                "Content: Small Business Specialist Info (Name)": "sbs_name",
                "Content: Small Business Specialist Info (Phone)": "sbs_phone",
                "CreatedDate": "created_date",
                "ChangedDate": "changed_date",
                "Published": "published",
            }

            # Create extras JSON column
            extras_data = []
            for _, row in df.iterrows():
                extras = {}
                for original_col, extra_key in extras_fields.items():
                    if original_col in df.columns:
                        value = row[original_col]
                        if pd.notna(value) and value != "":
                            extras[extra_key] = str(value)
                extras_data.append(extras if extras else {})

            # Add the extras JSON column (as dict, not JSON string)
            df["extras_json"] = extras_data

            self.logger.debug(f"Created extras JSON for {len(extras_data)} rows")

        except Exception as e:
            self.logger.warning(f"Error in custom_summary_fallback: {e}")

        return df

    async def scrape(self) -> int:
        """
        Execute the complete scraping workflow.
        Uses the standard pattern but can be customized if needed.
        """
        return await self.scrape_with_structure()


# Testing function
async def test_acquisition_gateway_scraper():
    """Test the consolidated scraper implementation."""
    scraper = AcquisitionGatewayScraper()

    try:
        logger.info("Testing Acquisition Gateway consolidated scraper...")

        # Test configuration
        assert scraper.source_name == "Acquisition Gateway"
        assert scraper.config.debug_mode == True  # Should be non-headless
        assert scraper.config.download_timeout_ms == 90000  # 90 seconds as requested
        assert scraper.config.export_button_selector == "button#export-0"

        # Test custom transform function
        test_df = pd.DataFrame(
            {
                "Description": ["Valid desc", None, ""],
                "Body": ["Body 1", "Body 2", "Body 3"],
                "Node_ID": ["123", "456", "789"],
                "Organization": ["GSA", "DOD", "VA"],
            }
        )

        transformed_df = scraper.custom_summary_fallback(test_df)

        # Verify fallback behavior
        assert transformed_df.loc[1, "Description"] == "Body 2"  # Filled from Body
        assert transformed_df.loc[2, "Description"] == "Body 3"  # Filled from Body
        assert transformed_df.loc[0, "Description"] == "Valid desc"  # Unchanged
        assert "Body" in transformed_df.columns  # Body column retained
        assert "extras_json" in transformed_df.columns  # Extras JSON column created

        # Verify extras dict contains expected data
        extras_0 = transformed_df.loc[0, "extras_json"]
        assert extras_0["node_id"] == "123"
        assert extras_0["body"] == "Body 1"
        assert extras_0["organization"] == "GSA"

        logger.info("✓ Acquisition Gateway consolidated scraper test passed")
        return True

    except Exception as e:
        logger.error(f"✗ Acquisition Gateway consolidated scraper test failed: {e}")
        return False


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_acquisition_gateway_scraper())
