import os
import datetime
import re
from typing import Optional, Dict, Any
from playwright.sync_api import Download, TimeoutError as PlaywrightTimeoutError, APIRequestContext
from app.exceptions import ScraperError
from app.utils.file_utils import ensure_directory 
# Assuming logger, config, page, context, playwright, download_path, source_name_short, 
# _last_download_path, _save_error_screenshot, _save_error_html, _handle_and_raise_scraper_error
# are available on 'self' from the BaseScraper class.

class DownloadMixin:
    """
    Mixin class for common file downloading tasks.
    Relies on attributes and methods from BaseScraper.
    """

    def _handle_download_event(self, download: Download) -> None:
        """Handles the Playwright download event. Saves the file and updates _last_download_path."""
        if not all(hasattr(self, attr) for attr in ['logger', 'config', 'download_path', 'source_name_short', '_last_download_path']):
            # This should ideally not happen if mixin is used correctly with BaseScraper
            print("DownloadMixin._handle_download_event critical attributes missing. Cannot process download.")
            try:
                download.cancel() # Try to prevent hanging download
            except Exception: pass
            return

        operation_desc = f"handling download event for '{download.suggested_filename}' from URL '{download.url}'"
        self.logger.info(f"Starting to {operation_desc}")
        try:
            suggested_filename = download.suggested_filename
            if not suggested_filename:
                self.logger.warning("Download event: suggested_filename is empty. Using a default name.")
                suggested_filename = f"{self.source_name_short}_download.unknown"

            _, ext = os.path.splitext(suggested_filename)
            if not ext: 
                ext = ".unknown"
                self.logger.warning(f"Downloaded file '{suggested_filename}' has no extension. Using '{ext}'.")
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            final_filename = f"{self.source_name_short}_{timestamp}{ext}"
            
            ensure_directory(self.download_path)
            save_path = os.path.join(self.download_path, final_filename)

            download.save_as(save_path)
            
            self._last_download_path = save_path
            self.logger.info(f"Download event: File '{suggested_filename}' saved as '{save_path}'")

        except Exception as e: # Catch any error during save_as or path manipulation
            # This is an event handler, raising an error might crash Playwright's event loop
            # or be unhandled. Logging is primary.
            self.logger.error(f"Error during {operation_desc}: {e}", exc_info=True)
            self._last_download_path = None 
            # Not calling _handle_and_raise_scraper_error here as it's an event callback.
            # The method that initiated the download should handle timeout/failure to get _last_download_path.

    def download_file_via_click(self, 
                                click_selector: str, 
                                expect_download_timeout: Optional[int] = None, 
                                pre_click_selector: Optional[str] = None, 
                                pre_click_wait_ms: Optional[int] = None, 
                                post_download_wait_ms: Optional[int] = None, 
                                click_options: Optional[Dict[str, Any]] = None) -> str:
        """Downloads a file triggered by clicking an element."""
        if not all(hasattr(self, attr) for attr in ['page', 'logger', 'config', '_last_download_path', '_save_error_screenshot', '_save_error_html', '_handle_and_raise_scraper_error', 'click_element']):
            raise ScraperError("DownloadMixin.download_file_via_click is missing required attributes/methods from BaseScraper/NavigationMixin.")

        self._last_download_path = None 
        effective_expect_timeout = expect_download_timeout if expect_download_timeout is not None else self.config.download_timeout_ms
        effective_post_wait = post_download_wait_ms if post_download_wait_ms is not None else self.config.default_wait_after_download_ms
        effective_pre_wait = pre_click_wait_ms if pre_click_wait_ms is not None else 0
        
        operation_desc = f"downloading file via click on '{click_selector}'"
        self.logger.info(f"Starting {operation_desc}")

        try:
            if pre_click_selector:
                # Use self.click_element from NavigationMixin for pre-click for consistency and error handling
                self.click_element(pre_click_selector, timeout_ms=self.config.interaction_timeout_ms)
                if effective_pre_wait > 0:
                    self.logger.info(f"Waiting {effective_pre_wait}ms after pre-click.")
                    self.page.wait_for_timeout(effective_pre_wait) # Direct Playwright call for simple pause

            self.logger.info(f"Expecting download within {effective_expect_timeout}ms after clicking '{click_selector}'.")
            
            with self.page.expect_download(timeout=effective_expect_timeout) as download_info:
                # Use self.click_element from NavigationMixin. It handles js_fallback internally if configured/needed.
                # Assuming click_element is robust and js_click_fallback is a param it can take.
                # For now, js_click_fallback is not directly passed here, assuming click_element default behavior.
                # If js_click_fallback is crucial, click_element must be called with it true, or this method needs it.
                self.click_element(selector=click_selector, click_options=click_options, timeout_ms=self.config.interaction_timeout_ms)
            
            # _handle_download_event (called by Playwright event) should set self._last_download_path
            self.page.wait_for_timeout(effective_post_wait) # Allow event processing

            if self._last_download_path and os.path.exists(self._last_download_path):
                self.logger.info(f"Successfully {operation_desc}. File saved at: {self._last_download_path}")
                return self._last_download_path
            else:
                # Debug info if download path not set
                download_obj = download_info.value 
                temp_playwright_path = "N/A"; 실패_reason = "Unknown"
                try:
                    if download_obj: temp_playwright_path = download_obj.path(); 실패_reason = download_obj.failure() or "No failure reason"
                except Exception: pass
                self.logger.error(f"Download via click on '{click_selector}' appears to have failed or file not found. "
                                  f"_last_download_path: {self._last_download_path}. Playwright temp path: {temp_playwright_path}, Failure: {실패_reason}")
                # Raise a generic ScraperError here, specific timeout/click errors handled by click_element
                raise ScraperError(f"Download via click on '{click_selector}' did not result in a saved file (path: {self._last_download_path}, Playwright failure: {실패_reason}).")

        except PlaywrightTimeoutError as e: # This catches timeout from expect_download primarily
            self.logger.warning(f"PlaywrightTimeoutError during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("download_expect_timeout")
            if self.config.save_html_on_error: self._save_error_html("download_expect_timeout")
            self._handle_and_raise_scraper_error(e, f"timeout during {operation_desc}")
        except Exception as e: # Catch other errors, including those from click_element if they bubble up
            self.logger.warning(f"Generic exception during '{operation_desc}'. Attempting to save debug info.")
            if self.config.screenshot_on_error: self._save_error_screenshot("download_click_error")
            if self.config.save_html_on_error: self._save_error_html("download_click_error")
            self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")


    def _extract_filename_from_cd(self, content_disposition: str) -> Optional[str]:
        """Extracts filename from Content-Disposition header."""
        if not content_disposition: return None
        # Simplified regex, robust parsing might be needed.
        match = re.search(r"filename\*?=(?:(?:\"([^\"]+)\")|(?:UTF-8'')?([^;]+))", content_disposition, flags=re.IGNORECASE)
        if match:
            filename = match.group(1) or match.group(2)
            if filename:
                try:
                    import urllib.parse
                    return urllib.parse.unquote(filename)
                except Exception: return filename 
        return None

    def download_file_directly(self, 
                               url: str, 
                               file_name_override: Optional[str] = None, 
                               request_options: Optional[Dict[str, Any]] = None,
                               api_context_options: Optional[Dict[str, Any]] = None) -> str:
        """Downloads a file directly from a URL using Playwright's APIRequestContext."""
        if not all(hasattr(self, attr) for attr in ['playwright', 'logger', 'config', 'download_path', 'source_name_short', '_last_download_path', '_handle_and_raise_scraper_error']):
            raise ScraperError("DownloadMixin.download_file_directly is missing required attributes/methods from BaseScraper.")

        self._last_download_path = None
        api_request_context: Optional[APIRequestContext] = None
        operation_desc = f"downloading file directly from URL: {url}"
        self.logger.info(f"Starting {operation_desc}")

        try:
            api_context_params = api_context_options or {}
            api_request_context = self.playwright.request.new_context(**api_context_params)
            
            effective_request_options = request_options or {}
            # Add timeout from config if not in request_options
            if 'timeout' not in effective_request_options:
                effective_request_options['timeout'] = self.config.download_timeout_ms

            response = api_request_context.get(url, **effective_request_options)

            if not response.ok:
                # Not calling _handle_and_raise_scraper_error here because it's an API response, not a browser page error.
                # The context for screenshot/HTML saving is missing.
                error_message = f"Direct download request for {url} failed. Status: {response.status} - {response.status_text}. Body: {response.text()[:500]}"
                self.logger.error(error_message)
                raise ScraperError(error_message) # Raise directly

            filename = file_name_override or self._extract_filename_from_cd(response.headers.get('content-disposition'))
            if not filename:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path) if parsed_url.path else f"{self.source_name_short}_download"
            
            _, ext = os.path.splitext(filename)
            if not ext:
                content_type = response.headers.get('content-type', '').lower()
                import mimetypes
                ext = mimetypes.guess_extension(content_type.split(';')[0].strip()) or ".unknown"
                filename += ext
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_base_filename = "".join(c if c.isalnum() or c in ['.', '-'] else "_" for c in os.path.splitext(filename)[0])
            final_filename = f"{self.source_name_short}_{safe_base_filename}_{timestamp}{ext}"
            
            ensure_directory(self.download_path)
            save_path = os.path.join(self.download_path, final_filename)

            with open(save_path, 'wb') as f: f.write(response.body())
            
            self._last_download_path = save_path
            self.logger.info(f"Successfully {operation_desc}. File saved as '{save_path}'")
            return save_path

        except PlaywrightTimeoutError as e: # Timeout from API request context's get call
            # No page context for screenshot/HTML saving.
            self._handle_and_raise_scraper_error(e, f"timeout during {operation_desc}")
        except Exception as e:
            # No page context for screenshot/HTML saving unless it's a ScraperError already handled.
            if not isinstance(e, ScraperError): # Avoid re-wrapping if already a ScraperError
                 self._handle_and_raise_scraper_error(e, f"generic error during {operation_desc}")
            else:
                 raise # Re-raise if it's already a ScraperError from a lower call
        finally:
            if api_request_context: api_request_context.dispose()
        return "" # Should be unreachable


    def get_last_downloaded_path(self) -> Optional[str]:
        """Returns the path of the last successfully downloaded file."""
        if not hasattr(self, '_last_download_path'):
            self.logger.warning("_last_download_path attribute not found. Returning None.")
            return None
        return self._last_download_path
```
