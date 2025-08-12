"""Migration check utility to ensure database schema is up to date."""

import subprocess
import sys
from app.utils.logger import logger


def check_pending_migrations():
    """Check if there are pending database migrations.
    
    Returns:
        bool: True if migrations are pending, False if up to date
    """
    try:
        # Run flask db current to get current migration
        result = subprocess.run(
            [sys.executable, "-m", "flask", "db", "current"],
            capture_output=True,
            text=True,
            env={"FLASK_APP": "run.py"}
        )
        
        if result.returncode != 0:
            logger.warning(f"Could not check migration status: {result.stderr}")
            return False
            
        current_revision = result.stdout.strip()
        
        # Run flask db heads to get target migration
        result = subprocess.run(
            [sys.executable, "-m", "flask", "db", "heads"],
            capture_output=True,
            text=True,
            env={"FLASK_APP": "run.py"}
        )
        
        if result.returncode != 0:
            logger.warning(f"Could not check migration heads: {result.stderr}")
            return False
            
        head_revision = result.stdout.strip()
        
        # Check if current matches head
        if current_revision != head_revision:
            logger.warning(
                f"Database migration pending! Current: {current_revision}, Target: {head_revision}"
            )
            logger.warning(
                "Run 'flask db upgrade' to apply pending migrations"
            )
            return True
            
        logger.debug("Database schema is up to date")
        return False
        
    except Exception as e:
        logger.error(f"Error checking migrations: {e}")
        return False


def auto_apply_migrations():
    """Automatically apply pending migrations in development mode."""
    try:
        from app.config import active_config
        
        # Only auto-apply in development
        if not active_config.DEBUG:
            logger.info("Auto-migration disabled in production")
            return False
            
        logger.info("Applying pending database migrations...")
        
        result = subprocess.run(
            [sys.executable, "-m", "flask", "db", "upgrade"],
            capture_output=True,
            text=True,
            env={"FLASK_APP": "run.py"}
        )
        
        if result.returncode == 0:
            logger.info("Database migrations applied successfully")
            return True
        else:
            logger.error(f"Failed to apply migrations: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        return False


def ensure_migration_tracking():
    """Ensure migration tracking is properly initialized."""
    try:
        from app.database import db
        
        # Check if alembic_version table exists
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'alembic_version' not in tables:
            logger.warning("Migration tracking not initialized!")
            logger.info("Initializing migration tracking...")
            
            # Stamp the database with the current head
            result = subprocess.run(
                [sys.executable, "-m", "flask", "db", "stamp", "head"],
                capture_output=True,
                text=True,
                env={"FLASK_APP": "run.py"}
            )
            
            if result.returncode == 0:
                logger.info("Migration tracking initialized successfully")
                return True
            else:
                logger.error(f"Failed to initialize migration tracking: {result.stderr}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring migration tracking: {e}")
        return False