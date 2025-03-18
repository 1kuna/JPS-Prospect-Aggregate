"""
Unified Logging System

This module provides a centralized, flexible logging system for the application,
with log management functionality included.

The module is divided into two main sections:
1. Logger Configuration - Functions for creating and configuring loggers
2. Log Management - Utilities for log file rotation and cleanup

Features:
- Configurable logging levels based on environment
- Console and file logging with consistent formatting
- Support for categorized loggers (component, scraper, etc.)
- Rotating file handlers with size limits
- Different log formats for development and production
- Log file cleanup and rotation utilities
"""

import os
import sys
import re
import glob
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any, Literal

from src.config import LOGS_DIR, LOG_FORMAT, LOG_FILE_MAX_BYTES, LOG_FILE_BACKUP_COUNT
from src.utils.file_utils import ensure_directories, cleanup_files

#################################################
# SECTION 1: LOGGER CONFIGURATION              #
#################################################

# Default log levels by environment
DEFAULT_LOG_LEVELS = {
    'development': logging.DEBUG,
    'testing': logging.DEBUG,
    'production': logging.INFO,
    'default': logging.INFO
}

# Log format constants
DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
SIMPLE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Logger categories
CATEGORY_COMPONENT = 'component'
CATEGORY_SCRAPER = 'scraper'
CATEGORY_SYSTEM = 'system'


def get_environment() -> str:
    """
    Get the current environment from environment variables.
    
    Returns:
        str: Current environment ('development', 'testing', 'production', or 'default')
    """
    return os.getenv('FLASK_ENV', 'default').lower()


def get_log_level(level_name: Optional[str] = None) -> int:
    """
    Convert a log level name to a logging level constant.
    
    Args:
        level_name: Log level name (e.g., 'DEBUG', 'INFO') or None to use environment default
        
    Returns:
        int: Logging level constant from the logging module
    """
    if level_name is None:
        # Use environment-specific default
        environment = get_environment()
        return DEFAULT_LOG_LEVELS.get(environment, DEFAULT_LOG_LEVELS['default'])
    
    if isinstance(level_name, int):
        # If it's already a level constant, return it
        return level_name
    
    # Convert string level to constant
    level_name = level_name.upper()
    level_map = {
        'CRITICAL': logging.CRITICAL,
        'FATAL': logging.FATAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'WARN': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET
    }
    
    return level_map.get(level_name, DEFAULT_LOG_LEVELS['default'])


def get_logger(
    name: str,
    category: str = CATEGORY_COMPONENT,
    log_level: Optional[Union[str, int]] = None,
    log_file: Optional[str] = None,
    console: bool = True,
    detailed_format: bool = False,
    propagate: bool = True,
    debug_mode: bool = False
) -> logging.Logger:
    """
    Unified function to get a configured logger for any purpose.
    
    This is the core logging function that handles all logging setup.
    Other specialized logging functions are thin wrappers around this.
    
    Args:
        name: Logger name (e.g., 'api', 'scraper.ssa')
        category: Logger category ('component', 'scraper', 'system')
        log_level: Log level (name or constant). If None, uses environment default.
        log_file: Log file name. If None, auto-generated based on category and name.
        console: Whether to log to console
        detailed_format: Whether to use detailed format (with filename/line numbers)
        propagate: Whether the logger should propagate to parent loggers
        debug_mode: Override to force DEBUG level (mainly for scrapers)
        
    Returns:
        logging.Logger: Configured logger
    """
    # Get the logger
    logger = logging.getLogger(name)
    
    # Determine log level
    if debug_mode:
        # Force debug mode if requested
        level = logging.DEBUG
    elif log_level is not None:
        # Use specified level
        level = get_log_level(log_level)
    else:
        # Use default from environment
        level = get_log_level()
    
    # Set log level
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Select log format
    log_format = DETAILED_FORMAT if detailed_format else SIMPLE_FORMAT
    formatter = logging.Formatter(log_format)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
    
    # Generate automatic log file name if not provided
    if log_file is None:
        # Clean up name for file naming
        clean_name = name.lower().replace('.', '_').replace(' ', '_')
        
        if category == CATEGORY_SCRAPER:
            log_file = f"{clean_name}_scraper.log"
        elif category == CATEGORY_SYSTEM:
            log_file = f"system_{clean_name}.log"
        else:  # Default component
            log_file = f"{clean_name}.log"
    
    # Add file handler
    if log_file:
        # Ensure logs directory exists
        ensure_directories(LOGS_DIR)
        
        # Create full path
        log_path = os.path.join(LOGS_DIR, log_file)
        
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    
    # Set propagation
    logger.propagate = propagate
    
    return logger


