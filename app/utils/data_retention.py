#!/usr/bin/env python3
"""
Data retention utility for managing raw data files.

This script implements a rolling retention policy that keeps only the most recent
N files per data source, deleting older files to prevent storage bloat.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_timestamp_from_filename(filename: str) -> datetime:
    """
    Extract timestamp from filename with format: prefix_YYYYMMDD_HHMMSS.ext
    
    Args:
        filename: The filename to parse
        
    Returns:
        datetime object representing the file's timestamp
        
    Raises:
        ValueError: If timestamp cannot be extracted
    """
    # Pattern matches YYYYMMDD_HHMMSS in filename
    pattern = r'(\d{8}_\d{6})'
    match = re.search(pattern, filename)
    
    if not match:
        raise ValueError(f"No timestamp found in filename: {filename}")
    
    timestamp_str = match.group(1)
    return datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')


def get_files_by_source(raw_data_path: Path) -> Dict[str, List[Tuple[Path, datetime]]]:
    """
    Scan raw data directory and group files by data source.
    
    Args:
        raw_data_path: Path to the raw data directory
        
    Returns:
        Dictionary mapping source name to list of (file_path, timestamp) tuples
    """
    files_by_source = {}
    
    if not raw_data_path.exists():
        logger.error(f"Raw data path does not exist: {raw_data_path}")
        return files_by_source
    
    for source_dir in raw_data_path.iterdir():
        if not source_dir.is_dir():
            continue
            
        source_name = source_dir.name
        files_with_timestamps = []
        
        for file_path in source_dir.iterdir():
            if file_path.is_file():
                try:
                    timestamp = extract_timestamp_from_filename(file_path.name)
                    files_with_timestamps.append((file_path, timestamp))
                except ValueError as e:
                    logger.warning(f"Skipping file with invalid timestamp: {e}")
                    continue
        
        # Sort by timestamp (newest first)
        files_with_timestamps.sort(key=lambda x: x[1], reverse=True)
        files_by_source[source_name] = files_with_timestamps
        
        logger.info(f"Found {len(files_with_timestamps)} files for source: {source_name}")
    
    return files_by_source


def apply_retention_policy(files_by_source: Dict[str, List[Tuple[Path, datetime]]], 
                          retention_count: int = 3,
                          dry_run: bool = True) -> Dict[str, int]:
    """
    Apply retention policy to files, keeping only the most recent N files per source.
    
    Args:
        files_by_source: Dictionary mapping source to files with timestamps
        retention_count: Number of most recent files to keep per source
        dry_run: If True, only log what would be deleted without actually deleting
        
    Returns:
        Dictionary with statistics about files processed/deleted per source
    """
    stats = {}
    total_deleted = 0
    total_kept = 0
    
    for source_name, files_with_timestamps in files_by_source.items():
        files_to_keep = files_with_timestamps[:retention_count]
        files_to_delete = files_with_timestamps[retention_count:]
        
        kept_count = len(files_to_keep)
        deleted_count = len(files_to_delete)
        
        stats[source_name] = {
            'kept': kept_count,
            'deleted': deleted_count
        }
        
        total_kept += kept_count
        total_deleted += deleted_count
        
        if files_to_delete:
            logger.info(f"Source '{source_name}': Keeping {kept_count} files, "
                       f"{'would delete' if dry_run else 'deleting'} {deleted_count} files")
            
            for file_path, timestamp in files_to_delete:
                if dry_run:
                    logger.info(f"  [DRY RUN] Would delete: {file_path.name} "
                               f"(timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
                else:
                    try:
                        file_path.unlink()
                        logger.info(f"  Deleted: {file_path.name}")
                    except OSError as e:
                        logger.error(f"  Failed to delete {file_path.name}: {e}")
        else:
            logger.info(f"Source '{source_name}': {kept_count} files, no deletion needed")
    
    logger.info(f"\nSummary: {total_kept} files kept, "
               f"{total_deleted} files {'would be deleted' if dry_run else 'deleted'}")
    
    return stats


def cleanup_raw_data(retention_count: int = 3, raw_data_path: str = None) -> Dict[str, int]:
    """
    Programmatic interface for data retention cleanup.
    
    Args:
        retention_count: Number of files to keep per source
        raw_data_path: Path to raw data directory (optional)
        
    Returns:
        Dictionary with cleanup statistics
    """
    # Determine raw data path
    if raw_data_path:
        path = Path(raw_data_path)
    else:
        # Default to data/raw relative to the project root
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent  # Go up two levels from app/utils/
        path = project_root / 'data' / 'raw'
    
    logger.info(f"Data retention cleanup starting (retention_count={retention_count})")
    logger.info(f"Raw data path: {path}")
    
    # Get files grouped by source
    files_by_source = get_files_by_source(path)
    
    if not files_by_source:
        logger.warning("No data sources found or no files to process")
        return {}
    
    # Apply retention policy (execute mode)
    stats = apply_retention_policy(
        files_by_source, 
        retention_count=retention_count,
        dry_run=False
    )
    
    logger.info("Data retention cleanup completed")
    return stats


def main():
    """Main entry point for the data retention utility."""
    parser = argparse.ArgumentParser(
        description="Apply data retention policy to raw data files"
    )
    parser.add_argument(
        '--retention-count', 
        type=int, 
        default=3,
        help='Number of most recent files to keep per source (default: 3)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Show what would be deleted without actually deleting (default: True)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually delete files (overrides --dry-run)'
    )
    parser.add_argument(
        '--raw-data-path',
        type=str,
        help='Path to raw data directory (default: data/raw relative to script)'
    )
    
    args = parser.parse_args()
    
    # Determine dry run mode
    dry_run = not args.execute
    
    # Determine raw data path
    if args.raw_data_path:
        raw_data_path = Path(args.raw_data_path)
    else:
        # Default to data/raw relative to the project root
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent  # Go up two levels from app/utils/
        raw_data_path = project_root / 'data' / 'raw'
    
    logger.info(f"Data retention utility starting...")
    logger.info(f"Raw data path: {raw_data_path}")
    logger.info(f"Retention count: {args.retention_count}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    
    if dry_run:
        logger.warning("Running in DRY RUN mode - no files will be deleted")
        logger.warning("Use --execute flag to actually delete files")
    
    # Get files grouped by source
    files_by_source = get_files_by_source(raw_data_path)
    
    if not files_by_source:
        logger.warning("No data sources found or no files to process")
        return
    
    # Apply retention policy
    stats = apply_retention_policy(
        files_by_source, 
        retention_count=args.retention_count,
        dry_run=dry_run
    )
    
    # Print final statistics
    print("\n" + "="*60)
    print("DATA RETENTION SUMMARY")
    print("="*60)
    for source_name, source_stats in stats.items():
        print(f"{source_name:35} | Kept: {source_stats['kept']:2} | "
              f"{'Would delete' if dry_run else 'Deleted'}: {source_stats['deleted']:2}")
    print("="*60)


if __name__ == '__main__':
    main()