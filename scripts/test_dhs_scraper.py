import sys
import time
import logging # Keep this for now, but complex logger setup moved down
from pathlib import Path
import os

# Determine project_root early for marker files
project_root = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = project_root / "temp"
LOG_FILE_PATH = project_root / "temp" / "dhs_test_run.log"

# Add project root to Python path (globally for pytest)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Main imports at global scope for pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from app.exceptions import ScraperError
from app.core.scrapers.dhs_scraper import DHSForecastScraper
from app.config import current_config # Might be needed by scraper or test setup

# --- Basic file I/O test function (minimal imports) ---
def initial_marker_and_log(message): # This can still be used for early __main__ block checks
    try:
        Path("temp").mkdir(parents=True, exist_ok=True)
        marker_path = project_root / "temp" / "dhs_test_marker.txt"
        with open(marker_path, "a") as f: # Append mode
            f.write(f"{time.strftime('%Y%m%d_%H%M%S')} - {message}\n")
        # This print might not show up, but the file is the key
        print(f"MARKER: {message}", file=sys.stderr)
        sys.stderr.flush()
    except Exception as e:
        print(f"CRITICAL MARKER ERROR: {e}", file=sys.stderr)
        sys.stderr.flush()
# --- End basic file I/O test ---

# --- Global logger variable, configured once ---
# Ensure directories exist (globally)
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

log_formatter_global = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
# StreamHandler for stdout
stream_handler_global = logging.StreamHandler(sys.stdout)
stream_handler_global.setFormatter(log_formatter_global)
# FileHandler to save logs
file_handler_global = logging.FileHandler(LOG_FILE_PATH, mode='w')
file_handler_global.setFormatter(log_formatter_global)

logger = logging.getLogger("test_dhs_scraper")
logger.setLevel(logging.INFO)
logger.handlers = []
logger.addHandler(stream_handler_global)
logger.addHandler(file_handler_global)
logger.propagate = False
logger.info("Logger configured globally.")


def configure_logger(): # This function becomes redundant if logger is configured globally
    pass


def take_screenshot_manual(page, filename_prefix: str):
    """Manual screenshot helper for the test script."""
    # Logger is now configured globally
    if page:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_prefix = "".join(c if c.isalnum() else "_" for c in filename_prefix)
        path = SCREENSHOT_DIR / f"dhs_test_{safe_prefix}_{timestamp}.png"
        try:
            page.screenshot(path=str(path))
            current_logger.info(f"Screenshot saved to {path}")
            return str(path)
        except Exception as e:
            current_logger.error(f"Failed to take screenshot: {e}")
    else:
        current_logger.warning("Page object not available for screenshot.")
    return None

def test_dhs_navigation_and_wait():

    logger.info("--- Starting DHS Navigation and Initial Wait Test ---") # Logger is globally available
    scraper = None
    nav_success = False
    total_time = 0
    log_entry_counter = 0

    def log_and_flush(msg, level="info"):
        nonlocal log_entry_counter
        log_entry_counter += 1
        full_msg = f"[Entry {log_entry_counter}] {msg}"
        if level == "info":
            logger.info(full_msg)
        elif level == "error":
            logger.error(full_msg)
        elif level == "warning":
            logger.warning(full_msg)
        # Explicitly flush file handler
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()

    try:
        log_and_flush("Instantiating DHSForecastScraper.")
        scraper = DHSForecastScraper(debug_mode=False)
        log_and_flush("Setting up browser.")
        scraper.setup_browser()
        log_and_flush("Browser setup complete.")

        # 1. Navigate to URL
        nav_start_time = time.time()
        log_and_flush(f"Navigating to {scraper.base_url} with 60s timeout for goto...")
        scraper.page.goto(scraper.base_url, wait_until='load', timeout=60000)
        log_and_flush("goto command finished. Waiting for load state (60s timeout)...")
        scraper.page.wait_for_load_state('load', timeout=60000)
        nav_time = time.time() - nav_start_time
        log_and_flush(f"Navigation to {scraper.base_url} successful in {nav_time:.2f}s.")
        total_time += nav_time

        # 2. Explicit 10-second wait
        wait_start_time = time.time()
        log_and_flush("Executing 10-second explicit wait (page.wait_for_timeout)...")
        scraper.page.wait_for_timeout(10000)
        wait_time = time.time() - wait_start_time
        log_and_flush(f"Explicit wait completed in {wait_time:.2f}s.")
        total_time += wait_time
        nav_success = True
        log_and_flush("Navigation and wait sequence marked successful.")

    except PlaywrightTimeoutError as pte:
        log_and_flush(f"PlaywrightTimeoutError during navigation/wait: {pte}", level="error")
        if scraper and scraper.page:
            take_screenshot_manual(scraper.page, "dhs_nav_wait_timeout")
    except ScraperError as se:
        log_and_flush(f"ScraperError during navigation/wait: {se}", level="error")
    except Exception as e:
        log_and_flush(f"Unexpected error during navigation/wait: {e}", level="error")
        if scraper and scraper.page:
            take_screenshot_manual(scraper.page, "dhs_nav_wait_unexpected_error")
    finally:
        log_and_flush("Entering finally block for navigation test.")
        if scraper:
            log_and_flush("Cleaning up browser.")
            scraper.cleanup_browser()
            log_and_flush("Browser cleanup finished.")
        logger.info(f"DHS Navigation and Initial Wait Test Summary: Success={nav_success}, TotalTime={total_time:.2f}s") # Use logger for summary
        logger.info("--- Finished DHS Navigation and Initial Wait Test ---") # Use logger for summary
        # Final flush for summary
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
    return nav_success

