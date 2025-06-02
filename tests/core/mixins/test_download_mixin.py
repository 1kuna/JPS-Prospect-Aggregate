import pytest
from unittest.mock import MagicMock, patch
import os
import datetime
import re # For testing _extract_filename_from_cd

from app.core.mixins.download_mixin import DownloadMixin
from app.core.configs.base_config import BaseScraperConfig
from app.exceptions import ScraperError
from playwright.sync_api import Download as PlaywrightDownload 
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, APIRequestContext


# A simple class that incorporates DownloadMixin for testing
class TestScraperWithDownload(DownloadMixin):
    def __init__(self, page, context, playwright_api, logger, config, download_path):
        self.page = page
        self.context = context 
        self.playwright = playwright_api 
        self.logger = logger
        self.config = config
        self.download_path = download_path
        self.source_name_short = config.source_name.lower().replace(' ', '_')
        self._last_download_path = None
        self._save_error_screenshot = MagicMock()
        self._save_error_html = MagicMock()
        # Mock the standardized error handler from BaseScraper
        self._handle_and_raise_scraper_error = MagicMock(
            side_effect=lambda e, desc: (_ for _ in ()).throw(ScraperError(f"Mocked ScraperError: {desc} from {type(e).__name__} - {e}"))
        )
        # Mock click_element from NavigationMixin as it's used by download_file_via_click
        self.click_element = MagicMock()


@pytest.fixture
def mock_page_dl():
    page = MagicMock()
    page.locator.return_value = MagicMock() # So that .click() can be called on it
    page.expect_download.return_value.__enter__.return_value = MagicMock() # For the 'with' statement
    return page

@pytest.fixture
def mock_context_dl():
    mock_ctx = MagicMock()
    mock_ctx.request = MagicMock() 
    # For download_with_new_tab placeholder test
    mock_new_page = MagicMock()
    mock_new_page.url = "http://newtab.com/download.zip"
    mock_new_page.expect_download.return_value.__enter__.return_value = MagicMock()
    mock_ctx.expect_page.return_value.__enter__.return_value.value = mock_new_page
    return mock_ctx

@pytest.fixture
def mock_playwright_api_dl():
    mock_pw = MagicMock()
    mock_api_req_context = MagicMock(spec=APIRequestContext) # Use spec for better mocking
    mock_api_req_context.get.return_value = MagicMock(ok=True, body=lambda: b"data", headers={})
    mock_api_req_context.dispose = MagicMock()
    mock_pw.request.new_context.return_value = mock_api_req_context
    return mock_pw


@pytest.fixture
def mock_logger_dl():
    return MagicMock()

@pytest.fixture
def base_config_dl(tmp_path):
    return BaseScraperConfig(
        source_name="TestDLScraper",
        download_timeout_ms=1000,
        default_wait_after_download_ms=100,
        interaction_timeout_ms=500, # For click_element calls within download_file_via_click
        screenshot_on_error=True, 
        save_html_on_error=True
    )

@pytest.fixture
def scraper_instance_dl(mock_page_dl, mock_context_dl, mock_playwright_api_dl, mock_logger_dl, base_config_dl, tmp_path):
    download_path = tmp_path / "test_downloads"
    download_path.mkdir()
    scraper = TestScraperWithDownload(
        page=mock_page_dl, 
        context=mock_context_dl,
        playwright_api=mock_playwright_api_dl,
        logger=mock_logger_dl, 
        config=base_config_dl,
        download_path=str(download_path)
    )
    return scraper

@pytest.fixture
def mock_download_event():
    mock_event = MagicMock(spec=PlaywrightDownload)
    mock_event.suggested_filename = "test_file.pdf"
    mock_event.failure.return_value = None 
    mock_event.page.return_value = MagicMock() 
    mock_event.url = "http://example.com/test_file.pdf"
    return mock_event

