import sys
import time
import logging
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.scrapers.acquisition_gateway import AcquisitionGatewayScraper
from app.exceptions import ScraperError

# Setup basic logging for the test script
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# StreamHandler for stdout (might not be captured, but keep for local testing)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)

# FileHandler to save logs to a file
Path("temp").mkdir(parents=True, exist_ok=True) # Ensure temp dir exists
file_handler = logging.FileHandler("temp/test_acq_gateway.log", mode='w') # Overwrite log each run
file_handler.setFormatter(log_formatter)

logger = logging.getLogger("test_acq_gateway")
logger.setLevel(logging.INFO)
logger.handlers = [] # Clear existing handlers if any
logger.addHandler(stream_handler)
logger.addHandler(file_handler)
logger.propagate = False # Prevent duplicate logging if root logger is also configured

# Silence SQLAlchemy INFO logs which can be noisy
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def test_navigation():
    logger.info("--- Starting Navigation Test ---")
    scraper = None
    navigation_time = -1
    success = False
    try:
        scraper = AcquisitionGatewayScraper(debug_mode=False) # Ensure headless operation
        scraper.setup_browser()

        logger.info("Calling navigate_to_forecast_page()...")
        start_time = time.time()
        try:
            scraper.navigate_to_forecast_page()
            navigation_time = time.time() - start_time
            logger.info(f"Navigation to forecast page completed in {navigation_time:.2f} seconds.")
            success = True
        except PlaywrightTimeoutError:
            navigation_time = time.time() - start_time
            logger.error(f"Navigation timed out after {navigation_time:.2f} seconds.")
            scraper._take_screenshot("navigation_timeout") # Use the scraper's method
            success = False
        except ScraperError as se:
            navigation_time = time.time() - start_time
            logger.error(f"ScraperError during navigation (after {navigation_time:.2f}s): {se}")
            scraper._take_screenshot("navigation_scraper_error")
            success = False
        except Exception as e:
            navigation_time = time.time() - start_time
            logger.error(f"Unexpected error during navigation (after {navigation_time:.2f}s): {e}")
            if scraper and scraper.page: # Check if page exists for screenshot
                 scraper._take_screenshot("navigation_unexpected_error")
            success = False

    finally:
        if scraper:
            scraper.cleanup_browser()
        logger.info(f"Navigation Test Summary: Success={success}, Duration={navigation_time:.2f}s")
        logger.info("--- Finished Navigation Test ---")
    assert success, "Navigation test failed"

def test_download_process():
    logger.info("--- Starting Download Process Test ---")
    scraper = None
    download_success = False
    try:
        scraper = AcquisitionGatewayScraper(debug_mode=False) # Ensure headless operation
        scraper.setup_browser()

        logger.info("Navigating to forecast page for download test...")
        try:
            scraper.navigate_to_forecast_page()
            logger.info("Navigation successful for download test.")
        except Exception as nav_e:
            logger.error(f"Navigation failed before download test could start: {nav_e}")
            if scraper and scraper.page:
                 scraper._take_screenshot("download_test_nav_failed")
            assert False, "Navigation failed before download test could start" # Fail test explicitly

        logger.info("Calling download_csv_file()...")
        try:
            download_file_path = scraper.download_csv_file()
            if download_file_path and Path(download_file_path).exists():
                logger.info(f"Download successful. File at: {download_file_path}")
                download_success = True
            else:
                logger.error("Download_csv_file returned None or file does not exist.")
                download_success = False
        except PlaywrightTimeoutError as pte:
            logger.error(f"PlaywrightTimeoutError during download process: {pte}")
            # Screenshot should be handled within download_csv_file now
            download_success = False
        except ScraperError as se:
            logger.error(f"ScraperError during download process: {se}")
            # Screenshot should be handled within download_csv_file now
            download_success = False
        except Exception as e:
            logger.error(f"Unexpected error during download_csv_file call: {e}")
            if scraper and scraper.page: # Check if page exists for screenshot
                 scraper._take_screenshot("download_test_unexpected_error")
            download_success = False

    finally:
        if scraper:
            scraper.cleanup_browser()
        logger.info(f"Download Process Test Summary: Success={download_success}")
        logger.info("--- Finished Download Process Test ---")
    assert download_success, "Download process test failed"

if __name__ == "__main__":
    print("--- TEST SCRIPT EXECUTION STARTED ---") # More prominent print
    sys.stdout.flush() # Explicit flush

    # Create a dummy file to check for execution side-effect
    try:
        with open("/tmp/test_acq_gateway_executed.txt", "w") as f:
            f.write("executed")
        print("--- Dummy file created in /tmp ---")
        sys.stdout.flush()
    except Exception as e:
        print(f"--- Error creating dummy file: {e} ---")
        sys.stdout.flush()

    logger.info("Starting Acquisition Gateway Scraper Tests...")

    # Ensure temp directory exists
    Path("temp").mkdir(parents=True, exist_ok=True)

    nav_success = test_navigation()

    if nav_success:
        logger.info("Navigation test passed. Proceeding to download test.")
        test_download_process()
    else:
        logger.warning("Navigation test failed. Skipping download test.")

    logger.info("Acquisition Gateway Scraper Tests Finished.")
