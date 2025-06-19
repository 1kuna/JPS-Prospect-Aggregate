# Scraper Code Duplication Analysis Report

This report details common patterns and areas of code duplication across the nine analyzed scrapers.

## 1. Navigation

*   **Retry Logic:**
    *   `dot_scraper.py`: Implements explicit retry logic for navigation (`navigate_to_forecast_page`) with multiple attempts using different `wait_until` strategies (`load`, `domcontentloaded`, `networkidle`, `commit`) and progressive delays. It specifically catches `PlaywrightTimeoutError`, `ERR_HTTP2_PROTOCOL_ERROR`, and `ERR_TIMED_OUT`.
    *   Other scrapers generally rely on Playwright's default retry mechanisms or simple `try-except PlaywrightTimeoutError` blocks for navigation and element interactions, without complex custom retry loops.
    *   `acquisition_gateway.py`: Has a fallback from standard click to JavaScript click if the standard click fails/times out.

*   **Timeout Handling:**
    *   Timeouts are generally handled using `try-except PlaywrightTimeoutError`.
    *   Common timeout values:
        *   Page navigation/load: `60000`ms, `90000`ms, `120000`ms (e.g., `dot_scraper`, `acquisition_gateway`, `treasury_scraper`).
        *   Element visibility/interaction: `15000`ms, `30000`ms, `60000`ms (e.g., `acquisition_gateway`, `dot_scraper`, `treasury_scraper`, `doj_scraper`).
        *   `expect_download`: Often longer, `60000`ms to `120000`ms.
    *   `BaseScraper`'s `_click_and_download` method (used by `hhs_forecast.py`, `dhs_scraper.py`) centralizes some timeout configurations for clicks and downloads.

*   **Page State Management:**
    *   `page.wait_for_load_state()`: Commonly used with states like `load`, `domcontentloaded`, `networkidle`.
        *   `acquisition_gateway.py`: Uses `page.wait_for_load_state('load', timeout=90000)` and an additional `page.wait_for_timeout(5000)`.
        *   `dot_scraper.py`: Tries various `wait_until` options in its navigation retry logic.
        *   `treasury_scraper.py`: Uses `page.wait_for_load_state('load', timeout=90000)`.
    *   `locator.wait_for(state='visible', timeout=...)`: Very common before interacting with elements (e.g., clicking buttons).
    *   `page.wait_for_timeout()`: Used for explicit pauses, often after actions like clicks or before navigation attempts.
        *   `acquisition_gateway.py`: `page.wait_for_timeout(5000)` after page load, `page.wait_for_timeout(2000)` after download starts.
        *   `dot_scraper.py`: `time.sleep()` used extensively within its retry logic, `page.wait_for_timeout(2000)` after download.
        *   `dhs_scraper.py`: `page.wait_for_timeout(10000)` before interacting.
        *   Most scrapers: `page.wait_for_timeout(2000)` after download initiation.
    *   `BaseScraper._click_and_download`: Has a `pre_click_wait_ms` parameter for waiting after a preliminary click (e.g., "View All") before the main download click.

*   **URL Construction and Management:**
    *   Base URLs are stored in `active_config` and passed to the scraper's `__init__`.
    *   `self.navigate_to_url()` (from `BaseScraper`): Standard method for navigating to `self.base_url`.
    *   `dos_scraper.py`: Downloads directly from a hardcoded file URL (`https://www.state.gov/wp-content/uploads/2025/02/FY25-Procurement-Forecast-2.xlsx`) using `api_request_context.get()`, bypassing page navigation for download.
    *   `doc_scraper.py`: Uses `urljoin(self.page.url, href)` to construct absolute URLs for download links found on the page.

## 2. Download Mechanisms

*   **File Type Detection:**
    *   Primarily implicit through the download link/button (e.g., link ends with `.xlsx` or button text is "Download CSV").
    *   `BaseScraper._handle_download`: Attempts to get the extension from `download.suggested_filename`.
    *   `dos_scraper.py`: Derives extension from the hardcoded URL, defaults to `.xlsx`, and logs `Content-Type` for potential validation.
    *   `treasury_scraper.py`: Expects an HTML table masquerading as an `.xls` file, attempts `pd.read_html` first, then `pd.read_excel` as a fallback.
    *   `dhs_scraper.py`: Tries `pd.read_csv` first, then `pd.read_excel` for a `.csv` file that might actually be Excel.

