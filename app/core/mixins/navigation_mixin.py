from typing import Optional, Dict, Any
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, Page # Import Page for type hinting if methods expect it directly
from app.exceptions import ScraperError
# Assuming logger, config, page, _save_error_screenshot, _save_error_html, _handle_and_raise_scraper_error
# are available on 'self' from the BaseScraper class.

class NavigationMixin:
    """
    Mixin class for common browser navigation and interaction tasks.
    Relies on attributes and methods from BaseScraper:
    - self.page: Playwright Page object.
    - self.logger: Logger instance.
    - self.config: Scraper configuration object (e.g., for default timeouts).
    - self._save_error_screenshot(): Method to save a screenshot on error.
    - self._save_error_html(): Method to save HTML content on error.
    - self._handle_and_raise_scraper_error(): Method to standardize error logging and raising.
    """

    def navigate_to_url(self, url: str, wait_until_state: Optional[str] = 'load', timeout_ms: Optional[int] = None) -> None:
        """Navigates the current page to the specified URL."""
        if not all(hasattr(self, attr) for attr in ['page', 'logger', 'config', '_save_error_screenshot', '_save_error_html', '_handle_and_raise_scraper_error']):
            # This check is more for development; in production, AttributeError would be raised.
            raise ScraperError("NavigationMixin.navigate_to_url is missing required attributes/methods from BaseScraper.")

        effective_timeout = timeout_ms if timeout_ms is not None else self.config.navigation_timeout_ms
        operation_desc = f"navigating to URL: {url}"
        self.logger.info(f"Attempting to {operation_desc} (wait_until: {wait_until_state}, timeout: {effective_timeout}ms)")
        
        try:
            self.page.goto(url, wait_until=wait_until_state, timeout=effective_timeout)
            self.logger.info(f"Successfully {operation_desc}")
        except PlaywrightTimeoutError as e:
            self.logger.warning(f"PlaywrightTimeoutError during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("navigate_timeout")
            if self.config.save_html_on_error: self._save_error_html("navigate_timeout")
            self._handle_and_raise_scraper_error(e, operation_desc) # Standardized handler
        except Exception as e:
            self.logger.warning(f"Generic exception during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("navigate_error") # Might fail if page context is bad
            if self.config.save_html_on_error: self._save_error_html("navigate_error")
            self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")


    def click_element(self, 
                        selector: str, 
                        timeout_ms: Optional[int] = None, 
                        wait_for_navigation: bool = False, 
                        navigation_wait_until_state: Optional[str] = 'load', 
                        js_click_fallback: bool = False,
                        click_options: Optional[Dict[str, Any]] = None) -> None:
        """Clicks an element specified by a selector, with options for navigation and JS fallback."""
        if not all(hasattr(self, attr) for attr in ['page', 'logger', 'config', '_save_error_screenshot', '_save_error_html', '_handle_and_raise_scraper_error']):
            raise ScraperError("NavigationMixin.click_element is missing required attributes/methods from BaseScraper.")

        effective_timeout = timeout_ms if timeout_ms is not None else self.config.interaction_timeout_ms
        loc = self.page.locator(selector)
        click_opts = click_options or {}
        operation_desc = f"clicking element: '{selector}' (navigation: {wait_for_navigation})"
        self.logger.info(f"Attempting to {operation_desc} (timeout: {effective_timeout}ms)")
        
        try:
            loc.wait_for(state='visible', timeout=effective_timeout)
            self.logger.debug(f"Element '{selector}' is visible.")

            if wait_for_navigation:
                self.logger.debug(f"Expecting navigation after click on '{selector}'. State: {navigation_wait_until_state}")
                with self.page.expect_navigation(wait_until=navigation_wait_until_state, timeout=effective_timeout):
                    loc.click(**click_opts)
            else:
                loc.click(**click_opts)
            self.logger.info(f"Successfully {operation_desc}")

        except PlaywrightTimeoutError as e:
            self.logger.warning(f"Initial click on '{selector}' failed or timed out: {e}")
            if js_click_fallback:
                self.logger.info(f"Attempting JavaScript click fallback for selector: '{selector}'")
                js_op_desc = f"JS click fallback for '{selector}'"
                try:
                    if wait_for_navigation:
                        self.logger.warning("JS click with 'wait_for_navigation' might not be perfectly synchronized.")
                        with self.page.expect_navigation(wait_until=navigation_wait_until_state, timeout=effective_timeout):
                             loc.evaluate("element => element.click()")
                    else:
                        loc.evaluate("element => element.click()")
                    self.logger.info(f"JavaScript click fallback for '{selector}' succeeded.")
                except Exception as js_e: # Catch any error from JS click
                    self.logger.error(f"JavaScript click fallback for '{selector}' also failed: {js_e}", exc_info=True)
                    if self.config.screenshot_on_error: self._save_error_screenshot("click_js_fallback_error")
                    if self.config.save_html_on_error: self._save_error_html("click_js_fallback_error")
                    self._handle_and_raise_scraper_error(js_e, js_op_desc) # Standardized handler
            else: 
                if self.config.screenshot_on_error: self._save_error_screenshot("click_timeout")
                if self.config.save_html_on_error: self._save_error_html("click_timeout")
                self._handle_and_raise_scraper_error(e, operation_desc) # Standardized handler for original timeout
        except Exception as e:
            self.logger.warning(f"Generic exception during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("click_error")
            if self.config.save_html_on_error: self._save_error_html("click_error")
            self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")


    def wait_for_selector(self, selector: str, timeout_ms: Optional[int] = None, visible: bool = True, hidden: bool = False, state: Optional[str] = None) -> None:
        """Waits for an element specified by a selector to be in a certain state (visible, hidden, etc.)."""
        if not all(hasattr(self, attr) for attr in ['page', 'logger', 'config', '_save_error_screenshot', '_save_error_html', '_handle_and_raise_scraper_error']):
            raise ScraperError("NavigationMixin.wait_for_selector is missing required attributes/methods from BaseScraper.")

        effective_timeout = timeout_ms if timeout_ms is not None else self.config.interaction_timeout_ms
        
        target_state = state
        if target_state is None:
            target_state = 'hidden' if hidden else ('visible' if visible else 'attached')
        
        operation_desc = f"waiting for selector '{selector}' to be {target_state}"
        self.logger.info(f"Attempting to {operation_desc} (timeout: {effective_timeout}ms)")
        
        try:
            self.page.locator(selector).wait_for(state=target_state, timeout=effective_timeout)
            self.logger.info(f"Selector '{selector}' is now {target_state}.")
        except PlaywrightTimeoutError as e:
            self.logger.warning(f"PlaywrightTimeoutError during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("wait_selector_timeout")
            if self.config.save_html_on_error: self._save_error_html("wait_selector_timeout")
            self._handle_and_raise_scraper_error(e, operation_desc)
        except Exception as e:
            self.logger.warning(f"Generic exception during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("wait_selector_error")
            if self.config.save_html_on_error: self._save_error_html("wait_selector_error")
            self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")


    def fill_input(self, selector: str, text: str, timeout_ms: Optional[int] = None, fill_options: Optional[Dict[str, Any]] = None) -> None:
        """Fills an input field with the given text."""
        if not all(hasattr(self, attr) for attr in ['page', 'logger', 'config', '_save_error_screenshot', '_save_error_html', '_handle_and_raise_scraper_error']):
            raise ScraperError("NavigationMixin.fill_input is missing required attributes/methods from BaseScraper.")

        effective_timeout = timeout_ms if timeout_ms is not None else self.config.interaction_timeout_ms
        operation_desc = f"filling input '{selector}'"
        self.logger.info(f"Attempting to {operation_desc}. (timeout for wait: {effective_timeout}ms)")
        
        try:
            self.wait_for_selector(selector, timeout_ms=effective_timeout, state='visible')
            loc = self.page.locator(selector)
            loc.fill(text, **(fill_options or {})) 
            self.logger.info(f"Successfully {operation_desc}.")
        except PlaywrightTimeoutError as e: # Can be from wait_for_selector or fill
            self.logger.warning(f"PlaywrightTimeoutError during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("fill_input_timeout")
            if self.config.save_html_on_error: self._save_error_html("fill_input_timeout")
            self._handle_and_raise_scraper_error(e, operation_desc)
        except Exception as e:
            self.logger.warning(f"Generic exception during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("fill_input_error")
            if self.config.save_html_on_error: self._save_error_html("fill_input_error")
            self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")

    def get_element_attribute(self, selector: str, attribute_name: str, timeout_ms: Optional[int] = None) -> Optional[str]:
        """Gets an attribute value from an element."""
        if not all(hasattr(self, attr) for attr in ['page', 'logger', 'config', '_save_error_screenshot', '_save_error_html', '_handle_and_raise_scraper_error']):
            raise ScraperError("NavigationMixin.get_element_attribute is missing required attributes/methods from BaseScraper.")

        effective_timeout = timeout_ms if timeout_ms is not None else self.config.interaction_timeout_ms
        operation_desc = f"getting attribute '{attribute_name}' from element '{selector}'"
        self.logger.info(f"Attempting to {operation_desc}. (timeout for wait: {effective_timeout}ms)")
        
        try:
            self.wait_for_selector(selector, timeout_ms=effective_timeout, state='attached')
            attribute_value = self.page.locator(selector).get_attribute(attribute_name, timeout=effective_timeout)
            self.logger.info(f"Successfully {operation_desc}. Value: '{attribute_value}'")
            return attribute_value
        except PlaywrightTimeoutError as e:
            self.logger.warning(f"PlaywrightTimeoutError during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("get_attribute_timeout")
            if self.config.save_html_on_error: self._save_error_html("get_attribute_timeout")
            self._handle_and_raise_scraper_error(e, operation_desc)
        except Exception as e:
            self.logger.warning(f"Generic exception during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("get_attribute_error")
            if self.config.save_html_on_error: self._save_error_html("get_attribute_error")
            self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")
        return None # Should be unreachable due to raises

    def get_element_text(self, selector: str, timeout_ms: Optional[int] = None) -> Optional[str]:
        """Gets the text content from an element."""
        if not all(hasattr(self, attr) for attr in ['page', 'logger', 'config', '_save_error_screenshot', '_save_error_html', '_handle_and_raise_scraper_error']):
            raise ScraperError("NavigationMixin.get_element_text is missing required attributes/methods from BaseScraper.")

        effective_timeout = timeout_ms if timeout_ms is not None else self.config.interaction_timeout_ms
        operation_desc = f"getting text content from element '{selector}'"
        self.logger.info(f"Attempting to {operation_desc}. (timeout for wait: {effective_timeout}ms)")
        
        try:
            self.wait_for_selector(selector, timeout_ms=effective_timeout, state='visible')
            text_content = self.page.locator(selector).text_content(timeout=effective_timeout)
            self.logger.info(f"Successfully {operation_desc}.")
            self.logger.debug(f"Text from '{selector}': '{text_content}'")
            return text_content
        except PlaywrightTimeoutError as e:
            self.logger.warning(f"PlaywrightTimeoutError during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("get_text_timeout")
            if self.config.save_html_on_error: self._save_error_html("get_text_timeout")
            self._handle_and_raise_scraper_error(e, operation_desc)
        except Exception as e:
            self.logger.warning(f"Generic exception during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("get_text_error")
            if self.config.save_html_on_error: self._save_error_html("get_text_error")
            self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")
        return None # Should be unreachable

    def wait_for_load_state(self, state: str = 'load', timeout_ms: Optional[int] = None) -> None:
        """Waits for the page to reach a specific load state."""
        if not all(hasattr(self, attr) for attr in ['page', 'logger', 'config', '_save_error_screenshot', '_save_error_html', '_handle_and_raise_scraper_error']):
            raise ScraperError("NavigationMixin.wait_for_load_state is missing required attributes/methods from BaseScraper.")

        effective_timeout = timeout_ms if timeout_ms is not None else self.config.navigation_timeout_ms
        operation_desc = f"waiting for page load state: '{state}'"
        self.logger.info(f"Attempting to {operation_desc} (timeout: {effective_timeout}ms)")
        
        try:
            self.page.wait_for_load_state(state, timeout=effective_timeout)
            self.logger.info(f"Page reached load state: '{state}'.")
        except PlaywrightTimeoutError as e:
            self.logger.warning(f"PlaywrightTimeoutError during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("load_state_timeout")
            if self.config.save_html_on_error: self._save_error_html("load_state_timeout")
            self._handle_and_raise_scraper_error(e, operation_desc)
        except Exception as e: 
            self.logger.warning(f"Generic exception during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("load_state_error")
            if self.config.save_html_on_error: self._save_error_html("load_state_error")
            self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")

    def wait_for_timeout(self, timeout_ms: int) -> None:
        """Explicitly pauses execution for a specified duration. Use sparingly."""
        if not all(hasattr(self, attr) for attr in ['page', 'logger', '_handle_and_raise_scraper_error']): # No config needed here directly
            raise ScraperError("NavigationMixin.wait_for_timeout is missing required attributes from BaseScraper.")
            
        operation_desc = f"waiting for explicit timeout: {timeout_ms}ms"
        self.logger.info(f"Attempting to {operation_desc}.")
        try:
            self.page.wait_for_timeout(timeout_ms)
            self.logger.info(f"Explicit timeout of {timeout_ms}ms completed.")
        except Exception as e: 
            # This is very unlikely for wait_for_timeout unless page is closed/context lost.
            self.logger.warning(f"Generic exception during '{operation_desc}'.")
            # No screenshot/HTML here as the page state might be unstable or closed.
            self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")
