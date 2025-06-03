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
        # Custom transforms run *before* raw_column_rename_map in DataProcessingMixin.transform_dataframe
        # However, for Treasury, the native_id logic and row_index addition are better handled
        # in a dedicated method *before* calling the main transform_dataframe.
        # So, list it here, but the call order will be managed in TreasuryScraper._process_method.
        custom_transform_functions=["_custom_treasury_transforms_in_mixin_flow"], # For transforms that fit the mixin flow (e.g. description init)
        
        raw_column_rename_map={
            # Native ID handled by _custom_treasury_pre_transform
            'Specific Id': 'native_id_intermediate', # Primary candidate
            'ShopCart/req': 'shopcart_req_intermediate', # Fallback candidate 1
            'Contract Number': 'contract_num_intermediate', # Fallback candidate 2
            
            'Bureau': 'agency_intermediate',
            'PSC': 'title_intermediate', # Used as title
            # 'Type of Requirement': 'requirement_type_extra', # For extra_data
            'Place of Performance': 'place_raw',
            'Contract Type': 'contract_type_intermediate',
            'NAICS': 'naics_intermediate',
            'Estimated Total Contract Value': 'estimated_value_raw',
            'Type of Small Business Set-aside': 'set_aside_intermediate',
            'Projected Award FY_Qtr': 'award_qtr_raw',
            'Project Period of Performance Start': 'release_date_raw'
        },
        place_column_configs=[
            {'column': 'place_raw', 
             'target_city_col': 'place_city', 
             'target_state_col': 'place_state',
             'target_country_col': 'place_country', # Will default to USA
            }
        ],
        value_column_configs=[
            {'column': 'estimated_value_raw', 
             'target_value_col': 'estimated_value', 
             'target_unit_col': 'est_value_unit'
            }
        ],
        date_column_configs=[
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True},
            # For 'Projected Award FY_Qtr' (award_qtr_raw)
            {'column': 'award_qtr_raw', 
             'target_date_col': 'award_date', 
             'target_fy_col': 'award_fiscal_year',
             'parse_type': 'fiscal_quarter'
            }
        ],
        db_column_rename_map={
            'native_id_final': 'native_id', # Created by _custom_treasury_pre_transform
            'agency_intermediate': 'agency',
            'title_intermediate': 'title',
            'description_final': 'description', # Created by _custom_treasury_transforms_in_mixin_flow
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'contract_type_intermediate': 'contract_type',
            'naics_intermediate': 'naics',
            'estimated_value': 'estimated_value',
            'est_value_unit': 'est_value_unit',
            'set_aside_intermediate': 'set_aside',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year',
            'release_date': 'release_date',
            'row_index': 'row_index' # Added by _custom_treasury_pre_transform, for id_hash and extra_data
        },
        fields_for_id_hash=[ # These are columns present after all transforms, before db_map
            'native_id_final', 
            'naics_intermediate', # Name after raw rename
            'title_intermediate', # Name after raw rename
            'description_final',  # Name after custom transform
            'agency_intermediate',# Name after raw rename
            'place_city', 
            'place_state', 
            'row_index' # Added by custom transform
        ],
        # required_fields_for_load: Optional[List[str]] = ['native_id_final', 'title_intermediate']
    ))
```