# Specialized logger functions

def get_component_logger(
    component_name: str,
    log_level: Optional[Union[str, int]] = None,
    detailed_format: bool = False
) -> logging.Logger:
    """
    Get a logger for a specific application component.
    
    Args:
        component_name: Component name (e.g., 'api', 'scraper.ssa')
        log_level: Log level (name or constant). If None, uses environment default.
        detailed_format: Whether to use detailed format (with filename/line numbers)
        
    Returns:
        logging.Logger: Configured logger
    """
    return get_logger(
        name=component_name,
        category=CATEGORY_COMPONENT,
        log_level=log_level,
        detailed_format=detailed_format,
        console=True
    )


def get_scraper_logger(scraper_name: str, debug_mode: bool = False) -> logging.Logger:
    """
    Get a logger specifically configured for a scraper.
    
    Args:
        scraper_name: Name of the scraper
        debug_mode: Whether to use DEBUG level logging
        
    Returns:
        logging.Logger: Configured logger
    """
    return get_logger(
        name=f"scraper.{scraper_name}",
        category=CATEGORY_SCRAPER,
        debug_mode=debug_mode,
        detailed_format=debug_mode,  # Use detailed format in debug mode
        console=True
    )


def configure_root_logger(log_level: Optional[Union[str, int]] = None) -> logging.Logger:
    """
    Configure the root logger for the application.
    
    Args:
        log_level: Log level (name or constant). If None, uses environment default.
        
    Returns:
        logging.Logger: Configured root logger
    """
    return get_logger(
        name='root',
        category=CATEGORY_SYSTEM,
        log_level=log_level,
        log_file='app.log',
        console=True,
        detailed_format=False,
        propagate=False  # Root logger doesn't propagate
    )


#################################################
# SECTION 2: LOG MANAGEMENT                    #
#################################################

# Set up logging using the component logger
logger = get_component_logger('utils.logging')

def cleanup_log_files(logs_dir, pattern, keep_count=3):
    """
    Cleanup log files matching the given pattern, keeping only the most recent ones.
    
    Args:
        logs_dir (str): Path to the logs directory
        pattern (str): Glob pattern to match log files (e.g., 'ssa_contract_forecast_*.log')
        keep_count (int): Number of most recent log files to keep
        
    Returns:
        int: Number of files deleted
    """
    return cleanup_files(logs_dir, pattern, keep_count)

def cleanup_all_logs(logs_dir=None, keep_count=3):
    """
    Cleanup all log files in the logs directory, keeping only the most recent ones for each type.
    
    Args:
        logs_dir (str, optional): Path to the logs directory. If None, uses the default logs directory.
        keep_count (int): Number of most recent log files to keep for each type
        
    Returns:
        dict: Dictionary with log types as keys and number of deleted files as values
    """
    # If logs_dir is not provided, use the default logs directory
    if logs_dir is None:
        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent.absolute()
        logs_dir = os.path.join(project_root, 'logs')
    
    # Define patterns for different types of log files
    log_patterns = {
        'ssa_contract_forecast': 'ssa_contract_forecast_*.log',
        'jps_startup': 'jps_startup_*.log',
        'app': 'app*.log',
        'flask': 'flask*.log',
        'celery_worker': 'celery_worker*.log',
        'celery_beat': 'celery_beat*.log',
        'flower': 'flower*.log',
        'react': 'react*.log',
        'acquisition_gateway': 'acquisition_gateway*.log',
        'health_check': 'health_check*.log',
        'component': '*_component.log',
        'scraper': '*_scraper.log',
        'system': 'system_*.log'
    }
    
    results = {}
    
    # Cleanup each type of log file
    for log_type, pattern in log_patterns.items():
        deleted_count = cleanup_log_files(logs_dir, pattern, keep_count)
        results[log_type] = deleted_count
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old {log_type} log files")
    
    return results


# When run directly, perform log cleanup
if __name__ == "__main__":
    results = cleanup_all_logs()
    for log_type, count in results.items():
        if count > 0:
            print(f"Deleted {count} old {log_type} log files") 