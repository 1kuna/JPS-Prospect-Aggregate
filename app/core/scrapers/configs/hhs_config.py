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
        # Raw column names from the CSV file
        raw_column_rename_map={
            'Procurement Number': 'native_id_raw',
            'Operating Division': 'agency_raw',
            'Requirement Title': 'title_raw',
            'Requirement Description': 'description_raw',
            'NAICS Code': 'naics_raw',
            'Contract Vehicle': 'contract_vehicle_extra', # For extra_data
            'Contract Type': 'contract_type_raw',
            'Estimated Contract Value': 'estimated_value_raw',
            'Anticipated Award Date': 'award_date_raw',
            'Anticipated Solicitation Release Date': 'release_date_raw',
            'Small Business Set-Aside': 'set_aside_raw',
            'Place of Performance City': 'place_city_raw',
            'Place of Performance State': 'place_state_raw',
            'Place of Performance Country': 'place_country_raw' # May be NA or present
            # 'Contact Name', 'Contact Email', 'Contact Phone' will become extra_data if present and not mapped
        },
        date_column_configs=[
            {'column': 'award_date_raw', 'target_column': 'award_date', 'parse_type': 'datetime', 'store_as_date': True,
             'create_fiscal_year_from_date': {'target_fy_column': 'award_fiscal_year'}
            },
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True}
        ],
        value_column_configs=[
            {'column': 'estimated_value_raw', 
             'target_value_col': 'estimated_value', 
             'target_unit_col': 'est_value_unit'
            }
        ],
        # db_column_rename_map maps from columns *after all transforms* (raw rename + custom) to DB fields.
        db_column_rename_map={
            'native_id_raw': 'native_id',
            'agency_raw': 'agency',
            'title_raw': 'title',
            'description_raw': 'description',
            'naics_raw': 'naics',
            'contract_type_raw': 'contract_type',
            'estimated_value': 'estimated_value',
            'est_value_unit': 'est_value_unit',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year',
            'release_date': 'release_date',
            'set_aside_raw': 'set_aside',
            'place_city_raw': 'place_city',
            'place_state_raw': 'place_state',
            'place_country_final': 'place_country', # Created by _custom_hhs_transforms
            'row_index': 'row_index' # Created by _custom_hhs_transforms
        },
        fields_for_id_hash=[ # These are columns after raw rename & custom transforms
            'native_id_raw', 'naics_raw', 'title_raw', 'description_raw', 
            'agency_raw', 'place_city_raw', 'place_state_raw', 'contract_type_raw', 
            'set_aside_raw', 'estimated_value', 'award_date', 'release_date', 
            'row_index' # Added by custom transform for uniqueness
        ],
        dropna_how_all: True
    ))
```
