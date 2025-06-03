from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.configs.base_config import BaseScraperConfig
from app.core.scrapers.configs.acquisition_gateway_config import DataProcessingRules # Re-use structure

@dataclass
class DOSConfig(BaseScraperConfig):
    """
    Configuration specific to the Department of State (DOS) Forecast scraper.
    """
    source_name: str = "Department of State"
    # base_url is not strictly needed as download is direct, but can be set to the main page for reference.
    # It will be set by the runner from active_config.DOS_FORECAST_URL.
    use_stealth: bool = False 

    direct_download_url: str = "https://www.state.gov/wp-content/uploads/2025/02/FY25-Procurement-Forecast-2.xlsx"
    file_type_hint: str = "excel"
    read_options: Dict[str, Any] = field(default_factory=lambda: {
        "sheet_name": "FY25-Procurement-Forecast", 
        "header": 0
    })

    data_processing_rules: DataProcessingRules = field(default_factory=lambda: DataProcessingRules(
        custom_transform_functions=["_custom_dos_transforms"],
        raw_column_rename_map={
            'Contract Number': 'native_id',
            'Office Symbol': 'agency',
            'Requirement Title': 'title',
            'Requirement Description': 'description',
            'Estimated Value': 'estimated_value_text', # Primary estimate field  
            'Dollar Value': 'estimated_value_text2', # Secondary estimate field
            'Place of Performance Country': 'place_country',
            'Place of Performance City': 'place_city',
            'Place of Performance State': 'place_state',
            'Award Type': 'contract_type',
            'Anticipated Award Date': 'award_date_raw', # Still needs date parsing
            'Target Award Quarter': 'award_qtr_raw', # For custom transform
            'Fiscal Year': 'award_fiscal_year',
            'Anticipated Set Aside': 'set_aside',
            'Anticipated Solicitation Release Date': 'release_date_raw' # Still needs date parsing
        },
        date_column_configs=[
            {'column': 'award_date_raw', 'target_column': 'award_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True}
        ],
        value_column_configs=[
            # No value parsing needed - keeping original text in estimated_value_text
        ],
        db_column_rename_map={
            # Most fields are already correctly named from raw_column_rename_map
            'native_id': 'native_id',
            'agency': 'agency',
            'title': 'title',
            'description': 'description',
            'place_country': 'place_country',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'contract_type': 'contract_type',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year',
            'set_aside': 'set_aside',
            'release_date': 'release_date',
            'estimated_value_text': 'estimated_value_text', # Custom transform will consolidate
            'naics_code': 'naics_code' # Custom transform will set to null
        },
        fields_for_id_hash=[
            'native_id', 
            'title', 
            'description', 
            'place_city', 
            'place_state'
        ],
        dropna_how_all=True
    ))
