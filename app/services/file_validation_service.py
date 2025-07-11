"""
File validation service for tracking processing success and implementing soft validation.

This service provides:
- Soft file validation with console warnings only
- Schema change detection and warnings  
- Processing success tracking for intelligent retention
- File content analysis without blocking scrapers
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


class FileValidationService:
    """Service for file validation and processing tracking."""
    
    def __init__(self):
        self.logger = logger.bind(name="services.file_validation")
    
    def create_processing_log(self, source_id: int, file_path: str) -> FileProcessingLog:
        """Create a new file processing log entry."""
        file_path_obj = Path(file_path)
        file_name = file_path_obj.name
        file_size = file_path_obj.stat().st_size if file_path_obj.exists() else None
        file_timestamp = extract_timestamp_from_filename(file_name)
        
        if not file_timestamp:
            self.logger.warning(f"Could not extract timestamp from filename: {file_name}")
            file_timestamp = datetime.now()
        
        log = FileProcessingLog(
            source_id=source_id,
            file_path=str(file_path),
            file_name=file_name,
            file_size=file_size,
            file_timestamp=file_timestamp
        )
        
        db.session.add(log)
        db.session.commit()
        
        self.logger.info(f"Created processing log for file: {file_name} (ID: {log.id})")
        return log
    
    def update_processing_success(self, log_id: int, success: bool, 
                                records_extracted: int = None, 
                                records_inserted: int = None,
                                schema_columns: List[str] = None,
                                schema_issues: Dict[str, Any] = None,
                                validation_warnings: List[str] = None,
                                error_message: str = None,
                                processing_duration: float = None):
        """Update processing log with results."""
        log = db.session.get(FileProcessingLog, log_id)
        if not log:
            self.logger.error(f"Processing log not found: {log_id}")
            return
        
        log.success = success
        log.records_extracted = records_extracted
        log.records_inserted = records_inserted
        log.schema_columns = schema_columns
        log.schema_issues = schema_issues
        log.validation_warnings = validation_warnings
        log.error_message = error_message
        log.processing_duration = processing_duration
        log.processing_completed_at = datetime.now()
        
        db.session.commit()
        
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"Updated processing log {log_id}: {status} - {records_inserted or 0} records inserted")
        
        # Log warnings if any
        if validation_warnings:
            for warning in validation_warnings:
                self.logger.warning(f"File validation warning: {warning}")
        
        # Log schema issues if any
        if schema_issues:
            if schema_issues.get('missing_columns'):
                self.logger.warning(f"Schema issue - Missing columns: {schema_issues['missing_columns']}")
            if schema_issues.get('extra_columns'):
                self.logger.warning(f"Schema issue - Extra columns: {schema_issues['extra_columns']}")
    
    def validate_file_content(self, file_path: str) -> Tuple[List[str], bool]:
        """
        Perform soft validation on file content.
        Returns (warnings, is_likely_valid)
        """
        warnings = []
        is_likely_valid = True
        
        if not os.path.exists(file_path):
            warnings.append(f"File does not exist: {file_path}")
            return warnings, False
        
        file_size = os.path.getsize(file_path)
        
        # Check file size (suspiciously small files might be error pages)
        if file_size < 100:  # Less than 100 bytes is suspicious
            warnings.append(f"File is suspiciously small ({file_size} bytes) - may be an error page")
            is_likely_valid = False
        elif file_size < 1000:  # Less than 1KB is concerning but not blocking
            warnings.append(f"File is quite small ({file_size} bytes) - verify it contains expected data")
        
        # Check for HTML error indicators (soft check)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first 2KB to check for HTML error patterns
                sample = f.read(2048).lower()
                
                html_error_patterns = [
                    '<html',
                    '<title>error',
                    '<title>404',
                    '<title>500',
                    'internal server error',
                    'page not found',
                    'access denied',
                    'authentication failed',
                    'session expired'
                ]
                
                for pattern in html_error_patterns:
                    if pattern in sample:
                        warnings.append(f"File may contain HTML error page (found: '{pattern}')")
                        is_likely_valid = False
                        break
                
                # Check if file looks like HTML when expecting data file
                if '<html' in sample and not file_path.lower().endswith('.html'):
                    warnings.append("File appears to be HTML but has non-HTML extension")
                    
        except Exception as e:
            warnings.append(f"Could not read file for content validation: {e}")
        
        return warnings, is_likely_valid
    
    def detect_schema_changes(self, file_path: str, expected_columns: List[str] = None) -> Dict[str, Any]:
        """
        Detect schema changes by comparing file columns to expected schema.
        Returns dict with missing_columns, extra_columns, and suggestions.
        """
        schema_issues = {
            'missing_columns': [],
            'extra_columns': [],
            'suggestions': []
        }
        
        if not expected_columns:
            # If no expected columns provided, we can't detect changes
            return schema_issues
        
        try:
            # Try to read file and get column names
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.csv':
                df = pd.read_csv(file_path, nrows=0)  # Just read headers
            elif file_extension in ['.xlsx', '.xls', '.xlsm']:
                df = pd.read_excel(file_path, nrows=0)  # Just read headers
            else:
                schema_issues['suggestions'].append(f"Cannot detect schema for file type: {file_extension}")
                return schema_issues
            
            actual_columns = list(df.columns)
            expected_set = set(expected_columns)
            actual_set = set(actual_columns)
            
            # Find missing and extra columns
            missing = list(expected_set - actual_set)
            extra = list(actual_set - expected_set)
            
            schema_issues['missing_columns'] = missing
            schema_issues['extra_columns'] = extra
            
            # Generate helpful suggestions
            if missing:
                schema_issues['suggestions'].append(f"Schema may have changed - missing expected columns: {missing}")
                schema_issues['suggestions'].append("Consider updating scraper column mappings")
            
            if extra:
                schema_issues['suggestions'].append(f"New columns found: {extra}")
                schema_issues['suggestions'].append("Consider adding new columns to data model if valuable")
            
            if missing or extra:
                schema_issues['suggestions'].append("Review source website to confirm schema changes")
            
        except Exception as e:
            schema_issues['suggestions'].append(f"Could not analyze file schema: {e}")
        
        return schema_issues
    
    def get_last_successful_files(self, source_id: int, count: int = 2) -> List[str]:
        """Get the last N successfully processed files for a data source."""
        try:
            logs = db.session.query(FileProcessingLog).filter(
                FileProcessingLog.source_id == source_id,
                FileProcessingLog.success == True
            ).order_by(
                FileProcessingLog.file_timestamp.desc()
            ).limit(count).all()
            
            return [log.file_path for log in logs]
            
        except Exception as e:
            self.logger.error(f"Error getting last successful files: {e}")
            return []
    
    def log_validation_summary(self, file_path: str, warnings: List[str], 
                             schema_issues: Dict[str, Any], is_likely_valid: bool):
        """Log a comprehensive validation summary."""
        file_name = Path(file_path).name
        
        if warnings or schema_issues.get('missing_columns') or schema_issues.get('extra_columns'):
            self.logger.warning(f"File validation summary for {file_name}:")
            
            if warnings:
                self.logger.warning(f"  Content warnings: {len(warnings)}")
                for warning in warnings:
                    self.logger.warning(f"    - {warning}")
            
            if schema_issues.get('missing_columns'):
                self.logger.warning(f"  Missing columns: {schema_issues['missing_columns']}")
            
            if schema_issues.get('extra_columns'):
                self.logger.warning(f"  Extra columns: {schema_issues['extra_columns']}")
            
            if schema_issues.get('suggestions'):
                self.logger.warning(f"  Suggestions:")
                for suggestion in schema_issues['suggestions']:
                    self.logger.warning(f"    - {suggestion}")
            
            if not is_likely_valid:
                self.logger.warning(f"  ⚠️  File may not contain valid data - review recommended")
        else:
            self.logger.info(f"File validation passed for {file_name} - no issues detected")


# Global instance
file_validation_service = FileValidationService()