def test_dhs_download_action():
    logger.info("--- Starting DHS Button Interaction and Download Test ---")
    scraper = None
    download_test_success = False
    try:
        scraper = DHSForecastScraper(debug_mode=False)
        scraper.setup_browser()

        # Navigate and initial wait
        logger.info(f"Navigating to {scraper.base_url} for download test...")
        scraper.page.goto(scraper.base_url, wait_until='load', timeout=60000)
        scraper.page.wait_for_load_state('load', timeout=60000)
        logger.info("Navigation successful. Executing 10-second explicit wait...")
        scraper.page.wait_for_timeout(10000)
        logger.info("Initial wait completed.")

        # Replicate _click_and_download logic for 'button.buttons-csv'
        download_trigger_selector = 'button.buttons-csv'
        wait_for_trigger_timeout_ms = 30000
        download_timeout_ms = 90000 # Default from BaseScraper's helper

        logger.info(f"Locating download trigger: {download_trigger_selector}")
        trigger_element = scraper.page.locator(download_trigger_selector)

        # Test visibility
        visible_success = False
        visible_start_time = time.time()
        try:
            trigger_element.wait_for(state='visible', timeout=wait_for_trigger_timeout_ms)
            visible_time = time.time() - visible_start_time
            logger.info(f"Download trigger '{download_trigger_selector}' became visible in {visible_time:.2f}s.")
            visible_success = True
        except PlaywrightTimeoutError as e_vis:
            visible_time = time.time() - visible_start_time
            logger.error(f"Timeout ({visible_time:.2f}s) waiting for download trigger '{download_trigger_selector}' to be visible: {e_vis}")
            take_screenshot_manual(scraper.page, "dhs_trigger_visible_timeout")
            raise ScraperError(f"DHS Download trigger not visible: {e_vis}") from e_vis

        if not visible_success: # Should have been raised already, but as a safeguard
            return False

        # Test click and download expectation
        logger.info(f"Attempting to click on download trigger '{download_trigger_selector}' and expecting download...")
        click_initiated_log = False
        download_expected_log = False
        download_path = None

        download_expect_start_time = time.time()
        try:
            with scraper.page.expect_download(timeout=download_timeout_ms) as download_info:
                download_expected_log = True
                logger.info(f"page.expect_download(timeout={download_timeout_ms}ms) started.")
                logger.info(f"Attempting click on '{download_trigger_selector}'...")
                trigger_element.click()
                click_initiated_log = True
                logger.info(f"Click on '{download_trigger_selector}' initiated.")

            download = download_info.value
            download_time_taken = time.time() - download_expect_start_time
            logger.info(f"Download event received after {download_time_taken:.2f}s.")
            logger.info(f"Download suggested filename: {download.suggested_filename}")

            # Manually save (mimicking _handle_download from BaseScraper)
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            final_filename = f"dhs_test_download_{timestamp_str}.csv" # Assume CSV for test
            download_path = SCREENSHOT_DIR / final_filename # Save in temp for test
            download.save_as(str(download_path))
            logger.info(f"Test download saved to: {download_path}")

            if os.path.exists(download_path) and os.path.getsize(download_path) > 0:
                logger.info("Download successful and file is not empty.")
                download_test_success = True
            else:
                logger.error(f"Download failed: File not found at {download_path} or is empty.")

        except PlaywrightTimeoutError as e_dl:
            download_time_taken = time.time() - download_expect_start_time
            if not click_initiated_log: logger.error("Click might not have been initiated before timeout.")
            if not download_expected_log: logger.error("page.expect_download might not have started correctly.")
            logger.error(f"Timeout ({download_time_taken:.2f}s) during expect_download for '{download_trigger_selector}': {e_dl}")
            take_screenshot_manual(scraper.page, "dhs_expect_download_timeout")
        except Exception as e_click_dl:
            download_time_taken = time.time() - download_expect_start_time
            logger.error(f"Error ({download_time_taken:.2f}s) during click/expect_download for '{download_trigger_selector}': {e_click_dl}", exc_info=True)
            take_screenshot_manual(scraper.page, "dhs_click_download_error")

    except PlaywrightTimeoutError as pte:
        logger.error(f"PlaywrightTimeoutError during DHS download test: {pte}")
        if scraper and scraper.page:
             take_screenshot_manual(scraper.page, "dhs_download_test_overall_timeout")
    except ScraperError as se:
        logger.error(f"ScraperError during DHS download test: {se}")
    except Exception as e:
        logger.error(f"Unexpected error during DHS download test: {e}", exc_info=True)
        if scraper and scraper.page:
            take_screenshot_manual(scraper.page, "dhs_download_test_unexpected_error")
    finally:
        if scraper:
            scraper.cleanup_browser()
        logger.info(f"DHS Button Interaction and Download Test Summary: Success={download_test_success}")
        logger.info("--- Finished DHS Button Interaction and Download Test ---")
    return download_test_success

if __name__ == "__main__":
    initial_marker_and_log("Script execution started in __main__.") # This still uses basic file I/O for very first marker

    # Imports are now global, path is set globally. Logger is configured globally.
    logger.info(">>> Starting DHS Scraper Tests (imports and logger should be globally available) <<<")

    nav_wait_completed = test_dhs_navigation_and_wait()
    if nav_wait_completed:
        logger.info("Navigation and initial wait test successful. Proceeding to download action test.")
        test_dhs_download_action()
    else:
        logger.warning("Skipping download action test due to navigation/initial wait failure.")

    logger.info(">>> DHS Scraper Tests Finished <<<")
    # Final flush of all handlers at the very end
    for handler in logger.handlers: # Logger is guaranteed to be configured
        handler.flush()
