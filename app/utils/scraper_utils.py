"""Utility functions and classes for web scraping."""

from app.utils.logger import logger
from app.exceptions import ScraperError

def handle_scraper_error(error: Exception, source_name: str, operation: str) -> None:
    """
    Handle scraper errors by logging them and raising a ScraperError.
    
    Args:
        error (Exception): The original exception that occurred
        source_name (str): Name of the scraper source
        operation (str): Description of the operation that failed
    """
    error_message = f"{source_name} - {operation}: {str(error)}"
    logger.error(error_message, exc_info=True)
    raise ScraperError(error_message) from error