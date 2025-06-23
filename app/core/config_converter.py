"""
Configuration converter to transform existing complex configurations
into the new unified ScraperConfig format.
"""
from typing import Optional, List, Dict, Any
from app.core.consolidated_scraper_base import ScraperConfig


def create_acquisition_gateway_config() -> ScraperConfig:
    """Create configuration for Acquisition Gateway scraper."""
    return ScraperConfig(
        source_name="Acquisition Gateway",
        base_url=None,  # Set by runner from active_config.ACQUISITION_GATEWAY_URL
        folder_name="acqgw",  # Use existing folder structure
        
        # Browser settings
        use_stealth=False,
        debug_mode=True,  # Non-headless for monitoring
        special_browser_args=[
            "--disable-features=VizDisplayCompositor",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding"
        ],
        
        # Timeouts
        download_timeout_ms=150000,  # Extended for slow downloads
        
        # Selectors
        export_button_selector="button#export-0",
        
        # File reading configuration
        csv_read_options={
            "encoding": "utf-8",
            "on_bad_lines": "skip",  # Skip malformed lines
            "quoting": 1,  # QUOTE_ALL - handle embedded quotes better
            "engine": "python"  # More robust parsing
        },
        
        # Data processing
        custom_transform_functions=["custom_summary_fallback"],
        raw_column_rename_map={
            # Core fields mapped to standard schema
            'Listing ID': 'native_id',
            'Title': 'title',
            'Description': 'description',  # Primary description field
            'NAICS Code': 'naics_code',
            'Estimated Contract Value': 'estimated_value_text',
            'Estimated Solicitation Date': 'release_date_raw',
            'Ultimate Completion Date': 'award_date_raw',
            'Estimated Award FY': 'award_fiscal_year',
            'Agency': 'agency',
            'Place of Performance City': 'place_city',
            'Place of Performance State': 'place_state', 
            'Place of Performance Country': 'place_country',
            'Contract Type': 'contract_type',
            'Set Aside Type': 'set_aside'
        },
        date_column_configs=[
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'award_date_raw', 'target_column': 'award_date', 'parse_type': 'datetime', 'store_as_date': True}
        ],
        fiscal_year_configs=[
            {'column': 'award_fiscal_year', 'target_column': 'award_fiscal_year', 'parse_type': 'direct'},
            {'date_column': 'award_date', 'target_column': 'award_fiscal_year', 'parse_type': 'from_date_year'}
        ],
        db_column_rename_map={
            'native_id': 'native_id',
            'title': 'title',
            'description': 'description',
            'naics_code': 'naics',
            'estimated_value_text': 'estimated_value_text',
            'release_date': 'release_date',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year',
            'agency': 'agency',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'contract_type': 'contract_type',
            'set_aside': 'set_aside',
            'extras_json': 'extra'  # Map extras JSON to database extra field
        },
        fields_for_id_hash=['native_id', 'naics_code', 'title', 'description']
    )


