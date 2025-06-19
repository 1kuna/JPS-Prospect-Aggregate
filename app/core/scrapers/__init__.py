"""
JPS Prospect Aggregate - Data Collectors Package
"""

# Import consolidated scrapers
from .acquisition_gateway_consolidated import AcquisitionGatewayScraper
from .doc_scraper_consolidated import DocScraper
from .dhs_scraper_consolidated import DHSForecastScraper as DhsScraper
from .doj_scraper_consolidated import DOJForecastScraper as DojScraper
from .dos_scraper_consolidated import DOSForecastScraper as DosScraper
from .hhs_scraper_consolidated import HHSForecastScraper as HhsForecastScraper
from .ssa_scraper_consolidated import SsaScraper
from .treasury_scraper_consolidated import TreasuryScraper
from .dot_scraper_consolidated import DotScraper

# Dictionary mapping agency names to scraper classes
SCRAPERS = {
    "acq_gateway": AcquisitionGatewayScraper,
    "doc": DocScraper,
    "dhs": DhsScraper,
    "doj": DojScraper,
    "dos": DosScraper,
    "hhs": HhsForecastScraper,
    "ssa": SsaScraper,
    "treasury": TreasuryScraper,
    "dot": DotScraper,
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