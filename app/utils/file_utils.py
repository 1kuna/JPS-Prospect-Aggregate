"""
Simplified file utilities using Python's standard library.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union
from app.utils.logger import logger

def ensure_directory(directory: Union[str, Path]) -> Path:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path as string or Path
        
    Returns:
        Path object for the directory
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path

def find_files(directory: Union[str, Path], pattern: str, min_size: int = 0) -> List[Path]:
    """
    Find files in a directory matching a pattern with minimum size.
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern to match (e.g., "*.csv")
        min_size: Minimum file size in bytes
        
    Returns:
        List of matching Path objects
    """
    path = Path(directory)
    if not path.exists():
        logger.warning(f"Directory not found: {directory}")
        return []
    
    return [
        file for file in path.glob(pattern)
        if file.is_file() and file.stat().st_size >= min_size
    ]

def clean_old_files(directory: Union[str, Path], pattern: str, keep_count: int = 0) -> int:
    """
    Delete old files in a directory, keeping the most recent ones.
    
    Args:
        directory: Directory containing files
        pattern: Glob pattern to match (e.g., "*.log")
        keep_count: Number of most recent files to keep
        
    Returns:
        Number of files deleted
    """
    path = Path(directory)
    if not path.exists():
        logger.warning(f"Directory not found: {directory}")
        return 0
    
    # Get files matching pattern with modification time
    files = [(file, file.stat().st_mtime) for file in path.glob(pattern) if file.is_file()]
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x[1], reverse=True)
    
    # Keep the most recent ones
    files_to_delete = files[keep_count:] if keep_count > 0 else files
    
    # Delete files
    deleted_count = 0
    for file_path, _ in files_to_delete:
        try:
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
    
    return deleted_count

def safe_file_copy(source: Union[str, Path], destination: Union[str, Path]) -> Optional[Path]:
    """
    Safely copy a file, ensuring the destination directory exists.
    
    Args:
        source: Source file path
        destination: Destination file path
        
    Returns:
        Path object for the destination file, or None if copy failed
    """
    src_path = Path(source)
    dst_path = Path(destination)
    
    if not src_path.exists():
        logger.error(f"Source file not found: {source}")
        return None
    
    # Ensure the destination directory exists
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        return Path(shutil.copy2(src_path, dst_path))
    except Exception as e:
        logger.error(f"Failed to copy {source} to {destination}: {e}")
        return None

# Backward compatibility functions removed as they were simple wrappers with no usage
# - ensure_directories
# - cleanup_files
# - find_valid_files 