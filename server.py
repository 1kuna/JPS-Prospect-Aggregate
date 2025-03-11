#!/usr/bin/env python3
"""
Main entry point for the JPS Prospect Aggregate application.

This script initializes and runs the Flask web application and sets up the Celery
background task processing. It loads configuration from environment variables
and provides a clean entry point for running the application.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from src.dashboard.factory import create_app
from src.celery_app import celery_app

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create the Flask application
try:
    app = create_app()
    logger.info("Flask application created successfully")
except Exception as e:
    logger.error(f"Failed to create Flask application: {str(e)}")
    sys.exit(1)

if __name__ == "__main__":
    # Log startup information
    logger.info(f"Starting application on {os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', 5001)}")
    logger.info(f"Debug mode: {os.getenv('DEBUG', 'False').lower() == 'true'}")
    
    try:
        # Run the Flask application
        app.run(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", 5001)),
            debug=os.getenv("DEBUG", "False").lower() == "true"
        )
    except Exception as e:
        logger.error(f"Error running Flask application: {str(e)}")
        sys.exit(1) 