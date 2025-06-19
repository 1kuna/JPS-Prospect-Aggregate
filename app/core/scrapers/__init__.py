"""
JPS Prospect Aggregate - Data Collectors Package
"""

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