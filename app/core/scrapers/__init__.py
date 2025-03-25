"""
JPS Prospect Aggregate - Data Collectors Package
"""

from src.data_collectors.base_scraper import BaseScraper
from src.data_collectors.acquisition_gateway import AcquisitionGatewayScraper
from src.data_collectors.ssa_contract_forecast import SSAContractForecastScraper

__all__ = ['BaseScraper', 'AcquisitionGatewayScraper', 'SSAContractForecastScraper'] 