def create_dhs_config() -> ScraperConfig:
    """Create configuration for DHS scraper."""
    return ScraperConfig(
        source_name="Department of Homeland Security",
        base_url=None,  # Set by runner from active_config.DHS_FORECAST_URL
        folder_name="dhs",  # Use existing folder structure
        
        # Browser settings
        use_stealth=False,
        
        # Selectors
        csv_button_selector='button.buttons-csv',
        
        # Wait times
        explicit_wait_ms_before_download=10000,
        
        # File reading
        file_read_strategy="csv_then_excel",
        csv_read_options={"encoding": "utf-8"},
        excel_read_options={"sheet_name": 0, "header": 0},
        
        # Data processing
        custom_transform_functions=["_custom_dhs_transforms", "_dhs_create_extras"],
        raw_column_rename_map={
            # Core fields mapped to standard schema
            'APFS Number': 'native_id',
            'NAICS': 'naics_code',
            'Component': 'agency',
            'Title': 'title',
            'Contract Type': 'contract_type',
            'Contract Vehicle': 'contract_vehicle',
            'Dollar Range': 'estimated_value_text',
            'Small Business Set-Aside': 'set_aside',
            'Small Business Program': 'small_business_program',
            'Contract Status': 'contract_status',
            'Place of Performance City': 'place_city',
            'Place of Performance State': 'place_state',
            'Description': 'description',
            'Estimated Solicitation Release': 'release_date_raw',
            'Award Quarter': 'award_qtr_raw',
            
            # Additional fields for extras capture - all 23 columns
            'Contract Number': 'contract_number',
            'Contractor': 'contractor',
            'Primary Contact First Name': 'primary_contact_first_name',
            'Primary Contact Last Name': 'primary_contact_last_name',
            'Primary Contact Phone': 'primary_contact_phone',
            'Primary Contact Email': 'primary_contact_email',
            'Forecast Published': 'forecast_published',
            'Forecast Previously Published': 'forecast_previously_published'
        },
        date_column_configs=[
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'award_qtr_raw', 
             'target_date_col': 'award_date', 
             'target_fy_col': 'award_fiscal_year',
             'parse_type': 'fiscal_quarter'
            }
        ],
        db_column_rename_map={
            'native_id': 'native_id',
            'naics_code': 'naics',
            'agency': 'agency',
            'title': 'title',
            'description': 'description',
            'contract_type': 'contract_type',
            'estimated_value_text': 'estimated_value_text',
            'release_date': 'release_date',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year',
            'set_aside': 'set_aside',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'extras_json': 'extra'  # Map extras JSON to database extra field
        },
        fields_for_id_hash=['native_id', 'naics_code', 'title', 'description', 'place_city', 'place_state']
    )


def create_treasury_config() -> ScraperConfig:
    """Create configuration for Treasury scraper."""
    return ScraperConfig(
        source_name="Department of Treasury",
        base_url=None,  # Set by runner from active_config.TREASURY_FORECAST_URL
        folder_name="treas",  # Use existing folder structure
        
        # Browser settings - simple approach like other working scrapers
        use_stealth=False,
        debug_mode=True,  # Visible mode for monitoring
        
        # Extended timeouts for potentially slow site  
        navigation_timeout_ms=180000,  # 3 minutes
        interaction_timeout_ms=60000,  # 1 minute
        download_timeout_ms=300000,  # 5 minutes for slow downloads
        
        # Selectors - Treasury uses XPath (corrected from original)
        export_button_selector="//lightning-button/button[contains(text(), 'Download Opportunity Data')]",  # XPath from original
        
        # File reading - XLS files only, no HTML fallback
        file_read_strategy="excel",
        read_options={"header": 0},
        
        # Data processing - restored from original working config
        custom_transform_functions=["_custom_treasury_transforms"],
        raw_column_rename_map={
            'Specific Id': 'native_id_primary', # Primary candidate for native_id
            'ShopCart/req': 'native_id_fallback1', # Fallback candidate 1
            'Contract Number': 'native_id_fallback2', # Fallback candidate 2
            'Bureau': 'agency',
            'PSC': 'title', # Used as title
            'Type of Requirement': 'requirement_type', # Will go to extras
            'Place of Performance': 'place_raw', # For place parsing
            'Contract Type': 'contract_type',
            'NAICS': 'naics_code',
            'Estimated Total Contract Value': 'estimated_value_text', # Keep original text
            'Type of Small Business Set-aside': 'set_aside',
            'Projected Award FY_Qtr': 'award_qtr_raw', # For fiscal quarter parsing
            'Project Period of Performance Start': 'release_date_raw' # Still needs date parsing
        },
        place_column_configs=[
            {'column': 'place_raw', 
             'target_city_col': 'place_city', 
             'target_state_col': 'place_state',
             'target_country_col': 'place_country'
            }
        ],
        date_column_configs=[
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'award_qtr_raw', 
             'target_date_col': 'award_date', 
             'target_fy_col': 'award_fiscal_year',
             'parse_type': 'fiscal_quarter'
            }
        ],
        db_column_rename_map={
            # Most fields are already correctly named from raw_column_rename_map
            'native_id': 'native_id', # Custom transform will create from primary/fallback fields
            'agency': 'agency',
            'title': 'title',
            'description': 'description', # Custom transform will create
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'contract_type': 'contract_type',
            'naics_code': 'naics',
            'estimated_value_text': 'estimated_value_text',
            'set_aside': 'set_aside',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year',
            'release_date': 'release_date'
        },
        fields_for_id_hash=[
            'native_id', 
            'naics_code', 
            'title', 
            'description',
            'agency',
            'place_city', 
            'place_state'
        ]
    )


