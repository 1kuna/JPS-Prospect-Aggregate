import logging

from app.database.session import engine
from app.database import db # Changed import from Base to db

# Configure logging (now handled by app.utils.logger)
logger = logging.getLogger(__name__) # Get standard logger instance

def initialize_database():
    """Creates database tables based on the defined models."""
    if not engine:
        logger.error("Database engine is not initialized. Cannot create tables.")
        return

    try:
        logger.info(f"Attempting to create tables for engine: {engine.url}")
        # Create all tables defined in models that inherit from db.Model
        db.metadata.create_all(bind=engine) # Changed Base.metadata to db.metadata
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        # Re-raise the exception to indicate failure
        raise

if __name__ == "__main__":
    logger.info("Running database initialization script...")
    initialize_database()
    logger.info("Database initialization script finished.") 