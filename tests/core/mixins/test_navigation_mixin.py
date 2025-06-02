import pytest
from unittest.mock import MagicMock, patch
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.core.mixins.navigation_mixin import NavigationMixin
from app.core.configs.base_config import BaseScraperConfig
from app.exceptions import ScraperError

# A simple class that incorporates NavigationMixin for testing purposes
class TestScraperWithNav(NavigationMixin):
    def __init__(self, page, logger, config):
        self.page = page
        self.logger = logger
        self.config = config
        # Mock error saving methods expected by the mixin
        self._save_error_screenshot = MagicMock()
        self._save_error_html = MagicMock()
        # Mock the standardized error handler from BaseScraper
        self._handle_and_raise_scraper_error = MagicMock(side_effect=lambda e, desc: (_ for _ in ()).throw(ScraperError(f"Mocked ScraperError: {desc} from {e}")))


@pytest.fixture
def mock_page():
    page = MagicMock()
    # Configure locator chain
    page.locator.return_value.wait_for = MagicMock()
    page.locator.return_value.click = MagicMock()
    page.locator.return_value.evaluate = MagicMock() # For JS click
    page.locator.return_value.get_attribute = MagicMock()
    page.locator.return_value.text_content = MagicMock()
    page.locator.return_value.fill = MagicMock()
    return page

@pytest.fixture
def mock_logger():
    return MagicMock()

@pytest.fixture
def base_config():
    return BaseScraperConfig(
        source_name="TestScraper",
        base_url="http://test.com",
        navigation_timeout_ms=1000, 
        interaction_timeout_ms=500,
        screenshot_on_error=True, 
        save_html_on_error=True   
    )

@pytest.fixture
def scraper_instance_nav(mock_page, mock_logger, base_config):
    return TestScraperWithNav(page=mock_page, logger=mock_logger, config=base_config)

# --- Tests for navigate_to_url ---
def test_navigate_to_url_success(scraper_instance_nav, mock_page):
    scraper_instance_nav.navigate_to_url("http://example.com")
    mock_page.goto.assert_called_once_with(
        "http://example.com",
        wait_until='load',
        timeout=scraper_instance_nav.config.navigation_timeout_ms
    )
    scraper_instance_nav.logger.info.assert_any_call("Successfully navigating to URL: http://example.com")

def test_navigate_to_url_timeout(scraper_instance_nav, mock_page):
    mock_page.goto.side_effect = PlaywrightTimeoutError("Timeout!")
    
    with pytest.raises(ScraperError, match="Mocked ScraperError: navigating to URL: http://example.com from Timeout!"):
        scraper_instance_nav.navigate_to_url("http://example.com")
    
    scraper_instance_nav.logger.warning.assert_any_call("PlaywrightTimeoutError during 'navigating to URL: http://example.com'. Attempting to save debug info.")
    scraper_instance_nav._save_error_screenshot.assert_called_once_with("navigate_timeout")
    scraper_instance_nav._save_error_html.assert_called_once_with("navigate_timeout")
    scraper_instance_nav._handle_and_raise_scraper_error.assert_called_once()

def test_navigate_to_url_generic_exception(scraper_instance_nav, mock_page):
    mock_page.goto.side_effect = Exception("Generic network error!")
    
    with pytest.raises(ScraperError, match="Mocked ScraperError: generic error during navigating to URL: http://example.com from Generic network error!"):
        scraper_instance_nav.navigate_to_url("http://example.com")
        
    scraper_instance_nav.logger.warning.assert_any_call("Generic exception during 'navigating to URL: http://example.com'. Attempting to save debug info.")
    scraper_instance_nav._save_error_screenshot.assert_called_once_with("navigate_error")
    scraper_instance_nav._save_error_html.assert_called_once_with("navigate_error")
    scraper_instance_nav._handle_and_raise_scraper_error.assert_called_once()

# --- Tests for click_element ---
def test_click_element_simple_success(scraper_instance_nav, mock_page):
    scraper_instance_nav.click_element("button#submit")
    mock_page.locator.assert_called_once_with("button#submit")
    mock_page.locator.return_value.wait_for.assert_called_once_with(state='visible', timeout=scraper_instance_nav.config.interaction_timeout_ms)
    mock_page.locator.return_value.click.assert_called_once_with()
    scraper_instance_nav.logger.info.assert_any_call("Successfully clicking element: 'button#submit' (navigation: False)")

def test_click_element_with_navigation(scraper_instance_nav, mock_page):
    with mock_page.expect_navigation(): # Simulate context manager
        scraper_instance_nav.click_element("a.nav-link", wait_for_navigation=True, navigation_wait_until_state='networkidle')
    
    mock_page.locator.assert_called_once_with("a.nav-link")
    mock_page.locator.return_value.wait_for.assert_called_once_with(state='visible', timeout=scraper_instance_nav.config.interaction_timeout_ms)
    mock_page.expect_navigation.assert_called_once_with(wait_until='networkidle', timeout=scraper_instance_nav.config.interaction_timeout_ms)
    mock_page.locator.return_value.click.assert_called_once_with() # Click inside with block
    scraper_instance_nav.logger.info.assert_any_call("Successfully clicking element: 'a.nav-link' (navigation: True)")

