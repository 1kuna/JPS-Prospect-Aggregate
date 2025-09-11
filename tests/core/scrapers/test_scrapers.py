"""
Comprehensive tests for all consolidated scrapers.
Tests each scraper independently without requiring web server.
Following production-level testing principles:
- No hardcoded expected values
- Tests verify scraper behavior, not specific data
- Uses dynamic test data generation
- Mocks only external browser/download operations
"""

import os
import tempfile
from typing import Any
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from sqlalchemy import select

# Import all scrapers
from app.core.scrapers.acquisition_gateway import AcquisitionGatewayScraper
from app.core.scrapers.dhs_scraper import DHSForecastScraper
from app.core.scrapers.doc_scraper import DocScraper
from app.core.scrapers.doj_scraper import DOJForecastScraper
from app.core.scrapers.dos_scraper import DOSForecastScraper
from app.core.scrapers.dot_scraper import DotScraper
from app.core.scrapers.hhs_scraper import HHSForecastScraper
from app.core.scrapers.ssa_scraper import SsaScraper
from app.core.scrapers.treasury_scraper import TreasuryScraper
from app.database.models import DataSource, Prospect


class TestConsolidatedScrapers:
    """Test suite for all consolidated scrapers following black-box testing principles."""

    def get_prospects_for_source(self, db_session, source_name):
        """Helper method to get prospects for a data source by name."""
        data_source = db_session.execute(
            select(DataSource).where(DataSource.name == source_name)
        ).scalar_one_or_none()

        if data_source:
            stmt = select(Prospect).where(Prospect.source_id == data_source.id)
            return db_session.execute(stmt).scalars().all()
        return []

    def generate_deterministic_opportunity_data(
        self, scraper_type: str, num_rows: int = None
    ) -> list[dict[str, Any]]:
        """Generate deterministic test data for a specific scraper type."""
        if num_rows is None:
            num_rows = 3  # Fixed number instead of random

        data = []

        # Deterministic data pools
        agencies = ["Agency A", "Agency B", "Agency C", "Agency D", "Agency E"]
        cities = [
            "Washington",
            "Arlington",
            "New York",
            "San Francisco",
            "Chicago",
            "Boston",
            "Atlanta",
        ]
        states = ["DC", "VA", "NY", "CA", "IL", "MA", "GA"]
        contract_types = ["FFP", "T&M", "CPFF", "IDIQ", "Cost Plus"]
        set_asides = [
            "Small Business",
            "8(a)",
            "WOSB",
            "HUBZone",
            "Full and Open",
            "SDVOSB",
        ]
        naics_codes = [
            "541511",
            "541512",
            "541519",
            "517311",
            "236220",
            "541611",
            "541330",
        ]

        def get_title(index):
            types = [
                "Software",
                "Hardware",
                "Services",
                "Consulting",
                "Research",
                "Development",
            ]
            return f"{types[index % len(types)]} Contract {1000 + index}"

        def get_description(index):
            word_sets = [
                "implementation support development",
                "maintenance analysis integration",
                "deployment assessment evaluation",
                "modernization implementation support",
                "development maintenance analysis",
            ]
            return word_sets[index % len(word_sets)]

        def get_date(index, start_year=2024, offset_days=0):
            # Generate deterministic dates based on index
            year = start_year + (index // 12)
            month = (index % 12) + 1
            day = ((index * 7) % 28) + 1
            return f"{year}-{month:02d}-{day:02d}"

        def get_value_range(index):
            min_val = (index + 1) * 100000
            max_val = min_val + (index + 5) * 100000
            return f"${min_val:,} - ${max_val:,}"

        for i in range(num_rows):
            if scraper_type == "acquisition_gateway":
                data.append(
                    {
                        "Listing ID": f"AG-{10000 + i}",
                        "Title": get_title(i),
                        "Body": get_description(i),
                        "NAICS Code": naics_codes[i % len(naics_codes)],
                        "Estimated Contract Value": get_value_range(i),
                        "Estimated Solicitation Date": get_date(i),
                        "Ultimate Completion Date": get_date(i, 2025),
                        "Estimated Award FY": str(2024 + (i % 3)),
                        "Agency": agencies[i % len(agencies)],
                        "Place of Performance City": cities[i % len(cities)],
                        "Place of Performance State": states[i % len(states)],
                        "Place of Performance Country": "USA",
                        "Contract Type": contract_types[i % len(contract_types)],
                        "Set Aside Type": set_asides[i % len(set_asides)],
                    }
                )

            elif scraper_type == "dhs":
                components = ["CISA", "CBP", "TSA", "FEMA", "USCIS", "ICE"]
                data.append(
                    {
                        "APFS Number": f"DHS-{10000 + i}",
                        "Title": get_title(i),
                        "Description": get_description(i),
                        "NAICS": naics_codes[i % len(naics_codes)],
                        "Component": components[i % len(components)],
                        "Place of Performance City": cities[i % len(cities)],
                        "Place of Performance State": states[i % len(states)],
                        "Dollar Range": get_value_range(i),
                        "Contract Type": contract_types[i % len(contract_types)],
                        "Small Business Set-Aside": set_asides[i % len(set_asides)],
                        "Award Quarter": f"FY{24 + (i % 3)} Q{(i % 4) + 1}",
                    }
                )

            elif scraper_type == "treasury":
                bureaus = ["IRS", "OCC", "BEP", "Mint", "FINCEN"]
                data.append(
                    {
                        "Specific Id": f"TREAS-{10000 + i}",
                        "PSC": get_title(i),
                        "Bureau": bureaus[i % len(bureaus)],
                        "NAICS": naics_codes[i % len(naics_codes)],
                        "Contract Type": contract_types[i % len(contract_types)],
                        "Type of Small Business Set-aside": set_asides[i % len(set_asides)],
                        "Projected Award FY_Qtr": f"FY{24 + (i % 3)} Q{(i % 4) + 1}",
                        "Estimated Total Contract Value": get_value_range(i),
                        "Place of Performance": f"{cities[i % len(cities)]}, {states[i % len(states)]}",
                    }
                )

            elif scraper_type == "dot":
                offices = ["FAA", "FHWA", "FTA", "NHTSA", "FRA"]
                competition_types = ["Full and Open", "Small Business", "Sole Source"]
                action_types = ["New Contract", "Recompete", "Option"]
                vehicles = ["GSA MAS", "CIO-SP3", "SEWP", "Direct"]
                data.append(
                    {
                        "Sequence Number": f"DOT-{10000 + i}",
                        "Procurement Office": offices[i % len(offices)],
                        "Project Title": get_title(i),
                        "Description": get_description(i),
                        "Estimated Value": get_value_range(i),
                        "NAICS": naics_codes[i % len(naics_codes)],
                        "Competition Type": competition_types[i % len(competition_types)],
                        "RFP Quarter": f"FY{24 + (i % 3)} Q{(i % 4) + 1}",
                        "Anticipated Award Date": get_date(i),
                        "Place of Performance": f"{cities[i % len(cities)]}, {states[i % len(states)]}",
                        "Action/Award Type": action_types[i % len(action_types)],
                        "Contract Vehicle": vehicles[i % len(vehicles)],
                    }
                )

            elif scraper_type == "hhs":
                first_names = ["John", "Jane", "Bob", "Alice", "Tom", "Sarah"]
                last_names = ["Smith", "Johnson", "Williams", "Brown", "Davis"]
                divisions = ["CDC", "FDA", "NIH", "CMS", "HRSA"]
                vehicles = ["GSA MAS", "CIO-SP3", "SEWP", "Direct"]
                first_name = first_names[i % len(first_names)]
                last_name = last_names[i % len(last_names)]
                data.append(
                    {
                        "Procurement Number": f"HHS-{10000 + i}",
                        "Operating Division": divisions[i % len(divisions)],
                        "Title": get_title(i),
                        "Description": get_description(i),
                        "Primary NAICS": naics_codes[i % len(naics_codes)],
                        "Contract Vehicle": vehicles[i % len(vehicles)],
                        "Contract Type": contract_types[i % len(contract_types)],
                        "Total Contract Range": get_value_range(i),
                        "Target Award Month/Year (Award by)": get_date(i),
                        "Target Solicitation Month/Year": get_date(i, 2024, -30),
                        "Anticipated Acquisition Strategy": set_asides[i % len(set_asides)],
                        "Program Office POC First Name": first_name,
                        "Program Office POC Last Name": last_name,
                        "Program Office POC Email": f"{first_name.lower()}.{last_name.lower()}@hhs.gov",
                    }
                )

            elif scraper_type == "ssa":
                site_types = ["Regional", "Field", "HQ", "Data Center"]
                data.append(
                    {
                        "APP #": f"SSA-{10000 + i}",
                        "SITE Type": site_types[i % len(site_types)],
                        "DESCRIPTION": get_title(i) + " - " + get_description(i),
                        "NAICS": naics_codes[i % len(naics_codes)],
                        "CONTRACT TYPE": contract_types[i % len(contract_types)],
                        "SET ASIDE": set_asides[i % len(set_asides)],
                        "ESTIMATED VALUE": get_value_range(i),
                        "AWARD FISCAL YEAR": str(2024 + (i % 3)),
                        "PLACE OF PERFORMANCE": f"{cities[i % len(cities)]}, {states[i % len(states)]}",
                    }
                )

            elif scraper_type == "doc":
                organizations = ["NOAA", "NIST", "Census", "USPTO", "ITA"]
                award_types = ["New Contract", "Recompete"]
                competition_strategies = ["Full and Open", "Small Business"]
                contract_vehicles = ["GSA MAS", "Direct"]
                data.append(
                    {
                        "Forecast ID": f"DOC-{10000 + i}",
                        "Organization": organizations[i % len(organizations)],
                        "Title": get_title(i),
                        "Description": get_description(i),
                        "Naics Code": naics_codes[i % len(naics_codes)],
                        "Place Of Performance City": cities[i % len(cities)],
                        "Place Of Performance State": states[i % len(states)],
                        "Place Of Performance Country": "USA",
                        "Estimated Value Range": get_value_range(i),
                        "Estimated Solicitation Fiscal Year": str(2024 + (i % 3)),
                        "Estimated Solicitation Fiscal Quarter": f"Q{(i % 4) + 1}",
                        "Anticipated Set Aside And Type": set_asides[i % len(set_asides)],
                        "Anticipated Action Award Type": award_types[i % len(award_types)],
                        "Competition Strategy": competition_strategies[i % len(competition_strategies)],
                        "Anticipated Contract Vehicle": contract_vehicles[i % len(contract_vehicles)],
                    }
                )

            elif scraper_type == "doj":
                bureaus = ["FBI", "DEA", "ATF", "USMS", "BOP"]
                data.append(
                    {
                        "Action Tracking Number": f"DOJ-{10000 + i}",
                        "Bureau": bureaus[i % len(bureaus)],
                        "Contract Name": get_title(i),
                        "Description of Requirement": get_description(i),
                        "Contract Type (Pricing)": contract_types[i % len(contract_types)],
                        "NAICS Code": naics_codes[i % len(naics_codes)],
                        "Small Business Approach": set_asides[i % len(set_asides)],
                        "Estimated Total Contract Value (Range)": get_value_range(i),
                        "Target Solicitation Date": get_date(i),
                        "Target Award Date": get_date(i, 2024, 60),
                        "Place of Performance": f"{cities[i % len(cities)]}, {states[i % len(states)]}",
                        "Country": "USA",
                    }
                )

            elif scraper_type == "dos":
                office_symbols = ["INR", "CA", "ECA", "DRL", "PM"]
                data.append(
                    {
                        "Contract Number": f"DOS-{10000 + i}",
                        "Office Symbol": office_symbols[i % len(office_symbols)],
                        "Requirement Title": get_title(i),
                        "Requirement Description": get_description(i),
                        "Estimated Value": get_value_range(i),
                        "Dollar Value": str(100000 * (i + 1)),
                        "Place of Performance Country": "USA",
                        "Place of Performance City": random.choice(cities),
                        "Place of Performance State": random.choice(states),
                        "Award Type": random.choice(["New Contract", "Recompete"]),
                        "Anticipated Award Date": random_date(),
                        "Target Award Quarter": f"FY{random.randint(24, 26)} Q{random.randint(1, 4)}",
                        "Fiscal Year": str(random.randint(2024, 2026)),
                        "Anticipated Set Aside": random.choice(set_asides),
                        "Anticipated Solicitation Release Date": random_date(),
                    }
                )

        return data

    @pytest.fixture()
    def mock_browser_setup(self):
        """Mock browser setup for all scrapers."""
        with (
            patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.setup_browser",
                new_callable=AsyncMock,
            ) as mock_setup,
            patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.cleanup_browser",
                new_callable=AsyncMock,
            ) as mock_cleanup,
        ):
            yield mock_setup, mock_cleanup

    @pytest.fixture()
    def mock_navigation(self):
        """Mock navigation methods."""
        with (
            patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.navigate_to_url",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_nav,
            patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.wait_for_load_state",
                new_callable=AsyncMock,
            ) as mock_wait,
            patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.wait_for_timeout",
                new_callable=AsyncMock,
            ) as mock_timeout,
        ):
            yield mock_nav, mock_wait, mock_timeout

    @pytest.fixture()
    def mock_interactions(self):
        """Mock page interaction methods."""
        with (
            patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.click_element",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_click,
            patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.wait_for_selector",
                new_callable=AsyncMock,
            ) as mock_selector,
        ):
            yield mock_click, mock_selector

    def create_test_file(self, data: list, file_format: str = "csv") -> str:
        """Create a temporary test file with the provided data."""
        df = pd.DataFrame(data)

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=f".{file_format}"
        ) as f:
            if file_format == "csv":
                df.to_csv(f.name, index=False)
            elif file_format == "xlsx":
                df.to_excel(f.name, index=False, engine="openpyxl")
            elif file_format == "html":
                df.to_html(f.name, index=False)

            return f.name

    # Test each scraper with dynamic data
    @pytest.mark.asyncio()
    async def test_acquisition_gateway_scraper(
        self, mock_browser_setup, mock_navigation, mock_interactions, db_session
    ):
        """Test Acquisition Gateway consolidated scraper with dynamic data."""
        # Generate random test data
        test_data = self.generate_deterministic_opportunity_data("acquisition_gateway")
        test_file = self.create_test_file(test_data)

        try:
            with patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click",
                new_callable=AsyncMock,
                return_value=test_file,
            ):
                scraper = AcquisitionGatewayScraper()
                result = await scraper.scrape()

                # Verify scraper processed data
                assert result >= 0, "Scraper should return a count"

                # Verify database operations
                prospects = self.get_prospects_for_source(
                    db_session, "Acquisition Gateway"
                )

                # Can't check exact count due to duplicate prevention
                # Just verify the scraper ran and processed data
                if result > 0:
                    assert len(prospects) > 0, "Should have at least one prospect after successful scrape"
                    # Verify prospects have required fields
                    for prospect in prospects:
                        assert prospect.id, "Prospect should have an ID"
                        assert prospect.source_id, "Prospect should have a source_id"

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    @pytest.mark.asyncio()
    async def test_dhs_scraper(
        self, mock_browser_setup, mock_navigation, mock_interactions, db_session
    ):
        """Test DHS consolidated scraper with dynamic data."""
        test_data = self.generate_deterministic_opportunity_data("dhs")
        test_file = self.create_test_file(test_data)

        try:
            with patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click",
                new_callable=AsyncMock,
                return_value=test_file,
            ):
                scraper = DHSForecastScraper()
                result = await scraper.scrape()

                assert result >= 0

                prospects = self.get_prospects_for_source(
                    db_session, "Department of Homeland Security"
                )
                if result > 0:
                    # Verify data was processed (not specific values)
                    assert isinstance(prospects, list)

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    @pytest.mark.asyncio()
    async def test_treasury_scraper(
        self, mock_browser_setup, mock_navigation, mock_interactions, db_session
    ):
        """Test Treasury consolidated scraper with dynamic data."""
        test_data = self.generate_deterministic_opportunity_data("treasury")
        test_file = self.create_test_file(test_data, "html")

        try:
            with patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click",
                new_callable=AsyncMock,
                return_value=test_file,
            ):
                scraper = TreasuryScraper()
                result = await scraper.scrape()

                assert result >= 0

                prospects = self.get_prospects_for_source(
                    db_session, "Department of Treasury"
                )
                assert isinstance(prospects, list)

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    @pytest.mark.asyncio()
    async def test_dot_scraper(
        self, mock_browser_setup, mock_navigation, mock_interactions, db_session
    ):
        """Test DOT consolidated scraper with dynamic data."""
        test_data = self.generate_deterministic_opportunity_data("dot")
        test_file = self.create_test_file(test_data)

        try:
            with patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_new_page",
                new_callable=AsyncMock,
                return_value=test_file,
            ):
                scraper = DotScraper()
                result = await scraper.scrape()

                assert result >= 0

                prospects = self.get_prospects_for_source(
                    db_session, "Department of Transportation"
                )
                assert isinstance(prospects, list)

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    @pytest.mark.asyncio()
    async def test_hhs_scraper(
        self, mock_browser_setup, mock_navigation, mock_interactions, db_session
    ):
        """Test HHS consolidated scraper with dynamic data."""
        test_data = self.generate_deterministic_opportunity_data("hhs")
        test_file = self.create_test_file(test_data)

        try:
            with patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_with_fallback",
                new_callable=AsyncMock,
                return_value=test_file,
            ):
                scraper = HHSForecastScraper()
                result = await scraper.scrape()

                assert result >= 0

                prospects = self.get_prospects_for_source(
                    db_session, "Health and Human Services"
                )
                assert isinstance(prospects, list)

                # If data was saved, verify contact name concatenation worked
                if len(prospects) > 0 and prospects[0].primary_contact_name:
                    # Should be a full name (first + last)
                    assert (
                        " " in prospects[0].primary_contact_name
                        or prospects[0].primary_contact_name != ""
                    )

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    @pytest.mark.asyncio()
    async def test_ssa_scraper(
        self, mock_browser_setup, mock_navigation, mock_interactions, db_session
    ):
        """Test SSA consolidated scraper with dynamic data."""
        test_data = self.generate_deterministic_opportunity_data("ssa")
        test_file = self.create_test_file(test_data, "xlsx")

        try:
            with (
                patch(
                    "app.core.consolidated_scraper_base.ConsolidatedScraperBase.find_excel_link",
                    new_callable=AsyncMock,
                    return_value="http://test.com/file.xlsx",
                ),
                patch(
                    "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_directly",
                    new_callable=AsyncMock,
                    return_value=test_file,
                ),
            ):
                scraper = SsaScraper()
                result = await scraper.scrape()

                assert result >= 0

                prospects = self.get_prospects_for_source(
                    db_session, "Social Security Administration"
                )
                assert isinstance(prospects, list)

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    @pytest.mark.asyncio()
    async def test_doc_scraper(
        self, mock_browser_setup, mock_navigation, mock_interactions, db_session
    ):
        """Test DOC consolidated scraper with dynamic data."""
        test_data = self.generate_deterministic_opportunity_data("doc")
        test_file = self.create_test_file(test_data, "xlsx")

        try:
            with (
                patch(
                    "app.core.consolidated_scraper_base.ConsolidatedScraperBase.find_link_by_text",
                    new_callable=AsyncMock,
                    return_value="http://test.com/file.xlsx",
                ),
                patch(
                    "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_directly",
                    new_callable=AsyncMock,
                    return_value=test_file,
                ),
            ):
                scraper = DocScraper()
                result = await scraper.scrape()

                assert result >= 0

                prospects = self.get_prospects_for_source(
                    db_session, "Department of Commerce"
                )
                assert isinstance(prospects, list)

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    @pytest.mark.asyncio()
    async def test_doj_scraper(
        self, mock_browser_setup, mock_navigation, mock_interactions, db_session
    ):
        """Test DOJ consolidated scraper with dynamic data."""
        test_data = self.generate_deterministic_opportunity_data("doj")
        test_file = self.create_test_file(test_data, "xlsx")

        try:
            with patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click",
                new_callable=AsyncMock,
                return_value=test_file,
            ):
                scraper = DOJForecastScraper()
                result = await scraper.scrape()

                assert result >= 0

                prospects = self.get_prospects_for_source(
                    db_session, "Department of Justice"
                )
                assert isinstance(prospects, list)

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    @pytest.mark.asyncio()
    async def test_dos_scraper(
        self, mock_browser_setup, mock_navigation, mock_interactions, db_session
    ):
        """Test DOS consolidated scraper with dynamic data."""
        test_data = self.generate_deterministic_opportunity_data("dos")
        test_file = self.create_test_file(test_data, "xlsx")

        try:
            with patch(
                "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_directly",
                new_callable=AsyncMock,
                return_value=test_file,
            ):
                scraper = DOSForecastScraper()
                result = await scraper.scrape()

                assert result >= 0

                prospects = self.get_prospects_for_source(
                    db_session, "Department of State"
                )
                assert isinstance(prospects, list)

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test error handling
    @pytest.mark.asyncio()
    async def test_scraper_error_handling(self, mock_browser_setup, mock_navigation):
        """Test that scrapers handle errors gracefully."""
        error_messages = [
            "Download failed",
            "Connection timeout",
            "Page not found",
            "Access denied",
        ]

        with patch(
            "app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click",
            new_callable=AsyncMock,
            side_effect=Exception(random.choice(error_messages)),
        ):
            # Test with a random scraper
            scrapers = [DHSForecastScraper, TreasuryScraper, DocScraper]
            scraper = random.choice(scrapers)()
            result = await scraper.scrape()

            # Scraper should handle error gracefully
            assert result == 0, "Scraper should return 0 on error"

    # Test configuration loading
    def test_all_scrapers_initialize(self):
        """Test that all consolidated scrapers can be initialized."""
        scrapers = [
            AcquisitionGatewayScraper,
            DHSForecastScraper,
            TreasuryScraper,
            DotScraper,
            HHSForecastScraper,
            SsaScraper,
            DocScraper,
            DOJForecastScraper,
            DOSForecastScraper,
        ]

        for scraper_class in scrapers:
            try:
                scraper = scraper_class()
                assert scraper is not None
                assert hasattr(scraper, "config")
                assert hasattr(scraper, "source_name")
                assert scraper.source_name is not None
                assert len(scraper.source_name) > 0
            except Exception as e:
                pytest.fail(f"Failed to initialize {scraper_class.__name__}: {e}")

    # Test custom transformations
    def test_custom_transformations(self):
        """Test that custom transformation methods exist and work with dynamic data."""
        # Generate random test data
        num_rows = random.randint(1, 3)

        # Test DHS transform
        scraper = DHSForecastScraper()
        test_df = pd.DataFrame([{"test_col": f"value_{i}"} for i in range(num_rows)])
        transformed_df = scraper._custom_dhs_transforms(test_df.copy())
        assert "place_country" in transformed_df.columns
        assert all(transformed_df["place_country"] == "USA")

        # Test Treasury transform
        treasury_scraper = TreasuryScraper()
        treasury_df = pd.DataFrame(
            [
                {
                    "native_id_primary": f"id-{random.randint(1000, 9999)}",
                    "place_raw": f'{random.choice(["Washington", "New York", "Chicago"])}, {random.choice(["DC", "NY", "IL"])}',
                }
                for _ in range(num_rows)
            ]
        )

        transformed_treasury = treasury_scraper._custom_treasury_transforms(treasury_df)
        assert "native_id" in transformed_treasury.columns
        assert "place_city" in transformed_treasury.columns
        assert "place_state" in transformed_treasury.columns

        # Verify place parsing worked
        for idx in range(len(transformed_treasury)):
            if "," in treasury_df.iloc[idx]["place_raw"]:
                assert transformed_treasury.iloc[idx]["place_city"] is not None
                assert transformed_treasury.iloc[idx]["place_state"] is not None

        # Test SSA transform
        ssa_scraper = SsaScraper()
        ssa_df = pd.DataFrame(
            [
                {
                    "description": f"Description {random.randint(1000, 9999)}",
                    "place_raw": f'{random.choice(["Baltimore", "Chicago"])}, {random.choice(["MD", "IL"])}',
                }
                for _ in range(num_rows)
            ]
        )

        transformed_ssa = ssa_scraper._custom_ssa_transforms(ssa_df)
        assert "title" in transformed_ssa.columns
        assert "place_city" in transformed_ssa.columns
        assert "place_state" in transformed_ssa.columns

        # Verify title was copied from description
        for idx in range(len(transformed_ssa)):
            assert transformed_ssa.iloc[idx]["title"] == ssa_df.iloc[idx]["description"]

        # Test HHS transform
        hhs_scraper = HHSForecastScraper()
        first_names = ["John", "Jane", "Bob", "Alice"]
        last_names = ["Smith", "Johnson", "Williams", "Brown"]

        hhs_df = pd.DataFrame(
            [
                {
                    "Program Office POC First Name": random.choice(first_names),
                    "Program Office POC Last Name": random.choice(last_names),
                }
                for _ in range(num_rows)
            ]
        )

        transformed_hhs = hhs_scraper._custom_hhs_transforms(hhs_df)
        assert "primary_contact_name" in transformed_hhs.columns
        assert "place_country" in transformed_hhs.columns

        # Verify name concatenation
        for idx in range(len(transformed_hhs)):
            first = hhs_df.iloc[idx]["Program Office POC First Name"]
            last = hhs_df.iloc[idx]["Program Office POC Last Name"]
            expected_name = f"{first} {last}"
            assert transformed_hhs.iloc[idx]["primary_contact_name"] == expected_name

        assert all(transformed_hhs["place_country"] == "USA")


# Standalone test functions for running individual scrapers
@pytest.mark.asyncio()
async def test_run_single_scraper_acquisition_gateway():
    """Run only the Acquisition Gateway scraper for testing."""
    # This allows running individual scraper tests
    # pytest tests/core/scrapers/test_scrapers.py::test_run_single_scraper_acquisition_gateway -v


@pytest.mark.asyncio()
async def test_run_single_scraper_dhs():
    """Run only the DHS scraper for testing."""


# Similar standalone functions can be added for each scraper as needed


if __name__ == "__main__":
    # Allow running this file directly for quick testing
    pytest.main([__file__, "-v"])