*   **Download Triggers:**
    *   `page.locator(...).click()`: Most common method.
    *   `page.evaluate("document.querySelector(...).click();")`: Used as a fallback in `acquisition_gateway.py` and `treasury_scraper.py` if standard click fails.
    *   `locator.dispatch_event('click')`: Used in `doc_scraper.py`.
    *   `with self.page.expect_download(timeout=...)`: Universally used to wrap the click action that triggers the download.
        *   `dot_scraper.py`: Uses `with self.context.expect_page()` for links opening in a new tab, then `with new_page.expect_download()` on the new page.
    *   `BaseScraper._click_and_download`: Centralizes download trigger logic for `hhs_forecast.py` and `dhs_scraper.py`.

*   **File Saving Procedures:**
    *   `BaseScraper._handle_download`: Central callback for the `page.on("download", ...)` event. It constructs a filename using `self.source_name`, a timestamp, and the original extension. Files are saved to `self.download_path`.
    *   All scrapers (except `dos_scraper.py` for direct download) rely on this `_handle_download` mechanism.
    *   `dos_scraper.py` (direct download): Manually constructs filename and path, uses `response.body()` and `open(final_save_path, 'wb').write()`.
    *   Verification: Most scrapers check `if not self._last_download_path or not os.path.exists(self._last_download_path)` after download. Some log Playwright's temporary path for debugging if `_last_download_path` is not set.
    *   `dot_scraper.py`: Has fallback logic to manually copy from Playwright's temp path if `_last_download_path` isn't set correctly.

*   **Use of Playwright's `download` event:**
    *   `self.page.on("download", self._handle_download)`: Set up in `BaseScraper.setup_browser()`, so it's active for all scrapers using page-based downloads.
    *   `dot_scraper.py`: Also sets `new_page.on("download", self._handle_download)` for downloads happening in a new tab.

## 3. Data Processing

*   **Data Extraction from Web Pages:**
    *   Not a primary focus for these scrapers as most download files.
    *   `ssa_scraper.py`: Uses `self.page.query_selector_all(selector)` and `link.get_attribute('href')` to find the Excel download link.
    *   `doc_scraper.py`: Uses `self.page.locator(selector)` and `locator.first.get_attribute('href')` for the download link.

*   **Data Transformation (Pandas heavy):**
    *   All scrapers use a `process_func(self, file_path: str)` method.
    *   `pd.read_csv()`, `pd.read_excel()`, `pd.read_html()`: Common for reading downloaded files. Specific parameters (header row, sheet name) vary.
        *   `treasury_scraper.py`: `pd.read_html()` then `pd.read_excel()` fallback.
        *   `dhs_scraper.py`: `pd.read_csv()` then `pd.read_excel()` fallback.
    *   `df.dropna(how='all', inplace=True)`: Common initial step.
    *   `df.rename(columns=rename_map, inplace=True)`: Universal for mapping source columns to standardized/intermediate names. `rename_map` is defined in each scraper.
    *   Date Parsing:
        *   `pd.to_datetime(df[column], errors='coerce').dt.date`: Common for converting date strings.
        *   `pd.to_datetime(df[column], errors='coerce').dt.year.astype('Int64')`: For extracting fiscal year.
        *   `fiscal_quarter_to_date()` (from `app.utils.parsing`): Used by `dot_scraper.py`, `treasury_scraper.py`, `doc_scraper.py`, `dhs_scraper.py`, `doj_scraper.py` to convert fiscal quarter strings (e.g., "FY24 Q1") to dates and fiscal years.
    *   Value Parsing:
        *   `parse_value_range()` (from `app.utils.parsing`): Used by `dot_scraper.py`, `ssa_scraper.py`, `treasury_scraper.py`, `hhs_forecast.py`, `doc_scraper.py`, `dhs_scraper.py`, `doj_scraper.py` to extract numeric values and units from string ranges (e.g., "$1M - $5M").
    *   Place of Performance Parsing:
        *   `split_place()` (from `app.utils.parsing`): Used by `dot_scraper.py`, `ssa_scraper.py`, `treasury_scraper.py`, `doj_scraper.py` to split city/state strings.
        *   Many scrapers default `place_country` to 'USA'.
    *   Setting default/missing values: `df[column] = None` or `df[column] = pd.NA`.
    *   `df.drop(columns=[...], errors='ignore', inplace=True)`: To remove raw/intermediate columns after processing.

