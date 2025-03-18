"""
Scraper registry module for maintaining a registry of all scrapers.

This module provides a central registry for all scrapers in the application,
making it easy to discover and manage scrapers.
"""

import logging
from src.utils.logging import get_component_logger

# Set up logging using the centralized utility
logger = get_component_logger('scrapers.registry')

class ScraperRegistry:
    """Registry for scrapers."""
    
    def __init__(self):
        """Initialize the scraper registry."""
        self.scrapers = {}
    
    def register_scraper(self, scraper_name, scraper_func):
        """
        Register a scraper.
        
        Args:
            scraper_name (str): Name of the scraper
            scraper_func (callable): Function that runs the scraper
        """
        logger.info(f"Registering scraper: {scraper_name}")
        self.scrapers[scraper_name] = scraper_func
    
    def get_scraper(self, scraper_name):
        """
        Get a scraper by name.
        
        Args:
            scraper_name (str): Name of the scraper
            
        Returns:
            callable: Scraper function, or None if not found
        """
        return self.scrapers.get(scraper_name)
    
    def get_all_scrapers(self):
        """
        Get all registered scrapers.
        
        Returns:
            dict: Dictionary of all registered scrapers
        """
        return self.scrapers

# Create a singleton instance of the scraper registry
scraper_registry = ScraperRegistry() 