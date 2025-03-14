#!/usr/bin/env python
"""
JPS Prospect Aggregate Application Launcher
===========================================

This script provides a cross-platform solution for starting all components of the 
JPS Prospect Aggregate application. It handles platform-specific differences between
Windows and Unix-like systems (macOS, Linux).

Components started:
- Flask web application
- Celery worker for background tasks
- Celery beat for scheduled tasks
- Flower for Celery monitoring
- React frontend (development server or production build)

Features:
- Cross-platform compatibility (Windows and Unix-like systems)
- Automatic Redis/Memurai detection and configuration
- Process monitoring and automatic restart on failure
- Comprehensive logging
- Environment configuration management

Usage:
    python scripts/run_app.py

Requirements:
    - Python 3.10+
    - Redis (Unix) or Memurai (Windows)
    - Node.js and npm (for React frontend)
"""

import os
import sys
import time
import atexit
import logging
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modular components
from scripts.process_manager import start_process, cleanup, monitor_processes
from scripts.dependency_checker import (
    test_redis_connection, check_memurai, check_server_py, 
    check_node_npm, frontend_needs_rebuild, ensure_env_file
)
from scripts.log_setup import setup_logging, cleanup_logs

# Platform detection
IS_WINDOWS = sys.platform == 'win32'

# Set up logging
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
logger = setup_logging(logs_dir=logs_dir)

# Load environment variables
load_dotenv()

# Get configuration from environment
HOST = os.getenv('HOST', '0.0.0.0')
PORT = os.getenv('PORT', '5001')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
REACT_DEV_MODE = os.getenv('REACT_DEV_MODE', 'True').lower() == 'true'


