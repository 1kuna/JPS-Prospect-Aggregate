"""
Simplified file utilities using Python's standard library.
"""

from pathlib import Path
from typing import Union, Optional, Any # Optional and Any for the logger type

# Logger is not imported at module level to prevent circular dependencies.
# Functions that need logging should accept a logger instance as an argument.

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

def clean_files_by_pattern(
    directory: Union[str, Path], 
    pattern: str, 
    keep_count: int = 0, 
    logger: Optional[Any] = None  # Accept an optional logger (can be Loguru, stdlib, etc.)
) -> int:
    """
    Delete old files in a directory matching a pattern, keeping the most recent ones.
    
    Args:
        directory: Directory containing files.
        pattern: Glob pattern to match (e.g., "*.log").
        keep_count: Number of most recent files to keep.
        logger: Optional logger instance for logging messages.
        
    Returns:
        Number of files deleted.
    """
    path = Path(directory)
    if not path.exists():
        if logger:
            logger.warning(f"Directory not found for cleaning: {directory}")
        else:
            print(f"Warning: Directory not found for cleaning: {directory}")
        return 0
    
    files = [(file, file.stat().st_mtime) for file in path.glob(pattern) if file.is_file()]
    files.sort(key=lambda x: x[1], reverse=True)
    
    files_to_delete = files[keep_count:] if keep_count > 0 else files
    
    deleted_count = 0
    for file_path, _ in files_to_delete:
        try:
            file_path.unlink()
            if logger:
                logger.info(f"Deleted old file: {file_path}")
            deleted_count += 1
        except Exception as e:
            if logger:
                logger.error(f"Failed to delete file {file_path}: {e}")
            else:
                print(f"Error: Failed to delete file {file_path}: {e}")
    
    return deleted_count

# Backward compatibility functions comments can remain or be removed if no longer relevant.
# - ensure_directories
# - cleanup_files
# - find_valid_files 