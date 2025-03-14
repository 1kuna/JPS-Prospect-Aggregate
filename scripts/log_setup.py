"""
Logging setup utilities for the JPS Prospect Aggregate application.

This module provides functions for setting up and configuring logging
for the application and its components.
"""

import os
import sys
import logging
import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional

# Set up logging
logger = logging.getLogger(__name__)


def setup_logging(logs_dir: str = 'logs', 
                 log_file: str = 'jps_startup.log',
                 log_level: str = 'INFO',
                 max_bytes: int = 5 * 1024 * 1024,
                 backup_count: int = 3) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        logs_dir: Directory to store log files
        log_file: Name of the log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        
    Returns:
        The configured logger
    """
    # Create logs directory if it doesn't exist
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create full path to log file
    log_file_path = os.path.join(logs_dir, log_file)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.getLevelName(log_level))
    
    # Clear existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # Create handlers with rotation
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=max_bytes, 
        backupCount=backup_count
    )
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Create formatters and add them to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to the logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log startup information
    logger.info("==========================================")
    logger.info("JPS Prospect Aggregate Application")
    logger.info("==========================================")
    logger.info(f"Logging to: {log_file_path}")
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
        from src.utils.log_manager import cleanup_all_logs
        
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