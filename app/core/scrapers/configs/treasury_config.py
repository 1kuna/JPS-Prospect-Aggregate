from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.configs.base_config import BaseScraperConfig
from app.core.scrapers.configs.acquisition_gateway_config import DataProcessingRules # Re-use structure

@dataclass
class TreasuryConfig(BaseScraperConfig):
    """
    Configuration specific to the Department of Treasury Forecast scraper.
    """
    source_name: str = "Department of Treasury"
    # base_url will be set by the runner from active_config.TREASURY_FORECAST_URL
    use_stealth: bool = False # Default, not specified as needing stealth

    download_button_xpath_selector: str = "//lightning-button/button[contains(text(), 'Download Opportunity Data')]"
    js_click_fallback_for_download: bool = True # Original scraper had JS click fallback

    # Custom flag for file reading strategy in _process_method
    file_read_strategy: str = "html_then_excel" 
    # Default read_options for the mixin's read_file_to_dataframe if strategy was different
    # For html_then_excel, these are used by the fallback excel read or if strategy changes.
    read_options: Dict[str, Any] = field(default_factory=lambda: {"header": 0})


    data_processing_rules: DataProcessingRules = field(default_factory=lambda: DataProcessingRules(
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
        value_column_configs=[
            # No value parsing needed - keeping original text in estimated_value_text
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
            'naics_code': 'naics_code',
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
    ))
