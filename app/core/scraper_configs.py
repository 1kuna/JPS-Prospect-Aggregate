"""Simplified Scraper Configurations

Replaces the complex config_converter.py with direct, simple dictionary-based configurations.
Each scraper now has a clear, readable configuration that can be easily modified.
"""

# Import the proper dataclass ScraperConfig from consolidated_scraper_base
from app.core.consolidated_scraper_base import ScraperConfig

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
        "--disable-renderer-backgrounding",
    ],
    # Selectors and timeouts
    export_button_selector="button#export-0",
    download_timeout_ms=90000,  # 90 seconds
    # File processing
    csv_read_options={
        "encoding": "utf-8",
        "on_bad_lines": "skip",
        "quoting": 1,
        "engine": "python",
    },
    # Column mappings
    raw_column_rename_map={
        "Listing ID": "native_id",
        "Title": "title",
        # Some exports use 'Description'; others only provide 'Body'.
        # 'Description' will be filled from 'Body' in a custom transform when missing.
        "Description": "description",
        # Map 'Organization' to agency to avoid missing agency when this header is present
        "Organization": "agency",
        "NAICS Code": "naics",  # Changed from naics_code to match Prospect model
        "Estimated Contract Value": "estimated_value_text",
        "Estimated Solicitation Date": "release_date_raw",  # Keep as raw for date parsing
        "Ultimate Completion Date": "award_date_raw",  # Keep as raw for date parsing
        "Agency": "agency",
        # Frequently present in AG exports
        "Estimated Award FY": "award_fiscal_year",
        "Place of Performance City": "place_city",
        "Place of Performance State": "place_state",
        "Place of Performance Country": "place_country",
        "Contract Type": "contract_type",
        "Set Aside Type": "set_aside",
        "Point of Contact (Email)": "primary_contact_email",
        "Content: Point of Contact (Name) For": "primary_contact_name",
    },
    # Date parsing configuration
    date_column_configs=[
        {
            "column": "release_date_raw",
            "target_column": "release_date",
            "store_as_date": True,
        },
        {
            "column": "award_date_raw",
            "target_column": "award_date",
            "store_as_date": True,
        },
    ],
    custom_transform_functions=["custom_summary_fallback"],
    fields_for_id_hash=[
        "native_id",
        "naics",
        "title",
        "description",
    ],  # Changed naics_code to naics
)