# --- Tests for _handle_download_event ---
def test_handle_download_event_success(scraper_instance_dl, mock_download_event):
    scraper_instance_dl._handle_download_event(mock_download_event)
    assert mock_download_event.save_as.call_count == 1
    saved_path_arg = mock_download_event.save_as.call_args[0][0]
    assert scraper_instance_dl.download_path in saved_path_arg
    assert scraper_instance_dl.source_name_short in saved_path_arg
    assert ".pdf" in saved_path_arg
    assert scraper_instance_dl._last_download_path == saved_path_arg

def test_handle_download_event_no_extension(scraper_instance_dl, mock_download_event):
    mock_download_event.suggested_filename = "file_no_ext"
    scraper_instance_dl._handle_download_event(mock_download_event)
    saved_path_arg = mock_download_event.save_as.call_args[0][0]
    assert ".unknown" in saved_path_arg # Default extension
    scraper_instance_dl.logger.warning.assert_any_call("Downloaded file 'file_no_ext' has no extension. Using '.unknown'.")


# --- Tests for download_file_via_click ---
@patch('os.path.exists', return_value=True)
def test_download_file_via_click_with_pre_click(mock_os_exists, scraper_instance_dl, mock_page_dl):
    scraper_instance_dl._last_download_path = "/path/to/downloaded_file.zip" # Simulate event handler worked
    
    scraper_instance_dl.download_file_via_click(
        click_selector="button#download",
        pre_click_selector="button#viewAll",
        pre_click_wait_ms=50
    )
    # Check pre_click call (uses self.click_element)
    scraper_instance_dl.click_element.assert_any_call("button#viewAll", timeout_ms=scraper_instance_dl.config.interaction_timeout_ms)
    scraper_instance_dl.logger.info.assert_any_call("Waiting 50ms after pre-click.")
    mock_page_dl.wait_for_timeout.assert_any_call(50) # Check explicit wait
    # Check main click call (uses self.click_element)
    scraper_instance_dl.click_element.assert_any_call(selector="button#download", click_options={}, timeout_ms=scraper_instance_dl.config.interaction_timeout_ms)
    mock_page_dl.expect_download.assert_called_once()


@patch('os.path.exists', return_value=False) # Simulate file not existing after download attempt
def test_download_file_via_click_file_not_found_error(mock_os_exists, scraper_instance_dl, mock_page_dl):
    # Simulate that _handle_download_event set a path, but file doesn't exist
    scraper_instance_dl._last_download_path = "/path/that/wont/exist.zip" 
    
    # Mock download_info.value to provide a Download object for error logging
    mock_dl_object = MagicMock(spec=PlaywrightDownload)
    mock_dl_object.path.return_value = "/playwright/temp/path"
    mock_dl_object.failure.return_value = "Download failed by Playwright"
    mock_page_dl.expect_download.return_value.__enter__.return_value.value = mock_dl_object

    with pytest.raises(ScraperError, match="Download via click on 'button#error' did not result in a saved file"):
        scraper_instance_dl.download_file_via_click(click_selector="button#error")
    
    scraper_instance_dl.logger.error.assert_any_call(
        "Download via click on 'button#error' appears to have failed or file not found. "
        f"_last_download_path: {scraper_instance_dl._last_download_path}. "
        f"Playwright temp path: /playwright/temp/path, Failure: Download failed by Playwright"
    )
    # Note: _handle_and_raise_scraper_error is NOT called here because the error is raised directly.

def test_download_file_via_click_expect_download_timeout(scraper_instance_dl, mock_page_dl):
    mock_page_dl.expect_download.side_effect = PlaywrightTimeoutError("expect_download timeout")
    
    with pytest.raises(ScraperError, match="Mocked ScraperError: timeout during downloading file via click on 'button#timeout' from PlaywrightTimeoutError - expect_download timeout"):
        scraper_instance_dl.download_file_via_click(click_selector="button#timeout")
    
    scraper_instance_dl._save_error_screenshot.assert_called_once_with("download_expect_timeout")
    scraper_instance_dl._save_error_html.assert_called_once_with("download_expect_timeout")
    scraper_instance_dl._handle_and_raise_scraper_error.assert_called_once()


