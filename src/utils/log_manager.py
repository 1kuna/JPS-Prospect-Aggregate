import os
import re
import glob
import logging
from datetime import datetime
from pathlib import Path

def cleanup_log_files(logs_dir, pattern, keep_count=3):
    """
    Cleanup log files matching the given pattern, keeping only the most recent ones.
    
    Args:
        logs_dir (str): Path to the logs directory
        pattern (str): Glob pattern to match log files (e.g., 'ssa_contract_forecast_*.log')
        keep_count (int): Number of most recent log files to keep
        
    Returns:
        int: Number of files deleted
    """
    # Get all matching log files
    log_files = glob.glob(os.path.join(logs_dir, pattern))
    
    # If we have fewer files than the keep count, no need to delete any
    if len(log_files) <= keep_count:
        return 0
    
    # Sort files by modification time (newest first)
    log_files.sort(key=os.path.getmtime, reverse=True)
    
    # Keep the first 'keep_count' files, delete the rest
    files_to_delete = log_files[keep_count:]
    deleted_count = 0
    
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            logging.info(f"Deleted old log file: {os.path.basename(file_path)}")
            deleted_count += 1
        except Exception as e:
            logging.error(f"Failed to delete log file {file_path}: {str(e)}")
    
    return deleted_count

def cleanup_all_logs(logs_dir=None, keep_count=3):
    """
    Cleanup all log files in the logs directory, keeping only the most recent ones for each type.
    
    Args:
        logs_dir (str, optional): Path to the logs directory. If None, uses the default logs directory.
        keep_count (int): Number of most recent log files to keep for each type
        
    Returns:
        dict: Dictionary with log types as keys and number of deleted files as values
    """
    # If logs_dir is not provided, use the default logs directory
    if logs_dir is None:
        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent.absolute()
        logs_dir = os.path.join(project_root, 'logs')
    
    # Define patterns for different types of log files
    log_patterns = {
        'ssa_contract_forecast': 'ssa_contract_forecast_*.log',
        'jps_startup': 'jps_startup_*.log',
        'app': 'app*.log',
        'flask': 'flask*.log',
        'celery_worker': 'celery_worker*.log',
        'celery_beat': 'celery_beat*.log',
        'flower': 'flower*.log',
        'react': 'react*.log',
        'acquisition_gateway': 'acquisition_gateway*.log',
        'health_check': 'health_check*.log'
    }
    
    results = {}
    
    # Cleanup each type of log file
    for log_type, pattern in log_patterns.items():
        deleted_count = cleanup_log_files(logs_dir, pattern, keep_count)
        results[log_type] = deleted_count
    
    return results

if __name__ == "__main__":
    # This allows running the script directly for testing
    logging.basicConfig(level=logging.INFO)
    results = cleanup_all_logs()
    for log_type, count in results.items():
        if count > 0:
            print(f"Deleted {count} old {log_type} log files") 