DHS_CONFIG = ScraperConfig(
    source_name="Department of Homeland Security",
    folder_name="dhs",
    # Selectors and timing
    csv_button_selector="button.buttons-csv",
    explicit_wait_ms_before_download=10000,
    # File processing
    file_read_strategy="csv_then_excel",
    csv_read_options={"encoding": "utf-8"},
    excel_read_options={"sheet_name": 0, "header": 0},
    # Column mappings
    raw_column_rename_map={
        "APFS Number": "native_id",
        "NAICS": "naics",  # Fixed: changed from naics_code to naics
        "Component": "agency",
        "Title": "title",
        "Contract Type": "contract_type",
        "Dollar Range": "estimated_value_text",
        "Small Business Set-Aside": "set_aside",
        "Small Business Program": "small_business_program",
        "Place of Performance City": "place_city",
        "Place of Performance State": "place_state",
        "Description": "description",
        "Estimated Solicitation Release": "release_date_raw",
        "Award Quarter": "award_qtr_raw",
        "Primary Contact First Name": "primary_contact_first_name",
        "Primary Contact Last Name": "primary_contact_last_name",
        "Primary Contact Email": "primary_contact_email",
    },
    # Date parsing configuration
    date_column_configs=[
        {
            "column": "release_date_raw",
            "target_column": "release_date",
            "store_as_date": True,
        },
        {
            "column": "award_qtr_raw",
            "parse_type": "fiscal_quarter",
            "target_date_col": "award_date",
            "target_fy_col": "award_fiscal_year",
        },
    ],
    custom_transform_functions=["_custom_dhs_transforms"],
    transform_params={
        "combine_names": {
            "first_col": "primary_contact_first_name",
            "last_col": "primary_contact_last_name",
            "out_col": "primary_contact_name"
        },
        "default_country": True
    },
    extras_fields_map={
        "Contract Number": "contract_number",
        "Contractor": "contractor",
        "Primary Contact First Name": "primary_contact_first_name",
        "Primary Contact Last Name": "primary_contact_last_name",
        "Primary Contact Phone": "primary_contact_phone",
        "Primary Contact Email": "primary_contact_email",
        "Forecast Published": "forecast_published",
        "Forecast Previously Published": "forecast_previously_published",
    },
    fields_for_id_hash=[
        "native_id",
        "naics",  # Fixed: changed from naics_code to naics
        "title",
        "description",
        "place_city",
        "place_state",
    ],
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
        "--no-first-run",
    ],
    # Selectors
    pre_export_click_selector="button:has-text('Apply')",
    export_button_selector="a:has-text('Download CSV')",
    wait_after_apply_ms=10000,
    # Retry configuration for DOT's custom setup
    retry_attempts=[
        {"delay_before_next_s": 0},
        {"delay_before_next_s": 5},
        {"delay_before_next_s": 10},
    ],
    # Column mappings
    raw_column_rename_map={
        "Sequence Number": "native_id",
        "Procurement Office": "agency",
        "Project Title": "title",
        "Description": "description",
        "Estimated Value": "estimated_value_text",
        "NAICS": "naics",  # Fixed: changed from naics_code to naics
        "Competition Type": "set_aside",
        "RFP Quarter": "solicitation_qtr_raw",
        "Place of Performance": "place_raw",
        "Contact Email": "primary_contact_email",
        "Contact Name": "primary_contact_name",
    },
    custom_transform_functions=["_custom_dot_transforms"],
    transform_params={
        "parse_place": {
            "source_col": "place_raw",
            "city_col": "place_city",
            "state_col": "place_state",
            "country_col": "place_country"
        },
        "default_country": True
    },
    extras_fields_map={
        "Publication Status": "publication_status",
        "Assigned To": "assigned_to",
        "Incumbent/Contract Number": "incumbent_contract_number",
        "Updates": "updates",
        "Contact Name": "contact_name",
        "Contact Email": "contact_email",
        "Contact Phone": "contact_phone",
        "Is this a follow-on to a current 8(a) contract?": "followon_8a_contract",
        "Is this funded through the American Recovery and Reinvestment Act?": "arra_funded",
        "Contract Awarded": "contract_awarded",
        "Expected Period of Performance - Start": "performance_start_date",
        "Expected Period of Performance - End": "performance_end_date",
        "Personnel Clearance Requirements": "clearance_requirements",
        "Date Modified": "date_modified",
        "Incumbent Contractor": "incumbent_contractor",
        "Action/Award Type": "action_award_type",
        "Anticipated Award Date": "anticipated_award_date",
        "Bipartisan Infrastructure Law (BIL) Opportunity": "bil_opportunity",
    },
    fields_for_id_hash=[
        "native_id",
        "naics",
        "title",
        "description",
        "agency",
    ],  # Fixed: changed naics_code to naics
)


