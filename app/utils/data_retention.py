#!/usr/bin/env python3
"""
Data retention utility for managing raw data files.

This script implements a rolling retention policy that keeps only the most recent
N files per data source, deleting older files to prevent storage bloat.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
from app.utils.logger import logger
from app.utils.file_utils import extract_timestamp_from_filename as extract_timestamp


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
                timestamp = extract_timestamp(file_path.name)
                if timestamp is not None:
                    files_with_timestamps.append((file_path, timestamp))
                else:
                    logger.warning(f"Skipping file with invalid timestamp: {file_path.name}")
                    continue
        
        # Sort by timestamp (newest first)
        files_with_timestamps.sort(key=lambda x: x[1], reverse=True)
        files_by_source[source_name] = files_with_timestamps
        
        logger.info(f"Found {len(files_with_timestamps)} files for source: {source_name}")
    
    return files_by_source


def apply_intelligent_retention_policy(files_by_source: Dict[str, List[Tuple[Path, datetime]]], 
                                     retention_count: int = 5,
                                     dry_run: bool = True) -> Dict[str, int]:
    """
    Apply intelligent retention policy: Keep N most recent files PLUS always preserve
    last 2 successfully processed files.
    
    CRITICAL IMPLEMENTATION DETAILS:
    This function implements a dual-criteria retention policy to balance storage 
    efficiency with data reliability:
    
    1. Time-based retention: Keeps the N most recent files based on timestamp
    2. Success-based retention: Always preserves the last 2 successfully processed files
    
    WHY THIS APPROACH:
    - Recent files are kept because they're most likely to be needed for reprocessing
    - Successfully processed files are kept as a fallback in case recent files are corrupted
    - The combination ensures we always have valid data available even if recent scrapes fail
    
    EXAMPLE SCENARIO:
    If we have files: [today_failed, yesterday_failed, 3days_ago_success, 1week_ago_success]
    With retention_count=2, we would keep:
    - today_failed (recent)
    - yesterday_failed (recent) 
    - 3days_ago_success (last successful)
    - 1week_ago_success (2nd last successful)
    
    This prevents a situation where all retained files are corrupted/failed scrapes.
    
    Args:
        files_by_source: Dictionary mapping source to files with timestamps
        retention_count: Number of most recent files to keep per source
        dry_run: If True, only log what would be deleted without actually deleting
        
    Returns:
        Dictionary with statistics about files processed/deleted per source
    """
    from app.utils.file_processing import get_recent_files_for_source
    
    stats = {}
    total_deleted = 0
    total_kept = 0
    
    for source_name, files_with_timestamps in files_by_source.items():
        # Get source ID for looking up successful files
        from app.utils.database_helpers import get_data_source_id_by_name
        source_id = get_data_source_id_by_name(source_name)
        
        # Get last 2 successfully processed files
        successful_files = []
        if source_id:
            recent_logs = get_recent_files_for_source(source_id, 2)
            successful_file_paths = [log.file_path for log in recent_logs if log.success]
            successful_files = [Path(fp) for fp in successful_file_paths if Path(fp).exists()]
        
        # Files to keep: N most recent + successful files (deduplicated)
        recent_files = [fp for fp, _ in files_with_timestamps[:retention_count]]
        files_to_preserve = set(recent_files + successful_files)
        
        # Split into keep and delete
        files_to_keep = [(fp, ts) for fp, ts in files_with_timestamps if fp in files_to_preserve]
        files_to_delete = [(fp, ts) for fp, ts in files_with_timestamps if fp not in files_to_preserve]
        
        kept_count = len(files_to_keep)
        deleted_count = len(files_to_delete)
        
        stats[source_name] = {
            'kept': kept_count,
            'deleted': deleted_count,
            'kept_recent': len(recent_files),
            'kept_successful': len([f for f in successful_files if f in files_to_preserve]),
            'total_successful_tracked': len(successful_files)
        }
        
        total_kept += kept_count
        total_deleted += deleted_count
        
        # Log retention details
        logger.info(f"Source '{source_name}': Keeping {kept_count} files "
                   f"({stats[source_name]['kept_recent']} recent + "
                   f"{stats[source_name]['kept_successful']} successful), "
                   f"{'would delete' if dry_run else 'deleting'} {deleted_count} files")
        
        if successful_files:
            logger.info(f"  Protected successful files: {[f.name for f in successful_files]}")
        
        if files_to_delete:
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
    
    logger.info(f"\nSummary: {total_kept} files kept, "
               f"{total_deleted} files {'would be deleted' if dry_run else 'deleted'}")
    
    return stats


def apply_retention_policy(files_by_source: Dict[str, List[Tuple[Path, datetime]]], 
                          retention_count: int = 5,
                          dry_run: bool = True) -> Dict[str, int]:
    """
    Legacy retention policy function - now uses intelligent retention.
    
    Args:
        files_by_source: Dictionary mapping source to files with timestamps
        retention_count: Number of most recent files to keep per source
        dry_run: If True, only log what would be deleted without actually deleting
        
    Returns:
        Dictionary with statistics about files processed/deleted per source
    """
    return apply_intelligent_retention_policy(files_by_source, retention_count, dry_run)


def cleanup_raw_data(retention_count: int = 5, raw_data_path: str = None) -> Dict[str, int]:
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
        default=5,
        help='Number of most recent files to keep per source (default: 5)'
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
    
    # Log final statistics
    logger.info("\n" + "="*60)
    logger.info("DATA RETENTION SUMMARY")
    logger.info("="*60)
    for source_name, source_stats in stats.items():
        logger.info(f"{source_name:35} | Kept: {source_stats['kept']:2} | "
                   f"{'Would delete' if dry_run else 'Deleted'}: {source_stats['deleted']:2}")
    logger.info("="*60)


if __name__ == '__main__':
    main()