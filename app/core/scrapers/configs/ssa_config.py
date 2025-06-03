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
            'APP #': 'native_id',
            'SITE Type': 'agency',
            'DESCRIPTION': 'description', # Will also be used for title if title is missing
            'REQUIREMENT TYPE': 'requirement_type', # Will go to extras
            'EST COST PER FY': 'estimated_value_text', # Keep original text
            'PLANNED AWARD DATE': 'award_date_raw', # Still needs date parsing
            'CONTRACT TYPE': 'contract_type',
            'NAICS': 'naics_code',
            'TYPE OF COMPETITION': 'set_aside',
            'PLACE OF PERFORMANCE': 'place_raw' # For place parsing
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
            {'column': 'award_date_raw', 
             'target_column': 'award_date',
             'parse_type': 'datetime', 
             'store_as_date': True
            }
        ],
        db_column_rename_map={
            # Most fields are already correctly named from raw_column_rename_map
            'native_id': 'native_id',
            'agency': 'agency',
            'description': 'description', 
            'title': 'title', # Custom transform will create from description
            'estimated_value_text': 'estimated_value_text',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year', # Custom transform will derive from award_date
            'contract_type': 'contract_type',
            'naics_code': 'naics_code',
            'set_aside': 'set_aside',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'release_date': 'release_date' # Custom transform will set to null
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