def main():
    """
    Start all components of the application.
    
    This is the main entry point of the script. It:
    1. Sets up the environment
    2. Checks dependencies
    3. Starts all required processes
    4. Monitors processes and restarts them if they fail
    """
    # Register cleanup handler
    atexit.register(cleanup)
    
    # Clean up old log files
    cleanup_logs(logs_dir, keep_count=3)
    
    # Ensure .env file exists with Redis configuration
    ensure_env_file()
    
    # Check Redis/Memurai based on platform
    if IS_WINDOWS:
        if not check_memurai():
            logger.error("Cannot start Celery without Redis/Memurai. Exiting.")
            sys.exit(1)
    else:
        # On non-Windows platforms, just test Redis connection
        if not test_redis_connection():
            logger.warning("Redis connection failed. Celery may not work properly.")
            logger.warning("Please ensure Redis is installed and running.")
            logger.warning("On macOS, you can install Redis with: brew install redis")
            logger.warning("On Linux, you can install Redis with: sudo apt-get install redis-server")
    
    # Check if server.py exists and is executable
    if not check_server_py():
        logger.error("Cannot start Flask app. Please check server.py for errors.")
        sys.exit(1)
    
    # Check if Node.js and npm are installed
    react_available = False
    frontend_built = False
    if check_node_npm():
        react_available = True
        
        # Check if frontend needs to be rebuilt
        rebuild_needed = frontend_needs_rebuild()
        
        # Set REACT_FORCE_REBUILD if needed
        if os.getenv('REACT_FORCE_REBUILD') is None and rebuild_needed:
            os.environ['REACT_FORCE_REBUILD'] = 'true'
            logger.info("Setting REACT_FORCE_REBUILD=true because frontend changes were detected")
    
    # Get the frontend directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    react_dir = os.path.join(project_root, 'frontend-react')
    
    # Define process configurations
    process_configs = {
        "Flask App": {
            "cmd": [sys.executable, os.path.join(project_root, "server.py")],
            "capture_output": True
        },
        "Celery Worker": {
            "cmd": [sys.executable, "-m", "celery", "-A", "src.celery_app.celery_app", "worker", "--loglevel=info"],
            "capture_output": True,
            "env": {**os.environ, "PYTHONPATH": project_root}
        },
        "Celery Beat": {
            "cmd": [sys.executable, "-m", "celery", "-A", "src.celery_app.celery_app", "beat", "--loglevel=info"],
            "capture_output": True,
            "env": {**os.environ, "PYTHONPATH": project_root}
        },
        "Flower": {
            "cmd": [sys.executable, "-m", "celery", "-A", "src.celery_app.celery_app", "flower", "--port=5555"],
            "capture_output": True,
            "env": {**os.environ, "PYTHONPATH": project_root}
        }
    }
    
    # Add React process configuration if available
    if react_available:
        if REACT_DEV_MODE:
            process_configs["React Dev Server"] = {
                "cmd": ["npm", "run", "dev"],
                "cwd": react_dir,
                "capture_output": True
            }
        else:
            # Check if we need to build the frontend
            if rebuild_needed or os.getenv('REACT_FORCE_REBUILD', '').lower() == 'true':
                logger.info("Building React frontend...")
                try:
                    # Run npm install if node_modules doesn't exist
                    if not os.path.exists(os.path.join(react_dir, 'node_modules')):
                        logger.info("Installing npm dependencies...")
                        start_process(
                            ["npm", "install"],
                            "NPM Install",
                            cwd=react_dir,
                            capture_output=True
                        )
                    
                    # Build the frontend
                    build_process = start_process(
                        ["npm", "run", "build"],
                        "React Build",
                        cwd=react_dir,
                        capture_output=True
                    )
                    
                    # Wait for the build to complete
                    build_process.wait()
                    
                    if build_process.returncode == 0:
                        logger.info("React frontend built successfully")
                        frontend_built = True
                    else:
                        logger.error("Failed to build React frontend")
                except Exception as e:
                    logger.error(f"Error building React frontend: {str(e)}")
    
    # Start Flask app
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("STARTING FLASK APPLICATION")
    logger.info("=" * 80)
    
    flask_process = start_process(
        process_configs["Flask App"]["cmd"],
        "Flask App",
        capture_output=process_configs["Flask App"]["capture_output"]
    )
    
    # Give Flask app time to start
    time.sleep(2)
    
    # Check if Flask app is still running
    if flask_process.poll() is not None:
        logger.error(f"Flask app failed to start (exit code {flask_process.returncode})")
        logger.error("Check the flask_app.log file in the logs directory for details")
        sys.exit(1)
    
    # Start Celery worker
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("STARTING CELERY WORKER")
    logger.info("=" * 80)
    
    start_process(
        process_configs["Celery Worker"]["cmd"],
        "Celery Worker",
        capture_output=process_configs["Celery Worker"]["capture_output"],
        env=process_configs["Celery Worker"]["env"]
    )
    
    # Start Celery beat
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("STARTING CELERY BEAT")
    logger.info("=" * 80)
    
    start_process(
        process_configs["Celery Beat"]["cmd"],
        "Celery Beat",
        capture_output=process_configs["Celery Beat"]["capture_output"],
        env=process_configs["Celery Beat"]["env"]
    )
    
    # Start Flower
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("STARTING FLOWER")
    logger.info("=" * 80)
    
    start_process(
        process_configs["Flower"]["cmd"],
        "Flower",
        capture_output=process_configs["Flower"]["capture_output"],
        env=process_configs["Flower"]["env"]
    )
    
    # Start React dev server if in dev mode
    if react_available and REACT_DEV_MODE:
        logger.info("\n")
        logger.info("=" * 80)
        logger.info("STARTING REACT DEV SERVER")
        logger.info("=" * 80)
        
        start_process(
            process_configs["React Dev Server"]["cmd"],
            "React Dev Server",
            cwd=process_configs["React Dev Server"]["cwd"],
            capture_output=process_configs["React Dev Server"]["capture_output"]
        )
    
    # Log startup complete
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("ALL COMPONENTS STARTED")
    logger.info("=" * 80)
    logger.info(f"Flask app running at: http://{HOST}:{PORT}")
    logger.info(f"Flower dashboard running at: http://{HOST}:5555")
    
    if react_available and REACT_DEV_MODE:
        logger.info(f"React dev server running at: http://localhost:5173")
    
    logger.info("\nPress Ctrl+C to stop all components\n")
    
    # Monitor processes and restart them if they fail
    monitor_processes(process_configs)


if __name__ == "__main__":
    main() 