def create_dot_config() -> ScraperConfig:
    """Create configuration for DOT scraper."""
    return ScraperConfig(
        source_name="Department of Transportation",
        base_url=None,  # Set by runner from active_config.DOT_FORECAST_URL
        folder_name="dot",  # Use existing folder structure
        
        # Browser settings - DOT needs stealth mode and special args
        # DOT batch processing requires visible browser (headless detection)
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
        
        # Wait times
        wait_after_apply_ms=10000,
        
        # File reading
        read_options={"on_bad_lines": "skip", "header": 0},
        
        # Complex retry configuration for DOT
        retry_attempts=[
            {'wait_until': 'load', 'timeout': 120000, 'delay_before_next_s': 0, 'retry_delay_on_timeout_s': 10},
            {'wait_until': 'domcontentloaded', 'timeout': 90000, 'delay_before_next_s': 5, 'retry_delay_on_timeout_s': 20},
            {'wait_until': 'networkidle', 'timeout': 60000, 'delay_before_next_s': 10, 'retry_delay_on_timeout_s': 30},
            {'wait_until': 'commit', 'timeout': 45000, 'delay_before_next_s': 15, 'retry_delay_on_timeout_s': 0}
        ],
        
        # New page download configuration
        new_page_download_expect_timeout_ms=60000,
        new_page_download_initiation_wait_ms=120000,
        new_page_initial_load_wait_ms=5000,
        
        # Data processing
        custom_transform_functions=["_custom_dot_transforms", "_dot_create_extras"],
        raw_column_rename_map={
            # Core fields mapped to standard schema
            'Sequence Number': 'native_id',
            'Procurement Office': 'agency', 
            'Project Title': 'title',
            'Description': 'description',
            'Estimated Value': 'estimated_value_text',
            'NAICS': 'naics_code',
            'Competition Type': 'set_aside',
            'RFP Quarter': 'solicitation_qtr_raw',
            'Place of Performance': 'place_raw',
            'Contract Vehicle': 'contract_vehicle',
            
            # Additional fields for extras capture - all 29 columns
            'Agency': 'dot_agency',
            'FY': 'fiscal_year',
            'Procurement Category': 'procurement_category',
            'Incumbent/Contract Number': 'incumbent_contract_number',
            'Updates': 'updates',
            'Contact Name': 'contact_name',
            'Contact Email': 'contact_email',
            'Contact Phone': 'contact_phone',
            'Is this a follow-on to a current 8(a) contract?': 'followon_8a_contract',
            'Is this funded through the American Recovery and Reinvestment Act?': 'arra_funded',
            'Contract Awarded': 'contract_awarded',
            'Expected Period of Performance - Start': 'performance_start_date',
            'Expected Period of Performance - End': 'performance_end_date',
            'Personnel Clearance Requirements': 'clearance_requirements',
            'Date Modified': 'date_modified',
            'Incumbent Contractor': 'incumbent_contractor',
            'Action/Award Type': 'action_award_type',
            'Anticipated Award Date': 'anticipated_award_date',
            'Bipartisan Infrastructure Law (BIL) Opportunity': 'bil_opportunity'
        },
        date_column_configs=[
            {'column': 'solicitation_qtr_raw', 
             'target_date_col': 'release_date', 
             'target_fy_col': 'release_fiscal_year',
             'parse_type': 'fiscal_quarter'
            }
            # Note: award_date handled by custom transform
        ],
        place_column_configs=[
            {'column': 'place_raw', 
             'target_city_col': 'place_city', 
             'target_state_col': 'place_state',
             'target_country_col': 'place_country'
            }
        ],
        db_column_rename_map={
            'native_id': 'native_id',
            'agency': 'agency',
            'title': 'title',
            'description': 'description',
            'naics_code': 'naics',
            'set_aside': 'set_aside',
            'estimated_value_text': 'estimated_value_text',
            'release_date': 'release_date',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'contract_vehicle': 'contract_type',
            'extras_json': 'extra'  # Map extras JSON to database extra field
        },
        fields_for_id_hash=['native_id', 'naics_code', 'title', 'description', 'agency']
    )


