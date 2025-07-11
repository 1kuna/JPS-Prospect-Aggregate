#!/usr/bin/env python3
"""
Backfill missing FileProcessingLog records for existing raw data files.

This script scans the raw data directory and creates processing log entries
for files that exist but aren't tracked in the database. This helps ensure
the fallback system can find previously processed files.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from app.database import db
from app.database.models import DataSource, FileProcessingLog
from app.services.file_validation_service import file_validation_service
from app.utils.logger import logger
from app.utils.file_utils import extract_timestamp_from_filename
from app.config import active_config


def create_app():
    """Create Flask app for database operations."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = active_config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_BINDS'] = {
        'users': active_config.USER_DATABASE_URI
    }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app


def get_raw_data_path():
    """Get the raw data directory path."""
    return Path(active_config.RAW_DATA_DIR)


def scan_raw_data_files():
    """Scan raw data directory and return files grouped by source."""
    raw_data_path = get_raw_data_path()
    
    if not raw_data_path.exists():
        logger.error(f"Raw data path does not exist: {raw_data_path}")
        return {}
    
    files_by_source = {}
    
    for source_dir in raw_data_path.iterdir():
        if not source_dir.is_dir():
            continue
            
        source_name = source_dir.name
        files = []
        
        for file_path in source_dir.iterdir():
            if file_path.is_file():
                file_timestamp = extract_timestamp_from_filename(file_path.name)
                if file_timestamp:
                    files.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'size': file_path.stat().st_size,
                        'timestamp': file_timestamp
                    })
        
        # Sort by timestamp (newest first)
        files.sort(key=lambda x: x['timestamp'], reverse=True)
        files_by_source[source_name] = files
        
        logger.info(f"Found {len(files)} files for source: {source_name}")
    
    return files_by_source


def get_existing_file_logs():
    """Get existing file processing logs grouped by source."""
    logs_by_source = {}
    
    try:
        # Get all existing processing logs with their data sources
        logs = db.session.query(FileProcessingLog, DataSource).join(
            DataSource, FileProcessingLog.source_id == DataSource.id
        ).all()
        
        for log, source in logs:
            source_name = source.name
            if source_name not in logs_by_source:
                logs_by_source[source_name] = []
            logs_by_source[source_name].append(log.file_path)
        
        logger.info(f"Found existing logs for {len(logs_by_source)} sources")
        
    except Exception as e:
        logger.error(f"Error getting existing file logs: {e}")
    
    return logs_by_source


def get_directory_to_source_mapping():
    """Map directory names to data source names."""
    return {
        'acqgw': 'Acquisition Gateway',
        'doc': 'Department of Commerce',
        'dhs': 'Department of Homeland Security',
        'doj': 'Department of Justice',
        'dos': 'Department of State',
        'dot': 'Department of Transportation',
        'hhs': 'Health and Human Services',
        'ssa': 'Social Security Administration',
        'treas': 'Department of Treasury'
    }


def backfill_missing_logs(dry_run=True):
    """Backfill missing file processing logs."""
    logger.info("Starting backfill of missing file processing logs")
    
    # Get all data sources
    data_sources = {source.name: source for source in db.session.query(DataSource).all()}
    logger.info(f"Found {len(data_sources)} data sources in database")
    
    # Get directory to source name mapping
    dir_to_source = get_directory_to_source_mapping()
    
    # Scan raw data files
    files_by_source = scan_raw_data_files()
    
    # Get existing logs
    existing_logs = get_existing_file_logs()
    
    total_created = 0
    
    for dir_name, files in files_by_source.items():
        # Map directory name to data source name
        source_name = dir_to_source.get(dir_name)
        if not source_name:
            logger.warning(f"Directory '{dir_name}' not mapped to any data source, skipping")
            continue
            
        if source_name not in data_sources:
            logger.warning(f"Source '{source_name}' not found in database, skipping")
            continue
        
        source = data_sources[source_name]
        existing_file_paths = set(existing_logs.get(source_name, []))
        
        # Find files that need processing logs
        missing_files = []
        for file_info in files:
            if file_info['path'] not in existing_file_paths:
                missing_files.append(file_info)
        
        if not missing_files:
            logger.info(f"No missing logs for {source_name}")
            continue
        
        logger.info(f"Creating {len(missing_files)} missing logs for {source_name}")
        
        for file_info in missing_files:
            if dry_run:
                logger.info(f"[DRY RUN] Would create log for: {file_info['name']}")
                total_created += 1
            else:
                try:
                    # Create processing log
                    log = FileProcessingLog(
                        source_id=source.id,
                        file_path=file_info['path'],
                        file_name=file_info['name'],
                        file_size=file_info['size'],
                        file_timestamp=file_info['timestamp'],
                        success=True,  # Assume success since files exist
                        records_extracted=None,  # Unknown
                        records_inserted=None,  # Unknown
                        processing_completed_at=file_info['timestamp']  # Use file timestamp
                    )
                    
                    db.session.add(log)
                    total_created += 1
                    
                    logger.info(f"Created processing log for: {file_info['name']}")
                    
                except Exception as e:
                    logger.error(f"Error creating log for {file_info['name']}: {e}")
        
        if not dry_run:
            try:
                db.session.commit()
                logger.info(f"Committed {len(missing_files)} logs for {source_name}")
            except Exception as e:
                logger.error(f"Error committing logs for {source_name}: {e}")
                db.session.rollback()
    
    if dry_run:
        logger.info(f"[DRY RUN] Would create {total_created} processing logs")
    else:
        logger.info(f"Successfully created {total_created} processing logs")
    
    return total_created


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill missing file processing logs")
    parser.add_argument('--execute', action='store_true', 
                       help='Execute the backfill (default is dry-run)')
    
    args = parser.parse_args()
    
    try:
        # Initialize database connection
        app = create_app()
        with app.app_context():
            total_created = backfill_missing_logs(dry_run=not args.execute)
            
            if args.execute:
                logger.info(f"Backfill complete: {total_created} logs created")
            else:
                logger.info(f"Dry run complete: {total_created} logs would be created")
                logger.info("Use --execute to actually create the logs")
                
    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())