"""
JPS Prospect Aggregate - Data Collectors Package
"""

from app.core.base_scraper import BaseScraper
from .acquisition_gateway import AcquisitionGatewayScraper
from .commerce_forecast import CommerceForecastScraper
from .dhs_scraper import DhsScraper
from .doj_scraper import DojScraper
from .dos_scraper import DosScraper
from .hhs_forecast import HhsForecastScraper
from .ssa_contract_forecast import SsaContractForecastScraper
from .treasury_scraper import TreasuryScraper
from .dot_scraper import DotScraper

# Dictionary mapping agency names to scraper classes
SCRAPERS = {
    "Acquisition Gateway": AcquisitionGatewayScraper,
    "Department of Commerce": CommerceForecastScraper,
    "Department of Homeland Security": DhsScraper,
    "Department of Justice": DojScraper,
    "Department of State": DosScraper,
    "Department of Health and Human Services": HhsForecastScraper,
    "Social Security Administration": SsaContractForecastScraper,
    "Treasury Forecast": TreasuryScraper,
    "DOT Forecast": DotScraper,
}

# Explicitly define what is exported when using 'from app.core.scrapers import *'
__all__ = [
    'BaseScraper',
    'AcquisitionGatewayScraper',
    'CommerceForecastScraper',
    'DhsScraper',
    'DojScraper',
    'DosScraper',
    'HhsForecastScraper',
    'SsaContractForecastScraper',
    'TreasuryScraper',
    'DotScraper',
    'SCRAPERS'
]