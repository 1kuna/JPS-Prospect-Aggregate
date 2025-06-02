from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from app.core.configs.base_config import BaseScraperConfig

@dataclass
class DataProcessingRules:
    """Configuration for data processing steps within a scraper."""
    raw_column_rename_map: Dict[str, str] = field(default_factory=dict)
    # Defines how raw date columns are found and what their target (parsed) column names should be
    date_column_configs: List[Dict[str, Any]] = field(default_factory=list) 
    # Defines how raw value columns are found and what their target (parsed) column names should be
    value_column_configs: List[Dict[str, Any]] = field(default_factory=list)
    # Defines how fiscal year columns are found or derived
    fiscal_year_configs: List[Dict[str, Any]] = field(default_factory=list)
    # Defines how place/location columns are found and parsed
    place_column_configs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Maps DataFrame column names (post-transformation) to Prospect model field names
    db_column_rename_map: Dict[str, str] = field(default_factory=dict)
    # List of DataFrame column names (post-transformation, pre-DB rename) to generate id_hash
    fields_for_id_hash: List[str] = field(default_factory=list)
    # Optional list of Prospect model field names that must be non-empty for a record to be loaded
    required_fields_for_load: Optional[List[str]] = None
    # List of method names (strings) on the scraper instance for custom DataFrame transformations
    custom_transform_functions: List[str] = field(default_factory=list)
    # Boolean to control initial dropna(how='all') in transform_dataframe
    dropna_how_all: bool = True


@dataclass
class AcquisitionGatewayConfig(BaseScraperConfig):
    """
    Configuration specific to the Acquisition Gateway scraper.
    """
    source_name: str = "Acquisition Gateway" # Default, but will be set by runner
    # base_url will be set by the runner/environment config (e.g., from active_config.ACQUISITION_GATEWAY_URL)
    use_stealth: bool = True
    
    # Scraper-specific selectors and settings
    export_button_selector: str = "button#export-0"
    file_type_hint: str = "csv"
    wait_after_load_ms: int = 5000  # Explicit wait after page load and before download interaction

    # Data processing rules
    data_processing_rules: DataProcessingRules = field(default_factory=lambda: DataProcessingRules(
        custom_transform_functions=["custom_summary_fallback"], # Runs before raw_column_rename_map
        raw_column_rename_map={
            # 'Summary' will be handled by custom_summary_fallback if 'Body' is missing.
            # If 'Body' exists, it's used. If 'Body' is missing and 'Summary' exists, 'Summary' becomes 'Body'.
            # Then, 'Body' (whether original or renamed from Summary) is mapped to 'description_intermediate'.
            'Listing ID': 'native_id_intermediate', # Using intermediate suffixes for clarity
            'Title': 'title_intermediate',
            'Body': 'description_intermediate', # This is the target for original 'Body' or renamed 'Summary'
            'NAICS Code': 'naics_intermediate',
            'Estimated Contract Value': 'estimated_value_raw', # Raw, needs parsing
            'Estimated Solicitation Date': 'release_date_raw', # Raw, needs parsing
            'Ultimate Completion Date': 'award_date_raw', # Raw, needs parsing
            'Estimated Award FY': 'award_fiscal_year_raw', # Raw, needs parsing
            'Organization': 'agency_intermediate',
            'Place of Performance City': 'place_city_intermediate',
            'Place of Performance State': 'place_state_intermediate',
            'Place of Performance Country': 'place_country_intermediate',
            'Contract Type': 'contract_type_intermediate',
            'Set Aside Type': 'set_aside_intermediate'
        },
        date_column_configs=[
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'award_date_raw', 'target_column': 'award_date', 'parse_type': 'datetime', 'store_as_date': True}
        ],
        value_column_configs=[
            # For 'Estimated Contract Value' (renamed to 'estimated_value_raw')
            {'column': 'estimated_value_raw', 'target_value_col': 'estimated_value', 'target_unit_col': 'est_value_unit', 'type': 'numeric'} # 'type':'numeric' implies direct conversion after cleaning
        ],
        fiscal_year_configs=[
            # For 'Estimated Award FY' (renamed to 'award_fiscal_year_raw')
            {'column': 'award_fiscal_year_raw', 'target_column': 'award_fiscal_year', 'parse_type': 'direct'}, # 'direct' means try to use as is after pd.to_numeric
            # Fallback: if 'award_fiscal_year' is still NA, derive from 'award_date' (parsed from 'award_date_raw')
            {'date_column': 'award_date', 'target_column': 'award_fiscal_year', 'parse_type': 'from_date_year'}
        ],
        # No specific place parsing needed beyond direct mapping if columns are already split.
        # If 'Place of Performance' was a single column, place_column_configs would be used.
        
        # db_column_rename_map maps from intermediate column names (after parsing/transformation) to final DB model fields
        db_column_rename_map={
            'native_id_intermediate': 'native_id',
            'title_intermediate': 'title',
            'description_intermediate': 'description',
            'naics_intermediate': 'naics',
            'estimated_value': 'estimated_value', # Parsed from estimated_value_raw
            'est_value_unit': 'est_value_unit',   # Created during value parsing
            'release_date': 'release_date',       # Parsed from release_date_raw
            'award_date': 'award_date',           # Parsed from award_date_raw
            'award_fiscal_year': 'award_fiscal_year', # Parsed or derived
            'agency_intermediate': 'agency',
            'place_city_intermediate': 'place_city',
            'place_state_intermediate': 'place_state',
            'place_country_intermediate': 'place_country',
            'contract_type_intermediate': 'contract_type',
            'set_aside_intermediate': 'set_aside'
            # 'id_hash' is generated and added separately by prepare_and_load_data
            # 'extra_data' is generated and added separately
        },
        fields_for_id_hash=[ # These should be intermediate names, present after raw_column_rename_map and custom transforms
            'native_id_intermediate', 
            'naics_intermediate', 
            'title_intermediate', 
            'description_intermediate'
        ],
        # required_fields_for_load: Optional[List[str]] = None # Example: ['native_id', 'title'] if some fields are critical for DB record
    ))

    # Override navigation_timeout_ms from BaseScraperConfig if needed for this specific scraper
    # navigation_timeout_ms: int = 100000 # Example
    # download_timeout_ms: int = 150000 # Example
    # interaction_timeout_ms: int = 45000 # Example
```
