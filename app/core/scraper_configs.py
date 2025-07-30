"""
Simplified Scraper Configurations

Replaces the complex config_converter.py with direct, simple dictionary-based configurations.
Each scraper now has a clear, readable configuration that can be easily modified.
"""

from typing import Dict, List, Any, Optional


class ScraperConfig:
    """Simplified scraper configuration class"""
    
    def __init__(self, **kwargs):
        # Required fields
        self.source_name: str = kwargs.get('source_name', '')
        self.folder_name: str = kwargs.get('folder_name', '')
        self.base_url: Optional[str] = kwargs.get('base_url')
        
        # Browser settings
        self.use_stealth: bool = kwargs.get('use_stealth', False)
        self.debug_mode: bool = kwargs.get('debug_mode', False)
        self.special_browser_args: List[str] = kwargs.get('special_browser_args', [])
        
        # Timeouts
        self.download_timeout_ms: int = kwargs.get('download_timeout_ms', 60000)
        self.navigation_timeout_ms: int = kwargs.get('navigation_timeout_ms', 60000)
        self.interaction_timeout_ms: int = kwargs.get('interaction_timeout_ms', 30000)
        
        # Selectors
        self.export_button_selector: str = kwargs.get('export_button_selector', '')
        self.csv_button_selector: str = kwargs.get('csv_button_selector', '')
        self.pre_export_click_selector: str = kwargs.get('pre_export_click_selector', '')
        
        # File handling
        self.file_read_strategy: str = kwargs.get('file_read_strategy', 'csv')
        self.csv_read_options: Dict = kwargs.get('csv_read_options', {})
        self.excel_read_options: Dict = kwargs.get('excel_read_options', {})
        
        # Wait times
        self.explicit_wait_ms_before_download: int = kwargs.get('explicit_wait_ms_before_download', 0)
        self.wait_after_apply_ms: int = kwargs.get('wait_after_apply_ms', 0)
        
        # Column mappings
        self.raw_column_rename_map: Dict[str, str] = kwargs.get('raw_column_rename_map', {})
        self.db_column_rename_map: Dict[str, str] = kwargs.get('db_column_rename_map', {})
        
        # Processing configurations
        self.custom_transform_functions: List[str] = kwargs.get('custom_transform_functions', [])
        self.fields_for_id_hash: List[str] = kwargs.get('fields_for_id_hash', [])
        
        # Optional configurations
        self.direct_download_url: Optional[str] = kwargs.get('direct_download_url')
        self.download_link_text: Optional[str] = kwargs.get('download_link_text')
        self.excel_link_selectors: List[str] = kwargs.get('excel_link_selectors', [])


# =============================================================================
# SIMPLIFIED SCRAPER CONFIGURATIONS
# =============================================================================

ACQUISITION_GATEWAY_CONFIG = ScraperConfig(
    source_name="Acquisition Gateway",
    folder_name="acqgw",
    
    # Browser settings - needs non-headless mode
    debug_mode=True,
    special_browser_args=[
        "--disable-features=VizDisplayCompositor",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding"
    ],
    
    # Selectors and timeouts
    export_button_selector="button#export-0",
    download_timeout_ms=90000,  # 90 seconds
    
    # File processing
    csv_read_options={
        "encoding": "utf-8",
        "on_bad_lines": "skip",
        "quoting": 1,
        "engine": "python"
    },
    
    # Column mappings
    raw_column_rename_map={
        'Listing ID': 'native_id',
        'Title': 'title',
        'Description': 'description',
        'NAICS Code': 'naics_code',
        'Estimated Contract Value': 'estimated_value_text',
        'Estimated Solicitation Date': 'release_date_raw',
        'Ultimate Completion Date': 'award_date_raw',
        'Agency': 'agency',
        'Place of Performance City': 'place_city',
        'Place of Performance State': 'place_state',
        'Place of Performance Country': 'place_country',
        'Contract Type': 'contract_type',
        'Set Aside Type': 'set_aside',
        'Point of Contact (Email)': 'primary_contact_email',
        'Content: Point of Contact (Name) For': 'primary_contact_name',
    },
    
    custom_transform_functions=["custom_summary_fallback"],
    fields_for_id_hash=['native_id', 'naics_code', 'title', 'description']
)


