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
            'Forecast ID': 'native_id',
            'Organization': 'agency',
            'Title': 'title',
            'Description': 'description',
            'Naics Code': 'naics_code',
            'Place Of Performance City': 'place_city',
            'Place Of Performance State': 'place_state',
            'Place Of Performance Country': 'place_country',
            'Estimated Value Range': 'estimated_value_text', # Keep original text
            'Estimated Solicitation Fiscal Year': 'solicitation_fy_raw', # For custom release_date
            'Estimated Solicitation Fiscal Quarter': 'solicitation_qtr_raw', # For custom release_date
            'Anticipated Set Aside And Type': 'set_aside',
            'Anticipated Action Award Type': 'action_award_type', # Will go to extras
            'Competition Strategy': 'competition_strategy', # Will go to extras
            'Anticipated Contract Vehicle': 'contract_vehicle' # Will go to extras
        },
        value_column_configs=[
            # No value parsing needed - keeping original text in estimated_value_text
        ],
        date_column_configs=[
            # Date parsing for release_date is custom due to FY/Qtr combination
        ],
        db_column_rename_map={
            # Most fields are already correctly named from raw_column_rename_map
            'native_id': 'native_id',
            'agency': 'agency',
            'title': 'title',
            'description': 'description',
            'naics_code': 'naics_code',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'estimated_value_text': 'estimated_value_text',
            'release_date': 'release_date', # Created by custom transform
            'set_aside': 'set_aside'
        },
        fields_for_id_hash=[
            'native_id', 
            'naics_code', 
            'title', 
            'description', 
            'place_city', 
            'place_state'
        ],
        dropna_how_all=True
    ))
