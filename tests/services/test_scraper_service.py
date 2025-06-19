import pytest
from unittest.mock import patch, MagicMock, call
import datetime

from app.services.scraper_service import ScraperService
from app.database.models import DataSource, ScraperStatus
from app.exceptions import NotFoundError, ScraperError, DatabaseError

@pytest.fixture(autouse=True)
def mock_db_session_and_logger():
    with patch('app.services.scraper_service.db') as mock_db:
        with patch('app.services.scraper_service.logger') as mock_logger:
            mock_session = MagicMock()
            mock_db.session = mock_session
            yield mock_session, mock_logger

@pytest.fixture
def mock_data_source():
    ds = DataSource(id=1, name="Acquisition Gateway", url="http://example.com")
    return ds

@pytest.fixture
def mock_status_record():
    sr = ScraperStatus(source_id=1, status='pending')
    return sr

@pytest.fixture
def mock_scraper_class():
    scraper_instance_mock = MagicMock()
    scraper_class_mock = MagicMock(return_value=scraper_instance_mock)
    return scraper_class_mock, scraper_instance_mock

class TestScraperService:

    def test_trigger_scrape_success(self, mock_db_session_and_logger, mock_data_source, mock_status_record, mock_scraper_class):
        mock_session, mock_logger = mock_db_session_and_logger
        ScraperClassMock, scraper_instance_mock = mock_scraper_class

        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = mock_status_record
        
        with patch('app.services.scraper_service.AcquisitionGatewayScraper', ScraperClassMock) as MockedAGScraper:
            with patch('app.services.scraper_service.SsaScraper', MagicMock()):
                result = ScraperService.trigger_scrape(source_id=1)

        assert result['status'] == 'success'
        assert result['scraper_status'] == 'completed'
        assert mock_data_source.name in result['message']
        
        MockedAGScraper.assert_called_once() 
        scraper_instance_mock.run.assert_called_once()
        assert mock_status_record.status == 'completed'
        assert mock_data_source.last_scraped is not None
        assert mock_session.commit.call_count == 2 

        mock_logger.info.assert_any_call(f"Starting scrape for {mock_data_source.name} (ID: 1)")
        mock_logger.info.assert_any_call(f"Scrape for {mock_data_source.name} completed successfully.")

    def test_trigger_scrape_new_status_record(self, mock_db_session_and_logger, mock_data_source, mock_scraper_class):
        mock_session, mock_logger = mock_db_session_and_logger
        ScraperClassMock, scraper_instance_mock = mock_scraper_class

        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = None 
        
        mock_created_status_record = MagicMock(spec=ScraperStatus)
        mock_created_status_record.source_id = 1
        mock_created_status_record.status = 'pending'

        with patch('app.services.scraper_service.ScraperStatus', return_value=mock_created_status_record) as MockStatusConstructor:
            with patch('app.services.scraper_service.AcquisitionGatewayScraper', ScraperClassMock):
                with patch('app.services.scraper_service.SsaScraper', MagicMock()):
                    result = ScraperService.trigger_scrape(source_id=1)

        MockStatusConstructor.assert_called_once_with(source_id=1, status='pending', details='Status record created on first pull trigger.')
        mock_session.add.assert_any_call(mock_created_status_record)

        assert result['status'] == 'success'
        assert result['scraper_status'] == 'completed'
        assert mock_created_status_record.status == 'completed' 
        scraper_instance_mock.run.assert_called_once()
        assert mock_session.commit.call_count == 2

    def test_trigger_scrape_datasource_not_found(self, mock_db_session_and_logger):
        mock_session, _ = mock_db_session_and_logger
        mock_session.query(DataSource).filter_by(id=1).first.return_value = None

        with pytest.raises(NotFoundError) as excinfo:
            ScraperService.trigger_scrape(source_id=1)
        
        assert "Data source with ID 1 not found" in str(excinfo.value)
        mock_session.rollback.assert_called_once()

    def test_trigger_scrape_no_scraper_configured(self, mock_db_session_and_logger, mock_data_source, mock_status_record):
        mock_session, mock_logger = mock_db_session_and_logger

        mock_data_source.name = "Unknown Scraper" 
        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = mock_status_record

        with pytest.raises(ScraperError) as excinfo:
            ScraperService.trigger_scrape(source_id=1)
        
        assert f"No scraper configured for data source: {mock_data_source.name}" in str(excinfo.value)
        assert mock_status_record.status == 'working' 
        mock_session.commit.assert_called_once() 
        mock_session.rollback.assert_called_once()

    def test_trigger_scrape_scraper_run_fails(self, mock_db_session_and_logger, mock_data_source, mock_status_record, mock_scraper_class):
        mock_session, mock_logger = mock_db_session_and_logger
        ScraperClassMock, scraper_instance_mock = mock_scraper_class

        scraper_instance_mock.run.side_effect = Exception("Scraper failed miserably")

        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = mock_status_record

        with patch('app.services.scraper_service.AcquisitionGatewayScraper', ScraperClassMock):
            with patch('app.services.scraper_service.SsaScraper', MagicMock()):
                with pytest.raises(ScraperError) as excinfo:
                    ScraperService.trigger_scrape(source_id=1)
        
        assert f"Scraping {mock_data_source.name} failed: Exception('Scraper failed miserably')" in str(excinfo.value)
        
        scraper_instance_mock.run.assert_called_once()
        assert mock_status_record.status == 'failed'
        assert "Scrape failed: Scraper failed miserably" in mock_status_record.details
        assert mock_session.commit.call_count == 2 
        mock_logger.error.assert_any_call(f"Scraper for {mock_data_source.name} failed: Scraper failed miserably", exc_info=True)

    def test_trigger_scrape_unexpected_exception_before_run(self, mock_db_session_and_logger, mock_data_source):
        mock_session, mock_logger = mock_db_session_and_logger

        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.side_effect = Exception("DB boom before status update")

        with pytest.raises(DatabaseError) as excinfo:
            ScraperService.trigger_scrape(source_id=1)
        
        assert f"Unexpected error processing pull for {mock_data_source.name} in service" in str(excinfo.value)
        mock_session.rollback.assert_called_once()
        mock_logger.error.assert_any_call(f"Unexpected error in scraper service for source ID 1: DB boom before status update", exc_info=True)
        mock_session.commit.assert_not_called()

    def test_trigger_scrape_unexpected_exception_updates_status_if_possible(self, mock_db_session_and_logger, mock_data_source, mock_status_record):
        mock_session, mock_logger = mock_db_session_and_logger

        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = mock_status_record
        
        FaultyScraperClassMock = MagicMock(side_effect=RuntimeError("Cannot init scraper"))

        with patch('app.services.scraper_service.AcquisitionGatewayScraper', FaultyScraperClassMock):
            with patch('app.services.scraper_service.SsaScraper', MagicMock()):
                with pytest.raises(DatabaseError) as excinfo:
                     ScraperService.trigger_scrape(source_id=1)

        assert f"Unexpected error processing pull for {mock_data_source.name} in service" in str(excinfo.value)
        assert mock_session.commit.call_count == 2
        assert mock_status_record.status == 'failed'
        assert "Pull process failed unexpectedly in service: Cannot init scraper" in mock_status_record.details
        mock_logger.error.assert_any_call(f"Unexpected error in scraper service for source ID 1: Cannot init scraper", exc_info=True)
        mock_session.rollback.assert_called_once()