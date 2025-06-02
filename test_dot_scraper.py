#!/usr/bin/env python3
"""
Test script to run the DOT scraper individually for troubleshooting.
"""

import sys
import os
import traceback

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.scrapers.dot_scraper import DotScraper
from app.utils.logger import logger

def test_dot_scraper(debug_mode=True):
    """Test the DOT scraper individually."""
    logger.info("Starting DOT scraper test...")
    
    try:
        # Initialize the scraper with debug mode
        scraper = DotScraper(debug_mode=debug_mode)
        
        # Run the scraper
        result = scraper.scrape()
        
        if result:
            logger.info("DOT scraper completed successfully!")
            logger.info(f"Result: {result}")
        else:
            logger.error("DOT scraper returned no result")
            
    except Exception as e:
        logger.error(f"DOT scraper failed with error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
if __name__ == "__main__":
    # Run with debug mode enabled to see browser
    test_dot_scraper(debug_mode=True)