DHS_CONFIG = ScraperConfig(
    source_name="Department of Homeland Security",
    folder_name="dhs",
    
    # Selectors and timing
    csv_button_selector='button.buttons-csv',
    explicit_wait_ms_before_download=10000,
    
    # File processing
    file_read_strategy="csv_then_excel",
    csv_read_options={"encoding": "utf-8"},
    excel_read_options={"sheet_name": 0, "header": 0},
    
    # Column mappings
    raw_column_rename_map={
        'APFS Number': 'native_id',
        'NAICS': 'naics_code',
        'Component': 'agency',
        'Title': 'title',
        'Contract Type': 'contract_type',
        'Dollar Range': 'estimated_value_text',
        'Small Business Set-Aside': 'set_aside',
        'Small Business Program': 'small_business_program',
        'Place of Performance City': 'place_city',
        'Place of Performance State': 'place_state',
        'Description': 'description',
        'Estimated Solicitation Release': 'release_date_raw',
        'Award Quarter': 'award_qtr_raw',
        'Primary Contact First Name': 'primary_contact_first_name',
        'Primary Contact Last Name': 'primary_contact_last_name',
        'Primary Contact Email': 'primary_contact_email',
    },
    
    custom_transform_functions=["_custom_dhs_transforms", "_dhs_create_extras"],
    fields_for_id_hash=['native_id', 'naics_code', 'title', 'description', 'place_city', 'place_state']
)


DOT_CONFIG = ScraperConfig(
    source_name="Department of Transportation",
    folder_name="dot",
    
    # Browser settings - needs stealth mode
    use_stealth=True,
    debug_mode=True,
    special_browser_args=[
        "--disable-http2",
        "--disable-features=VizDisplayCompositor",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--no-first-run"
    ],
    
    # Selectors
    pre_export_click_selector="button:has-text('Apply')",
    export_button_selector="a:has-text('Download CSV')",
    wait_after_apply_ms=10000,
    
    # Column mappings
    raw_column_rename_map={
        'Sequence Number': 'native_id',
        'Procurement Office': 'agency',
        'Project Title': 'title',
        'Description': 'description',
        'Estimated Value': 'estimated_value_text',
        'NAICS': 'naics_code',
        'Competition Type': 'set_aside',
        'RFP Quarter': 'solicitation_qtr_raw',
        'Place of Performance': 'place_raw',
        'Contact Email': 'primary_contact_email',
        'Contact Name': 'primary_contact_name',
    },
    
    custom_transform_functions=["_custom_dot_transforms", "_dot_create_extras"],
    fields_for_id_hash=['native_id', 'naics_code', 'title', 'description', 'agency']
)


TREASURY_CONFIG = ScraperConfig(
    source_name="Department of Treasury",
    folder_name="treas",
    
    # Browser settings
    debug_mode=True,
    navigation_timeout_ms=180000,  # 3 minutes
    interaction_timeout_ms=60000,
    download_timeout_ms=300000,    # 5 minutes
    
    # Selectors (XPath)
    export_button_selector="//lightning-button/button[contains(text(), 'Download Opportunity Data')]",
    
    # File handling - Treasury files are HTML with .xls extension
    file_read_strategy="html",
    
    # Column mappings
    raw_column_rename_map={
        'Specific Id': 'native_id_primary',
        'Bureau': 'agency',
        'PSC': 'title',
        'Place of Performance': 'place_raw',
        'Contract Type': 'contract_type',
        'NAICS': 'naics_code',
        'Estimated Total Contract Value': 'estimated_value_text',
        'Type of Small Business Set-aside': 'set_aside',
        'Projected Award FY_Qtr': 'award_qtr_raw',
        'Bureau Point of Contact': 'bureau_contact_name',
    },
    
    custom_transform_functions=["_custom_treasury_transforms", "_treasury_create_extras"],
    fields_for_id_hash=['native_id', 'naics_code', 'title', 'description', 'agency', 'place_city', 'place_state']
)


