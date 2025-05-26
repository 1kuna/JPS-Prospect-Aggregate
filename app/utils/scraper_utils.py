"""Utility functions and classes for web scraping."""

import requests
from app.utils.logger import logger

def check_url_accessibility(url: str, timeout: int = 10, verify_ssl: bool = True) -> bool:
    """
    Check if a URL is accessible.
    
    Args:
        url (str): URL to check
        timeout (int): Timeout in seconds
        verify_ssl (bool): Whether to verify SSL certificate. Defaults to True.
        
    Returns:
        bool: True if the URL is accessible, False otherwise
    """
    logger.info(f"Checking accessibility of {url} (SSL Verify: {verify_ssl})")
    
    try:
        response = requests.head(url, timeout=timeout, verify=verify_ssl)
        if response.status_code < 400:
            logger.info(f"URL {url} is accessible (status code: {response.status_code})")
            return True
        
        logger.error(f"URL {url} returned status code {response.status_code}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking URL {url}: {str(e)}")
        return False