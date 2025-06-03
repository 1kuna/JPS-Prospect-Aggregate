"""Utility functions and classes for web scraping."""

import requests
from app.utils.logger import logger
from app.exceptions import ScraperError
import pandas as pd # Added for generate_id_hash
import hashlib # Added for generate_id_hash

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


def handle_scraper_error(error: Exception, source_name: str, operation: str) -> None:
    """
    DEPRECATED for use within scraper classes. Scraper classes should use
    `self._handle_and_raise_scraper_error` for standardized error handling.
    This function remains for utility scripts or contexts outside of a scraper class instance.

    Handles scraper errors by logging them and raising a ScraperError.
    
    Args:
        error (Exception): The original exception that occurred
        source_name (str): Name of the scraper source
        operation (str): Description of the operation that failed
    """
    error_message = f"{source_name} - {operation}: {str(error)}"
    logger.error(error_message, exc_info=True)
    raise ScraperError(error_message) from error

def generate_id_hash(df: pd.DataFrame, columns: list[str], prefix: str = "") -> pd.Series:
    """
    Generates a hash for each row based on specified columns.
    A prefix can be added to the hash input to further namespace if needed.
    """
    if not isinstance(df, pd.DataFrame):
        # This kind of type checking might be too verbose for production,
        # but good for development. Consider using type hints + static analysis.
        logger.error("generate_id_hash: Input 'df' must be a pandas DataFrame.")
        raise TypeError("Input 'df' must be a pandas DataFrame.")
    if not isinstance(columns, list):
        logger.error("generate_id_hash: 'columns' must be a list of column names.")
        raise TypeError("'columns' must be a list of column names.")
    if not all(isinstance(col, str) for col in columns):
        logger.error("generate_id_hash: All elements in 'columns' must be strings.")
        raise ValueError("All elements in 'columns' must be strings.")

    cols_to_hash = [col for col in columns if col in df.columns]
    
    if not cols_to_hash:
        logger.warning(f"generate_id_hash: No valid columns found in DataFrame for hashing. Provided: {columns}. Available: {df.columns.tolist()}")
        return pd.Series([None] * len(df), index=df.index, dtype='object')

    def create_hash_input(row):
        input_parts = [prefix]
        for col in cols_to_hash: # Use only columns that actually exist in the DataFrame
            input_parts.append(str(row[col]) if pd.notna(row[col]) else '')
        return "-".join(input_parts)

    if df.empty:
        return pd.Series(dtype='object')

    hash_input_series = df.apply(create_hash_input, axis=1)
    
    return hash_input_series.apply(lambda x: hashlib.sha256(x.encode('utf-8')).hexdigest())
