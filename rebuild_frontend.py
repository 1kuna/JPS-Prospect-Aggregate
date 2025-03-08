#!/usr/bin/env python
"""
JPS Prospect Aggregate Frontend Rebuild Script
=============================================

This script forces a rebuild of the Vue.js frontend for the JPS Prospect Aggregate application.
It's useful when you've made changes to the frontend and want to rebuild it without restarting
the entire application.

Usage:
    python rebuild_frontend.py
"""

import os
import sys
import subprocess
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Force a rebuild of the Vue.js frontend."""
    logger.info("=" * 80)
    logger.info("FORCING REBUILD OF VUE.JS FRONTEND")
    logger.info("=" * 80)
    
    # Set environment variables
    os.environ['VUE_FORCE_REBUILD'] = 'true'
    
    # Import the build_vue_frontend function from start_all.py
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from start_all import build_vue_frontend, check_node_npm
    except ImportError as e:
        logger.error(f"Error importing from start_all.py: {e}")
        logger.error("Make sure you're running this script from the project root directory.")
        sys.exit(1)
    
    # Check if Node.js and npm are installed
    if not check_node_npm():
        logger.error("Node.js or npm not found. Please install them to build the frontend.")
        sys.exit(1)
    
    # Build the frontend
    logger.info("Starting frontend rebuild...")
    success = build_vue_frontend()
    
    if success:
        logger.info("=" * 80)
        logger.info("FRONTEND REBUILD COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info("You may need to restart the application to see the changes.")
    else:
        logger.error("=" * 80)
        logger.error("FRONTEND REBUILD FAILED")
        logger.error("=" * 80)
        sys.exit(1)

if __name__ == "__main__":
    main() 