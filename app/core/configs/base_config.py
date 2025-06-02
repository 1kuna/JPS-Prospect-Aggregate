from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class BaseScraperConfig:
    """
    Base configuration class for scrapers.
    
    Attributes:
        source_name (str): The official name of the data source.
        base_url (Optional[str]): The primary starting URL for the scraper.
        use_stealth (bool): Whether to apply playwright-stealth patches. Defaults to False.
        download_timeout_ms (int): Timeout for download operations in milliseconds. Defaults to 120000.
        navigation_timeout_ms (int): Timeout for navigation actions (e.g., page.goto) in milliseconds. Defaults to 90000.
        default_wait_after_download_ms (int): Default pause after a download is initiated. Defaults to 2000.
        screenshot_on_error (bool): Whether to take a screenshot if an error occurs. Defaults to True.
        save_html_on_error (bool): Whether to save the page's HTML content if an error occurs. Defaults to False.
        
        # Common processing related fields that might be useful in base or specialized configs
        # These are more related to DataProcessingMixin but can be part of a unified config structure.
        # For now, keeping them here for consideration.
        # column_rename_map (Dict[str, str]): Maps source file column names to standardized intermediate names.
        # prospect_model_fields (List[str]): List of fields that directly map to the Prospect model.
        # fields_for_id_hash (List[str]): List of (renamed) DataFrame column names to generate a unique ID hash.
        # required_fields (Optional[List[str]]): Optional list of Prospect model field names that must be non-empty.
    """
    source_name: str
    base_url: Optional[str] = None
    use_stealth: bool = False
    
    # Timeouts
    download_timeout_ms: int = 120000  # Default based on previous report
    navigation_timeout_ms: int = 90000 # Default based on previous report
    interaction_timeout_ms: int = 30000 # Default for clicks, waits for selectors, etc.
    
    # Waits
    default_wait_after_download_ms: int = 2000
    default_wait_after_click_ms: int = 0 # If a small pause is needed after generic clicks
    
    # Error Handling
    screenshot_on_error: bool = True
    save_html_on_error: bool = False
    
    # Data processing hints (can be overridden by specific scraper configs)
    # These are better placed in specific configs or a processing-specific config object,
    # but including placeholders here for completeness if a unified config is desired.
    # file_type_hint: Optional[str] = None # E.g., 'csv', 'xlsx', 'html'
    # csv_read_options: Dict = field(default_factory=dict)
    # excel_read_options: Dict = field(default_factory=dict)
    # html_read_options: Dict = field(default_factory=dict)

    # Column mapping and ID generation strategy for data processing
    # These are typically very scraper-specific.
    # column_rename_map: Dict[str, str] = field(default_factory=dict) # From source file to intermediate names
    # fields_for_id_hash: List[str] = field(default_factory=list)   # Intermediate names for hashing
    # final_db_column_map: Dict[str, str] = field(default_factory=dict) # From intermediate to Prospect model fields

    def __post_init__(self):
        if not self.source_name:
            raise ValueError("source_name must be provided.")
        if self.base_url and not self.base_url.startswith(('http://', 'https://')):
            # Basic validation for base_url, can be expanded
            # Allow None for base_url as some scrapers might not have one (e.g. direct file URL scrapers)
            pass # No raise, just an observation. Could log a warning.

        # Ensure timeouts are non-negative
        if self.download_timeout_ms < 0:
            self.download_timeout_ms = 0
        if self.navigation_timeout_ms < 0:
            self.navigation_timeout_ms = 0
        if self.interaction_timeout_ms < 0:
            self.interaction_timeout_ms = 0
        if self.default_wait_after_download_ms < 0:
            self.default_wait_after_download_ms = 0
        if self.default_wait_after_click_ms < 0:
            self.default_wait_after_click_ms = 0

# Example of how it might be used:
# base_conf = BaseScraperConfig(source_name="Generic Source", base_url="http://example.com")
# print(base_conf)
# specific_conf_no_url = BaseScraperConfig(source_name="Direct File Source")
# print(specific_conf_no_url)
# error_conf = BaseScraperConfig(source_name="") # This would raise ValueError
