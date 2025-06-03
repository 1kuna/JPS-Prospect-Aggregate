from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.configs.base_config import BaseScraperConfig
from app.core.scrapers.configs.acquisition_gateway_config import DataProcessingRules # Re-use structure

@dataclass
class DHSConfig(BaseScraperConfig):
    """
    Configuration specific to the Department of Homeland Security (DHS) Forecast scraper.
    """
    source_name: str = "Department of Homeland Security"
    # base_url will be set by the runner from active_config.DHS_FORECAST_URL
    use_stealth: bool = False # Default, not specified as needing stealth

    csv_button_selector: str = 'button.buttons-csv'
    explicit_wait_ms_before_download: int = 10000

    file_read_strategy: str = "csv_then_excel" # Custom flag for _process_method
    csv_read_options: Dict[str, Any] = field(default_factory=lambda: {"encoding": "utf-8"})
    excel_read_options: Dict[str, Any] = field(default_factory=lambda: {"sheet_name": 0, "header": 0})

    data_processing_rules: DataProcessingRules = field(default_factory=lambda: DataProcessingRules(
        custom_transform_functions=["_custom_dhs_transforms"],
        raw_column_rename_map={
            'APFS Number': 'native_id_raw',
            'NAICS': 'naics_raw',
            'Component': 'agency_raw',
            'Title': 'title_raw',
            'Contract Type': 'contract_type_raw',
            'Contract Vehicle': 'contract_vehicle_extra', # For extra_data
            'Dollar Range': 'estimated_value_raw',
            'Small Business Set-Aside': 'set_aside_raw',
            'Small Business Program': 'small_business_program_extra', # For extra_data
            'Contract Status': 'contract_status_extra', # For extra_data
            'Place of Performance City': 'place_city_raw',
            'Place of Performance State': 'place_state_raw',
            # No 'Place of Performance Country' in source, will be defaulted by custom transform
            'Description': 'description_raw',
            'Estimated Solicitation Release': 'release_date_raw',
            'Award Quarter': 'award_qtr_raw' # For custom award_date and award_fiscal_year
        },
        date_column_configs=[
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'award_qtr_raw', 
             'target_date_col': 'award_date', 
             'target_fy_col': 'award_fiscal_year',
             'parse_type': 'fiscal_quarter' # Processed by DataProcessingMixin.transform_dataframe
            }
        ],
        value_column_configs=[
            {'column': 'estimated_value_raw', 
             'target_value_col': 'estimated_value', 
             'target_unit_col': 'est_value_unit'
            }
        ],
        db_column_rename_map={
            'native_id_raw': 'native_id',
            'naics_raw': 'naics',
            'agency_raw': 'agency',
            'title_raw': 'title',
            'description_raw': 'description',
            'contract_type_raw': 'contract_type',
            'release_date': 'release_date',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year',
            'estimated_value': 'estimated_value',
            'est_value_unit': 'est_value_unit',
            'set_aside_raw': 'set_aside',
            'place_city_raw': 'place_city',
            'place_state_raw': 'place_state',
            'place_country_final': 'place_country', # Created by _custom_dhs_transforms
        },
        fields_for_id_hash=[ # Names after raw rename and custom transforms
            'native_id_raw', 
            'naics_raw', 
            'title_raw', 
            'description_raw', 
            'place_city_raw', 
            'place_state_raw'
            # Note: row_index was not in original DHS scraper's hash fields
        ],
        dropna_how_all: True # This is the default in DataProcessingRules, explicitly stated for clarity
    ))
```