*   **Data Validation:**
    *   `if df.empty:`: Common check after loading data.
    *   Implicit validation through `pd.to_datetime(errors='coerce')` and `pd.to_numeric(errors='coerce')` which turn unparseable values into `NaT`/`NaN`.
    *   `KeyError` in `try-except` blocks during `df.rename` or column access can indicate schema changes.

*   **Logic for Preparing Data for Database Insertion:**
    *   `BaseScraper._process_and_load_data(df, column_rename_map, prospect_model_fields, fields_for_id_hash)`: This is the core method used by all scrapers.
        *   `column_rename_map`: A dictionary mapping current DataFrame column names to `Prospect` model field names.
        *   `prospect_model_fields`: List of valid fields in the `Prospect` model.
        *   `fields_for_id_hash`: List of DataFrame column names used to generate a unique `id_hash` for each prospect. This list varies significantly between scrapers, reflecting efforts to define uniqueness based on available data. Some include `native_id`, `title`, `description`, `naics`, location fields, and even `row_index` for sources with potential duplicates (e.g., `treasury_scraper`, `dos_scraper`, `hhs_forecast`).
    *   The `_process_and_load_data` method handles:
        *   Renaming columns to match model fields.
        *   Creating an `extra_data` dictionary for columns not in `prospect_model_fields`.
        *   Generating `id_hash`.
        *   Converting DataFrame rows to `Prospect` model instances.
        *   Bulk upserting data using `bulk_upsert_prospects`.

## 4. Error Handling

*   **Common `try-except` block patterns:**
    *   Outer `try-except Exception as e:` in main `scrape` or download/process methods, often calling `handle_scraper_error(e, self.source_name, "Descriptive message")` and then re-raising as `ScraperError`.
    *   `try-except PlaywrightTimeoutError as e:` for navigation and interaction timeouts.
    *   `try-except FileNotFoundError:`, `pd.errors.EmptyDataError:`, `KeyError as e:` within `process_func`.
    *   `BaseScraper.scrape_with_structure` provides a common `try-except` wrapper around `setup_func`, `extract_func`, and `process_func`.

*   **Specific Exceptions Caught and Handled:**
    *   `PlaywrightTimeoutError`: Most common for UI interactions. Often results in logging, screenshot capture (e.g., `dot_scraper`, `treasury_scraper`), and re-raising as `ScraperError`.
    *   `ScraperError`: Custom exception, often raised after catching a more specific error.
    *   `FileNotFoundError`, `pd.errors.EmptyDataError`, `KeyError`: Handled in `process_func` to deal with issues in downloaded files or data structure changes.
    *   `dot_scraper.py`: Specifically catches string patterns like `"ERR_HTTP2_PROTOCOL_ERROR"` and `"ERR_TIMED_OUT"` in its navigation retry logic.
    *   `BaseScraper._click_and_download`: Catches `PlaywrightTimeoutError` and general `Exception`, logs them, and re-raises them as `ScraperError`.

*   **Reporting or Logging of Errors:**
    *   `self.logger.error()`: Used extensively. Often includes `traceback.format_exc()` for full stack traces.
    *   `handle_scraper_error(e, self.source_name, message)`: Utility function used by many scrapers to standardize error logging/reporting (though its internal implementation is not visible here, it likely logs the error and potentially updates a status).
    *   Screenshots on timeout: `dot_scraper.py`, `treasury_scraper.py`, `ssa_scraper.py` (if link not found), `doc_scraper.py` (if link not found).
    *   Saving page HTML on error: `ssa_scraper.py`, `doc_scraper.py` (if link not found).

