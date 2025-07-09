#!/usr/bin/env python3
"""
Add role column to existing users table if it doesn't exist.
This handles the case where the users table was created before the role column was added to the model.
"""

import os
import sys
from pathlib import Path
import sqlite3

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.utils.logger import logger

def add_role_column():
    """Add role column to users table if it doesn't exist."""
    db_path = Path("data/jps_users.db")
    
    if not db_path.exists():
        logger.error(f"User database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if role column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'role' in column_names:
            logger.info("Role column already exists in users table")
            return True
        
        # Add role column with default value 'user'
        logger.info("Adding role column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
        
        # Create index on role column
        cursor.execute("CREATE INDEX ix_users_role ON users(role)")
        
        conn.commit()
        logger.success("Role column added successfully!")
        
        # Update existing users to have 'user' role
        cursor.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
        conn.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding role column: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = add_role_column()
    if success:
        logger.success("✅ Role column added successfully!")
    else:
        logger.error("❌ Failed to add role column")
        sys.exit(1)