from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.configs.base_config import BaseScraperConfig
from app.core.scrapers.configs.acquisition_gateway_config import DataProcessingRules # Re-use DataProcessingRules for structure

@dataclass
class SSAConfig(BaseScraperConfig):
    """
    Configuration specific to the Social Security Administration (SSA) Forecast scraper.
    """
    source_name: str = "Social Security Administration"
    # base_url will be set by the runner from active_config.SSA_CONTRACT_FORECAST_URL
    use_stealth: bool = False # Not specified as needing stealth

    excel_link_selectors: List[str] = field(default_factory=lambda: [
        'a:has-text("FY25 SSA Contract Forecast")', # Observed specific link text
        'a[href$=".xlsx"]',
        'a[href$=".xls"]',
        'a:has-text("Excel")',
        'a:has-text("Forecast")'
    ])
    
    file_type_hint: str = "excel"
    read_options: Dict[str, Any] = field(default_factory=lambda: {
        "sheet_name": "Sheet1", 
        "header": 4, # Row 5 in Excel is index 4
        "engine": "openpyxl" # For .xlsm if encountered, or modern .xlsx
    })

    data_processing_rules: DataProcessingRules = field(default_factory=lambda: DataProcessingRules(
        custom_transform_functions=["_custom_ssa_transforms"],
        raw_column_rename_map={
            'APP #': 'native_id_raw', # Using _raw for clarity before any type conversion
            'SITE Type': 'agency_raw',
            'DESCRIPTION': 'description_raw', # Will also be used for title if title is missing
            'REQUIREMENT TYPE': 'requirement_type_extra', # Goes to extra_data
            'EST COST PER FY': 'estimated_value_raw',
            'PLANNED AWARD DATE': 'award_date_raw',
            'CONTRACT TYPE': 'contract_type_raw',
            'NAICS': 'naics_raw',
            'TYPE OF COMPETITION': 'set_aside_raw',
            'PLACE OF PERFORMANCE': 'place_raw'
        },
        place_column_configs=[
            {'column': 'place_raw', 
             'target_city_col': 'place_city', 
             'target_state_col': 'place_state',
             'target_country_col': 'place_country', # Will default to USA if not parsed by split_place
            }
        ],
        value_column_configs=[
            {'column': 'estimated_value_raw', 
             'target_value_col': 'estimated_value', 
             'target_unit_col': 'est_value_unit'
            }
        ],
        date_column_configs=[
            # For 'PLANNED AWARD DATE' (renamed to 'award_date_raw')
            # This will create 'award_date' and 'award_fiscal_year' columns
            {'column': 'award_date_raw', 
             'target_column': 'award_date',  # Output column for the date part
             'parse_type': 'datetime', 
             'store_as_date': True,
             'create_fiscal_year_from_date': { # New sub-config for this behavior
                 'target_fy_column': 'award_fiscal_year'
                }
            }
        ],
        # db_column_rename_map maps from *intermediate, processed* column names
        # to final Prospect model field names.
        db_column_rename_map={
            'native_id_raw': 'native_id', # Assuming direct mapping after initial rename if no type change
            'agency_raw': 'agency',
            'description_final': 'description', # After custom transforms create/finalize it
            'title_final': 'title',             # After custom transforms create/finalize it
            'estimated_value': 'estimated_value',
            'est_value_unit_final': 'est_value_unit', # After custom transforms modify it
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year',
            'contract_type_raw': 'contract_type',
            'naics_raw': 'naics',
            'set_aside_raw': 'set_aside',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'release_date_final': 'release_date', # After custom transforms initialize it
            # Fields intended for 'extra_data' (e.g., 'requirement_type_extra')
            # don't need to be in this map if their names are final for the extra_data dict.
        },
        fields_for_id_hash=[ # These should be intermediate names, after raw rename & custom transforms
            'native_id_raw', 
            'naics_raw', 
            'title_final', 
            'description_final', 
            'agency_raw', 
            'place_city', 
            'place_state'
        ],
        # required_fields_for_load: Optional[List[str]] = ['native_id_raw', 'title_final'] # Example
    ))
```
