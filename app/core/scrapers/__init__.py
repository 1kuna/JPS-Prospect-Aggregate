"""
JPS Prospect Aggregate - Data Collectors Package
"""

from app.core.base_scraper import BaseScraper
from .acquisition_gateway import AcquisitionGatewayScraper
from .ssa_contract_forecast import SSAContractForecastScraper

__all__ = ['BaseScraper', 'AcquisitionGatewayScraper', 'SSAContractForecastScraper'] 