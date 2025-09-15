"""Treasury scraper using the consolidated architecture.
Simplified to download XLS files only - no HTML fallbacks.
"""

import os

import pandas as pd

from app.config import active_config
from app.core.scraper_base import ConsolidatedScraperBase
from app.core.scraper_configs import get_scraper_config
from html.parser import HTMLParser


class _SimpleHTMLTableParser(HTMLParser):
    """Very lightweight HTML table parser that extracts the first table into rows.

    This avoids external dependencies (bs4/html5lib/lxml) so we always have a
    last-resort parser available for Treasury's HTML-in-XLS files.
    """

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.table_depth = 0
        self.in_row = False
        self.in_cell = False
        self.is_header_cell = False
        self.current_cell = []
        self.current_row = []
        self.rows: list[list[str]] = []
        self.has_header = False
        self.done = False

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        tag = tag.lower()
        if tag == "table":
            if not self.in_table:
                self.in_table = True
            self.table_depth += 1
        elif self.in_table:
            if tag == "tr":
                self.in_row = True
                self.current_row = []
            elif tag in ("td", "th"):
                self.in_cell = True
                self.is_header_cell = tag == "th"
                self.current_cell = []

    def handle_endtag(self, tag):
        if self.done:
            return
        tag = tag.lower()
        if tag == "table" and self.in_table:
            self.table_depth -= 1
            if self.table_depth == 0:
                self.in_table = False
                # Stop after first table
                self.done = True
        elif self.in_table:
            if tag == "tr" and self.in_row:
                # finalize row
                self.rows.append(self.current_row)
                self.in_row = False
            elif tag in ("td", "th") and self.in_cell:
                # finalize cell
                text = "".join(self.current_cell).strip()
                self.current_row.append(text)
                if self.is_header_cell and not self.rows:
                    self.has_header = True
                self.in_cell = False
                self.is_header_cell = False

    def handle_data(self, data):
        if self.in_cell and not self.done:
            self.current_cell.append(data)

    def to_dataframe(self) -> pd.DataFrame | None:
        if not self.rows:
            return None
        # Determine header
        if self.has_header and self.rows:
            headers = self.rows[0]
            data_rows = self.rows[1:]
        else:
            headers = [f"col_{i+1}" for i in range(max(len(r) for r in self.rows))]
            data_rows = self.rows

        # Normalize row lengths
        max_len = len(headers)
        normalized = [r + [None] * (max_len - len(r)) for r in data_rows]
        try:
            return pd.DataFrame(normalized, columns=headers)
        except Exception:
            return None


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

            # Row index is now added via transform_params

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

            # Place parsing and country default now handled via transform_params
            # Handle alternate column name for place if needed
            if "Place of Performance" in df.columns and "place_raw" not in df.columns:
                df["place_raw"] = df["Place of Performance"]

        except Exception as e:
            self.logger.warning(f"Error in _custom_treasury_transforms: {e}")

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

        # Verify we have an XLS file (moved from treasury_process)
        if not file_path.lower().endswith((".xls", ".xlsx")):
            self.logger.error(f"Expected XLS file, got: {file_path}")
            return None

        self.logger.info(f"Reading Treasury file: {file_path}")

        # Check if it's HTML content disguised as XLS
        if self._is_html_content(file_path):
            self.logger.info("Detected HTML content in .xls file, using HTML parser")
            try:
                # Prefer bs4 flavor (works with beautifulsoup4 + html5lib), then lxml if available
                flavors_to_try = ["bs4", "lxml"]

                for flavor in flavors_to_try:
                    try:
                        self.logger.info(f"Trying HTML flavor: {flavor}")
                        tables = pd.read_html(
                            file_path,
                            header=0,  # First row contains headers
                            encoding="utf-8",
                            flavor=flavor,
                        )

                        if tables and len(tables) > 0:
                            df = tables[0]
                            self.logger.info(
                                f"Successfully read HTML table with {flavor}: {len(df)} rows and {len(df.columns)} columns"
                            )

                            # If empty, try without header specification
                            if len(df) == 0:
                                self.logger.info(
                                    "Table empty with header=0, trying without header specification"
                                )
                                tables = pd.read_html(
                                    file_path,
                                    encoding="utf-8",
                                    flavor=flavor,
                                )
                                if tables and len(tables[0]) > 0:
                                    df = tables[0]
                                    self.logger.info(
                                        f"Successfully read HTML table without header spec: {len(df)} rows and {len(df.columns)} columns"
                                    )

                            if len(df) > 0:
                                return df

                    except ImportError as dep_err:
                        # Missing optional dependency for this flavor; try next
                        self.logger.debug(f"Flavor {flavor} unavailable: {dep_err}")
                        continue
                    except Exception as parser_error:
                        self.logger.debug(f"Flavor {flavor} failed: {parser_error}")
                        continue

                # Last-resort fallback: parse first HTML table without external deps
                try:
                    self.logger.info("Falling back to built-in HTML table parser (no external deps)")
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        html = f.read()
                    parser = _SimpleHTMLTableParser()
                    parser.feed(html)
                    df = parser.to_dataframe()
                    if df is not None and not df.empty:
                        self.logger.info(
                            f"Parsed HTML table via built-in parser: {len(df)} rows, {len(df.columns)} columns"
                        )
                        return df
                    else:
                        self.logger.warning("Built-in HTML parser found no data")
                        return None
                except Exception as e:
                    self.logger.warning(f"Built-in HTML parser fallback failed: {e}")
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

    async def scrape(self) -> int:
        """Execute the complete Treasury scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.treasury_setup,
            extract_method=self.treasury_extract,
            # Uses standard_process by default
        )
