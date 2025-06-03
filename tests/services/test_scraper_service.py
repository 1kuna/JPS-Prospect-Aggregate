import pytest
from unittest.mock import patch, MagicMock

from app.services.scraper_service import ScraperService
from app.database.models import DataSource, ScraperStatus # Changed import
from app.exceptions import NotFoundError, ScraperError, DatabaseError

@pytest.fixture(autouse=True)
def mock_db_session_and_logger():
    mock_session = MagicMock()
    # Patch the db.session object within the app.models module,
    # as both scraper_service and db_utils import 'db' from 'app.models'.
    with patch('app.models.db.session', new=mock_session) as _mocked_db_session, \
         patch('app.services.scraper_service.logger') as mock_logger:
        # Note: _mocked_db_session is the MagicMock for app.models.db.session
        # mock_session is the actual MagicMock instance we passed as 'new'.
        # We yield mock_session so tests can assert calls on it.
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

    def test_trigger_scrape_success(self, mock_db_session_and_logger, mock_data_source, mock_status_record, mock_scraper_class, app):
        mock_session, mock_logger = mock_db_session_and_logger
        ScraperClassMock, scraper_instance_mock = mock_scraper_class

        # Ensure mock_data_source has the correct scraper_key
        mock_data_source.scraper_key = 'acq_gateway' # Or any key that SCRAPERS dict will be patched with

        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = mock_status_record
        
        # Patch the SCRAPERS dictionary in app.core.scrapers (where it's defined and used by ScraperService)
        with patch.dict('app.core.scrapers.SCRAPERS', {mock_data_source.scraper_key: ScraperClassMock}, clear=True):
            result = ScraperService.trigger_scrape(source_id=1)

        assert result['status'] == 'success'
        assert result['scraper_status'] == 'completed'
        assert mock_data_source.name in result['message']
        
        ScraperClassMock.assert_called_once_with(debug_mode=False) # Check it was instantiated
        scraper_instance_mock.run.assert_called_once()
        assert mock_status_record.status == 'completed'
        assert mock_data_source.last_scraped is not None
        assert mock_session.commit.call_count == 3

        mock_logger.info.assert_any_call(f"Starting scrape for {mock_data_source.name} (ID: 1)")
        mock_logger.info.assert_any_call(f"Scrape for {mock_data_source.name} completed successfully.")

    def test_trigger_scrape_new_status_record(self, mock_db_session_and_logger, mock_data_source, mock_scraper_class, app):
        mock_session, mock_logger = mock_db_session_and_logger
        ScraperClassMock, scraper_instance_mock = mock_scraper_class

        # Ensure mock_data_source has the correct scraper_key
        mock_data_source.scraper_key = 'acq_gateway'

        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = None 
        
        mock_created_status_record = MagicMock(spec=ScraperStatus)
        mock_created_status_record.source_id = 1
        mock_created_status_record.status = 'pending'

        # Patch the SCRAPERS dictionary
        with patch.dict('app.core.scrapers.SCRAPERS', {mock_data_source.scraper_key: ScraperClassMock}, clear=True):
            # Patch ScraperStatus where it's defined and imported by app.utils.db_utils
            with patch('app.database.models.ScraperStatus', return_value=mock_created_status_record) as MockStatusConstructor:
                result = ScraperService.trigger_scrape(source_id=1)

        # Check if the constructor was called with arguments for the 'working' state,
        # as update_scraper_status creates this first when a record is new.
        # It will also be called for 'completed', so assert_any_call is appropriate.
        MockStatusConstructor.assert_any_call(source_id=1, status='working', details='Scrape process initiated.')
        mock_session.add.assert_any_call(mock_created_status_record) # This mock_created_status_record is 'pending' initially
        ScraperClassMock.assert_called_once_with(debug_mode=False) # Verify ScraperClassMock was used

        assert result['status'] == 'success'
        assert result['scraper_status'] == 'completed'
        assert mock_created_status_record.status == 'completed' 
        scraper_instance_mock.run.assert_called_once()
        assert mock_session.commit.call_count == 2

    def test_trigger_scrape_datasource_not_found(self, mock_db_session_and_logger, app):
        mock_session, _ = mock_db_session_and_logger
        mock_session.query(DataSource).filter_by(id=1).first.return_value = None

        with pytest.raises(NotFoundError) as excinfo:
            ScraperService.trigger_scrape(source_id=1)
        
        assert "Data source with ID 1 not found" in str(excinfo.value)
        mock_session.rollback.assert_called_once()

    def test_trigger_scrape_no_scraper_configured(self, mock_db_session_and_logger, mock_data_source, mock_status_record, app):
        mock_session, mock_logger = mock_db_session_and_logger

        mock_data_source.name = "Unknown Scraper" 
        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = mock_status_record

        with pytest.raises(ScraperError) as excinfo:
            ScraperService.trigger_scrape(source_id=1)
        
        expected_error_message = f"Data source {mock_data_source.name} (ID: {mock_data_source.id}) does not have a scraper_key configured."
        assert str(excinfo.value) == expected_error_message
        assert mock_status_record.status == 'pending'
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_called_once()

    def test_trigger_scrape_scraper_run_fails(self, mock_db_session_and_logger, mock_data_source, mock_status_record, mock_scraper_class, app):
        mock_session, mock_logger = mock_db_session_and_logger
        ScraperClassMock, scraper_instance_mock = mock_scraper_class

        scraper_instance_mock.run.side_effect = Exception("Scraper failed miserably")

        # Ensure mock_data_source has the correct scraper_key
        mock_data_source.scraper_key = 'acq_gateway'

        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = mock_status_record

        # Patch the SCRAPERS dictionary
        with patch.dict('app.core.scrapers.SCRAPERS', {mock_data_source.scraper_key: ScraperClassMock}, clear=True):
            with pytest.raises(ScraperError) as excinfo:
                ScraperService.trigger_scrape(source_id=1)
        
        assert f"Scraping {mock_data_source.name} failed: Scraper failed miserably" == str(excinfo.value)
        
        ScraperClassMock.assert_called_once_with(debug_mode=False)
        scraper_instance_mock.run.assert_called_once()
        assert mock_status_record.status == 'failed'
        assert "Scrape failed: Scraper failed miserably" in mock_status_record.details
        assert mock_session.commit.call_count == 2 
        mock_logger.error.assert_any_call(f"Scraper for {mock_data_source.name} failed: Scraper failed miserably", exc_info=True)

    def test_trigger_scrape_unexpected_exception_before_run(self, mock_db_session_and_logger, mock_data_source, app):
        mock_session, mock_logger = mock_db_session_and_logger

        # Ensure the mock_data_source has a scraper_key for this test
        mock_data_source.scraper_key = 'acq_gateway'
        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.side_effect = Exception("DB boom before status update")

        with pytest.raises(ScraperError) as excinfo: # Changed from DatabaseError
            ScraperService.trigger_scrape(source_id=1)
        
        assert "DB boom before status update" in str(excinfo.value) # Check for original error
        mock_session.rollback.assert_called_once()
        mock_logger.error.assert_any_call(f"Unexpected error in scraper service for source ID 1: DB boom before status update", exc_info=True)
        mock_session.commit.assert_not_called()

    def test_trigger_scrape_unexpected_exception_updates_status_if_possible(self, mock_db_session_and_logger, mock_data_source, mock_status_record, app):
        mock_session, mock_logger = mock_db_session_and_logger

        # Ensure mock_data_source has the correct scraper_key
        mock_data_source.scraper_key = 'acq_gateway'

        mock_session.query(DataSource).filter_by(id=1).first.return_value = mock_data_source
        mock_session.query(ScraperStatus).filter_by(source_id=1).order_by().first.return_value = mock_status_record
        
        FaultyScraperClassMock = MagicMock(side_effect=RuntimeError("Cannot init scraper"))

        # Patch the SCRAPERS dictionary
        with patch.dict('app.core.scrapers.SCRAPERS', {mock_data_source.scraper_key: FaultyScraperClassMock}, clear=True):
            with pytest.raises(DatabaseError) as excinfo:
                 ScraperService.trigger_scrape(source_id=1)

        assert f"Unexpected error processing pull for {mock_data_source.name} in service" in str(excinfo.value)
        FaultyScraperClassMock.assert_called_once_with(debug_mode=False)
        assert mock_session.commit.call_count == 2 # Initial status update + failed status update
        assert mock_status_record.status == 'failed'
        assert "Pull process failed unexpectedly in service: Cannot init scraper" in mock_status_record.details
        mock_logger.error.assert_any_call(f"Unexpected error in scraper service for source ID 1: Cannot init scraper", exc_info=True)
        mock_session.rollback.assert_called_once()