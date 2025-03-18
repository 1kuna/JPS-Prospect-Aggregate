"""
Logging setup utilities for the JPS Prospect Aggregate application.

This module provides functions for setting up and configuring logging
for the application and its components.
"""

import os
import sys
import logging
import datetime
from typing import Dict, Optional

# Import our centralized logging utilities
from src.utils.logging import configure_root_logger, get_component_logger
from src.utils.file_utils import ensure_directories

# Set up logging for this module
logger = get_component_logger('log_setup')


def setup_logging(logs_dir: str = 'logs', 
                 log_file: str = 'jps_startup.log',
                 log_level: str = 'INFO',
                 max_bytes: int = 5 * 1024 * 1024,
                 backup_count: int = 3) -> logging.Logger:
    """
    Set up logging for the application.
    
    This function now leverages the centralized logging configuration utility.
    
    Args:
        logs_dir: Directory to store log files (now mainly for compatibility)
        log_file: Name of the log file (now mainly for compatibility)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of log file before rotation (now handled by logging)
        backup_count: Number of backup log files to keep (now handled by logging)
        
    Returns:
        The configured root logger
    """
    # Ensure the logs directory exists
    ensure_directories(logs_dir)
    
    # Configure the root logger using our centralized utility
    root_logger = configure_root_logger(log_level)
    
    # Log startup information
    logger.info("==========================================")
    logger.info("JPS Prospect Aggregate Application")
    logger.info("==========================================")
    logger.info(f"Started at: {datetime.datetime.now()}")
    logger.info(f"Platform: {'Windows' if sys.platform == 'win32' else 'Unix-like'}")
    logger.info("==========================================")
    
    return root_logger


def cleanup_logs(logs_dir: str, keep_count: int = 3) -> Dict[str, int]:
    """
    Clean up old log files.
    
    Args:
        logs_dir: Directory containing log files
        keep_count: Number of most recent log files to keep for each type
        
    Returns:
        Dictionary with log types as keys and number of deleted files as values
    """
    try:
        # Import the log manager if available
        from src.utils.logging import cleanup_all_logs
        
        # Clean up logs using the log manager
        cleanup_results = cleanup_all_logs(logs_dir, keep_count=keep_count)
        
        # Log cleanup results
        for log_type, count in cleanup_results.items():
            if count > 0:
                logger.info(f"Cleaned up {count} old {log_type} log files")
        
        return cleanup_results
    except ImportError:
        logger.warning("Log manager not available, skipping log cleanup")
        return {}
    except Exception as e:
        logger.error(f"Error cleaning up logs: {str(e)}")
        return {} 