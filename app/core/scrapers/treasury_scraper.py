"""Treasury scraper using the consolidated architecture.
Simplified to download XLS files only - no HTML fallbacks.
"""

import os

import pandas as pd

from app.config import active_config
from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.scraper_configs import get_scraper_config


class TreasuryScraper(ConsolidatedScraperBase):
    """Consolidated Treasury scraper.
    Preserves all original functionality including complex native_id handling.
    """

    def __init__(self):
        config = get_scraper_config("treasury")
        config.base_url = active_config.TREASURY_FORECAST_URL
        super().__init__(config)

    def _custom_treasury_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Custom Treasury transformations using original working logic.
        Handles native_id selection from primary/fallback fields and description creation.
        """
        try:
            self.logger.info("Applying Treasury transformations...")

            # Handle native_id selection (from original working config)
            if (
                "native_id_primary" in df.columns
                and df["native_id_primary"].notna().any()
            ):
                df["native_id"] = df["native_id_primary"]
                self.logger.debug("Used 'native_id_primary' as native_id.")
            elif (
                "native_id_fallback1" in df.columns
                and df["native_id_fallback1"].notna().any()
            ):
                df["native_id"] = df["native_id_fallback1"]
                self.logger.info("Used 'native_id_fallback1' as native_id.")
            elif (
                "native_id_fallback2" in df.columns
                and df["native_id_fallback2"].notna().any()
            ):
                df["native_id"] = df["native_id_fallback2"]
                self.logger.info("Used 'native_id_fallback2' as native_id.")
            else:
                df["native_id"] = None
                self.logger.warning(
                    "No primary or fallback native ID column found. 'native_id' set to None."
                )

            # Add row_index for unique ID generation (Treasury data may have duplicates)
            df.reset_index(drop=True, inplace=True)
            df["row_index"] = df.index
            self.logger.debug("Added 'row_index' to DataFrame.")

            # Treasury data doesn't have a clear title field
            # Use "Type of Requirement" as title if available
            if "title" not in df.columns and "Type of Requirement" in df.columns:
                df["title"] = df["Type of Requirement"]
                self.logger.debug(
                    "Used 'Type of Requirement' as title for Treasury data."
                )

            # Create description from title if description doesn't exist
            if "description" not in df.columns:
                if "title" in df.columns:
                    df["description"] = df["title"]
                else:
                    df["description"] = None
                self.logger.debug("Initialized 'description' from title or None.")

            # Handle contact information - Treasury has names but no emails
            # Use Program Office Point of Contact as primary contact name
            if "program_office_contact_name" in df.columns:
                df["primary_contact_name"] = df["program_office_contact_name"]
                self.logger.debug("Set program office contact as primary contact name.")

            # Note: Treasury has no email addresses in the data
            # Bureau contact name will go to extras via _treasury_create_extras

            # Parse place_raw or 'Place of Performance' to extract city and state
            if "place_raw" in df.columns:
                # Treasury typically has format like "Washington, DC" or just city name
                df[["place_city", "place_state"]] = df["place_raw"].str.extract(
                    r"^([^,]+)(?:,\s*([A-Z]{2}))?$", expand=True
                )
                df["place_city"] = df["place_city"].str.strip()
                df["place_state"] = df["place_state"].str.strip()
                df["place_country"] = "USA"  # Default for Treasury data
                self.logger.debug("Parsed place_raw into city, state, and country.")
            elif "Place of Performance" in df.columns:
                df[["place_city", "place_state"]] = df[
                    "Place of Performance"
                ].str.extract(r"^([^,]+)(?:,\s*([A-Z]{2}))?$", expand=True)
                df["place_city"] = df["place_city"].str.strip()
                df["place_state"] = df["place_state"].str.strip()
                df["place_country"] = "USA"
                self.logger.debug(
                    "Parsed 'Place of Performance' into city, state, and country."
                )

        except Exception as e:
            self.logger.warning(f"Error in _custom_treasury_transforms: {e}")

        return df

    def _treasury_create_extras(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create extras JSON with Treasury-specific fields that aren't in core schema.
        Captures additional data points for comprehensive data retention.
        """
        try:
            # Define Treasury-specific extras fields mapping (using original CSV column names)
            extras_fields = {
                "PSC": "product_service_code",  # Product Service Code classification
                "Type of Requirement": "requirement_type",
                "Specific Id": "native_id_primary",
                "ShopCart/req": "native_id_fallback1",
                "Contract Number": "native_id_fallback2",
                "Place of Performance": "place_raw",
                "Projected Award FY_Qtr": "award_qtr_raw",
                "Project Period of Performance Start": "release_date_raw",
            }

            # Create extras JSON column
            extras_data = []
            for _, row in df.iterrows():
                extras = {}
                for df_col, extra_key in extras_fields.items():
                    if df_col in df.columns:
                        value = row[df_col]
                        if pd.notna(value) and value != "":
                            extras[extra_key] = str(value)
                extras_data.append(extras if extras else {})

            # Add the extras JSON column (as dict, not JSON string)
            df["extras_json"] = extras_data

            self.logger.debug(
                f"Created Treasury extras JSON for {len(extras_data)} rows with {len(extras_fields)} potential fields"
            )

        except Exception as e:
            self.logger.warning(f"Error in _treasury_create_extras: {e}")

        return df

    def _is_html_content(self, file_path: str) -> bool:
        """Check if file contains HTML content even with .xls extension."""
        try:
            with open(file_path, encoding="utf-8") as f:
                first_chunk = f.read(100).strip().lower()
                return first_chunk.startswith("<table") or "<html" in first_chunk
        except:
            return False

    def read_file_to_dataframe(self, file_path: str) -> pd.DataFrame | None:
        """Treasury-specific file reading that handles HTML content in .xls files."""
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"File does not exist: {file_path}")
            return None

        self.logger.info(f"Reading Treasury file: {file_path}")

        # Check if it's HTML content disguised as XLS
        if self._is_html_content(file_path):
            self.logger.info("Detected HTML content in .xls file, using HTML parser")
            try:
                # Try different parsers for HTML parsing
                parsers_to_try = ["lxml", "html.parser", "html5lib"]

                for parser in parsers_to_try:
                    try:
                        self.logger.info(f"Trying HTML parser: {parser}")
                        tables = pd.read_html(
                            file_path,
                            header=0,  # First row contains headers
                            encoding="utf-8",
                            flavor=parser if parser != "html.parser" else None,
                        )

                        if tables and len(tables) > 0:
                            df = tables[0]
                            self.logger.info(
                                f"Successfully read HTML table with {parser}: {len(df)} rows and {len(df.columns)} columns"
                            )

                            # If empty, try without header specification
                            if len(df) == 0:
                                self.logger.info(
                                    "Table empty with header=0, trying without header specification"
                                )
                                tables = pd.read_html(
                                    file_path,
                                    encoding="utf-8",
                                    flavor=parser if parser != "html.parser" else None,
                                )
                                if tables and len(tables[0]) > 0:
                                    df = tables[0]
                                    self.logger.info(
                                        f"Successfully read HTML table without header spec: {len(df)} rows and {len(df.columns)} columns"
                                    )

                            if len(df) > 0:
                                return df

                    except Exception as parser_error:
                        self.logger.debug(f"Parser {parser} failed: {parser_error}")
                        continue

                self.logger.warning("All HTML parsers failed")
                return None

            except Exception as e:
                self.logger.warning(f"Failed to read as HTML: {e}")
                # Fall back to Excel parsing

        # Fall back to standard Excel parsing
        self.logger.info("Using standard Excel parser")
        return super().read_file_to_dataframe(file_path)

    async def treasury_setup(self) -> bool:
        """Simple Treasury setup like other working scrapers."""
        if not self.base_url:
            self.logger.error("Base URL not configured.")
            return False

        self.logger.info(f"Treasury setup: Navigating to {self.base_url}")

        success = await self.navigate_to_url(
            self.base_url, wait_until="domcontentloaded"
        )
        if success:
            # Wait for the page to be fully interactive
            await self.wait_for_load_state("domcontentloaded")
            self.logger.info("Page DOM content loaded and interactive.")

            # Additional wait for Lightning components to fully initialize
            self.logger.info(
                "Waiting 5 seconds for Lightning components to fully load..."
            )
            await self.page.wait_for_timeout(5000)
            self.logger.info(
                "Treasury setup completed, page should be ready for interaction."
            )

        return success

    async def treasury_extract(self) -> str | None:
        """Simple Treasury extraction like other working scrapers."""
        self.logger.info("Starting Treasury XLS file download.")

        selector = self.config.export_button_selector

        # Wait for the download button to be visible
        if not await self.wait_for_selector(selector, state="visible"):
            self.logger.error(f"Download button '{selector}' not found or not visible")
            return None

        self.logger.info(f"Download button '{selector}' is visible.")

        # Simple download approach with fallback like other working scrapers
        return await self.download_with_fallback(
            selector=selector,
            js_click_fallback=True,
            wait_after_click=2000,
            timeout=60000,
        )

    def treasury_process(self, file_path: str) -> int:
        """Treasury-specific processing for XLS files only."""
        if not file_path:
            # Try to get most recent download
            file_path = self.get_last_downloaded_path()
            if not file_path:
                self.logger.error("No XLS file available for processing")
                return 0

        # Verify we have an XLS file
        if not file_path.lower().endswith((".xls", ".xlsx")):
            self.logger.error(f"Expected XLS file, got: {file_path}")
            return 0

        self.logger.info(f"Starting Treasury processing for XLS file: {file_path}")

        # Read XLS file
        df = self.read_file_to_dataframe(file_path)
        if df is None or df.empty:
            self.logger.info(
                "DataFrame is empty after reading XLS. Nothing to process."
            )
            return 0

        # Initial cleanup
        df = df.dropna(how="all")
        if df.empty:
            self.logger.info(
                "DataFrame is empty after initial dropna. Nothing to process."
            )
            return 0

        # Apply transformations
        df = self.transform_dataframe(df)
        if df.empty:
            self.logger.info(
                "DataFrame is empty after transformations. Nothing to load."
            )
            return 0

        # Load to database
        return self.prepare_and_load_data(df)

    async def scrape(self) -> int:
        """Execute the complete Treasury scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.treasury_setup,
            extract_method=self.treasury_extract,
            process_method=self.treasury_process,
        )