HHS_CONFIG = ScraperConfig(
    source_name="Health and Human Services",
    folder_name="hhs",
    
    # Browser settings
    use_stealth=True,
    special_browser_args=[
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-web-security",
        "--disable-features=VizDisplayCompositor",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding"
    ],
    
    # Extended timeouts for JavaScript-heavy site
    navigation_timeout_ms=120000,
    interaction_timeout_ms=45000,
    
    # Selectors
    pre_export_click_selector='button[data-cy="viewAllBtn"]',
    csv_button_selector='button:has-text("Export")',
    explicit_wait_ms_before_download=10000,
    
    # Column mappings
    raw_column_rename_map={
        'Title': 'title',
        'Description': 'description',
        'Operating Division': 'agency',
        'Primary NAICS': 'naics_code',
        'Total Contract Range': 'estimated_value_text',
        'Target Award Month/Year (Award by)': 'award_date_raw',
        'Target Solicitation Month/Year': 'release_date_raw',
        'Anticipated Acquisition Strategy': 'set_aside',
        'Program Office POC Email': 'primary_contact_email',
        'Program Office POC First Name': 'poc_first_name',
        'Program Office POC Last Name': 'poc_last_name',
    },
    
    custom_transform_functions=["_custom_hhs_transforms", "_hhs_create_extras"],
    fields_for_id_hash=['title', 'description', 'agency', 'naics_code', 'row_index']
)


SSA_CONFIG = ScraperConfig(
    source_name="Social Security Administration",
    folder_name="ssa",
    
    # Excel file handling
    file_read_strategy="excel",
    excel_read_options={"sheet_name": "Sheet1", "header": 4, "engine": "openpyxl"},
    
    # Excel link selectors
    excel_link_selectors=[
        "a[href$='.xlsx']",
        "a[href$='.xls']",
        "a[href$='.xlsm']",
        "a:contains('Excel')",
        "a:contains('Download')"
    ],
    
    # Column mappings
    raw_column_rename_map={
        'APP #': 'native_id',
        'SITE Type': 'agency',
        'DESCRIPTION': 'description',
        'NAICS': 'naics_code',
        'CONTRACT TYPE': 'contract_type',
        'SET ASIDE': 'set_aside',
        'ESTIMATED VALUE': 'estimated_value_text',
        'AWARD FISCAL YEAR': 'award_fiscal_year',
        'PLACE OF PERFORMANCE': 'place_raw',
        'PLANNED AWARD DATE': 'planned_award_date',
    },
    
    custom_transform_functions=["_custom_ssa_transforms", "_ssa_create_extras"],
    fields_for_id_hash=['native_id', 'naics_code', 'title', 'description']
)


DOC_CONFIG = ScraperConfig(
    source_name="Department of Commerce",
    folder_name="doc",
    
    # Direct download approach
    download_link_text="Current Procurement Forecasts",
    
    # Excel file handling
    file_read_strategy="excel",
    excel_read_options={"sheet_name": "Sheet1", "header": 2},
    
    # Column mappings
    raw_column_rename_map={
        'Forecast ID': 'native_id',
        'Organization': 'agency',
        'Title': 'title',
        'Description': 'description',
        'Naics Code': 'naics_code',
        'Place Of Performance City': 'place_city',
        'Place Of Performance State': 'place_state',
        'Place Of Performance Country': 'place_country_raw',
        'Estimated Value Range': 'estimated_value_text',
        'Anticipated Set Aside And Type': 'set_aside',
        'Point Of Contact Email': 'primary_contact_email',
        'Point Of Contact Name': 'primary_contact_name',
    },
    
    custom_transform_functions=["_custom_doc_transforms", "_doc_create_extras"],
    fields_for_id_hash=['native_id', 'naics_code', 'title', 'description', 'place_city', 'place_state']
)