def create_hhs_config() -> ScraperConfig:
    """Create configuration for HHS scraper."""
    return ScraperConfig(
        source_name="Health and Human Services",
        base_url=None,  # Set by runner from active_config.HHS_FORECAST_URL
        folder_name="hhs",  # Use existing folder structure
        
        # Browser settings - enable stealth and special args for HHS
        use_stealth=True,
        debug_mode=False,  # Headless mode for production
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
        
        # Selectors - matching original HHS config
        pre_export_click_selector='button[data-cy="viewAllBtn"]',  # "View All" button
        csv_button_selector='button:has-text("Export")',
        
        # Wait times
        pre_export_click_wait_ms=10000,
        
        # File reading
        read_options={"on_bad_lines": "skip", "header": 0},
        
        # Data processing
        custom_transform_functions=["_custom_hhs_transforms", "_hhs_create_extras"],
        raw_column_rename_map={
            # Core fields mapped to standard schema
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
            'Contracting Office': 'contract_office',
            'CO Email': 'co_email',
            'CO First Name': 'co_first_name',
            'CO Last Name': 'co_last_name',
            
            # Additional fields for extras capture - all 18 columns
            'Program POC Office': 'program_poc_office',
            'Incumbent Contractor (if applicable)': 'incumbent_contractor',
            'Existing Contract number (if applicable)': 'existing_contract_number'
        },
        date_column_configs=[
            {'column': 'award_date_raw', 'target_column': 'award_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True}
        ],
        fiscal_year_configs=[
            {'parse_type': 'from_date_year', 'date_column': 'award_date', 'target_column': 'award_fiscal_year'}
        ],
        db_column_rename_map={
            'native_id': 'native_id',  # Created by custom transform
            'title': 'title',
            'agency': 'agency',
            'description': 'description',
            'naics_code': 'naics',
            'estimated_value_text': 'estimated_value_text',
            'award_date': 'award_date',
            'release_date': 'release_date',
            'award_fiscal_year': 'award_fiscal_year',
            'set_aside': 'set_aside',
            'primary_contact_email': 'primary_contact_email',
            'primary_contact_name': 'primary_contact_name',  # Created by custom transform
            'place_country_final': 'place_country',
            'extras_json': 'extra'  # Map extras JSON to database extra field
        },
        fields_for_id_hash=['title', 'description', 'agency', 'naics_code', 'row_index'],  # row_index added by custom transform
        required_fields_for_load=['native_id', 'title']  # Minimal requirements for HHS
    )


def create_ssa_config() -> ScraperConfig:
    """Create configuration for SSA scraper."""
    return ScraperConfig(
        source_name="Social Security Administration",
        base_url=None,  # Set by runner from active_config.SSA_CONTRACT_FORECAST_URL
        folder_name="ssa",  # Use existing folder structure
        
        # Browser settings
        use_stealth=False,
        
        # Selectors for Excel links
        excel_link_selectors=[
            "a[href$='.xlsx']",
            "a[href$='.xls']", 
            "a[href$='.xlsm']",
            "a:contains('Excel')",
            "a:contains('Download')"
        ],
        
        # File reading - Excel specific with header at row 4
        file_read_strategy="excel",
        read_options={"sheet_name": "Sheet1", "header": 4, "engine": "openpyxl"},
        
        # Data processing
        custom_transform_functions=["_custom_ssa_transforms", "_ssa_create_extras"],
        raw_column_rename_map={
            # Core fields mapped to standard schema
            'APP #': 'native_id',
            'SITE Type': 'agency',
            'DESCRIPTION': 'description',  # Also used for title mapping
            'NAICS': 'naics_code',
            'CONTRACT TYPE': 'contract_type',
            'SET ASIDE': 'set_aside',
            'ESTIMATED VALUE': 'estimated_value_text',
            'AWARD FISCAL YEAR': 'award_fiscal_year',
            'PLACE OF PERFORMANCE': 'place_raw',
            
            # Additional fields for extras capture
            'REQUIREMENT TYPE': 'requirement_type',
            'EST COST PER FY': 'est_cost_per_fy',
            'PLANNED AWARD DATE': 'planned_award_date',
            'EXISTING AWD #': 'existing_award_number',
            'INCUMBENT VENDOR': 'incumbent_vendor',
            'NAICS DESCRIPTION': 'naics_description',
            'TYPE OF COMPETITION': 'type_of_competition',
            'NET VIEW TOTAL OBLIGATED AMT': 'net_view_total_obligated_amount',
            'ULTIMATE COMPLETION DATE': 'ultimate_completion_date'
        },
        place_column_configs=[
            {'column': 'place_raw', 
             'target_city_col': 'place_city', 
             'target_state_col': 'place_state',
             'target_country_col': 'place_country'
            }
        ],
        db_column_rename_map={
            'native_id': 'native_id',
            'agency': 'agency',
            'title': 'title',  # Created from description in custom transform
            'description': 'description',
            'naics_code': 'naics',
            'contract_type': 'contract_type',
            'set_aside': 'set_aside',
            'estimated_value_text': 'estimated_value_text',
            'award_fiscal_year': 'award_fiscal_year',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'extras_json': 'extra'  # Map extras JSON to database extra field
        },
        fields_for_id_hash=['native_id', 'naics_code', 'title', 'description']
    )


def create_doc_config() -> ScraperConfig:
    """Create configuration for DOC scraper."""
    return ScraperConfig(
        source_name="Department of Commerce",
        base_url=None,  # Set by runner from active_config.COMMERCE_FORECAST_URL
        folder_name="doc",  # Use existing folder structure
        
        # Browser settings
        use_stealth=False,
        
        # DOC-specific link finding
        download_link_text="Current Procurement Forecasts",
        
        # File reading - Excel specific with header at row 2
        file_read_strategy="excel",
        read_options={"sheet_name": "Sheet1", "header": 2},
        
        # Data processing
        custom_transform_functions=["_custom_doc_transforms", "_doc_create_extras"],
        raw_column_rename_map={
            # Core fields mapped to standard schema
            'Forecast ID': 'native_id',
            'Organization': 'agency',
            'Title': 'title',
            'Description': 'description',
            'Naics Code': 'naics_code',
            'Place Of Performance City': 'place_city',
            'Place Of Performance State': 'place_state',
            'Place Of Performance Country': 'place_country_raw',
            'Estimated Value Range': 'estimated_value_text',
            'Estimated Solicitation Fiscal Year': 'solicitation_fy_raw',
            'Estimated Solicitation Fiscal Quarter': 'solicitation_qtr_raw',
            'Anticipated Set Aside And Type': 'set_aside',
            'Anticipated Action Award Type': 'action_award_type',
            'Competition Strategy': 'competition_strategy',
            'Anticipated Contract Vehicle': 'contract_vehicle',
            
            # Additional fields for extras capture - all 30 columns
            'Workspace Number': 'workspace_number',
            'Date Created': 'date_created',
            'Office': 'office',
            'Organization Unit': 'organization_unit',
            'Months': 'months',
            'Years': 'years',
            'Type Of Awardee': 'type_of_awardee',
            'New Requirement Or Recompete': 'new_requirement_or_recompete',
            'Incumbent Contractor Name': 'incumbent_contractor_name',
            'Awarded Contract Order Number': 'awarded_contract_order_number',
            'Point Of Contact Name': 'point_of_contact_name',
            'Point Of Contact Email': 'point_of_contact_email',
            'Does This Acquisition Contain Information Technology': 'contains_information_technology',
            'Date Created or Modified': 'date_created_or_modified',
            'Awarded?': 'awarded'
        },
        db_column_rename_map={
            'native_id': 'native_id',
            'agency': 'agency',
            'title': 'title',
            'description': 'description',
            'naics_code': 'naics',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country_final': 'place_country',
            'estimated_value_text': 'estimated_value_text',
            'release_date_final': 'release_date',
            'award_date_final': 'award_date',
            'award_fiscal_year_final': 'award_fiscal_year',
            'set_aside': 'set_aside',
            'extras_json': 'extra'  # Map extras JSON to database extra field
        },
        fields_for_id_hash=['native_id', 'naics_code', 'title', 'description', 'place_city', 'place_state']
    )


def create_doj_config() -> ScraperConfig:
    """Create configuration for DOJ scraper.""" 
    return ScraperConfig(
        source_name="Department of Justice",
        base_url=None,  # Set by runner from active_config.DOJ_FORECAST_URL
        folder_name="doj",  # Use existing folder structure
        
        # Browser settings
        use_stealth=False,
        
        # Selectors
        export_button_selector='a:has-text("Download the Excel File")',
        
        # Timeouts
        interaction_timeout_ms=20000,  # For download link visibility
        
        # File reading - Excel specific with header at row 12
        file_read_strategy="excel",
        read_options={"sheet_name": "Contracting Opportunities Data", "header": 12},
        
        # Data processing
        custom_transform_functions=["_custom_doj_transforms", "_doj_create_extras"],
        raw_column_rename_map={
            # Core fields mapped to standard schema
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
            'Country': 'place_country_raw',
            
            # Additional fields for extras capture
            'Fiscal Year': 'fiscal_year',
            'OBD': 'obd',
            'Contracting Office': 'contracting_office',
            'DOJ Small Business POC - Name': 'doj_sb_poc_name',
            'DOJ Small Business POC - Email Address': 'doj_sb_poc_email',
            'DOJ Requirement POC - Name': 'doj_req_poc_name',
            'DOJ Requirement POC - Email Address': 'doj_req_poc_email',
            'Category': 'category',
            'Subcategory': 'subcategory',
            'Award Type': 'award_type',
            'Product Service Code': 'product_service_code',
            'Competition Approach': 'competition_approach',
            'Contracting Solution': 'contracting_solution',
            'Contract Availability': 'contract_availability',
            'Length of Contract': 'length_of_contract',
            'Request for Information (RFI) Planned': 'rfi_planned',
            'Acquisition History': 'acquisition_history',
            'Incumbent Contractor': 'incumbent_contractor',
            'Incumbent Contractor PIID': 'incumbent_contractor_piid',
            'Solicitation Link': 'solicitation_link',
            'Other Information': 'other_information'
        },
        date_column_configs=[
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'award_date_raw', 'target_column': 'award_date', 'parse_type': 'datetime', 'store_as_date': True}
        ],
        place_column_configs=[
            {'column': 'place_raw', 
             'target_city_col': 'place_city', 
             'target_state_col': 'place_state',
             'target_country_col': 'place_country'
            }
        ],
        db_column_rename_map={
            'native_id': 'native_id',
            'agency': 'agency',
            'title': 'title',
            'description': 'description',
            'contract_type': 'contract_type',
            'naics_code': 'naics',
            'set_aside': 'set_aside',
            'estimated_value_text': 'estimated_value_text',
            'release_date': 'release_date',
            'award_date_final': 'award_date',  # From custom transform
            'award_fiscal_year_final': 'award_fiscal_year',  # From custom transform
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country_final': 'place_country',  # From custom transform
            'extras_json': 'extra'  # Map extras JSON to database extra field
        },
        fields_for_id_hash=['native_id', 'naics_code', 'title', 'description', 'place_city', 'place_state']
    )


