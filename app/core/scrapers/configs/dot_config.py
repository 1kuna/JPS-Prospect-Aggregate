from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.configs.base_config import BaseScraperConfig
from app.core.scrapers.configs.acquisition_gateway_config import DataProcessingRules # Re-use structure

@dataclass
class DOTConfig(BaseScraperConfig):
    """
    Configuration specific to the Department of Transportation (DOT) Forecast scraper.
    """
    source_name: str = "Department of Transportation"
    # base_url will be set by the runner from active_config.DOT_FORECAST_URL
    use_stealth: bool = True # DOT scraper used stealth

    apply_button_selector: str = "button:has-text('Apply')"
    wait_after_apply_ms: int = 10000
    download_csv_link_selector: str = "a:has-text('Download CSV')"

    # List of dictionaries, each defining parameters for a navigation attempt for the custom navigation logic
    navigation_retry_attempts: List[Dict[str, Any]] = field(default_factory=lambda: [
        {'wait_until': 'load', 'timeout': 120000, 'delay_before_next_s': 0, 'retry_delay_on_timeout_s': 10}, # First attempt, no delay before
        {'wait_until': 'domcontentloaded', 'timeout': 90000, 'delay_before_next_s': 5, 'retry_delay_on_timeout_s': 20},
        {'wait_until': 'networkidle', 'timeout': 60000, 'delay_before_next_s': 10, 'retry_delay_on_timeout_s': 30},
        {'wait_until': 'commit', 'timeout': 45000, 'delay_before_next_s': 15, 'retry_delay_on_timeout_s': 0} # Last attempt
    ])
    
    # For the new page opened for download
    new_page_download_expect_timeout_ms: int = 60000 
    new_page_download_initiation_wait_ms: int = 120000 # Timeout for new_page.expect_download
    new_page_initial_load_wait_ms: int = 5000 # Small wait on new page for download to start

    file_type_hint: str = "csv"
    # Default read_options for CSV, e.g., handling bad lines
    read_options: Dict[str, Any] = field(default_factory=lambda: {"on_bad_lines": "skip", "header": 0})


    data_processing_rules: DataProcessingRules = field(default_factory=lambda: DataProcessingRules(
        custom_transform_functions=["_custom_dot_transforms"],
        raw_column_rename_map={
            'Sequence Number': 'native_id',
            'Procurement Office': 'agency',
            'Project Title': 'title',
            'Description': 'description',
            'Estimated Value': 'estimated_value_text', # Keep original text
            'NAICS': 'naics_code',
            'Competition Type': 'set_aside',
            'RFP Quarter': 'solicitation_qtr_raw', # For fiscal quarter parsing
            'Anticipated Award Date': 'award_date_raw', # For custom date parsing
            'Place of Performance': 'place_raw', # For place parsing
            'Action/Award Type': 'contract_type_raw', # For custom contract_type
            'Contract Vehicle': 'contract_vehicle' # Will go to extras
        },
        place_column_configs=[
            {'column': 'place_raw', 
             'target_city_col': 'place_city', 
             'target_state_col': 'place_state',
             'target_country_col': 'place_country'
            }
        ],
        value_column_configs=[
            # No value parsing needed - keeping original text in estimated_value_text
        ],
        date_column_configs=[
            {'column': 'solicitation_qtr_raw', 
             'target_date_col': 'release_date', 
             'target_fy_col': 'release_fiscal_year',
             'parse_type': 'fiscal_quarter'
            },
            {'column': 'award_date_raw', 'target_column': 'award_date', 'parse_type': 'datetime', 'store_as_date': True}
        ],
        db_column_rename_map={
            # Most fields are already correctly named from raw_column_rename_map
            'native_id': 'native_id',
            'agency': 'agency',
            'title': 'title',
            'description': 'description',
            'naics_code': 'naics_code',
            'set_aside': 'set_aside',
            'estimated_value_text': 'estimated_value_text',
            'release_date': 'release_date',
            'award_date': 'award_date',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'contract_type': 'contract_type' # Custom transform will derive from contract_type_raw
        },
        fields_for_id_hash=[
            'native_id', 'naics_code', 'title', 'description', 
            'place_city', 'place_state'
        ],
        dropna_how_all=True
    ))