## 5. Logging

*   **What Information is Logged:**
    *   Scraper initialization: `logger.bind(name="scraper.X")`.
    *   Navigation steps: `Navigating to {url}`, `Page loaded.`, `Waiting for selector...`.
    *   Download process: `Clicking X and waiting for download...`, `Download process completed. File saved at: {path}`.
    *   Processing steps: `Processing downloaded file: {file_path}`, `Loaded {N} rows from {file_path}`.
    *   Errors: Detailed error messages, often with exception details and stack traces.
    *   Debug information: Selector attempts (`ssa_scraper`), specific states or values during execution.
    *   Success/failure of operations.
    *   Number of records processed/loaded.

*   **Consistency of Logging Messages and Levels:**
    *   `self.logger.info()`: Most common for general progress.
    *   `self.logger.error()`: For errors.
    *   `self.logger.warning()`: For non-critical issues or fallbacks (e.g., "Standard click timed out, trying JavaScript click.").
    *   Log messages are generally informative. There's a good degree of consistency in the *types* of events logged (navigation, download, processing).
    *   The exact wording and level of detail can vary slightly between scrapers, especially older ones or those with more complex logic (e.g., `dot_scraper`).
    *   The use of `logger.bind(name="scraper.{source_name_short}")` provides good context for logs.

## 6. Browser Interaction (Playwright specific)

*   **Browser Launch and Context Setup:**
    *   Handled by `BaseScraper.setup_browser()` and `BaseScraper.close_browser()`. This includes:
        *   Launching Playwright (`sync_playwright().start()`).
        *   Creating a new browser instance (`self.playwright.chromium.launch()`).
        *   Creating a new browser context (`self.browser.new_context()`).
        *   Creating a new page (`self.context.new_page()`).
        *   Setting up download handling: `self.page.on("download", self._handle_download)`.
    *   `use_stealth=True` is passed by `acquisition_gateway.py` and `dot_scraper.py` to `BaseScraper.__init__`, presumably to enable anti-detection measures.

*   **Common Playwright Actions Used:**
    *   `self.page.goto(url, **params)`
    *   `self.page.wait_for_load_state(state, timeout=...)`
    *   `self.page.locator(selector)`
    *   `locator.click(timeout=...)`
    *   `locator.wait_for(state='visible', timeout=...)`
    *   `locator.get_attribute(name)`
    *   `locator.first` (e.g. `doc_scraper.py`)
    *   `self.page.expect_download(timeout=...)`
    *   `self.page.evaluate(js_expression)` (for JS clicks)
    *   `self.page.screenshot(path=...)`
    *   `self.page.content()`
    *   `self.page.wait_for_timeout(ms)`
    *   `self.page.query_selector_all(selector)` (`ssa_scraper.py`)
    *   `self.context.expect_page(timeout=...)` (`dot_scraper.py`)
    *   `download_locator.dispatch_event('click')` (`doc_scraper.py`)
    *   `api_request_context.get()` (`dos_scraper.py` for direct download)

*   **Use of Selectors and Locators:**
    *   CSS Selectors: Most common.
        *   By ID: `button#export-0` (`acquisition_gateway.py`)
        *   By text: `button:has-text('Apply')` (`dot_scraper.py`), `a:has-text("Download the Excel File")` (`doj_scraper.py`)
        *   By attribute: `a[href$=".xlsx"]` (`ssa_scraper.py`)
        *   By class: `button.buttons-csv` (`dhs_scraper.py`)
        *   Combinations: `button[data-cy="viewAllBtn"]` (`hhs_forecast.py`)
    *   XPath Selectors:
        *   `treasury_scraper.py`: `//lightning-button/button[contains(text(), 'Download Opportunity Data')]`
    *   Locators are typically defined as string variables and then passed to `self.page.locator()`.
    *   Some scrapers try multiple selectors to find an element (e.g., `ssa_scraper.py` for the Excel link).

This analysis should provide a good foundation for identifying areas where mixins or base class enhancements can reduce duplication and standardize approaches.
