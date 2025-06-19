"""
Agency abbreviation mapping for consistent naming across the system.

This module provides standardized agency abbreviations and mappings to ensure
consistent naming conventions throughout the JPS Prospect Aggregate system.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AgencyInfo:
    """Information about a government agency."""
    abbreviation: str
    full_name: str
    scraper_name: str
    data_directory: str


# Standard agency abbreviations and information
AGENCIES = {
    "ACQGW": AgencyInfo(
        abbreviation="ACQGW",
        full_name="Acquisition Gateway",
        scraper_name="acquisition_gateway",
        data_directory="acqgw"
    ),
    "DHS": AgencyInfo(
        abbreviation="DHS",
        full_name="Department of Homeland Security",
        scraper_name="dhs_scraper",
        data_directory="dhs"
    ),
    "SSA": AgencyInfo(
        abbreviation="SSA",
        full_name="Social Security Administration",
        scraper_name="ssa_scraper",
        data_directory="ssa"
    ),
    "DOC": AgencyInfo(
        abbreviation="DOC",
        full_name="Department of Commerce",
        scraper_name="doc_scraper",
        data_directory="doc"
    ),
    "DOS": AgencyInfo(
        abbreviation="DOS",
        full_name="Department of State",
        scraper_name="dos_scraper",
        data_directory="dos"
    ),
    "HHS": AgencyInfo(
        abbreviation="HHS",
        full_name="Health and Human Services",
        scraper_name="hhs_scraper",
        data_directory="hhs"
    ),
    "DOJ": AgencyInfo(
        abbreviation="DOJ",
        full_name="Department of Justice",
        scraper_name="doj_scraper",
        data_directory="doj"
    ),
    "TREAS": AgencyInfo(
        abbreviation="TREAS",
        full_name="Department of Treasury",
        scraper_name="treasury_scraper",
        data_directory="treas"
    ),
    "DOT": AgencyInfo(
        abbreviation="DOT",
        full_name="Department of Transportation",
        scraper_name="dot_scraper",
        data_directory="dot"
    ),
}

# NOTE: Forecast data is now consolidated into main agency directories
# No separate forecast directories - all data goes into agency abbreviation folders

# Legacy name mappings for backwards compatibility during migration
LEGACY_MAPPINGS = {
    # Old directory names -> New abbreviations
    "department_of_homeland_security": "DHS",
    "social_security_administration": "SSA", 
    "department_of_commerce": "DOC",
    "department_of_state": "DOS",
    "health_and_human_services": "HHS",
    "department_of_justice": "DOJ",
    "department_of_treasury": "TREAS",
    "department_of_transportation": "DOT",
    "acquisition_gateway": "ACQGW",
    
    # Old scraper names -> New abbreviations
    "dhs_scraper": "DHS",
    "ssa_scraper": "SSA",
    "doc_scraper": "DOC", 
    "dos_scraper": "DOS",
    "hhs_scraper": "HHS",
    "doj_scraper": "DOJ",
    "treasury_scraper": "TREAS",
    "dot_scraper": "DOT",
}


def get_agency_by_abbreviation(abbrev: str) -> AgencyInfo:
    """Get agency information by abbreviation."""
    if abbrev not in AGENCIES:
        raise ValueError(f"Unknown agency abbreviation: {abbrev}")
    return AGENCIES[abbrev]


def get_agency_by_legacy_name(legacy_name: str) -> AgencyInfo:
    """Get agency information by legacy name (for migration purposes)."""
    if legacy_name not in LEGACY_MAPPINGS:
        raise ValueError(f"Unknown legacy name: {legacy_name}")
    abbrev = LEGACY_MAPPINGS[legacy_name]
    return AGENCIES[abbrev]


def get_all_abbreviations() -> List[str]:
    """Get list of all agency abbreviations."""
    return list(AGENCIES.keys())


def get_abbreviation_mapping() -> Dict[str, str]:
    """Get mapping of full names to abbreviations."""
    return {info.full_name: abbrev for abbrev, info in AGENCIES.items()}


def get_data_directory_mapping() -> Dict[str, str]:
    """Get mapping of current data directory names to abbreviations."""
    return {info.data_directory: abbrev for abbrev, info in AGENCIES.items()}


# Forecast directory mapping removed - all data now in consolidated agency directories


def standardize_file_name(agency_abbrev: str, timestamp: str, extension: str = "csv") -> str:
    """
    Generate standardized file name based on agency abbreviation.
    
    Args:
        agency_abbrev: Standard agency abbreviation (e.g., 'DHS', 'SSA')
        timestamp: Timestamp string (YYYYMMDD_HHMMSS format)
        extension: File extension without dot (default: 'csv')
    
    Returns:
        Standardized filename: {abbrev}_{timestamp}.{extension}
    """
    if agency_abbrev not in AGENCIES:
        raise ValueError(f"Unknown agency abbreviation: {agency_abbrev}")
    
    return f"{agency_abbrev.lower()}_{timestamp}.{extension}"


def validate_agency_abbreviation(abbrev: str) -> bool:
    """Validate if abbreviation is a known agency."""
    return abbrev in AGENCIES