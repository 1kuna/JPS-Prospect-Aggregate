#!/usr/bin/env python
"""
JPS Prospect Aggregate Application Launcher
===========================================

This script starts the Flask web application using the Waitress WSGI server.
"""

import os
import sys
from dotenv import load_dotenv
from waitress import serve
from app import create_app
from app.utils.logger import logger

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment variables
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5001))
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true' # Use FLASK_DEBUG for waitress compatibility

# Create the Flask app instance
app = create_app()

def main():
    """Main entry point to start the server."""
    if DEBUG:
        logger.info(f"Starting Flask development server on http://{HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=True)
    else:
        logger.info(f"Starting production server on http://{HOST}:{PORT}")
        serve(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()