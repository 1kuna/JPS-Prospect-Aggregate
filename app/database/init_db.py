import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from app.database import db
from app.utils.logger import logger # Use application's logger

def initialize_database():
    """
    Creates database tables based on the defined models within an application context.
    """
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"Attempting to create tables for engine: {db.engine.url}")
            # Create all tables defined in models that inherit from db.Model
            db.create_all() 
            logger.info("Database tables checked/created successfully.")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}", exc_info=True)
            # Re-raise the exception to indicate failure
            raise

if __name__ == "__main__":
    logger.info("Running database initialization script...")
    try:
        initialize_database()
        logger.info("Database initialization script finished successfully.")
    except Exception:
        logger.error("Database initialization script failed.")
        sys.exit(1)