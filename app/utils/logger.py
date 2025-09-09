"""Centralized logging configuration for the application using Loguru."""

import inspect
import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

# Define log directory - should match current config
project_root = Path(__file__).parent.parent.parent.absolute()
LOGS_DIR = os.path.join(project_root, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Get log level from environment
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


# Configure Loguru
def configure_logging():
    """Configure Loguru loggers for the application."""
    # Remove default handler
    logger.remove()

    # Add console handler
    logger.add(
        sys.stdout,
        level=DEFAULT_LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # Add application log file (rotation at 10MB, retention for 10 days)
    logger.add(
        os.path.join(LOGS_DIR, "app.log"),
        rotation="10 MB",
        retention="10 days",
        level=DEFAULT_LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # Add scraper-specific log file
    logger.add(
        os.path.join(LOGS_DIR, "scrapers.log"),
        rotation="10 MB",
        retention="10 days",
        level=DEFAULT_LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        filter=lambda record: "scraper" in record["name"],
    )

    # Add error-only log file
    logger.add(
        os.path.join(LOGS_DIR, "errors.log"),
        rotation="10 MB",
        retention="10 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )


# Clean up old log files
def cleanup_logs(logs_dir=None, keep_count=3):
    """Clean up old log files, keeping only the most recent ones.

    Args:
        logs_dir: Directory containing log files (default is LOGS_DIR)
        keep_count: Number of most recent log files to keep for each type

    Returns:
        Dictionary with log types as keys and number of deleted files as values
    """
    from app.utils.file_utils import clean_old_files

    if logs_dir is None:
        logs_dir = LOGS_DIR

    results = {}

    # Clean up each log type
    patterns = {
        "app": "app*.log*",
        "scraper": "scrapers*.log*",
        "error": "errors*.log*",
    }

    for log_type, pattern in patterns.items():
        deleted = clean_old_files(logs_dir, pattern, keep_count)
        results[log_type] = deleted

    return results


def get_logger(name: str | None = None) -> Any:
    """Get a bound logger with the specified or auto-detected name.
    
    Args:
        name: Logger name. If None, uses the calling module's __name__
        
    Returns:
        Bound logger instance
    """
    if name is None:
        # Auto-detect from calling module
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get('__name__', 'unknown')
    return logger.bind(name=name)


# Configure logging
configure_logging()

# Export the logger
__all__ = ["logger", "get_logger", "cleanup_logs"]
