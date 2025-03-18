"""
Database rebuild script.
This script will:
1. Back up the existing database
2. Create a new database with the updated schema
3. Copy all data from the old database to the new one
"""

import sys
import sqlite3
import argparse
from pathlib import Path

# Add the root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.imports import (
    os, datetime, time, glob, traceback, 
    shutil, re, logging
)
from src.utils.logging import get_component_logger
from src.utils.file_utils import ensure_directories, find_valid_files, cleanup_files

# Set up logging using the centralized utility
logger = get_component_logger('rebuild_db')

# Define paths
ROOT_DIR = Path(__file__).parent.parent.absolute()
DATA_DIR = ROOT_DIR / 'data'
BACKUP_DIR = DATA_DIR / 'backups'
DB_PATH = DATA_DIR / 'proposals.db'

def cleanup_old_backups(backup_dir, max_backups=5):
    """
    Clean up old database backups, keeping only the most recent ones.
    
    Args:
        backup_dir (str): Directory containing the backups
        max_backups (int): Maximum number of backups to keep
    """
    # Use the centralized cleanup_files function from file_utils
    pattern = "proposals_backup_*.db"
    deleted_count = cleanup_files(backup_dir, pattern, max_backups)
    
    logger.info(f"Cleaned up {deleted_count} old database backups, keeping {max_backups} most recent ones")

