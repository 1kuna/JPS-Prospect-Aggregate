#!/usr/bin/env python3
"""
Loguru Migration Helper Script.

This script helps migrate Python files from the old logging system to Loguru.
It scans Python files in the specified directory and performs automatic replacements
of common logging patterns.

Usage:
    python migrate_to_loguru.py [path]
    
If path is not specified, it will use the current working directory.
"""

import os
import sys
import re
import argparse
from pathlib import Path

# Migration patterns
REPLACEMENTS = [
    # Import replacements
    (r'from src\.utils\.logging import get_component_logger', 'from src.utils.logger import logger'),
    (r'from src\.utils\.logging import get_scraper_logger', 'from src.utils.logger import logger'),
    (r'from src\.utils\.logging import configure_root_logger', 'from src.utils.logger import logger'),
    (r'from src\.utils\.logging import cleanup_all_logs', 'from src.utils.logger import cleanup_logs'),
    
    # Logger creation patterns
    (r'logger\s*=\s*get_component_logger\([\'"]([^\'"]+)[\'"]\)', r'logger = logger.bind(name="\1")'),
    (r'logger\s*=\s*get_scraper_logger\([\'"]([^\'"]+)[\'"](,\s*debug_mode=True)?\)', r'logger = logger.bind(name="scraper.\1")'),
    (r'configure_root_logger\([^\)]*\)', '# Removed root logger configuration - this is automatic with Loguru'),
    
    # Cleanup function pattern
    (r'cleanup_all_logs\((.*?)\)', r'cleanup_logs(\1)'),
]

def migrate_file(file_path):
    """
    Migrate a Python file to use Loguru instead of the old logging system.
    
    Args:
        file_path: Path to the Python file to migrate
    
    Returns:
        bool: True if the file was modified, False otherwise
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Make a copy of the original content
    original_content = content
    
    # Apply each replacement pattern
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)
    
    # Check if the content was modified
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def migrate_directory(directory_path):
    """
    Migrate all Python files in a directory and its subdirectories.
    
    Args:
        directory_path: Path to the directory to process
    
    Returns:
        dict: Statistics about the migration process
    """
    stats = {
        'files_processed': 0,
        'files_modified': 0,
    }
    
    # Find all Python files
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                stats['files_processed'] += 1
                
                # Skip the logger.py file itself
                if file == 'logger.py' and os.path.basename(os.path.dirname(file_path)) == 'utils':
                    continue
                
                # Skip the migration script itself
                if file == 'migrate_to_loguru.py' and os.path.basename(os.path.dirname(file_path)) == 'scripts':
                    continue
                
                # Try to migrate the file
                try:
                    if migrate_file(file_path):
                        stats['files_modified'] += 1
                        print(f"Modified: {file_path}")
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
    
    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Python files from old logging system to Loguru.")
    parser.add_argument("path", nargs="?", default=os.getcwd(), help="Directory to process (default: current directory)")
    
    args = parser.parse_args()
    directory_path = os.path.abspath(args.path)
    
    if not os.path.isdir(directory_path):
        print(f"Error: {directory_path} is not a directory.")
        sys.exit(1)
    
    print(f"Processing directory: {directory_path}")
    stats = migrate_directory(directory_path)
    
    print("\nMigration completed:")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files modified: {stats['files_modified']}")
    
    if stats['files_modified'] > 0:
        print("\nPlease review the changes manually to ensure they are correct.")
        print("Some patterns may require manual adjustments, especially if:")
        print("1. Custom parameters were passed to the logger creation")
        print("2. Debug mode was enabled and needs to be preserved")
        print("3. Custom log files were specified")
    
    print("\nRefer to src/utils/LOGURU_MIGRATION.md for more information.") 