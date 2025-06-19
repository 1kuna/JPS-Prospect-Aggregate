"""
JPS Prospect Aggregate - Data Collectors Package
"""

# Import agency mapping for consistent naming
from app.constants.agency_mapping import AGENCIES

# Import scrapers
from .acquisition_gateway import AcquisitionGatewayScraper
from .doc_scraper import DocScraper
from .dhs_scraper import DHSForecastScraper as DhsScraper
from .doj_scraper import DOJForecastScraper as DojScraper
from .dos_scraper import DOSForecastScraper as DosScraper
from .hhs_scraper import HHSForecastScraper as HhsForecastScraper
from .ssa_scraper import SsaScraper
from .treasury_scraper import TreasuryScraper
from .dot_scraper import DotScraper

# Dictionary mapping agency abbreviations to scraper classes
# Using standardized abbreviations from agency_mapping
SCRAPERS = {
    "ACQGW": AcquisitionGatewayScraper,  # Acquisition Gateway
    "DOC": DocScraper,                  # Department of Commerce
    "DHS": DhsScraper,                  # Department of Homeland Security
    "DOJ": DojScraper,                  # Department of Justice
    "DOS": DosScraper,                  # Department of State
    "HHS": HhsForecastScraper,          # Health and Human Services
    "SSA": SsaScraper,                  # Social Security Administration
    "TREAS": TreasuryScraper,           # Department of Treasury
    "DOT": DotScraper,                  # Department of Transportation
}

# Legacy mapping for backwards compatibility
LEGACY_SCRAPER_NAMES = {
    "acq_gateway": "ACQGW",
    "doc": "DOC",
    "dhs": "DHS",
    "doj": "DOJ",
    "dos": "DOS",
    "hhs": "HHS",
    "ssa": "SSA",
    "treasury": "TREAS",
    "dot": "DOT",
}

# Helper function to get scraper by name (supports legacy names)
def get_scraper(name: str):
    """Get scraper class by name, supporting both new and legacy naming."""
    # Try new naming first
    if name in SCRAPERS:
        return SCRAPERS[name]
    
    # Try legacy naming
    if name in LEGACY_SCRAPER_NAMES:
        new_name = LEGACY_SCRAPER_NAMES[name]
        return SCRAPERS[new_name]
    
    raise ValueError(f"Unknown scraper: {name}. Available: {list(SCRAPERS.keys())}")

# Explicitly define what is exported when using 'from app.core.scrapers import *'
__all__ = [
    'AcquisitionGatewayScraper',
    'DocScraper',
    'DhsScraper',
    'DojScraper',
    'DosScraper',
    'HhsForecastScraper',
    'SsaScraper',
    'TreasuryScraper',
    'DotScraper',
    'SCRAPERS',
    'LEGACY_SCRAPER_NAMES',
    'get_scraper'
]