def list_backups(backup_dir):
    """
    List all database backups in the specified directory.
    
    Args:
        backup_dir (str): Directory containing the backups
    
    Returns:
        list: List of backup files with their creation time and size
    """
    # Find all database backup files using find_valid_files
    backup_files = find_valid_files(backup_dir, 'proposals_backup_*.db')
    
    # Sort files by modification time (newest first)
    backup_files = sorted(backup_files, key=lambda x: os.path.getmtime(x), reverse=True)
    
    # Prepare the list of backups with details
    backups = []
    for backup in backup_files:
        size_bytes = os.path.getsize(backup)
        size_mb = size_bytes / (1024 * 1024)
        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(backup))
        backups.append({
            'file': os.path.basename(backup),
            'size': f"{size_mb:.2f} MB",
            'created': mod_time.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return backups

def rebuild_database(max_backups=5):
    """
    Rebuild the database with the new schema
    
    Args:
        max_backups (int): Maximum number of backups to keep
    """
    # Get the database path - use project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(project_root, 'data')
    db_path = os.path.join(db_dir, 'proposals.db')
    
    # Ensure the directory exists
    ensure_directories(db_dir)
    
    # Check if the database exists
    if not os.path.exists(db_path):
        error_msg = f"Database file not found: {db_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    # Create a backup of the existing database
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(db_dir, f'proposals_backup_{timestamp}.db')
    
    logger.info(f"Creating backup of database at: {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    # Clean up old backups, keeping only the specified number of most recent ones
    cleanup_old_backups(db_dir, max_backups=max_backups)
    
    # Import here to avoid circular imports
    from src.database.db_session_manager import engine, Session
    
    # Close all existing connections to the database
    logger.info("Closing all existing database connections")
    try:
        # Close SQLAlchemy engine and remove session
        Session.remove()
        engine.dispose()
        logger.info("SQLAlchemy connections closed")
    except Exception as e:
        logger.warning(f"Error closing SQLAlchemy connections: {e}")
    
    # Connect to the existing database
    old_conn = None
    new_conn = None
    
    try:
        # Wait a moment for connections to fully close
        time.sleep(2)
        
        old_conn = sqlite3.connect(backup_path)
        old_cursor = old_conn.cursor()
        
        # Try to delete the database file
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
                logger.info(f"Removed existing database file: {db_path}")
        except PermissionError:
            logger.error("Could not delete database file - it's still in use by another process")
            logger.info("Trying alternative approach with a new filename")
            
            # If we can't delete the file, create a new one with a different name
            temp_db_path = os.path.join(db_dir, f'proposals_new_{timestamp}.db')
            new_conn = sqlite3.connect(temp_db_path)
            
            # After rebuilding, we'll try to replace the original file
            db_path_to_use = temp_db_path
        except Exception as e:
            error_msg = f"Error removing database file: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        else:
            # If deletion succeeded, create a new database at the original path
            new_conn = sqlite3.connect(db_path)
            db_path_to_use = db_path
        
        new_cursor = new_conn.cursor()
        
        # Check if the data_sources table exists in the old database
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_sources'")
        if not old_cursor.fetchone():
            error_msg = "data_sources table not found in the database. Database may be corrupted."
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Create the data_sources table in the new database
        new_cursor.execute("""
        CREATE TABLE data_sources (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            url VARCHAR(255) NOT NULL,
            description TEXT,
            last_scraped TIMESTAMP
        )
        """)
        
        # Copy data from the old data_sources table to the new one
        old_cursor.execute("SELECT id, name, url, description, last_scraped FROM data_sources")
        data_sources = old_cursor.fetchall()
        
        for data_source in data_sources:
            new_cursor.execute(
                "INSERT INTO data_sources (id, name, url, description, last_scraped) VALUES (?, ?, ?, ?, ?)",
                data_source
            )
        
        logger.info(f"Copied {len(data_sources)} records from data_sources table")
        
        # Create the proposals table in the new database with the new schema
        new_cursor.execute("""
        CREATE TABLE proposals (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            external_id VARCHAR(100),
            title VARCHAR(255) NOT NULL,
            agency VARCHAR(100),
            office VARCHAR(100),
            description TEXT,
            naics_code VARCHAR(20),
            estimated_value FLOAT,
            release_date TIMESTAMP,
            response_date TIMESTAMP,
            contact_info TEXT,
            url VARCHAR(255),
            status VARCHAR(50),
            last_updated TIMESTAMP,
            imported_at TIMESTAMP,
            is_latest BOOLEAN,
            contract_type VARCHAR(100),
            set_aside VARCHAR(100),
            competition_type VARCHAR(100),
            solicitation_number VARCHAR(100),
            award_date TIMESTAMP,
            place_of_performance TEXT,
            incumbent VARCHAR(255),
            FOREIGN KEY (source_id) REFERENCES data_sources (id)
        )
        """)
        
        # Copy data from the old proposals table to the new one
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proposals'")
        if old_cursor.fetchone():
            # Get column names from the old table
            old_cursor.execute("PRAGMA table_info(proposals)")
            old_columns = [column[1] for column in old_cursor.fetchall()]
            
            # Determine which columns to copy
            columns_to_copy = [
                "id", "source_id", "external_id", "title", "agency", "office",
                "description", "naics_code", "estimated_value", "release_date",
                "response_date", "contact_info", "url", "status", "last_updated"
            ]
            
            # Add imported_at and is_latest if they exist in the old schema
            if "imported_at" in old_columns:
                columns_to_copy.append("imported_at")
            
            if "is_latest" in old_columns:
                columns_to_copy.append("is_latest")
            
            # Build the SELECT query for the old table
            select_columns = ", ".join(col for col in columns_to_copy if col in old_columns)
            
            # Build the INSERT query for the new table
            insert_columns = select_columns
            placeholders = ", ".join(["?"] * len(insert_columns.split(", ")))
            
            # Query the old data
            old_cursor.execute(f"SELECT {select_columns} FROM proposals")
            proposals = old_cursor.fetchall()
            
            # Insert into the new table
            for proposal in proposals:
                # Create a list of values with the correct length
                values = list(proposal)
                
                # Count how many columns we're inserting from the old table
                num_old_columns = len(values)
                
                # Add NULL values for missing columns in the old schema
                if "imported_at" not in old_columns:
                    values.append(None)
                    num_old_columns += 1
                
                if "is_latest" not in old_columns:
                    values.append(1)  # Default to True
                    num_old_columns += 1
                
                # Add NULL values for the new columns
                values.extend([None, None, None, None, None, None, None])  # 7 new columns
                
                # Build a new placeholder string with the correct number of placeholders
                total_placeholders = "?, " * (num_old_columns + 7)  # Old columns + 7 new columns
                total_placeholders = total_placeholders.rstrip(", ")  # Remove trailing comma
                
                # Build the full column list
                full_columns = insert_columns
                if "imported_at" not in old_columns:
                    full_columns += ", imported_at"
                if "is_latest" not in old_columns:
                    full_columns += ", is_latest"
                full_columns += ", contract_type, set_aside, competition_type, solicitation_number, award_date, place_of_performance, incumbent"
                
                # Insert into the new table
                new_cursor.execute(
                    f"INSERT INTO proposals ({full_columns}) VALUES ({total_placeholders})",
                    values
                )
            
            logger.info(f"Copied {len(proposals)} records from proposals table")
        
        # Create the proposal_history table in the new database with the new schema
        new_cursor.execute("""
        CREATE TABLE proposal_history (
            id INTEGER PRIMARY KEY,
            proposal_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            external_id VARCHAR(100),
            title VARCHAR(255) NOT NULL,
            agency VARCHAR(100),
            office VARCHAR(100),
            description TEXT,
            naics_code VARCHAR(20),
            estimated_value FLOAT,
            release_date TIMESTAMP,
            response_date TIMESTAMP,
            contact_info TEXT,
            url VARCHAR(255),
            status VARCHAR(50),
            imported_at TIMESTAMP,
            contract_type VARCHAR(100),
            set_aside VARCHAR(100),
            competition_type VARCHAR(100),
            solicitation_number VARCHAR(100),
            award_date TIMESTAMP,
            place_of_performance TEXT,
            incumbent VARCHAR(255),
            FOREIGN KEY (proposal_id) REFERENCES proposals (id),
            FOREIGN KEY (source_id) REFERENCES data_sources (id)
        )
        """)
        
        # Copy data from the old proposal_history table to the new one if it exists
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proposal_history'")
        if old_cursor.fetchone():
            # Get column names from the old table
            old_cursor.execute("PRAGMA table_info(proposal_history)")
            old_columns = [column[1] for column in old_cursor.fetchall()]
            
            # Determine which columns to copy
            columns_to_copy = [
                "id", "proposal_id", "source_id", "external_id", "title", "agency", "office",
                "description", "naics_code", "estimated_value", "release_date",
                "response_date", "contact_info", "url", "status", "imported_at"
            ]
            
            # Build the SELECT query for the old table
            select_columns = ", ".join(col for col in columns_to_copy if col in old_columns)
            
            # Build the INSERT query for the new table
            insert_columns = select_columns
            placeholders = ", ".join(["?"] * len(insert_columns.split(", ")))
            
            # Query the old data
            old_cursor.execute(f"SELECT {select_columns} FROM proposal_history")
            history_records = old_cursor.fetchall()
            
            # Insert into the new table
            for record in history_records:
                # Create a list of values with the correct length
                values = list(record)
                
                # Count how many columns we're inserting from the old table
                num_old_columns = len(values)
                
                # Add NULL values for missing columns in the old schema
                if "imported_at" not in old_columns:
                    values.append(None)
                    num_old_columns += 1
                
                # Add NULL values for the new columns
                values.extend([None, None, None, None, None, None, None])  # 7 new columns
                
                # Build a new placeholder string with the correct number of placeholders
                total_placeholders = "?, " * (num_old_columns + 7)  # Old columns + 7 new columns
                total_placeholders = total_placeholders.rstrip(", ")  # Remove trailing comma
                
                # Build the full column list
                full_columns = insert_columns
                if "imported_at" not in old_columns:
                    full_columns += ", imported_at"
                full_columns += ", contract_type, set_aside, competition_type, solicitation_number, award_date, place_of_performance, incumbent"
                
                # Insert into the new table
                new_cursor.execute(
                    f"INSERT INTO proposal_history ({full_columns}) VALUES ({total_placeholders})",
                    values
                )
            
            logger.info(f"Copied {len(history_records)} records from proposal_history table")
        
        # Commit the changes
        new_conn.commit()
        
        # If we created a temporary database, try to replace the original
        if db_path_to_use != db_path:
            try:
                # Close connections
                new_conn.close()
                old_conn.close()
                
                # Try again to delete the original file
                if os.path.exists(db_path):
                    os.remove(db_path)
                    logger.info(f"Removed existing database file: {db_path}")
                
                # Rename the temporary file to the original name
                os.rename(db_path_to_use, db_path)
                logger.info(f"Renamed temporary database to: {db_path}")
                
                # Reopen the connection to the new file
                new_conn = sqlite3.connect(db_path)
            except Exception as e:
                logger.error(f"Error replacing original database file: {e}")
                logger.info(f"The new database is available at: {db_path_to_use}")
        
        logger.info("Database rebuild completed successfully!")
        
    except Exception as e:
        logger.error(f"Error rebuilding database: {e}")
        if new_conn:
            new_conn.rollback()
        raise  # Re-raise the exception
    finally:
        # Close connections
        if old_conn:
            old_conn.close()
        if new_conn:
            new_conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database rebuild and backup management utility")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the database")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old database backups")
    parser.add_argument("--list", action="store_true", help="List all database backups")
    parser.add_argument("--max-backups", type=int, default=5, help="Maximum number of backups to keep when cleaning up")
    
    args = parser.parse_args()
    
    # Get the database directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(project_root, 'data')
    
    if args.list:
        print("Available database backups:")
        backups = list_backups(db_dir)
        if not backups:
            print("No backups found.")
        else:
            print(f"{'Filename':<40} {'Size':<10} {'Created':<20}")
            print("-" * 70)
            for backup in backups:
                print(f"{backup['file']:<40} {backup['size']:<10} {backup['created']:<20}")
    elif args.cleanup:
        print(f"Cleaning up old database backups, keeping {args.max_backups} most recent...")
        cleanup_old_backups(db_dir, max_backups=args.max_backups)
        print("Cleanup complete!")
    elif args.rebuild:
        print("Rebuilding database...")
        rebuild_database(max_backups=args.max_backups)
        print("Database rebuild complete!")
    else:
        # Default behavior if no arguments are provided
        print("Rebuilding database...")
        rebuild_database(max_backups=args.max_backups)
        print("Database rebuild complete!") 