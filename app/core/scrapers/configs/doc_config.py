from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.configs.base_config import BaseScraperConfig
from app.core.scrapers.configs.acquisition_gateway_config import DataProcessingRules # Re-use structure

@dataclass
class DOCConfig(BaseScraperConfig):
    """
    Configuration specific to the Department of Commerce (DOC) Forecast scraper.
    """
    source_name: str = "Department of Commerce"
    # base_url will be set by the runner from active_config.COMMERCE_FORECAST_URL
    use_stealth: bool = False

    download_link_text: str = "Current Procurement Forecasts"
    file_type_hint: str = "excel"
    read_options: Dict[str, Any] = field(default_factory=lambda: {
        "sheet_name": "Sheet1", 
        "header": 2 # Row 3 in Excel is index 2
    })

    data_processing_rules: DataProcessingRules = field(default_factory=lambda: DataProcessingRules(
        custom_transform_functions=["_custom_doc_transforms"],
        raw_column_rename_map={
            'Forecast ID': 'native_id_raw',
            'Organization': 'agency_raw',
            'Title': 'title_raw',
            'Description': 'description_raw',
            'Naics Code': 'naics_raw',
            'Place Of Performance City': 'place_city_raw',
            'Place Of Performance State': 'place_state_raw',
            'Place Of Performance Country': 'place_country_raw',
            'Estimated Value Range': 'estimated_value_raw', 
            'Estimated Solicitation Fiscal Year': 'solicitation_fy_raw', # For custom release_date
            'Estimated Solicitation Fiscal Quarter': 'solicitation_qtr_raw', # For custom release_date
            'Anticipated Set Aside And Type': 'set_aside_raw',
            'Anticipated Action Award Type': 'action_award_type_extra', # For extra_data
            'Competition Strategy': 'competition_strategy_extra', # For extra_data
            'Anticipated Contract Vehicle': 'contract_vehicle_extra' # For extra_data
        },
        value_column_configs=[ # Declarative parsing for value ranges
            {'column': 'estimated_value_raw', 
             'target_value_col': 'estimated_value', 
             'target_unit_col': 'est_value_unit'
            }
        ],
        # Date parsing for release_date is custom due to FY/Qtr combination.
        # Award date is initialized as None in custom transforms.
        
        db_column_rename_map={
            'native_id_raw': 'native_id',
            'agency_raw': 'agency',
            'title_raw': 'title',
            'description_raw': 'description',
            'naics_raw': 'naics',
            'place_city_raw': 'place_city',
            'place_state_raw': 'place_state',
            'place_country_final': 'place_country', # Created by custom transform
            'estimated_value': 'estimated_value',
            'est_value_unit': 'est_value_unit',
            'release_date_final': 'release_date', # Created by custom transform
            'award_date_final': 'award_date',       # Created by custom transform
            'award_fiscal_year_final': 'award_fiscal_year', # Created by custom transform
            'set_aside_raw': 'set_aside',
        },
        fields_for_id_hash=[ # Names after raw_rename and custom transforms
            'native_id_raw', 
            'naics_raw', 
            'title_raw', 
            'description_raw', 
            'place_city_raw', 
            'place_state_raw'
            # 'release_date_final' could be added if it's stable enough
        ],
        dropna_how_all: True
    ))
```
