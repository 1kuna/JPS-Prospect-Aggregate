"""
Utility functions for file operations.

This module provides concise utility functions for common file operations
like directory creation, file cleanup, and file verification.
"""

import os
import glob
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

# Create a simple logger directly to avoid circular imports with logging.py
logger = logging.getLogger('utils.file')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def ensure_directories(*directories: str) -> None:
    """
    Ensure that the specified directories exist, creating them if necessary.
    
    Args:
        *directories: Variable number of directory paths to ensure exist
    """
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def cleanup_files(directory: str, pattern: str = "*", keep_count: int = 0) -> int:
    """
    Clean up files in a directory that match a pattern, optionally keeping the most recent ones.
    
    Args:
        directory: Directory containing files to clean up
        pattern: Glob pattern to match files (default: "*")
        keep_count: Number of most recent files to keep (default: 0, meaning delete all)
        
    Returns:
        Number of files removed
    """
    # Get matching files with their modification times
    files = []
    for file_path in glob.glob(os.path.join(directory, pattern)):
        if os.path.isfile(file_path):
            files.append((file_path, os.path.getmtime(file_path)))
    
    # Sort files by modification time (newest first)
    files.sort(key=lambda x: x[1], reverse=True)
    
    # Keep the specified number of files
    files_to_remove = files[keep_count:] if keep_count > 0 else files
    
    # Remove each file
    count = 0
    for file_path, _ in files_to_remove:
        try:
            os.remove(file_path)
            logger.info(f"Removed file: {file_path}")
            count += 1
        except Exception as e:
            logger.error(f"Failed to remove file {file_path}: {str(e)}")
    
    return count

def find_valid_files(directory: str, pattern: str, min_size: int = 0) -> List[Path]:
    """
    Find files matching a pattern in a directory with a minimum size.
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern to match files
        min_size: Minimum file size in bytes (default: 0)
        
    Returns:
        List of Path objects for valid files
    """
    # Ensure the directory exists
    if not os.path.exists(directory):
        logger.info(f"Directory does not exist: {directory}")
        return []
    
    # Find files matching the pattern
    matching_files = list(Path(directory).glob(pattern))
    
    # Filter files by size
    valid_files = [
        file_path for file_path in matching_files 
        if os.path.isfile(file_path) and os.path.getsize(file_path) > min_size
    ]
    
    return valid_files 