def test_click_element_js_fallback_success(scraper_instance_nav, mock_page):
    # Standard click fails, JS click succeeds
    mock_page.locator.return_value.click.side_effect = PlaywrightTimeoutError("Standard click timeout")
    
    scraper_instance_nav.click_element("button#fallback", js_click_fallback=True)
    
    assert mock_page.locator.return_value.click.call_count == 1 # Standard click attempted
    mock_page.locator.return_value.evaluate.assert_called_once_with("element => element.click()") # JS click attempted
    scraper_instance_nav.logger.info.assert_any_call("JavaScript click fallback for 'button#fallback' succeeded.")

def test_click_element_js_fallback_fails_too(scraper_instance_nav, mock_page):
    mock_page.locator.return_value.click.side_effect = PlaywrightTimeoutError("Standard click timeout")
    mock_page.locator.return_value.evaluate.side_effect = Exception("JS click also failed")

    with pytest.raises(ScraperError, match="Mocked ScraperError: JS click fallback for 'button#fallback_fail' from JS click also failed"):
        scraper_instance_nav.click_element("button#fallback_fail", js_click_fallback=True)
        
    scraper_instance_nav._save_error_screenshot.assert_called_once_with("click_js_fallback_error")
    scraper_instance_nav._save_error_html.assert_called_once_with("click_js_fallback_error")
    scraper_instance_nav._handle_and_raise_scraper_error.assert_called_once()

def test_click_element_standard_click_timeout_no_fallback(scraper_instance_nav, mock_page):
    mock_page.locator.return_value.click.side_effect = PlaywrightTimeoutError("Standard click timeout")

    with pytest.raises(ScraperError, match="Mocked ScraperError: clicking element: 'button#no_fallback' (navigation: False) from Standard click timeout"):
        scraper_instance_nav.click_element("button#no_fallback", js_click_fallback=False)

    scraper_instance_nav._save_error_screenshot.assert_called_once_with("click_timeout")
    scraper_instance_nav._save_error_html.assert_called_once_with("click_timeout")
    scraper_instance_nav._handle_and_raise_scraper_error.assert_called_once()


# --- Tests for wait_for_selector ---
def test_wait_for_selector_success_visible(scraper_instance_nav, mock_page):
    scraper_instance_nav.wait_for_selector("div.content", visible=True)
    mock_page.locator.assert_called_once_with("div.content")
    mock_page.locator.return_value.wait_for.assert_called_once_with(state='visible', timeout=scraper_instance_nav.config.interaction_timeout_ms)
    scraper_instance_nav.logger.info.assert_any_call("Selector 'div.content' is now visible.")

def test_wait_for_selector_success_hidden(scraper_instance_nav, mock_page):
    scraper_instance_nav.wait_for_selector("div.loader", visible=False, hidden=True) # explicit hidden
    mock_page.locator.assert_called_once_with("div.loader")
    mock_page.locator.return_value.wait_for.assert_called_once_with(state='hidden', timeout=scraper_instance_nav.config.interaction_timeout_ms)

def test_wait_for_selector_success_state_override(scraper_instance_nav, mock_page):
    scraper_instance_nav.wait_for_selector("div.content", state='attached') # explicit state
    mock_page.locator.assert_called_once_with("div.content")
    mock_page.locator.return_value.wait_for.assert_called_once_with(state='attached', timeout=scraper_instance_nav.config.interaction_timeout_ms)


def test_wait_for_selector_timeout(scraper_instance_nav, mock_page):
    mock_page.locator.return_value.wait_for.side_effect = PlaywrightTimeoutError("Wait for selector timeout")
    
    with pytest.raises(ScraperError, match="Mocked ScraperError: waiting for selector 'div.content_missing' to be visible from Wait for selector timeout"):
        scraper_instance_nav.wait_for_selector("div.content_missing")
        
    scraper_instance_nav._save_error_screenshot.assert_called_once_with("wait_selector_timeout")
    scraper_instance_nav._save_error_html.assert_called_once_with("wait_selector_timeout")
    scraper_instance_nav._handle_and_raise_scraper_error.assert_called_once()


# --- Minimal Placeholder tests for other methods (already had basic ones) ---
def test_fill_input_success(scraper_instance_nav, mock_page):
    scraper_instance_nav.fill_input("input#name", "Test Name")
    mock_page.locator.return_value.fill.assert_called_once_with("Test Name")

def test_get_element_attribute_success(scraper_instance_nav, mock_page):
    mock_page.locator.return_value.get_attribute.return_value = "http://link.com"
    attr_value = scraper_instance_nav.get_element_attribute("a.link", "href")
    assert attr_value == "http://link.com"

def test_get_element_text_success(scraper_instance_nav, mock_page):
    mock_page.locator.return_value.text_content.return_value = "Hello World"
    text = scraper_instance_nav.get_element_text("p.greeting")
    assert text == "Hello World"

def test_wait_for_load_state_success(scraper_instance_nav, mock_page):
    scraper_instance_nav.wait_for_load_state("networkidle")
    mock_page.wait_for_load_state.assert_called_once_with("networkidle", timeout=scraper_instance_nav.config.navigation_timeout_ms)

def test_wait_for_timeout_success(scraper_instance_nav, mock_page):
    scraper_instance_nav.wait_for_timeout(500)
    mock_page.wait_for_timeout.assert_called_once_with(500)

```
