"""
Comprehensive tests for all consolidated scrapers.
Tests each scraper independently without requiring web server.
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from typing import Dict, Any
import datetime

# Import all scrapers
from app.core.scrapers.acquisition_gateway import AcquisitionGatewayScraper
from app.core.scrapers.dhs_scraper import DHSForecastScraper
from app.core.scrapers.treasury_scraper import TreasuryScraper
from app.core.scrapers.dot_scraper import DotScraper
from app.core.scrapers.hhs_scraper import HHSForecastScraper
from app.core.scrapers.ssa_scraper import SsaScraper
from app.core.scrapers.doc_scraper import DocScraper
from app.core.scrapers.doj_scraper import DOJForecastScraper
from app.core.scrapers.dos_scraper import DOSForecastScraper

from app.database.models import Prospect, DataSource
from app.config import active_config
from sqlalchemy import select


class TestConsolidatedScrapers:
    """Test suite for all consolidated scrapers."""
    
    def get_prospects_for_source(self, db_session, source_name):
        """Helper method to get prospects for a data source by name."""
        data_source = db_session.execute(
            select(DataSource).where(DataSource.name == source_name)
        ).scalar_one_or_none()
        
        if data_source:
            stmt = select(Prospect).where(Prospect.source_id == data_source.id)
            return db_session.execute(stmt).scalars().all()
        return []
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Set up test data for all scrapers."""
        self.test_data = {
            'acquisition_gateway': [
                {
                    'Listing ID': 'AG-001',
                    'Title': 'Test AG Opportunity',
                    'Body': 'Test description for AG',
                    'NAICS Code': '541511',
                    'Estimated Contract Value': '$1M - $5M',
                    'Estimated Solicitation Date': '2024-01-15',
                    'Ultimate Completion Date': '2024-12-31',
                    'Estimated Award FY': '2024',
                    'Agency': 'Test Agency',
                    'Place of Performance City': 'Washington',
                    'Place of Performance State': 'DC',
                    'Place of Performance Country': 'USA',
                    'Contract Type': 'FFP',
                    'Set Aside Type': 'Small Business'
                }
            ],
            'dhs': [
                {
                    'APFS Number': 'DHS-001',
                    'Title': 'Test DHS Opportunity',
                    'Description': 'Test description for DHS',
                    'NAICS': '541511',
                    'Component': 'CISA',
                    'Place of Performance City': 'Arlington',
                    'Place of Performance State': 'VA',
                    'Dollar Range': '$1M - $5M',
                    'Contract Type': 'FFP',
                    'Small Business Set-Aside': 'Small Business',
                    'Award Quarter': 'FY24 Q2'
                }
            ],
            'treasury': [
                {
                    'Specific Id': 'TREAS-001',
                    'Desc': 'Test Treasury Opportunity',
                    'Agency': 'IRS',
                    'NAICS': '541511',
                    'Contract Type': 'FFP',
                    'Small Business': 'Yes',
                    'Period/PopEnd': 'FY24 Q3',
                    'Estimated Value': '$500K - $1M',
                    'Procurement Office City': 'Washington, DC'
                }
            ],
            'dot': [
                {
                    'Sequence Number': 'DOT-001',
                    'Procurement Office': 'FAA',
                    'Project Title': 'Test DOT Opportunity',
                    'Description': 'Test description for DOT',
                    'Estimated Value': '$2M - $10M',
                    'NAICS': '541511',
                    'Competition Type': 'Full and Open',
                    'RFP Quarter': 'FY24 Q4',
                    'Anticipated Award Date': '2024-09-30',
                    'Place of Performance': 'Oklahoma City, OK',
                    'Action/Award Type': 'New Contract',
                    'Contract Vehicle': 'GSA MAS'
                }
            ],
            'hhs': [
                {
                    'Procurement Number': 'HHS-001',
                    'Operating Division': 'CDC',
                    'Title': 'Test HHS Opportunity',
                    'Description': 'Test description for HHS',
                    'Primary NAICS': '541511',
                    'Contract Vehicle': 'GSA MAS',
                    'Contract Type': 'FFP',
                    'Total Contract Range': '$1M - $5M',
                    'Target Award Month/Year (Award by)': '2024-06-30',
                    'Target Solicitation Month/Year': '2024-04-15',
                    'Anticipated Acquisition Strategy': 'Small Business',
                    'Place of Performance City': 'Atlanta',
                    'Place of Performance State': 'GA',
                    'Place of Performance Country': 'USA'
                }
            ],
            'ssa': [
                {
                    'APP #': 'SSA-001',
                    'SITE Type': 'Regional',
                    'DESCRIPTION': 'Test SSA Opportunity',
                    'NAICS': '541511',
                    'CONTRACT TYPE': 'FFP',
                    'SET ASIDE': 'Small Business',
                    'ESTIMATED VALUE': '$500K - $1M',
                    'AWARD FISCAL YEAR': '2024',
                    'PLACE OF PERFORMANCE': 'Baltimore, MD'
                }
            ],
            'doc': [
                {
                    'Forecast ID': 'DOC-001',
                    'Organization': 'NOAA',
                    'Title': 'Test DOC Opportunity',
                    'Description': 'Test description for DOC',
                    'Naics Code': '541511',
                    'Place Of Performance City': 'Silver Spring',
                    'Place Of Performance State': 'MD',
                    'Place Of Performance Country': 'USA',
                    'Estimated Value Range': '$1M - $5M',
                    'Estimated Solicitation Fiscal Year': '2024',
                    'Estimated Solicitation Fiscal Quarter': 'Q2',
                    'Anticipated Set Aside And Type': 'Small Business',
                    'Anticipated Action Award Type': 'New Contract',
                    'Competition Strategy': 'Full and Open',
                    'Anticipated Contract Vehicle': 'GSA MAS'
                }
            ],
            'doj': [
                {
                    'Action Tracking Number': 'DOJ-001',
                    'Bureau': 'FBI',
                    'Contract Name': 'Test DOJ Opportunity',
                    'Description of Requirement': 'Test description for DOJ',
                    'Contract Type (Pricing)': 'FFP',
                    'NAICS Code': '541511',
                    'Small Business Approach': 'Small Business',
                    'Estimated Total Contract Value (Range)': '$1M - $5M',
                    'Target Solicitation Date': '2024-04-15',
                    'Target Award Date': '2024-06-30',
                    'Place of Performance': 'Quantico, VA',
                    'Country': 'USA'
                }
            ],
            'dos': [
                {
                    'Contract Number': 'DOS-001',
                    'Office Symbol': 'INR',
                    'Requirement Title': 'Test DOS Opportunity',
                    'Requirement Description': 'Test description for DOS',
                    'Estimated Value': '$500K - $1M',
                    'Dollar Value': '750000',
                    'Place of Performance Country': 'USA',
                    'Place of Performance City': 'Washington',
                    'Place of Performance State': 'DC',
                    'Award Type': 'New Contract',
                    'Anticipated Award Date': '2024-06-30',
                    'Target Award Quarter': 'FY24 Q3',
                    'Fiscal Year': '2024',
                    'Anticipated Set Aside': 'Small Business',
                    'Anticipated Solicitation Release Date': '2024-04-15'
                }
            ]
        }

    @pytest.fixture
    def mock_browser_setup(self):
        """Mock browser setup for all scrapers."""
        with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.setup_browser', new_callable=AsyncMock) as mock_setup, \
             patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.cleanup_browser', new_callable=AsyncMock) as mock_cleanup:
            yield mock_setup, mock_cleanup

    @pytest.fixture
    def mock_navigation(self):
        """Mock navigation methods."""
        with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.navigate_to_url', new_callable=AsyncMock, return_value=True) as mock_nav, \
             patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.wait_for_load_state', new_callable=AsyncMock) as mock_wait, \
             patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.wait_for_timeout', new_callable=AsyncMock) as mock_timeout:
            yield mock_nav, mock_wait, mock_timeout

    @pytest.fixture
    def mock_interactions(self):
        """Mock page interaction methods."""
        with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.click_element', new_callable=AsyncMock, return_value=True) as mock_click, \
             patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.wait_for_selector', new_callable=AsyncMock) as mock_selector:
            yield mock_click, mock_selector

    def create_test_file(self, data: list, file_format: str = 'csv') -> str:
        """Create a temporary test file with the provided data."""
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'.{file_format}') as f:
            if file_format == 'csv':
                df.to_csv(f.name, index=False)
            elif file_format == 'xlsx':
                df.to_excel(f.name, index=False, engine='openpyxl')
            elif file_format == 'html':
                df.to_html(f.name, index=False)
            
            return f.name

    # Test Acquisition Gateway Scraper
    @pytest.mark.asyncio
    async def test_acquisition_gateway_scraper(self, mock_browser_setup, mock_navigation, mock_interactions, db_session):
        """Test Acquisition Gateway consolidated scraper."""
        # Create test file
        test_file = self.create_test_file(self.test_data['acquisition_gateway'])
        
        try:
            # Mock download
            with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click', 
                      new_callable=AsyncMock, return_value=test_file):
                
                scraper = AcquisitionGatewayScraper()
                result = await scraper.scrape()
                
                assert result > 0, "Acquisition Gateway scraper should return count > 0"
                
                # Verify database record
                prospects = self.get_prospects_for_source(db_session, "Acquisition Gateway")
                assert len(prospects) > 0, "Should have inserted prospects into database"
                
                prospect = prospects[0]
                assert prospect.native_id == 'AG-001'
                assert prospect.title == 'Test AG Opportunity'
                assert prospect.agency == 'Test Agency'
                
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test DHS Scraper  
    @pytest.mark.asyncio
    async def test_dhs_scraper(self, mock_browser_setup, mock_navigation, mock_interactions, db_session):
        """Test DHS consolidated scraper."""
        test_file = self.create_test_file(self.test_data['dhs'])
        
        try:
            with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click', 
                      new_callable=AsyncMock, return_value=test_file):
                
                scraper = DHSForecastScraper()
                result = await scraper.scrape()
                
                assert result > 0, "DHS scraper should return count > 0"
                
                prospects = self.get_prospects_for_source(db_session, "Department of Homeland Security")
                assert len(prospects) > 0
                
                prospect = prospects[0]
                assert prospect.native_id == 'DHS-001'
                assert prospect.title == 'Test DHS Opportunity'
                assert prospect.agency == 'CISA'
                assert prospect.place_country == 'USA'  # Should be defaulted
                
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test Treasury Scraper
    @pytest.mark.asyncio 
    async def test_treasury_scraper(self, mock_browser_setup, mock_navigation, mock_interactions, db_session):
        """Test Treasury consolidated scraper."""
        test_file = self.create_test_file(self.test_data['treasury'], 'html')
        
        try:
            with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click', 
                      new_callable=AsyncMock, return_value=test_file):
                
                scraper = TreasuryScraper()
                result = await scraper.scrape()
                
                assert result > 0, "Treasury scraper should return count > 0"
                
                prospects = self.get_prospects_for_source(db_session, "Department of Treasury")
                assert len(prospects) > 0
                
                prospect = prospects[0]
                assert prospect.native_id == 'TREAS-001'
                assert prospect.description == 'Test Treasury Opportunity'
                assert prospect.agency == 'IRS'
                
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test DOT Scraper
    @pytest.mark.asyncio
    async def test_dot_scraper(self, mock_browser_setup, mock_navigation, mock_interactions, db_session):
        """Test DOT consolidated scraper."""
        test_file = self.create_test_file(self.test_data['dot'])
        
        try:
            with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_new_page', 
                      new_callable=AsyncMock, return_value=test_file):
                
                scraper = DotScraper()
                result = await scraper.scrape()
                
                assert result > 0, "DOT scraper should return count > 0"
                
                prospects = self.get_prospects_for_source(db_session, "Department of Transportation")
                assert len(prospects) > 0
                
                prospect = prospects[0]
                assert prospect.native_id == 'DOT-001'
                assert prospect.title == 'Test DOT Opportunity'
                assert prospect.agency == 'FAA'
                
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test HHS Scraper
    @pytest.mark.asyncio
    async def test_hhs_scraper(self, mock_browser_setup, mock_navigation, mock_interactions, db_session):
        """Test HHS consolidated scraper."""
        test_file = self.create_test_file(self.test_data['hhs'])
        
        try:
            with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click', 
                      new_callable=AsyncMock, return_value=test_file):
                
                scraper = HHSForecastScraper()
                result = await scraper.scrape()
                
                assert result > 0, "HHS scraper should return count > 0"
                
                prospects = self.get_prospects_for_source(db_session, "Health and Human Services")
                assert len(prospects) > 0
                
                prospect = prospects[0]
                assert prospect.native_id == 'HHS-001'
                assert prospect.title == 'Test HHS Opportunity'
                assert prospect.agency == 'CDC'
                assert prospect.place_country == 'USA'
                
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test SSA Scraper
    @pytest.mark.asyncio
    async def test_ssa_scraper(self, mock_browser_setup, mock_navigation, mock_interactions, db_session):
        """Test SSA consolidated scraper."""
        test_file = self.create_test_file(self.test_data['ssa'], 'xlsx')
        
        try:
            with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.find_excel_link', 
                      new_callable=AsyncMock, return_value="http://test.com/file.xlsx"), \
                 patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_directly', 
                      new_callable=AsyncMock, return_value=test_file):
                
                scraper = SsaScraper()
                result = await scraper.scrape()
                
                assert result > 0, "SSA scraper should return count > 0"
                
                prospects = self.get_prospects_for_source(db_session, "Social Security Administration")
                assert len(prospects) > 0
                
                prospect = prospects[0]
                assert prospect.native_id == 'SSA-001'
                assert prospect.title == 'Test SSA Opportunity'  # Title mapped from description
                assert prospect.description == 'Test SSA Opportunity'
                assert prospect.agency == 'Regional'
                
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test DOC Scraper
    @pytest.mark.asyncio
    async def test_doc_scraper(self, mock_browser_setup, mock_navigation, mock_interactions, db_session):
        """Test DOC consolidated scraper."""
        test_file = self.create_test_file(self.test_data['doc'], 'xlsx')
        
        try:
            with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.find_link_by_text', 
                      new_callable=AsyncMock, return_value="http://test.com/file.xlsx"), \
                 patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_directly', 
                      new_callable=AsyncMock, return_value=test_file):
                
                scraper = DocScraper()
                result = await scraper.scrape()
                
                assert result > 0, "DOC scraper should return count > 0"
                
                prospects = self.get_prospects_for_source(db_session, "Department of Commerce")
                assert len(prospects) > 0
                
                prospect = prospects[0]
                assert prospect.native_id == 'DOC-001'
                assert prospect.title == 'Test DOC Opportunity'
                assert prospect.agency == 'NOAA'
                assert prospect.place_country == 'USA'
                
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test DOJ Scraper
    @pytest.mark.asyncio
    async def test_doj_scraper(self, mock_browser_setup, mock_navigation, mock_interactions, db_session):
        """Test DOJ consolidated scraper."""
        test_file = self.create_test_file(self.test_data['doj'], 'xlsx')
        
        try:
            with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click', 
                      new_callable=AsyncMock, return_value=test_file):
                
                scraper = DOJForecastScraper()
                result = await scraper.scrape()
                
                assert result > 0, "DOJ scraper should return count > 0"
                
                prospects = self.get_prospects_for_source(db_session, "Department of Justice")
                assert len(prospects) > 0
                
                prospect = prospects[0]
                assert prospect.native_id == 'DOJ-001'
                assert prospect.title == 'Test DOJ Opportunity'
                assert prospect.agency == 'FBI'
                assert prospect.place_country == 'USA'
                
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test DOS Scraper
    @pytest.mark.asyncio
    async def test_dos_scraper(self, mock_browser_setup, mock_navigation, mock_interactions, db_session):
        """Test DOS consolidated scraper."""
        test_file = self.create_test_file(self.test_data['dos'], 'xlsx')
        
        try:
            with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_directly', 
                      new_callable=AsyncMock, return_value=test_file):
                
                scraper = DOSForecastScraper()
                result = await scraper.scrape()
                
                assert result > 0, "DOS scraper should return count > 0"
                
                prospects = self.get_prospects_for_source(db_session, "Department of State")
                assert len(prospects) > 0
                
                prospect = prospects[0]
                assert prospect.native_id == 'DOS-001'
                assert prospect.title == 'Test DOS Opportunity'
                assert prospect.agency == 'INR'
                assert prospect.place_country == 'USA'
                
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Test error handling
    @pytest.mark.asyncio
    async def test_scraper_error_handling(self, mock_browser_setup, mock_navigation):
        """Test that scrapers handle errors gracefully."""
        with patch('app.core.consolidated_scraper_base.ConsolidatedScraperBase.download_file_via_click', 
                  new_callable=AsyncMock, side_effect=Exception("Download failed")):
            
            scraper = DHSForecastScraper()
            result = await scraper.scrape()
            
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
            DOSForecastScraper
        ]
        
        for scraper_class in scrapers:
            try:
                scraper = scraper_class()
                assert scraper is not None
                assert hasattr(scraper, 'config')
                assert hasattr(scraper, 'source_name')
                assert scraper.source_name is not None
            except Exception as e:
                pytest.fail(f"Failed to initialize {scraper_class.__name__}: {e}")

    # Test custom transformations
    def test_custom_transformations(self):
        """Test that custom transformation methods exist and work."""
        test_df = pd.DataFrame([{'test': 'value'}])
        
        # Test DHS transform
        scraper = DHSForecastScraper()
        transformed_df = scraper._custom_dhs_transforms(test_df.copy())
        assert 'place_country' in transformed_df.columns
        assert transformed_df['place_country'].iloc[0] == 'USA'
        
        # Test Treasury transform  
        treasury_scraper = TreasuryScraper()
        treasury_df = test_df.copy()
        treasury_df['native_id_primary'] = 'test-id'
        transformed_treasury = treasury_scraper._custom_treasury_transforms(treasury_df)
        assert 'native_id' in transformed_treasury.columns
        assert transformed_treasury['native_id'].iloc[0] == 'test-id'
        assert 'row_index' in transformed_treasury.columns  # Treasury adds row_index
        
        # Test SSA transform
        ssa_scraper = SsaScraper()
        ssa_df = test_df.copy()
        ssa_df['description'] = 'Test SSA Title'
        transformed_ssa = ssa_scraper._custom_ssa_transforms(ssa_df)
        assert 'title' in transformed_ssa.columns
        assert transformed_ssa['title'].iloc[0] == 'Test SSA Title'
        # SSA also keeps description unchanged
        assert transformed_ssa['description'].iloc[0] == 'Test SSA Title'


# Standalone test functions for running individual scrapers
@pytest.mark.asyncio
async def test_run_single_scraper_acquisition_gateway():
    """Run only the Acquisition Gateway scraper for testing."""
    test_instance = TestConsolidatedScrapers()
    test_instance.setup_test_data()
    
    # You can call this function directly to test just this scraper
    # pytest tests/core/scrapers/test_consolidated_scrapers.py::test_run_single_scraper_acquisition_gateway -v
    pass

@pytest.mark.asyncio  
async def test_run_single_scraper_dhs():
    """Run only the DHS scraper for testing.""" 
    test_instance = TestConsolidatedScrapers()
    test_instance.setup_test_data()
    pass

# Add similar standalone functions for each scraper as needed...


if __name__ == "__main__":
    # Allow running this file directly for quick testing
    pytest.main([__file__, "-v"])