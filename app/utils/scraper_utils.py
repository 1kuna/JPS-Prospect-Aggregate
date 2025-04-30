"""Utility functions and classes for web scraping."""

import os
import datetime
import traceback
import shutil
from typing import Optional, Dict, Any, List, Union
import pandas as pd
import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, Page, Locator

from app.exceptions import ScraperError
from app.utils.logger import logger
from app.utils.file_utils import ensure_directory
from app.config import RAW_DATA_DIR as DOWNLOADS_DIR

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

def download_file(page, selector: str, timeout: int = 60000) -> str:
    """
    Download a file using Playwright.
    
    Args:
        page: Playwright page object
        selector (str): CSS selector for the download link/button
        timeout (int): Timeout in milliseconds
        
    Returns:
        str: Path to the downloaded file
        
    Raises:
        ScraperError: If download fails
    """
    try:
        with page.expect_download(timeout=timeout) as download_info:
            page.click(selector)
            download = download_info.value
            
            # Save and verify file
            download_path = download.path()
            if not os.path.exists(download_path) or os.path.getsize(download_path) == 0:
                raise ScraperError("Download failed: File is empty or does not exist")
            
            return download_path
            
    except PlaywrightTimeoutError as e:
        raise ScraperError(f"Timeout error during download: {str(e)}")
    except Exception as e:
        raise ScraperError(f"Error downloading file: {str(e)}")

def save_permanent_copy(temp_path: str, source_name: str, file_type: str) -> str:
    """
    Save a permanent copy of a file with timestamp.
    
    Args:
        temp_path (str): Path to temporary file
        source_name (str): Name of the data source
        file_type (str): Type of file (e.g., 'csv', 'xlsx')
        
    Returns:
        str: Path to the permanent file
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source_name.lower().replace(' ', '_')}_{timestamp}.{file_type}"
    permanent_path = os.path.join(DOWNLOADS_DIR, filename)
    
    ensure_directory(os.path.dirname(permanent_path))
    shutil.copy2(temp_path, permanent_path)
    logger.info(f"Saved permanent copy to {permanent_path}")
    
    return permanent_path

def read_dataframe(file_path: str, file_type: str = 'csv') -> pd.DataFrame:
    """
    Read a data file into a pandas DataFrame.
    
    Args:
        file_path (str): Path to the file
        file_type (str): Type of file ('csv' or 'xlsx')
        
    Returns:
        pd.DataFrame: Loaded DataFrame
        
    Raises:
        ScraperError: If file reading fails
    """
    try:
        if file_type == 'csv':
            df = pd.read_csv(file_path)
        elif file_type == 'xlsx':
            df = pd.read_excel(file_path)
        else:
            raise ScraperError(f"Unsupported file type: {file_type}")
            
        if df.empty:
            raise ScraperError(f"{file_type.upper()} file has no data rows")
            
        return df
    except pd.errors.EmptyDataError:
        raise ScraperError(f"{file_type.upper()} file is empty or has no data")
    except Exception as e:
        raise ScraperError(f"Error reading {file_type.upper()} file: {str(e)}")

def transform_dataframe(
    df: pd.DataFrame,
    column_mapping: Dict[str, str],
    date_columns: Optional[List[str]] = None,
    value_columns: Optional[List[str]] = None,
    parse_funcs: Optional[Dict[str, callable]] = None
) -> List[Dict[str, Any]]:
    """
    Transform a DataFrame using column mapping and custom parsing functions.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        column_mapping (Dict[str, str]): Mapping of DataFrame columns to output fields
        date_columns (List[str], optional): Columns to parse as dates
        value_columns (List[str], optional): Columns to parse as numeric values
        parse_funcs (Dict[str, callable], optional): Custom parsing functions for specific fields
        
    Returns:
        List[Dict[str, Any]]: Transformed data
    """
    date_columns = date_columns or []
    value_columns = value_columns or []
    parse_funcs = parse_funcs or {}
    
    transformed_data = []
    
    for _, row in df.iterrows():
        item = {}
        
        for excel_col, db_field in column_mapping.items():
            value = row[excel_col]
            
            # Handle NaN values
            if pd.isna(value):
                value = None
            # Parse dates
            elif db_field in date_columns and value is not None:
                value = parse_funcs.get('date', lambda x: x)(str(value))
            # Parse numeric values
            elif db_field in value_columns and value is not None:
                value = parse_funcs.get('value', lambda x: x)(str(value))
            # Use custom parsing function if available
            elif db_field in parse_funcs and value is not None:
                value = parse_funcs[db_field](value)
                
            item[db_field] = value
            
        transformed_data.append(item)
    
    return transformed_data

def handle_scraper_error(error: Exception, source_name: str, context: str = "") -> None:
    """
    Handle scraper errors with consistent logging and status updates.
    
    Args:
        error (Exception): The error that occurred
        source_name (str): Name of the data source
        context (str): Additional context about where the error occurred
    """
    error_msg = f"{context + ': ' if context else ''}{str(error)}"
    logger.error(error_msg)
    logger.error(traceback.format_exc())
    
    # Update scraper status in database
    # --> Temporarily disable DB update during testing <--
    # from app.utils.db_utils import update_scraper_status
    # update_scraper_status(source_name, "error", error_msg) 