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
    'SCRAPERS'
]