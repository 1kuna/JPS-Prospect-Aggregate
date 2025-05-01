import os
import sys
import logging
from pathlib import Path

# --- Start temporary path adjustment ---
# Ensure the app directory is in the Python path for imports
_project_root = Path(__file__).resolve().parents[2] # Assuming init_db.py is in app/database/
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
# --- End temporary path adjustment ---

from app.database.session import engine
from app.database.models import Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_database():
    """Creates database tables based on the defined models."""
    if not engine:
        logger.error("Database engine is not initialized. Cannot create tables.")
        return

    try:
        logger.info(f"Attempting to create tables for engine: {engine.url}")
        # Create all tables defined in models that inherit from Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        # Re-raise the exception to indicate failure
        raise

if __name__ == "__main__":
    logger.info("Running database initialization script...")
    initialize_database()
    logger.info("Database initialization script finished.") 