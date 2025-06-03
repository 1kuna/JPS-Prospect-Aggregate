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
            'Sequence Number': 'native_id_raw',
            'Procurement Office': 'agency_raw',
            'Project Title': 'title_raw',
            'Description': 'description_raw',
            'Estimated Value': 'estimated_value_raw', # For value parsing
            'NAICS': 'naics_raw',
            'Competition Type': 'set_aside_raw',
            'RFP Quarter': 'solicitation_qtr_raw', # For date parsing
            'Anticipated Award Date': 'award_date_raw_custom', # For custom date parsing
            'Place of Performance': 'place_raw', # For place parsing
            'Action/Award Type': 'action_award_type_extra', # For extra_data and custom contract_type
            'Contract Vehicle': 'contract_vehicle_extra' # For extra_data
        },
        place_column_configs=[
            {'column': 'place_raw', 
             'target_city_col': 'place_city_intermediate', 
             'target_state_col': 'place_state_intermediate',
             'target_country_col': 'place_country_intermediate' # Defaults to USA if not parsed
            }
        ],
        value_column_configs=[
            {'column': 'estimated_value_raw', 
             'target_value_col': 'estimated_value', 
             'target_unit_col': 'est_value_unit'
            }
        ],
        date_column_configs=[ # For RFP Quarter -> release_date
            {'column': 'solicitation_qtr_raw', 
             'target_date_col': 'release_date_intermediate', 
             # 'target_fy_col': 'solicitation_fiscal_year', # If needed
             'parse_type': 'fiscal_quarter'
            }
            # Award date (award_date_raw_custom) is handled by _custom_dot_transforms
        ],
        db_column_rename_map={
            'native_id_raw': 'native_id',
            'agency_raw': 'agency',
            'title_raw': 'title',
            'description_raw': 'description',
            'naics_raw': 'naics',
            'set_aside_raw': 'set_aside',
            'release_date_intermediate': 'release_date',
            'award_date_final': 'award_date',           # From custom transform
            'award_fiscal_year_final': 'award_fiscal_year', # From custom transform
            'place_city_intermediate': 'place_city',
            'place_state_intermediate': 'place_state',
            'place_country_intermediate': 'place_country',
            'estimated_value': 'estimated_value',
            'est_value_unit': 'est_value_unit',
            'contract_type_final': 'contract_type', # From custom transform
        },
        fields_for_id_hash=[
            'native_id_raw', 'naics_raw', 'title_raw', 'description_raw', 
            'place_city_intermediate', 'place_state_intermediate'
        ],
        dropna_how_all: True
    ))
```
