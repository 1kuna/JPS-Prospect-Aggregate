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
            # Direct mapping to new schema fields
            'Listing ID': 'native_id',
            'Title': 'title',
            'Body': 'description', # Will be handled by custom_summary_fallback if missing
            'NAICS Code': 'naics_code',
            'Estimated Contract Value': 'estimated_value_text', # Keep original text
            'Estimated Solicitation Date': 'release_date_raw', # Still needs date parsing
            'Ultimate Completion Date': 'award_date_raw', # Still needs date parsing
            'Estimated Award FY': 'award_fiscal_year',
            'Organization': 'agency',
            'Agency': 'parent_agency', # Additional agency info
            'Place of Performance City': 'place_city',
            'Place of Performance State': 'place_state', 
            'Place of Performance Country': 'place_country',
            'Contract Type': 'contract_type',
            'Set Aside Type': 'set_aside'
        },
        date_column_configs=[
            {'column': 'release_date_raw', 'target_column': 'release_date', 'parse_type': 'datetime', 'store_as_date': True},
            {'column': 'award_date_raw', 'target_column': 'award_date', 'parse_type': 'datetime', 'store_as_date': True}
        ],
        value_column_configs=[
            # No value parsing needed - keeping original text in estimated_value_text
        ],
        fiscal_year_configs=[
            # Award fiscal year is already mapped correctly, just ensure it's numeric
            {'column': 'award_fiscal_year', 'target_column': 'award_fiscal_year', 'parse_type': 'direct'},
            # Fallback: if 'award_fiscal_year' is still NA, derive from 'award_date'
            {'date_column': 'award_date', 'target_column': 'award_fiscal_year', 'parse_type': 'from_date_year'}
        ],
        # No specific place parsing needed beyond direct mapping if columns are already split.
        # If 'Place of Performance' was a single column, place_column_configs would be used.
        
        # db_column_rename_map maps from intermediate column names (after parsing/transformation) to final DB model fields
        db_column_rename_map={
            # Most fields are already correctly named from raw_column_rename_map
            # Only map fields that need different names for the DB
            'native_id': 'native_id',
            'title': 'title',
            'description': 'description',
            'naics_code': 'naics_code',
            'estimated_value_text': 'estimated_value_text',
            'release_date': 'release_date',
            'award_date': 'award_date',
            'award_fiscal_year': 'award_fiscal_year',
            'agency': 'agency',
            'place_city': 'place_city',
            'place_state': 'place_state',
            'place_country': 'place_country',
            'contract_type': 'contract_type',
            'set_aside': 'set_aside'
        },
        fields_for_id_hash=[ # These should match the column names after raw_column_rename_map
            'native_id', 
            'naics_code', 
            'title', 
            'description'
        ],
        # required_fields_for_load: Optional[List[str]] = None # Example: ['native_id', 'title'] if some fields are critical for DB record
    ))

    # Override navigation_timeout_ms from BaseScraperConfig if needed for this specific scraper
    # navigation_timeout_ms: int = 100000 # Example
    # download_timeout_ms: int = 150000 # Example
    # interaction_timeout_ms: int = 45000 # Example
