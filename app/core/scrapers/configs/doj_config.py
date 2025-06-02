from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.configs.base_config import BaseScraperConfig
from app.core.scrapers.configs.acquisition_gateway_config import DataProcessingRules # Re-use structure

@dataclass
class DOJConfig(BaseScraperConfig):
    """
    Configuration specific to the Department of Justice (DOJ) Forecast scraper.
    """
    source_name: str = "Department of Justice"
    # base_url will be set by the runner from active_config.DOJ_FORECAST_URL
    use_stealth: bool = False

    download_link_selector: str = 'a:has-text("Download the Excel File")'
    download_link_wait_timeout_ms: int = 20000 # Timeout for the link to be visible

    file_type_hint: str = "excel"
    read_options: Dict[str, Any] = field(default_factory=lambda: {
        "sheet_name": "Contracting Opportunities Data", 
        "header": 12 
    })

    data_processing_rules: DataProcessingRules = field(default_factory=lambda: DataProcessingRules(
        custom_transform_functions=["_custom_doj_transforms"],
        raw_column_rename_map={
            'Action Tracking Number': 'native_id_raw',
            'Bureau': 'agency_raw',
            'Contract Name': 'title_raw',
            'Description of Requirement': 'description_raw',
            'Contract Type (Pricing)': 'contract_type_raw',
            'NAICS Code': 'naics_raw',
            'Small Business Approach': 'set_aside_raw',
            'Estimated Total Contract Value (Range)': 'estimated_value_raw',
            'Target Solicitation Date': 'release_date_raw', 
            'Target Award Date': 'award_date_raw', # Input for complex custom date logic
            'Place of Performance': 'place_raw', # For declarative place parsing
            'Country': 'place_country_raw' # For custom place country logic
        },
        place_column_configs=[ # Declarative parsing for main place components
            {'column': 'place_raw', 
             'target_city_col': 'place_city_intermediate', # Use intermediate names
             'target_state_col': 'place_state_intermediate',
             # Country handled by custom transform due to specific 'Country' column
            }
        ],
        value_column_configs=[
            {'column': 'estimated_value_raw', 
             'target_value_col': 'estimated_value', 
             'target_unit_col': 'est_value_unit'
            }
        ],
        date_column_configs=[ # Declarative parsing for release_date
            {'column': 'release_date_raw', 
             'target_column': 'release_date_intermediate', # Use intermediate name
             'parse_type': 'datetime', 
             'store_as_date': True
            }
            # Award date (award_date_raw) is handled by _custom_doj_transforms
        ],
        db_column_rename_map={
            'native_id_raw': 'native_id',
            'agency_raw': 'agency',
            'title_raw': 'title',
            'description_raw': 'description',
            'contract_type_raw': 'contract_type',
            'naics_raw': 'naics',
            'set_aside_raw': 'set_aside',
            'estimated_value': 'estimated_value',
            'est_value_unit': 'est_value_unit',
            'release_date_intermediate': 'release_date', # From declarative parsing
            'award_date_final': 'award_date',           # From custom transform
            'award_fiscal_year_final': 'award_fiscal_year', # From custom transform
            'place_city_intermediate': 'place_city',     # From declarative parsing
            'place_state_intermediate': 'place_state',   # From declarative parsing
            'place_country_final': 'place_country',     # From custom transform
        },
        fields_for_id_hash=[ # Names after raw rename, declarative parse, and custom transforms
            'native_id_raw', 
            'naics_raw', 
            'title_raw', 
            'description_raw', 
            'place_city_intermediate', # Name after declarative place parse
            'place_state_intermediate' # Name after declarative place parse
        ],
        dropna_how_all: True
    ))
```
