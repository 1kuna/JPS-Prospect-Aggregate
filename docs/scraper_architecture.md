# Scraper Architecture Guide

## 1. Overview

This document describes the refactored scraper architecture designed to reduce code duplication, improve maintainability, and standardize scraper development. The architecture is built upon a `BaseScraper`, several Mixin classes for common functionalities, a configuration-driven approach, and specialized base scrapers.

Key components:
- `BaseScraper`: Core setup, teardown, and orchestration.
- Mixins: `NavigationMixin`, `DownloadMixin`, `DataProcessingMixin`.
- Configuration Dataclasses: For scraper-specific settings.
- Specialized Scrapers: e.g., `PageInteractionScraper`.

## 2. Core Components

### 2.1. `BaseScraper` (`app.core.base_scraper.BaseScraper`)

- **Role:** Handles Playwright browser initialization (`setup_browser`), context/page creation, and closing (`close_browser`). Manages the main configuration object (`self.config`). Provides the `scrape_with_structure` method for orchestrating scraper execution through distinct setup, extraction, and processing phases. Initializes the logger. Handles top-level error catching and standardized error reporting via `_handle_and_raise_scraper_error`.
- **Configuration:** Takes a `BaseScraperConfig` (or subclass) instance. Key config fields used: `source_name`, `base_url`, timeouts, error handling flags (`screenshot_on_error`, `save_html_on_error`), `use_stealth`.
- **Key Methods:**
    - `__init__(self, config: BaseScraperConfig, debug_mode: Optional[bool] = None)`
    - `setup_browser()`
    - `close_browser()` (corrected from `close_browser` to `cleanup_browser` as per implementation)
    - `cleanup_browser()` 
    - `scrape_with_structure(self, setup_func, extract_func, process_func)` (Corrected args)
    - `_handle_and_raise_scraper_error(self, error: Exception, operation_description: str)`
    - `_save_error_screenshot(self, prefix: str = "error")`
    - `_save_error_html(self, prefix: str = "error")`

### 2.2. Mixins (`app.core.mixins.*`)

Mixins provide reusable functionalities that can be composed into scraper classes. They rely on `self` (the scraper instance) having `self.page`, `self.context`, `self.logger`, `self.config`, `self.db_session` (if applicable, though `DataProcessingMixin` uses `bulk_upsert_prospects` which manages its own session), etc.

#### 2.2.1. `NavigationMixin`

- **Purpose:** Standardizes page navigation and element interactions.
- **Key Methods:**
    - `navigate_to_url(self, url: str, wait_until_state: Optional[str] = 'load', timeout_ms: Optional[int] = None) -> None`
    - `click_element(self, selector: str, timeout_ms: Optional[int] = None, wait_for_navigation: bool = False, navigation_wait_until_state: Optional[str] = 'load', js_click_fallback: bool = False, click_options: Optional[Dict[str, Any]] = None) -> None`
    - `wait_for_selector(self, selector: str, timeout_ms: Optional[int] = None, visible: bool = True, hidden: bool = False, state: Optional[str] = None) -> None`
    - `fill_input(self, selector: str, text: str, timeout_ms: Optional[int] = None, fill_options: Optional[Dict[str, Any]] = None) -> None`
    - `get_element_attribute(self, selector: str, attribute_name: str, timeout_ms: Optional[int] = None) -> Optional[str]`
    - `get_element_text(self, selector: str, timeout_ms: Optional[int] = None) -> Optional[str]`
    - `wait_for_load_state(self, state: str = 'load', timeout_ms: Optional[int] = None) -> None`
    - `wait_for_timeout(self, timeout_ms: int) -> None`
- **Configuration:** Uses `self.config.navigation_timeout_ms`, `self.config.interaction_timeout_ms`, and error flags from `self.config`.

#### 2.2.2. `DownloadMixin`

- **Purpose:** Handles file downloading operations.
- **Key Methods:**
    - `_handle_download_event(self, download: Download) -> None`: Callback for Playwright's download event, saves file.
    - `download_file_via_click(self, click_selector: str, expect_download_timeout: Optional[int] = None, ...) -> str`
    - `download_file_directly(self, url: str, file_name_override: Optional[str] = None, ...) -> str`
    - `get_last_downloaded_path(self) -> Optional[str]`
- **Configuration:** Uses `self.config.download_timeout_ms`, `self.config.default_wait_after_download_ms`. Relies on `BaseScraper` (specifically `setup_browser`) to register `_handle_download_event` for the `page.on('download', ...)` event.

#### 2.2.3. `DataProcessingMixin`

- **Purpose:** Standardizes reading files, transforming data (using pandas), and loading to the database.
- **Key Methods:**
    - `_determine_file_type(self, file_path: str, file_type_hint: Optional[str] = None) -> str`
    - `read_file_to_dataframe(self, file_path: str, file_type_hint: Optional[str] = None, read_options: Optional[Dict[str, Any]] = None) -> pd.DataFrame`
    - `transform_dataframe(self, df: pd.DataFrame, config_params: Any) -> pd.DataFrame`: Applies renaming, type conversions, parsing (dates, values, places using `app.utils.parsing`), and custom transformations.
    - `prepare_and_load_data(self, df: pd.DataFrame, config_params: Any) -> int`: Generates `id_hash`, maps columns to DB schema, handles `extra_data`, and calls `bulk_upsert_prospects`.
- **Configuration:** Heavily driven by `config_params` passed to its methods, typically from a nested structure within the scraper's main config (e.g., `self.config.data_processing_rules`). This includes column maps, parsing rules, `fields_for_id_hash`, etc.

### 2.3. Configuration System (`app.core.configs.*`)