# --- Tests for _extract_filename_from_cd ---
@pytest.mark.parametrize("header_value, expected_filename", [
    ("attachment; filename=\"example.pdf\"", "example.pdf"),
    ("attachment; filename=example.pdf", "example.pdf"),
    ("form-data; name=\"upload\"; filename=\"sample.xlsx\"", "sample.xlsx"),
    ("attachment; filename*=UTF-8''Report%20%C2%A3100.txt", "Report £100.txt"), # Handles URI encoding
    ("attachment; filename = spaced_name.zip ", "spaced_name.zip"), # Handles spaces around =
    ("inline; filename=\"another.document.tar.gz\"", "another.document.tar.gz"),
    ("filename=\"only_filename.dat\"", "only_filename.dat"), # No disposition type
    (None, None),
    ("", None),
    ("invalid_header_format", None),
    ("attachment; filenametypo=\"bad.txt\"", None),
])
def test_extract_filename_from_cd(scraper_instance_dl, header_value, expected_filename):
    assert scraper_instance_dl._extract_filename_from_cd(header_value) == expected_filename


# --- Tests for download_file_directly ---
def test_download_file_directly_filename_override(scraper_instance_dl, mock_playwright_api_dl, tmp_path):
    override_name = "custom_name.dat"
    file_path = scraper_instance_dl.download_file_directly("http://direct.com/file.unknown", file_name_override=override_name)
    
    # Check if the saved filename contains the override (plus source_name_short and timestamp)
    assert override_name.split('.')[0] in os.path.basename(file_path) 
    assert override_name.split('.')[1] in os.path.basename(file_path)
    assert scraper_instance_dl.source_name_short in file_path

@patch('mimetypes.guess_extension', return_value=".guessed_ext")
def test_download_file_directly_url_parsing_and_mimetype_guess(mock_guess_ext, scraper_instance_dl, mock_playwright_api_dl, tmp_path):
    # Mock API response to have no content-disposition and a specific content-type
    mock_api_response = MagicMock(ok=True, body=lambda: b"data", headers={'content-type': 'application/custom-type'})
    mock_playwright_api_dl.request.new_context.return_value.get.return_value = mock_api_response
    
    file_path = scraper_instance_dl.download_file_directly("http://direct.com/fileFromUrl") # No extension in URL path part
    
    assert "fileFromUrl" in os.path.basename(file_path)
    assert ".guessed_ext" in os.path.basename(file_path) # Guessed from content-type
    mock_guess_ext.assert_called_once_with('application/custom-type')

def test_download_file_directly_request_not_ok(scraper_instance_dl, mock_playwright_api_dl):
    mock_api_response = MagicMock(ok=False, status=404, status_text="Not Found", text=lambda: "File missing", headers={})
    mock_playwright_api_dl.request.new_context.return_value.get.return_value = mock_api_response
    
    with pytest.raises(ScraperError, match="Failed to download file directly from http://error.com/file.txt. Status: 404"):
        scraper_instance_dl.download_file_directly("http://error.com/file.txt")
    # Note: _handle_and_raise_scraper_error is NOT called by this specific path in download_file_directly, it raises ScraperError directly.

def test_download_file_directly_api_timeout(scraper_instance_dl, mock_playwright_api_dl):
    mock_playwright_api_dl.request.new_context.return_value.get.side_effect = PlaywrightTimeoutError("API request timeout")

    with pytest.raises(ScraperError, match="Mocked ScraperError: timeout during downloading file directly from URL: http://timeout.com/file.api from PlaywrightTimeoutError - API request timeout"):
        scraper_instance_dl.download_file_directly("http://timeout.com/file.api")
    scraper_instance_dl._handle_and_raise_scraper_error.assert_called_once()


# Test for get_last_downloaded_path
def test_get_last_downloaded_path(scraper_instance_dl):
    assert scraper_instance_dl.get_last_downloaded_path() is None # Initially None
    scraper_instance_dl._last_download_path = "/test/path.zip"
    assert scraper_instance_dl.get_last_downloaded_path() == "/test/path.zip"

```
