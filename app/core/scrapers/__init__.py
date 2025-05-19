"""
JPS Prospect Aggregate - Data Collectors Package
"""

from app.core.base_scraper import BaseScraper
from .acquisition_gateway import AcquisitionGatewayScraper
from .doc_scraper import DocScraper
from .dhs_scraper import DHSForecastScraper as DhsScraper
from .doj_scraper import DOJForecastScraper as DojScraper
from .dos_scraper import DOSForecastScraper as DosScraper
from .hhs_forecast import HHSForecastScraper as HhsForecastScraper
from .ssa_scraper import SsaScraper
from .treasury_scraper import TreasuryScraper
from .dot_scraper import DotScraper

# Dictionary mapping agency names to scraper classes
SCRAPERS = {
    "Acquisition Gateway": AcquisitionGatewayScraper,
    "Department of Commerce": DocScraper,
    "Department of Homeland Security": DhsScraper,
    "Department of Justice": DojScraper,
    "Department of State": DosScraper,
    "Department of Health and Human Services": HhsForecastScraper,
    "Social Security Administration": SsaScraper,
    "Treasury Forecast": TreasuryScraper,
    "DOT Forecast": DotScraper,
}

# Explicitly define what is exported when using 'from app.core.scrapers import *'
__all__ = [
    'BaseScraper',
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