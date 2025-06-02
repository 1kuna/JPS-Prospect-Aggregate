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
        # Raw column names from the Excel file
        raw_column_rename_map={
            'Contract Number': 'native_id_raw',
            'Office Symbol': 'agency_raw',
            'Requirement Title': 'title_raw',
            'Requirement Description': 'description_raw',
            'Estimated Value': 'estimated_value_raw1', # Primary estimate field
            'Dollar Value': 'estimated_value_raw2',    # Secondary estimate field
            'Place of Performance Country': 'place_country_raw',
            'Place of Performance City': 'place_city_raw',
            'Place of Performance State': 'place_state_raw',
            'Award Type': 'contract_type_raw',
            'Anticipated Award Date': 'award_date_raw', # Raw direct date
            'Target Award Quarter': 'award_qtr_raw',    # Raw quarter string
            'Fiscal Year': 'award_fiscal_year_raw', # Raw fiscal year number
            'Anticipated Set Aside': 'set_aside_raw',
            'Anticipated Solicitation Release Date': 'release_date_raw'
        },
        # Declarative parsing for simple fields (if any) can be defined here.
        # Most complex parsing (dates, values with priority) is handled in _custom_dos_transforms.
        # For example, if 'place_country_raw' was just 'place_country', no specific place_column_config needed here if direct map.
        # The _custom_dos_transforms will create final versions of columns like 'award_date', 'award_fiscal_year', 'estimated_value', etc.
        
        # db_column_rename_map maps from columns *after all transforms* (including custom) to DB fields.
        db_column_rename_map={
            'native_id_raw': 'native_id', # Assuming direct map after initial rename
            'agency_raw': 'agency',
            'title_raw': 'title',
            'description_raw': 'description',
            'place_country_final': 'place_country', # Created/defaulted in custom
            'place_city_final': 'place_city',       # Created/defaulted in custom
            'place_state_final': 'place_state',     # Created/defaulted in custom
            'contract_type_raw': 'contract_type',
            'award_date_final': 'award_date',           # Created in custom
            'award_fiscal_year_final': 'award_fiscal_year', # Created in custom
            'set_aside_raw': 'set_aside',
            'release_date_final': 'release_date',       # Created in custom (parsed from release_date_raw)
            'estimated_value_final': 'estimated_value', # Created in custom
            'est_value_unit_final': 'est_value_unit',   # Created in custom
            'naics_final': 'naics',                     # Created in custom (set to NA)
            'row_index': 'row_index'                    # Created in custom
        },
        fields_for_id_hash=[ # These should be names of columns available after all transforms
            'native_id_raw', 
            'naics_final', 
            'title_raw', 
            'description_raw', 
            'place_city_final', 
            'place_state_final', 
            'release_date_final', 
            'award_date_final', 
            'row_index'
        ],
        dropna_how_all: True # Initial drop of fully empty rows
    ))
```
