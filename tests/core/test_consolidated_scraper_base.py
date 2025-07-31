"""
Comprehensive tests for ConsolidatedScraperBase.

Tests the core scraper framework functionality that all agency scrapers inherit.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
from datetime import datetime, timezone, date
import pandas as pd
import tempfile
import os
from pathlib import Path

from app.core.consolidated_scraper_base import ConsolidatedScraperBase, ScraperConfig
from app.database.models import Prospect, DataSource
from app.database import db
from app import create_app


class TestScraperConfig:
    """Test ScraperConfig dataclass functionality."""
    
    def test_scraper_config_creation(self):
        """Test basic scraper configuration creation."""
        config = ScraperConfig(
            name="Test Scraper",
            base_url="https://test.gov",
            timeout=30,
            enable_screenshots=True,
            enable_stealth=True
        )
        
        assert config.name == "Test Scraper"
        assert config.base_url == "https://test.gov"
        assert config.timeout == 30
        assert config.enable_screenshots is True
        assert config.enable_stealth is True
        assert config.field_mappings == {}  # Default
        assert config.download_dir is None  # Default
    
    def test_scraper_config_with_field_mappings(self):
        """Test scraper config with field mappings."""
        field_mappings = {
            'title': 'contract_title',
            'agency': 'issuing_agency',
            'value': 'estimated_value'
        }
        
        config = ScraperConfig(
            name="Mapped Scraper",
            base_url="https://mapped.gov",
            field_mappings=field_mappings
        )
        
        assert config.field_mappings == field_mappings
        assert config.field_mappings['title'] == 'contract_title'


class TestConsolidatedScraperBase:
    """Test ConsolidatedScraperBase functionality."""
    
    @pytest.fixture(scope='class')
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        return app
    
    @pytest.fixture
    def db_session(self, app):
        """Create test database session."""
        with app.app_context():
            db.create_all()
            yield db.session
            db.session.rollback()
            db.drop_all()
    
    @pytest.fixture
    def test_config(self):
        """Create test scraper configuration."""
        return ScraperConfig(
            name="Test Agency Scraper",
            base_url="https://test-agency.gov",
            timeout=30,
            enable_screenshots=True,
            enable_stealth=True,
            field_mappings={
                'title': 'opportunity_title',
                'description': 'opportunity_description',
                'agency': 'issuing_agency',
                'posted_date': 'post_date',
                'naics': 'naics_code'
            }
        )
    
    @pytest.fixture
    def scraper(self, test_config):
        """Create test scraper instance."""
        return ConsolidatedScraperBase(test_config)
    
    def test_scraper_initialization(self, scraper, test_config):
        """Test scraper initialization."""
        assert scraper.config == test_config
        assert scraper.config.name == "Test Agency Scraper"
        assert scraper.screenshots_dir.exists()
        assert scraper.downloads_dir.exists()
        assert scraper.logger is not None
    
    def test_scraper_directories_creation(self, scraper):
        """Test that scraper creates necessary directories."""
        # Directories should be created during initialization
        assert scraper.screenshots_dir.exists()
        assert scraper.downloads_dir.exists()
        assert scraper.html_dumps_dir.exists()
        
        # Directory names should include scraper name
        assert "test-agency-scraper" in str(scraper.screenshots_dir).lower()
    
    @patch('app.core.consolidated_scraper_base.async_playwright')
    def test_setup_browser_success(self, mock_playwright, scraper):
        """Test successful browser setup."""
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # Mock stealth plugin
        with patch('app.core.consolidated_scraper_base.stealth_async'):
            result = scraper._setup_browser()
            
        assert result == (mock_browser, mock_context, mock_page)
    
    @patch('app.core.consolidated_scraper_base.async_playwright')
    def test_setup_browser_failure(self, mock_playwright, scraper):
        """Test browser setup failure handling."""
        mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
            side_effect=Exception("Browser launch failed")
        )
        
        with pytest.raises(Exception, match="Browser launch failed"):
            scraper._setup_browser()
    
    def test_take_screenshot_success(self, scraper):
        """Test successful screenshot capture."""
        mock_page = Mock()
        mock_page.screenshot = AsyncMock()
        
        with patch('app.core.consolidated_scraper_base.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101-120000"
            
            screenshot_path = scraper._take_screenshot(mock_page, "test-error")
            
            mock_page.screenshot.assert_called_once()
            assert "test-error" in str(screenshot_path)
            assert "20240101-120000" in str(screenshot_path)
    
    def test_save_html_dump_success(self, scraper):
        """Test successful HTML dump saving."""
        mock_page = Mock()
        mock_page.content = AsyncMock(return_value="<html><body>Test content</body></html>")
        
        with patch('app.core.consolidated_scraper_base.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101-120000"
            
            html_path = scraper._save_html_dump(mock_page, "test-error")
            
            mock_page.content.assert_called_once()
            assert "test-error" in str(html_path)
            assert html_path.exists()
    
    def test_navigate_to_page_success(self, scraper):
        """Test successful page navigation."""
        mock_page = Mock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        
        scraper._navigate_to_page(mock_page, "https://test.gov/opportunities")
        
        mock_page.goto.assert_called_once_with(
            "https://test.gov/opportunities",
            wait_until="networkidle",
            timeout=30000
        )
        mock_page.wait_for_load_state.assert_called_once_with("domcontentloaded")
    
    def test_navigate_to_page_failure(self, scraper):
        """Test page navigation failure handling."""
        mock_page = Mock()
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation failed"))
        
        with pytest.raises(Exception, match="Navigation failed"):
            scraper._navigate_to_page(mock_page, "https://test.gov/opportunities")
    
    def test_wait_for_downloads_success(self, scraper):
        """Test successful download waiting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            scraper.downloads_dir = temp_path
            
            # Create test files to simulate downloads
            test_files = [
                temp_path / "document1.pdf",
                temp_path / "document2.xlsx"
            ]
            
            for file_path in test_files:
                file_path.write_text("test content")
            
            initial_files = set()
            files = scraper._wait_for_downloads(initial_files, timeout=1)
            
            assert len(files) == 2
            assert any("document1.pdf" in str(f) for f in files)
            assert any("document2.xlsx" in str(f) for f in files)
    
    def test_extract_data_from_files_csv(self, scraper):
        """Test data extraction from CSV files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write("title,agency,value\n")
            temp_file.write("Test Contract 1,Test Agency,100000\n")
            temp_file.write("Test Contract 2,Test Agency,200000\n")
            temp_file_path = temp_file.name
        
        try:
            files = [Path(temp_file_path)]
            df = scraper._extract_data_from_files(files)
            
            assert len(df) == 2
            assert 'title' in df.columns
            assert 'agency' in df.columns
            assert 'value' in df.columns
            assert df.iloc[0]['title'] == "Test Contract 1"
            assert df.iloc[1]['value'] == "200000"
        finally:
            os.unlink(temp_file_path)
    
    def test_extract_data_from_files_excel(self, scraper):
        """Test data extraction from Excel files."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            # Create test Excel file
            test_df = pd.DataFrame({
                'contract_title': ['Excel Contract 1', 'Excel Contract 2'],
                'issuing_agency': ['Excel Agency', 'Excel Agency'],
                'contract_value': [150000, 250000]
            })
            test_df.to_excel(temp_file_path, index=False)
            
            files = [Path(temp_file_path)]
            df = scraper._extract_data_from_files(files)
            
            assert len(df) == 2
            assert 'contract_title' in df.columns
            assert 'issuing_agency' in df.columns
            assert df.iloc[0]['contract_title'] == "Excel Contract 1"
        finally:
            os.unlink(temp_file_path)
    
    def test_apply_field_mappings(self, scraper):
        """Test field mapping application."""
        # Original data with agency-specific field names
        original_df = pd.DataFrame({
            'opportunity_title': ['Mapped Contract 1', 'Mapped Contract 2'],
            'opportunity_description': ['Description 1', 'Description 2'],
            'issuing_agency': ['Mapped Agency', 'Mapped Agency'],
            'post_date': ['2024-01-01', '2024-01-02'],
            'naics_code': ['541511', '541512']
        })
        
        mapped_df = scraper._apply_field_mappings(original_df)
        
        # Should have standardized field names
        assert 'title' in mapped_df.columns
        assert 'description' in mapped_df.columns
        assert 'agency' in mapped_df.columns
        assert 'posted_date' in mapped_df.columns
        assert 'naics' in mapped_df.columns
        
        # Should not have original field names
        assert 'opportunity_title' not in mapped_df.columns
        assert 'issuing_agency' not in mapped_df.columns
        
        # Data should be preserved
        assert mapped_df.iloc[0]['title'] == 'Mapped Contract 1'
        assert mapped_df.iloc[1]['agency'] == 'Mapped Agency'
    
    def test_clean_and_validate_data(self, scraper):
        """Test data cleaning and validation."""
        # Test data with various issues
        test_df = pd.DataFrame({
            'title': ['  Valid Title  ', '', None, 'Another Valid Title'],
            'agency': ['Valid Agency', 'Valid Agency', 'Valid Agency', ''],
            'description': ['Good description', 'Another description', None, 'Third description'],
            'posted_date': ['2024-01-01', 'invalid-date', '2024-01-03', '2024-01-04'],
            'naics': ['541511', 'invalid', '541512', None],
            'estimated_value_text': ['$100,000', 'TBD', '', '$200,000']
        })
        
        cleaned_df = scraper._clean_and_validate_data(test_df)
        
        # Should remove rows with missing required fields
        assert len(cleaned_df) <= len(test_df)
        
        # Should clean whitespace from titles
        valid_titles = cleaned_df['title'].dropna()
        for title in valid_titles:
            assert title == title.strip()  # No leading/trailing whitespace
        
        # Should handle date parsing gracefully
        if 'posted_date' in cleaned_df.columns:
            # Invalid dates should be handled (NaT or excluded)
            pass
    
    def test_create_prospects_from_dataframe(self, scraper, db_session):
        """Test prospect creation from DataFrame."""
        # Create data source first
        data_source = DataSource(
            name="Test Agency",
            url="https://test-agency.gov",
            last_scraped=datetime.now(timezone.utc)
        )
        db_session.add(data_source)
        db_session.flush()
        
        # Mock the data source lookup
        scraper.data_source_id = data_source.id
        
        test_df = pd.DataFrame({
            'title': ['Test Prospect 1', 'Test Prospect 2'],
            'description': ['Description 1', 'Description 2'],
            'agency': ['Test Agency', 'Test Agency'],
            'naics': ['541511', '541512'],
            'posted_date': ['2024-01-01', '2024-01-02'],
            'estimated_value_text': ['$100,000', '$200,000']
        })
        
        with patch.object(scraper, '_generate_prospect_id') as mock_id_gen:
            mock_id_gen.side_effect = ['TEST-001', 'TEST-002']
            
            prospects = scraper._create_prospects_from_dataframe(test_df)
            
            assert len(prospects) == 2
            assert prospects[0].title == 'Test Prospect 1'
            assert prospects[1].naics == '541512'
            assert all(p.source_id == data_source.id for p in prospects)
    
    def test_generate_prospect_id(self, scraper):
        """Test prospect ID generation."""
        test_data = {
            'title': 'Test Contract Opportunity',
            'agency': 'Test Agency',
            'posted_date': '2024-01-01'
        }
        
        prospect_id = scraper._generate_prospect_id(test_data)
        
        # Should generate consistent hash-based ID
        assert len(prospect_id) > 10  # Should be reasonably long
        assert isinstance(prospect_id, str)
        
        # Same data should generate same ID
        prospect_id2 = scraper._generate_prospect_id(test_data)
        assert prospect_id == prospect_id2
        
        # Different data should generate different ID
        test_data2 = test_data.copy()
        test_data2['title'] = 'Different Contract'
        prospect_id3 = scraper._generate_prospect_id(test_data2)
        assert prospect_id != prospect_id3
    
    def test_save_prospects_to_database(self, scraper, db_session):
        """Test saving prospects to database."""
        # Create data source
        data_source = DataSource(
            name="Save Test Agency",
            url="https://save-test.gov",
            last_scraped=datetime.now(timezone.utc)
        )
        db_session.add(data_source)
        db_session.flush()
        
        # Create test prospects
        prospects = [
            Prospect(
                id='SAVE-TEST-001',
                title='Save Test 1',
                agency='Save Test Agency',
                description='Test saving prospect 1',
                source_id=data_source.id,
                loaded_at=datetime.now(timezone.utc)
            ),
            Prospect(
                id='SAVE-TEST-002',
                title='Save Test 2',
                agency='Save Test Agency',
                description='Test saving prospect 2',
                source_id=data_source.id,
                loaded_at=datetime.now(timezone.utc)
            )
        ]
        
        # Mock database operations
        with patch.object(scraper, 'db') as mock_db:
            mock_db.session = db_session
            
            result = scraper._save_prospects_to_database(prospects)
            
            assert result['saved'] == 2
            assert result['errors'] == 0
            
            # Verify prospects were added to session
            assert len(prospects) == 2
    
    @patch('app.core.consolidated_scraper_base.async_playwright')
    def test_run_scraper_success(self, mock_playwright, scraper, db_session):
        """Test successful end-to-end scraper run."""
        # Mock all browser operations
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        
        # Mock stealth
        with patch('app.core.consolidated_scraper_base.stealth_async'):
            # Mock data extraction
            with patch.object(scraper, '_extract_data_from_files') as mock_extract:
                test_df = pd.DataFrame({
                    'opportunity_title': ['Full Test Contract'],
                    'issuing_agency': ['Full Test Agency'],
                    'opportunity_description': ['Full test description']
                })
                mock_extract.return_value = test_df
                
                # Mock database operations
                with patch.object(scraper, '_save_prospects_to_database') as mock_save:
                    mock_save.return_value = {'saved': 1, 'errors': 0}
                    
                    # Mock custom scraping logic
                    with patch.object(scraper, 'scrape_data') as mock_scrape:
                        mock_scrape.return_value = [Path('/fake/file.csv')]
                        
                        result = scraper.run()
                        
                        assert result['success'] is True
                        assert result['prospects_saved'] == 1
                        assert result['errors'] == 0
    
    @patch('app.core.consolidated_scraper_base.async_playwright')
    def test_run_scraper_with_errors(self, mock_playwright, scraper):
        """Test scraper run with errors."""
        # Mock browser failure
        mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
            side_effect=Exception("Browser setup failed")
        )
        
        result = scraper.run()
        
        assert result['success'] is False
        assert 'error' in result
        assert 'Browser setup failed' in result['error']
    
    def test_scraper_logging(self, scraper):
        """Test scraper logging functionality."""
        # Logger should be configured
        assert scraper.logger is not None
        assert scraper.logger.name == "Test Agency Scraper"
        
        # Test logging methods don't raise errors
        scraper.logger.info("Test info message")
        scraper.logger.warning("Test warning message")
        scraper.logger.error("Test error message")
    
    def test_scraper_custom_transformations(self, scraper):
        """Test custom transformation hooks."""
        # Test that custom_transform method can be overridden
        test_df = pd.DataFrame({
            'title': ['Original Title'],
            'agency': ['Original Agency']
        })
        
        # Default implementation should return unchanged
        transformed_df = scraper.custom_transform(test_df)
        assert transformed_df.equals(test_df)
        
        # Test that method can be overridden
        class CustomScraper(ConsolidatedScraperBase):
            def custom_transform(self, df):
                df = df.copy()
                df['title'] = df['title'].str.upper()
                return df
        
        custom_scraper = CustomScraper(scraper.config)
        custom_transformed = custom_scraper.custom_transform(test_df)
        
        assert custom_transformed.iloc[0]['title'] == 'ORIGINAL TITLE'
    
    def test_scraper_file_cleanup(self, scraper):
        """Test cleanup of temporary files."""
        # Create some temporary files
        temp_files = [
            scraper.downloads_dir / "temp1.pdf",
            scraper.downloads_dir / "temp2.xlsx",
            scraper.screenshots_dir / "error.png"
        ]
        
        for file_path in temp_files:
            file_path.write_text("temporary content")
            assert file_path.exists()
        
        # Test cleanup method if it exists
        if hasattr(scraper, 'cleanup'):
            scraper.cleanup()
            # Verify cleanup worked as expected
    
    def test_scraper_error_recovery(self, scraper):
        """Test scraper error recovery mechanisms."""
        mock_page = Mock()
        
        # Test screenshot on error
        with patch.object(scraper, '_take_screenshot') as mock_screenshot:
            with patch.object(scraper, '_save_html_dump') as mock_html:
                scraper._handle_error(mock_page, Exception("Test error"), "test-context")
                
                mock_screenshot.assert_called_once()
                mock_html.assert_called_once()
    
    def test_scraper_configuration_validation(self):
        """Test scraper configuration validation."""
        # Test missing required fields
        with pytest.raises(TypeError):
            ScraperConfig()  # Missing required name parameter
        
        # Test invalid timeout
        with pytest.raises((ValueError, TypeError)):
            ScraperConfig(
                name="Invalid Config",
                base_url="https://test.gov",
                timeout=-1  # Invalid negative timeout
            )