DOJ_CONFIG = ScraperConfig(
    source_name="Department of Justice",
    folder_name="doj",
    
    # Selectors and timeouts
    export_button_selector='a:has-text("Download the Excel File")',
    interaction_timeout_ms=20000,
    
    # Excel file handling
    file_read_strategy="excel",
    excel_read_options={"sheet_name": "Contracting Opportunities Data", "header": 12},
    
    # Column mappings
    raw_column_rename_map={
        'Action Tracking Number': 'native_id',
        'Bureau': 'agency',
        'Contract Name': 'title',
        'Description of Requirement': 'description',
        'Contract Type (Pricing)': 'contract_type',
        'NAICS Code': 'naics_code',
        'Small Business Approach': 'set_aside',
        'Estimated Total Contract Value (Range)': 'estimated_value_text',
        'Target Solicitation Date': 'release_date_raw',
        'Target Award Date': 'award_date_raw',
        'Place of Performance': 'place_raw',
        'DOJ Small Business POC - Email Address': 'primary_contact_email',
        'DOJ Requirement POC - Name': 'primary_contact_name',
    },
    
    custom_transform_functions=["_custom_doj_transforms", "_doj_create_extras"],
    fields_for_id_hash=['native_id', 'naics_code', 'title', 'description', 'place_city', 'place_state']
)


DOS_CONFIG = ScraperConfig(
    source_name="Department of State",
    folder_name="dos",
    
    # Direct download
    direct_download_url="https://www.state.gov/wp-content/uploads/2025/02/FY25-Procurement-Forecast-2.xlsx",
    
    # Excel file handling
    file_read_strategy="excel",
    excel_read_options={"sheet_name": "FY25-Procurement-Forecast", "header": 0},
    
    # Column mappings
    raw_column_rename_map={
        'Contract Number': 'native_id',
        'Office Symbol': 'agency',
        'Requirement Title': 'title',
        'Requirement Description': 'description',
        'Estimated Value': 'estimated_value_raw1',
        'Place of Performance Country': 'place_country_raw',
        'Place of Performance City': 'place_city_raw',
        'Place of Performance State': 'place_state_raw',
        'Award Type': 'contract_type',
        'Anticipated Award Date': 'award_date_raw',
        'Anticipated Set Aside': 'set_aside',
        'Anticipated Solicitation Release Date': 'release_date_raw',
    },
    
    custom_transform_functions=["_custom_dos_transforms", "_dos_create_extras"],
    fields_for_id_hash=['native_id', 'title', 'description', 'place_city_final', 'place_state_final', 'row_index']
)


# =============================================================================
# CONFIGURATION GETTER FUNCTIONS
# =============================================================================

def get_scraper_config(scraper_type: str) -> ScraperConfig:
    """Get configuration for a specific scraper type"""
    configs = {
        'acquisition_gateway': ACQUISITION_GATEWAY_CONFIG,
        'dhs': DHS_CONFIG,
        'dot': DOT_CONFIG,
        'treasury': TREASURY_CONFIG,
        'hhs': HHS_CONFIG,
        'ssa': SSA_CONFIG,
        'doc': DOC_CONFIG,
        'doj': DOJ_CONFIG,
        'dos': DOS_CONFIG,
    }
    
    if scraper_type not in configs:
        raise ValueError(f"Unknown scraper type: {scraper_type}. Available: {list(configs.keys())}")
    
    return configs[scraper_type]


def list_available_scrapers() -> List[str]:
    """Get list of available scraper types"""
    return [
        'acquisition_gateway', 'dhs', 'dot', 'treasury', 
        'hhs', 'ssa', 'doc', 'doj', 'dos'
    ]


# Backward compatibility functions
def create_acquisition_gateway_config() -> ScraperConfig:
    return ACQUISITION_GATEWAY_CONFIG

def create_dhs_config() -> ScraperConfig:
    return DHS_CONFIG

def create_dot_config() -> ScraperConfig:
    return DOT_CONFIG

def create_treasury_config() -> ScraperConfig:
    return TREASURY_CONFIG

def create_hhs_config() -> ScraperConfig:
    return HHS_CONFIG

def create_ssa_config() -> ScraperConfig:
    return SSA_CONFIG

def create_doc_config() -> ScraperConfig:
    return DOC_CONFIG

def create_doj_config() -> ScraperConfig:
    return DOJ_CONFIG

def create_dos_config() -> ScraperConfig:
    return DOS_CONFIG