TREASURY_CONFIG = ScraperConfig(
    source_name="Department of Treasury",
    folder_name="treas",
    # Browser settings
    debug_mode=True,
    navigation_timeout_ms=180000,  # 3 minutes
    interaction_timeout_ms=60000,
    download_timeout_ms=300000,  # 5 minutes
    # Selectors (XPath)
    export_button_selector="//lightning-button/button[contains(text(), 'Download Opportunity Data')]",
    # File handling - Treasury files are HTML with .xls extension
    file_read_strategy="html",
    # Column mappings
    raw_column_rename_map={
        "Specific Id": "native_id_primary",
        "Bureau": "agency",
        # PSC is Product Service Code, not a title - will be preserved in extras
        "Place of Performance": "place_raw",
        "Contract Type": "contract_type",
        "NAICS": "naics",  # Fixed: changed from naics_code to naics
        "Estimated Total Contract Value": "estimated_value_text",
        "Type of Small Business Set-aside": "set_aside",
        "Projected Award FY_Qtr": "award_qtr_raw",
        "Bureau Point of Contact": "bureau_contact_name",
    },
    # Date parsing configuration (for fiscal quarter)
    date_column_configs=[
        {
            "column": "award_qtr_raw",
            "parse_type": "fiscal_quarter",
            "target_date_col": "award_date",
            "target_fy_col": "award_fiscal_year",
        },
    ],
    custom_transform_functions=[
        "_custom_treasury_transforms",
    ],
    transform_params={
        "add_row_index": True,
        "parse_place": {
            "source_col": "place_raw",
            "city_col": "place_city",
            "state_col": "place_state",
            "country_col": "place_country"
        },
        "default_country": True
    },
    extras_fields_map={
        "PSC": "product_service_code",  # Product Service Code classification
        "Type of Requirement": "requirement_type",
        "Specific Id": "native_id_primary",
        "ShopCart/req": "native_id_fallback1",
        "Contract Number": "native_id_fallback2",
        "Place of Performance": "place_raw",
        "Projected Award FY_Qtr": "award_qtr_raw",
        "Project Period of Performance Start": "release_date_raw",
    },
    fields_for_id_hash=[
        "native_id",
        "naics",  # Fixed: changed from naics_code to naics
        "title",
        "description",
        "agency",
        "place_city",
        "place_state",
    ],
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
        "--disable-renderer-backgrounding",
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
        "Title": "title",
        "Description": "description",
        "Operating Division": "agency",
        "Primary NAICS": "naics",  # Fixed: changed from naics_code to naics
        "Total Contract Range": "estimated_value_text",
        "Target Award Month/Year (Award by)": "award_date_raw",
        "Target Solicitation Month/Year": "release_date_raw",
        "Anticipated Acquisition Strategy": "set_aside",
        "Program Office POC Email": "primary_contact_email",
    },
    # Date parsing configuration
    date_column_configs=[
        {
            "column": "release_date_raw",
            "target_column": "release_date",
            "store_as_date": True,
        },
        {
            "column": "award_date_raw",
            "target_column": "award_date",
            "store_as_date": True,
        },
    ],
    custom_transform_functions=["_custom_hhs_transforms"],
    transform_params={
        "add_row_index": True,
        "combine_names": {
            "first_col": "Program Office POC First Name",
            "last_col": "Program Office POC Last Name",
            "out_col": "primary_contact_name"
        },
        "default_country": True
    },
    extras_fields_map={
        "Program POC Office": "program_poc_office",
        "Incumbent Contractor (if applicable)": "incumbent_contractor",
        "Existing Contract number (if applicable)": "existing_contract_number",
    },
    fields_for_id_hash=[
        "title",
        "description",
        "agency",
        "naics",
        "row_index",
    ],  # Fixed: changed naics_code to naics
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
        "a:contains('Download')",
    ],
    # Column mappings
    raw_column_rename_map={
        "APP #": "native_id",
        "SITE Type": "agency",
        "DESCRIPTION": "description",
        "NAICS": "naics",  # Fixed: changed from naics_code to naics
        "CONTRACT TYPE": "contract_type",
        # Map both variants commonly seen in SSA files
        "TYPE OF COMPETITION": "set_aside",
        "SET ASIDE": "set_aside",
        # Value field variants
        "EST COST PER FY": "estimated_value_text",
        "ESTIMATED VALUE": "estimated_value_text",
        # If present in some files, capture award fiscal year
        "AWARD FISCAL YEAR": "award_fiscal_year",
        "PLACE OF PERFORMANCE": "place_raw",
        "PLANNED AWARD DATE": "planned_award_date_raw",  # Keep as raw for date parsing
    },
    # Date parsing configuration
    date_column_configs=[
        {
            "column": "planned_award_date_raw",
            "target_column": "award_date",
            "store_as_date": True,
        },
    ],
    custom_transform_functions=["_custom_ssa_transforms"],
    transform_params={
        "parse_place": {
            "source_col": "place_raw",
            "city_col": "place_city",
            "state_col": "place_state",
            "country_col": "place_country"
        },
        "default_country": True
    },
    extras_fields_map={
        "REQUIREMENT TYPE": "requirement_type",
        "EST COST PER FY": "est_cost_per_fy",
        "PLANNED AWARD DATE": "planned_award_date",
        "EXISTING AWD #": "existing_award_number",
        "INCUMBENT VENDOR": "incumbent_vendor",
        "NAICS DESCRIPTION": "naics_description",
        "TYPE OF COMPETITION": "type_of_competition",
        "NET VIEW TOTAL OBLIGATED AMT": "net_view_total_obligated_amount",
        "ULTIMATE COMPLETION DATE": "ultimate_completion_date",
    },
    fields_for_id_hash=[
        "native_id",
        "naics",
        "title",
        "description",
    ],  # Fixed: changed naics_code to naics
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
        "Forecast ID": "native_id",
        "Organization": "agency",
        "Title": "title",
        "Description": "description",
        "Naics Code": "naics",  # Fixed: changed from naics_code to naics
        "Place Of Performance City": "place_city",
        "Place Of Performance State": "place_state",
        "Place Of Performance Country": "place_country_raw",
        "Estimated Value Range": "estimated_value_text",
        "Type Of Awardee": "set_aside",  # Fixed: This contains actual set-aside info
        "Anticipated Set Aside And Type": "competition_strategy",  # This contains competition type
        "Competition Strategy": "competition_strategy_alt",  # Alternate competition field
        "Point Of Contact Email": "primary_contact_email",
        "Point Of Contact Name": "primary_contact_name",
    },
    custom_transform_functions=["_custom_doc_transforms"],
    transform_params={
        "derive_date_from_fyq": {
            "year_col": "Estimated Solicitation Fiscal Year",
            "quarter_col": "Estimated Solicitation Fiscal Quarter",
            "out_date_col": "release_date_final",
            "out_fy_col": None
        },
        "default_country": {"column": "place_country_final"}
    },
    # Map computed final fields into model column names
    db_column_rename_map={
        "release_date_final": "release_date",
        "award_date_final": "award_date",
        "award_fiscal_year_final": "award_fiscal_year",
        "place_country_final": "place_country",
    },
    extras_fields_map={
        "Workspace Number": "workspace_number",
        "Date Created": "date_created",
        "Office": "office",
        "Organization Unit": "organization_unit",
        "Months": "months",
        "Years": "years",
        "Anticipated Set Aside And Type": "anticipated_set_aside_and_type",
        "Competition Strategy": "competition_strategy",
        "New Requirement Or Recompete": "new_requirement_or_recompete",
        "Incumbent Contractor Name": "incumbent_contractor_name",
        "Awarded Contract Order Number": "awarded_contract_order_number",
        "Point Of Contact Name": "point_of_contact_name",
        "Point Of Contact Email": "point_of_contact_email",
        "Does This Acquisition Contain Information Technology": "contains_information_technology",
        "Date Created or Modified": "date_created_or_modified",
        "Awarded?": "awarded",
    },
    fields_for_id_hash=[
        "native_id",
        "naics",  # Fixed: changed from naics_code to naics
        "title",
        "description",
        "place_city",
        "place_state",
    ],
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
        "Action Tracking Number": "native_id",
        "Bureau": "agency",
        "Contract Name": "title",
        "Description of Requirement": "description",
        "Contract Type (Pricing)": "contract_type",
        "NAICS Code": "naics",  # Fixed: changed from naics_code to naics
        "Small Business Approach": "set_aside",
        "Estimated Total Contract Value (Range)": "estimated_value_text",
        "Target Solicitation Date": "release_date_raw",
        "Target Award Date": "award_date_raw",
        "Place of Performance": "place_raw",
        # Ensure country is mapped for DOJ if present
        "Country": "place_country_raw",
        "DOJ Small Business POC - Email Address": "doj_sb_poc_email",
        "DOJ Small Business POC - Name": "doj_sb_poc_name",
        "DOJ Requirement POC - Name": "doj_req_poc_name",
        "DOJ Requirement POC - Email Address": "doj_req_poc_email",
    },
    # Date parsing configuration
    date_column_configs=[
        {
            "column": "release_date_raw",
            "target_column": "release_date",
            "store_as_date": True,
        },
        {
            "column": "award_date_raw",
            "target_column": "award_date",
            "store_as_date": True,
        },
    ],
    custom_transform_functions=["_custom_doj_transforms"],
    transform_params={
        "derive_award_date_priority": {
            "date_col": "award_date_raw",
            "qtr_col": "award_date_raw",
            "fy_col": None,
            "out_date_col": "award_date_final",
            "out_fy_col": "award_fiscal_year_final"
        },
        "default_country": True
    },
    extras_fields_map={
        "Fiscal Year": "fiscal_year",
        "OBD": "organizational_business_division",
        "Contracting Office": "contracting_office",
        "DOJ Small Business POC - Name": "small_business_poc_name",
        "DOJ Small Business POC - Email Address": "small_business_poc_email",
        "DOJ Requirement POC - Name": "requirement_poc_name",
        "DOJ Requirement POC - Email Address": "requirement_poc_email",
        "Category": "category",
        "Subcategory": "subcategory",
        "Award Type": "award_type",
        "Product Service Code": "product_service_code",
        "Competition Approach": "competition_approach",
        "Contracting Solution": "contracting_solution",
        "Contract Availability": "contract_availability",
        "Length of Contract": "length_of_contract",
        "Request for Information (RFI) Planned": "rfi_planned",
        "Acquisition History": "acquisition_history",
        "Incumbent Contractor": "incumbent_contractor",
        "Incumbent Contractor PIID": "incumbent_contractor_piid",
        "Special Interest": "special_interest",
        "Comments": "comments",
    },
    fields_for_id_hash=[
        "native_id",
        "naics",  # Fixed: changed from naics_code to naics
        "title",
        "description",
        "place_city",
        "place_state",
    ],
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
        "Contract Number": "native_id",
        "Office Symbol": "agency",
        "Requirement Title": "title",
        "Requirement Description": "description",
        "Estimated Value": "estimated_value_raw1",
        # Some files include a separate numeric Dollar Value field
        "Dollar Value": "estimated_value_raw2",
        "Place of Performance Country": "place_country_raw",
        "Place of Performance City": "place_city_raw",
        "Place of Performance State": "place_state_raw",
        "Award Type": "contract_type",
        "Anticipated Award Date": "award_date_raw",
        "Anticipated Set Aside": "set_aside",
        "Anticipated Solicitation Release Date": "release_date_raw",
    },
    # Date parsing configuration
    date_column_configs=[
        {
            "column": "release_date_raw",
            "target_column": "release_date",
            "store_as_date": True,
        },
        {
            "column": "award_date_raw",
            "target_column": "award_date",
            "store_as_date": True,
        },
    ],
    custom_transform_functions=["_custom_dos_transforms"],
    transform_params={
        "add_row_index": True,
        "derive_award_date_priority": {
            "date_col": "award_date_raw",
            "qtr_col": "award_qtr_raw",
            "fy_col": "award_fiscal_year_raw",
            "out_date_col": "award_date_final",
            "out_fy_col": "award_fiscal_year_final"
        },
        "parse_value_priority": {
            "primary_col": "estimated_value_raw1",
            "secondary_col": "estimated_value_raw2",
            "out_value_col": "estimated_value_final",
            "out_unit_col": "est_value_unit_final"
        },
        "default_country": {"column": "place_country_final"}
    },
    # Map computed final fields into model column names
    db_column_rename_map={
        "release_date_final": "release_date",
        "award_date_final": "award_date",
        "award_fiscal_year_final": "award_fiscal_year",
        "estimated_value_final": "estimated_value",
        "est_value_unit_final": "est_value_unit",
        "place_city_final": "place_city",
        "place_state_final": "place_state",
        "place_country_final": "place_country",
        "naics_final": "naics",
    },
    extras_fields_map={
        "Organization": "organization",
        "Category": "category",
        "Planned Solicitation": "planned_solicitation",
        "Type of Opportunity": "type_of_opportunity",
        "Product Service Code": "product_service_code",
        "Anticipated Competition Type": "anticipated_competition_type",
        "Acquisition Type": "acquisition_type",
        "Type of Contract Vehicle": "type_of_contract_vehicle",
        "Magnitude": "magnitude",
        "Incumbent Name": "incumbent_name",
        "Additional Comments": "additional_comments",
    },
    fields_for_id_hash=[
        "native_id",
        "title",
        "description",
        "place_city_final",
        "place_state_final",
        "row_index",
    ],
)


# =============================================================================
# CONFIGURATION GETTER FUNCTIONS
# =============================================================================


def get_scraper_config(scraper_type: str) -> ScraperConfig:
    """Get configuration for a specific scraper type"""
    configs = {
        "acquisition_gateway": ACQUISITION_GATEWAY_CONFIG,
        "dhs": DHS_CONFIG,
        "dot": DOT_CONFIG,
        "treasury": TREASURY_CONFIG,
        "hhs": HHS_CONFIG,
        "ssa": SSA_CONFIG,
        "doc": DOC_CONFIG,
        "doj": DOJ_CONFIG,
        "dos": DOS_CONFIG,
    }

    if scraper_type not in configs:
        raise ValueError(
            f"Unknown scraper type: {scraper_type}. Available: {list(configs.keys())}"
        )

    return configs[scraper_type]


def list_available_scrapers() -> list[str]:
    """Get list of available scraper types"""
    return [
        "acquisition_gateway",
        "dhs",
        "dot",
        "treasury",
        "hhs",
        "ssa",
        "doc",
        "doj",
        "dos",
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
