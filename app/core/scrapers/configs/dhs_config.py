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
            'APFS Number': 'native_id',
            'NAICS': 'naics_code',
            'Component': 'agency',
            'Title': 'title',
            'Contract Type': 'contract_type',
            'Contract Vehicle': 'contract_vehicle', # Will go to extras
            'Dollar Range': 'estimated_value_text', # Keep original text
            'Small Business Set-Aside': 'set_aside',
            'Small Business Program': 'small_business_program', # Will go to extras
            'Contract Status': 'contract_status', # Will go to extras
            'Place of Performance City': 'place_city',
            'Place of Performance State': 'place_state',
            'Description': 'description',
            'Estimated Solicitation Release': 'release_date_raw', # Still needs date parsing
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
            # No value parsing needed - keeping original text in estimated_value_text
        ],
        db_column_rename_map={
            # Most fields are already correctly named from raw_column_rename_map
            'native_id': 'native_id',
            'naics_code': 'naics_code',
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
            'place_country': 'place_country' # Created by custom transform
        },
        fields_for_id_hash=[ # Names after raw rename and custom transforms
            'native_id', 
            'naics_code', 
            'title', 
            'description', 
            'place_city', 
            'place_state'
        ],
        dropna_how_all=True # This is the default in DataProcessingRules, explicitly stated for clarity
    ))
