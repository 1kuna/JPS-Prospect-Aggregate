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
            'Action Tracking Number': 'native_id',
            'Bureau': 'agency',
            'Contract Name': 'title',
            'Description of Requirement': 'description',
            'Contract Type (Pricing)': 'contract_type',
            'NAICS Code': 'naics_code',
            'Small Business Approach': 'set_aside',
            'Estimated Total Contract Value (Range)': 'estimated_value_text', # Keep original text
            'Target Solicitation Date': 'release_date_raw', # Still needs date parsing
            'Target Award Date': 'award_date_raw', # Still needs date parsing
            'Place of Performance': 'place_raw', # For place parsing
            'Country': 'place_country_raw' # For custom place parsing
        },
        place_column_configs=[
            {'column': 'place_raw', 
             'target_city_col': 'place_city', 
             'target_state_col': 'place_state',
             'target_country_col': 'place_country' # Will be overridden by custom transform
            }
        ],
        value_column_configs=[
            # No value parsing needed - keeping original text in estimated_value_text
        ],
        date_column_configs=[
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'award_date_raw', 'target_column': 'award_date', 'parse_type': 'datetime', 'store_as_date': True}
        ],
        db_column_rename_map={
            # Most fields are already correctly named from raw_column_rename_map
            'native_id': 'native_id',
            'agency': 'agency',
            'title': 'title',
            'description': 'description',
            'contract_type': 'contract_type',
            'naics_code': 'naics_code',
            'set_aside': 'set_aside',
            'estimated_value_text': 'estimated_value_text',
            'release_date': 'release_date',
            'award_date': 'award_date',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country' # From custom transform using place_country_raw
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
