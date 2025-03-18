#!/usr/bin/env python3
"""
Main entry point for the JPS Prospect Aggregate application.

This script initializes and runs the Flask web application and sets up the Celery
background task processing. It loads configuration from environment variables
and provides a clean entry point for running the application.
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from src.dashboard.factory import create_app
from src.celery_app import celery_app
from src.utils.logging import configure_root_logger, get_component_logger

# Load environment variables
load_dotenv()

# Configure root logger
configure_root_logger(os.getenv("LOG_LEVEL", "INFO"))

# Get component-specific logger
logger = get_component_logger('server')

# Create the Flask application
try:
    app = create_app()
    logger.info("Flask application created successfully")
except Exception as e:
    logger.error(f"Failed to create Flask application: {str(e)}")
    sys.exit(1)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='JPS Prospect Aggregate Flask Application')
    parser.add_argument('--host', default=os.getenv("HOST", "0.0.0.0"), help='Host to bind to')
    parser.add_argument('--port', type=int, default=int(os.getenv("PORT", 5001)), help='Port to bind to')
    parser.add_argument('--debug', action='store_true', default=os.getenv("DEBUG", "False").lower() == "true", 
                        help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Log startup information
    logger.info(f"Starting application on {args.host}:{args.port}")
    logger.info(f"Debug mode: {args.debug}")
    
    try:
        # Run the Flask application
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    except Exception as e:
        logger.error(f"Error running Flask application: {str(e)}")
        sys.exit(1) 