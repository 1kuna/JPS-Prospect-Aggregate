from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.configs.base_config import BaseScraperConfig
from app.core.scrapers.configs.acquisition_gateway_config import DataProcessingRules # Re-use structure

@dataclass
class HHSConfig(BaseScraperConfig):
    """
    Configuration specific to the Department of Health and Human Services (HHS) Forecast scraper.
    """
    source_name: str = "Health and Human Services"
    # base_url will be set by the runner from active_config.HHS_FORECAST_URL
    use_stealth: bool = False # Not specified as needing stealth

    view_all_button_selector: str = 'button[data-cy="viewAllBtn"]'
    export_button_selector: str = 'button:has-text("Export")'
    pre_export_click_wait_ms: int = 10000 # Wait after "View All" before clicking "Export"
    
    file_type_hint: str = "csv"
    # Default read_options for CSV, e.g., handling bad lines
    read_options: Dict[str, Any] = field(default_factory=lambda: {"on_bad_lines": "skip"})


    data_processing_rules: DataProcessingRules = field(default_factory=lambda: DataProcessingRules(
        custom_transform_functions=["_custom_hhs_transforms"],
        raw_column_rename_map={
            'Procurement Number': 'native_id',
            'Operating Division': 'agency',
            'Requirement Title': 'title',
            'Requirement Description': 'description',
            'NAICS Code': 'naics_code',
            'Contract Vehicle': 'contract_vehicle', # Will go to extras
            'Contract Type': 'contract_type',
            'Estimated Contract Value': 'estimated_value_text', # Keep original text
            'Anticipated Award Date': 'award_date_raw', # Still needs date parsing
            'Anticipated Solicitation Release Date': 'release_date_raw', # Still needs date parsing
            'Small Business Set-Aside': 'set_aside',
            'Place of Performance City': 'place_city',
            'Place of Performance State': 'place_state',
            'Place of Performance Country': 'place_country'
            # 'Contact Name', 'Contact Email', 'Contact Phone' will become extra_data
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
            'naics_code': 'naics_code',
            'contract_type': 'contract_type',
            'estimated_value_text': 'estimated_value_text',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year', # Custom transform will derive from award_date
            'release_date': 'release_date',
            'set_aside': 'set_aside',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country' # Custom transform will default to USA if missing
        },
        fields_for_id_hash=[
            'native_id', 'naics_code', 'title', 'description', 
            'agency', 'place_city', 'place_state'
        ],
        dropna_how_all=True
    ))
