"""
File Processing Utilities

Replaces FileValidationService with simple utility functions.
Provides file validation, processing tracking, and content analysis.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
import pandas as pd

from app.database import db
from app.database.models import FileProcessingLog, DataSource
from app.utils.logger import logger
from app.utils.file_utils import extract_timestamp_from_filename
from app.constants.agency_mapping import get_data_directory_mapping


def create_processing_log(source_id: int, file_path: str) -> FileProcessingLog:
    """Create a new file processing log entry."""
    file_path_obj = Path(file_path)
    file_name = file_path_obj.name
    file_size = file_path_obj.stat().st_size if file_path_obj.exists() else None
    file_timestamp = extract_timestamp_from_filename(file_name)

    if not file_timestamp:
        logger.warning(f"Could not extract timestamp from filename: {file_name}")
        file_timestamp = datetime.now()

    log = FileProcessingLog(
        source_id=source_id,
        file_path=str(file_path),
        file_name=file_name,
        file_size=file_size,
        file_timestamp=file_timestamp,
    )

    db.session.add(log)
    return log


def update_processing_log(
    log: FileProcessingLog,
    success: bool,
    records_processed: int = 0,
    error_message: str = None,
):
    """Update processing log with results."""
    log.processed_at = datetime.now()
    log.success = success
    log.records_processed = records_processed
    log.error_message = error_message

    db.session.commit()


def validate_file_content(
    file_path: str, expected_columns: List[str] = None
) -> Dict[str, Any]:
    """
    Perform soft validation on file content.
    Returns validation results without blocking processing.
    """
    try:
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return {"valid": False, "error": "File does not exist"}

        if file_path_obj.stat().st_size == 0:
            return {"valid": False, "error": "File is empty"}

        # Try to read file and check basic structure
        try:
            if file_path.endswith((".xls", ".xlsx", ".xlsm")):
                df = pd.read_excel(file_path, nrows=5)  # Just check first few rows
            else:
                df = pd.read_csv(file_path, nrows=5)

            if df.empty:
                return {"valid": False, "error": "File contains no data"}

            # Check for expected columns if provided
            missing_columns = []
            if expected_columns:
                missing_columns = [
                    col for col in expected_columns if col not in df.columns
                ]

            return {
                "valid": True,
                "columns": list(df.columns),
                "row_count_sample": len(df),
                "missing_expected_columns": missing_columns,
                "has_schema_changes": len(missing_columns) > 0,
            }

        except Exception as e:
            return {"valid": False, "error": f"Could not read file: {str(e)}"}

    except Exception as e:
        logger.error(f"Error validating file {file_path}: {e}")
        return {"valid": False, "error": f"Validation error: {str(e)}"}


def get_recent_files_for_source(
    source_id: int, limit: int = 10
) -> List[FileProcessingLog]:
    """Get recent processing logs for a data source."""
    return (
        FileProcessingLog.query.filter_by(source_id=source_id)
        .order_by(FileProcessingLog.file_timestamp.desc())
        .limit(limit)
        .all()
    )


def cleanup_old_processing_logs(days_old: int = 90):
    """Clean up old processing logs to prevent database bloat."""
    cutoff_date = datetime.now() - pd.Timedelta(days=days_old)

    deleted_count = (
        db.session.query(FileProcessingLog)
        .filter(FileProcessingLog.processed_at < cutoff_date)
        .delete()
    )

    db.session.commit()
    logger.info(f"Cleaned up {deleted_count} old processing logs")

    return deleted_count


def analyze_file_processing_trends(source_id: int, days: int = 30) -> Dict[str, Any]:
    """Analyze processing trends for a data source."""
    cutoff_date = datetime.now() - pd.Timedelta(days=days)

    logs = FileProcessingLog.query.filter(
        FileProcessingLog.source_id == source_id,
        FileProcessingLog.processed_at >= cutoff_date,
    ).all()

    if not logs:
        return {"message": "No recent processing logs found"}

    success_count = sum(1 for log in logs if log.success)
    total_count = len(logs)
    avg_records = (
        sum(log.records_processed or 0 for log in logs if log.success) / success_count
        if success_count > 0
        else 0
    )

    return {
        "total_files": total_count,
        "successful_files": success_count,
        "success_rate": (success_count / total_count) * 100 if total_count > 0 else 0,
        "average_records_per_file": avg_records,
        "date_range": f"{cutoff_date.date()} to {datetime.now().date()}",
    }