- **`BaseScraperConfig` (`app.core.configs.base_config.BaseScraperConfig`):** Base dataclass for all scraper configurations. Contains common fields like `source_name`, `base_url`, `use_stealth`, various timeouts, and error handling flags.
- **Scraper-Specific Configs (e.g., `app.core.scrapers.configs.acquisition_gateway_config.AcquisitionGatewayConfig`):**
    - Inherit from `BaseScraperConfig`.
    - Define all scraper-specific parameters (selectors, specific URLs or URL patterns, file types, data processing rules, etc.).
    - **Data Processing Rules:** Often a nested dataclass (e.g., `DataProcessingRules` as defined in `AcquisitionGatewayConfig`) within the specific config to group all parameters for `DataProcessingMixin`. This includes `raw_column_rename_map`, `date_column_configs`, `value_column_configs`, `fiscal_year_configs`, `place_column_configs`, `db_column_rename_map`, `fields_for_id_hash`, `custom_transform_functions`, etc.
- **Instantiation:** Config objects are instantiated (typically by a scraper runner or service) and passed to the scraper's `__init__`.

### 2.4. Specialized Scrapers (`app.core.specialized_scrapers.*`)

- **Purpose:** Pre-compose `BaseScraper` with common sets of mixins to provide convenient base classes for specific types of scrapers.
- **Example: `PageInteractionScraper(NavigationMixin, DownloadMixin, DataProcessingMixin, BaseScraper)`:**
    - A general-purpose scraper base for sites requiring page navigation, file download (often via clicks), and subsequent data processing.

## 3. Developing a New Scraper

1.  **Create Configuration Dataclass:**
    - In `app/core/scrapers/configs/your_scraper_name_config.py`.
    - Define a class `YourScraperNameConfig(BaseScraperConfig)`.
    - Add all scraper-specific fields: selectors, specific URLs or patterns, file type hints.
    - Define a nested `DataProcessingRules` dataclass instance within this config (e.g., `data_processing_rules: DataProcessingRules = field(default_factory=DataProcessingRules)`) and populate its fields: `raw_column_rename_map`, `date_column_configs`, `value_column_configs`, `fiscal_year_configs`, `place_column_configs`, `db_column_rename_map`, `fields_for_id_hash`, `custom_transform_functions`.
2.  **Create Scraper Class:**
    - In `app/core/scrapers/your_scraper_name.py`.
    - Inherit from `PageInteractionScraper` (or another suitable specialized scraper, or `BaseScraper` + relevant mixins directly).
    - Implement `__init__(self, config: YourScraperNameConfig, debug_mode: Optional[bool] = None): super().__init__(config, debug_mode)`.
3.  **Implement Core Scraper Logic (using `scrape_with_structure`):**
    - Define the three main operational methods:
        - `def _setup_method(self) -> None:` (e.g., `self.navigate_to_url(self.config.target_page_url)`)
        - `def _extract_method(self) -> Optional[str]:` (e.g., `return self.download_file_via_click(...)` or `self.download_file_directly(...)`)
        - `def _process_method(self, file_path: Optional[str]) -> Optional[int]:`
            - Handle `if not file_path: return 0`.
            - `df = self.read_file_to_dataframe(file_path, file_type_hint=self.config.file_type_hint, read_options=self.config.read_options_override or None)`
            - `df = self.transform_dataframe(df, config_params=self.config.data_processing_rules)`
            - `loaded_count = self.prepare_and_load_data(df, config_params=self.config.data_processing_rules)`
            - `return loaded_count`
    - Implement the main `scrape` method:
        - `def scrape(self): return self.scrape_with_structure(setup_func=self._setup_method, extract_func=self._extract_method, process_func=self._process_method)`
4.  **Add Custom Transformations (if needed):**
    - Implement methods on your scraper class for any unique data transformations (e.g., `def my_custom_logic(self, df: pd.DataFrame) -> pd.DataFrame:`).
    - List these method names (as strings) in your scraper's config: `data_processing_rules.custom_transform_functions = ["my_custom_logic"]`. `DataProcessingMixin.transform_dataframe` will call them.
5.  **Instantiate and Run:** Update scraper execution scripts (e.g., `scraper_service.py` or `main.py`) to instantiate your new scraper with its config object and call its `run()` or `scrape()` method.

## 4. Logging and Error Handling

- **Logging:** The logger is bound with the scraper's `source_name_short` in `BaseScraper.__init__`. Mixins and scraper methods use `self.logger` for INFO, WARNING, ERROR level logging. Log messages are designed to provide context about the operation being performed.
- **Error Handling:**
    - Mixin methods and `BaseScraper` methods raise `ScraperError` for issues encountered during scraping operations.
    - `BaseScraper._handle_and_raise_scraper_error(self, error: Exception, operation_description: str)` standardizes the formatting of error messages and ensures the original exception is chained. This method is used internally by the mixins.
    - Screenshots and HTML dumps on error (for page-related errors) are configurable via `BaseScraperConfig` (e.g., `screenshot_on_error`, `save_html_on_error`) and are triggered by methods in `NavigationMixin` and `DownloadMixin` before calling `_handle_and_raise_scraper_error`.

## 5. Testing

- Place scraper-specific tests in `tests/core/scrapers/test_your_scraper_name.py`.
- Place mixin unit tests in `tests/core/mixins/`.
- Mock dependencies (Playwright objects like `Page`, `Context`; database sessions; configurations) to test scraper logic in isolation.
- For scraper tests, focus on:
    - Correct instantiation with its specific configuration.
    - Orchestration logic within `_setup_method`, `_extract_method`, and `_process_method`.
    - Any custom transformation methods specific to the scraper.
- Mixin functionality (e.g., the detailed behavior of `navigate_to_url`) is tested in the mixin's own test file (e.g., `test_navigation_mixin.py`).

```