def create_dos_config() -> ScraperConfig:
    """Create configuration for DOS scraper."""
    return ScraperConfig(
        source_name="Department of State",
        base_url=None,  # Set by runner from active_config.DOS_FORECAST_URL (for reference)
        folder_name="dos",  # Use existing folder structure
        
        # Browser settings
        use_stealth=False,
        
        # DOS-specific direct download
        direct_download_url="https://www.state.gov/wp-content/uploads/2025/02/FY25-Procurement-Forecast-2.xlsx",
        
        # File reading - Excel specific 
        file_read_strategy="excel",
        read_options={"sheet_name": "FY25-Procurement-Forecast", "header": 0},
        
        # Data processing
        custom_transform_functions=["_custom_dos_transforms", "_dos_create_extras"],
        raw_column_rename_map={
            # Core fields mapped to standard schema
            'Contract Number': 'native_id',
            'Office Symbol': 'agency',
            'Requirement Title': 'title',
            'Requirement Description': 'description',
            'Estimated Value': 'estimated_value_raw1',  # Primary estimate field
            'Dollar Value': 'estimated_value_raw2',  # Secondary estimate field
            'Place of Performance Country': 'place_country_raw',
            'Place of Performance City': 'place_city_raw',
            'Place of Performance State': 'place_state_raw',
            'Award Type': 'contract_type',
            'Anticipated Award Date': 'award_date_raw',
            'Target Award Quarter': 'award_qtr_raw',
            'Fiscal Year': 'award_fiscal_year_raw',
            'Anticipated Set Aside': 'set_aside',
            'Anticipated Solicitation Release Date': 'release_date_raw',
            
            # Additional fields for extras capture - all 26 columns
            'New Requirement?': 'new_requirement',
            'Length of Performance': 'length_of_performance',
            'Facility Security Clearance': 'facility_security_clearance',
            'Past Competition': 'past_competition',
            'Past Set-Aside': 'past_set_aside',
            'Incumbent Contractor': 'incumbent_contractor',
            'Contract Vehicle': 'contract_vehicle',
            'Program Funding Agency': 'program_funding_agency',
            'Acquisition Phase': 'acquisition_phase',
            'Extent Competed': 'extent_competed',
            'Modified': 'modified'
        },
        db_column_rename_map={
            'native_id': 'native_id',
            'agency': 'agency',
            'title': 'title',
            'description': 'description',
            'place_country_final': 'place_country',
            'place_city_final': 'place_city',
            'place_state_final': 'place_state',
            'contract_type': 'contract_type',
            'award_date_final': 'award_date',
            'award_fiscal_year_final': 'award_fiscal_year',
            'set_aside': 'set_aside',
            'release_date_final': 'release_date',
            'estimated_value_final': 'estimated_value',
            'est_value_unit_final': 'est_value_unit',
            'naics_final': 'naics',
            'extras_json': 'extra'  # Map extras JSON to database extra field
        },
        fields_for_id_hash=['native_id', 'title', 'description', 'place_city_final', 'place_state_final', 'row_index']
    )