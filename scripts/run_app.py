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
import signal
from dotenv import load_dotenv
import traceback
from src.utils.logger import logger, cleanup_logs
from src.utils.file_utils import ensure_directory
import datetime

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modular components
from scripts.process_manager import start_process, cleanup, monitor_processes, processes
from scripts.dependency_checker import (
    test_redis_connection, check_memurai, check_server_py, 
    check_node_npm, frontend_needs_rebuild, ensure_env_file
)

# Platform detection
IS_WINDOWS = sys.platform == 'win32'

# Set up logging
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
ensure_directory(logs_dir)

# Get component-specific logger
logger = logger.bind(name="run_app")

# Startup logging
logger.info("==========================================")
logger.info("JPS Prospect Aggregate Application")
logger.info("==========================================")
logger.info(f"Started at: {datetime.datetime.now()}")
logger.info(f"Platform: {'Windows' if IS_WINDOWS else 'Unix-like'}")
logger.info("==========================================")

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
    logger.info("Registering cleanup handler...")
    atexit.register(cleanup)
    
    # Register signal handlers for graceful shutdown
    # This is crucial for proper cleanup of Celery worker processes
    logger.info("Setting up signal handlers...")
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Clean up old log files
    logger.info("Cleaning up old log files...")
    cleanup_logs(logs_dir, keep_count=3)
    
    # Ensure .env file exists with Redis configuration
    logger.info("Checking .env file...")
    ensure_env_file()
    
    # Check Redis/Memurai based on platform
    logger.info("Checking Redis/Memurai...")
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
    logger.info("Checking server.py...")
    if not check_server_py():
        logger.error("Cannot start Flask app. Please check server.py for errors.")
        sys.exit(1)
    
    # Check if Node.js and npm are installed
    logger.info("Checking Node.js and npm...")
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
    logger.info("Setting up project paths...")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    react_dir = os.path.join(project_root, 'frontend-react')
    
    # Define process configurations
    logger.info("Defining process configurations...")
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
    
    # Before starting new processes, ensure any lingering Celery processes are terminated
    logger.info("Checking for and terminating any lingering Celery processes before startup...")
    cleanup()
    
    # Add React process configuration if available
    if react_available:
        logger.info("Setting up React configuration...")
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
    
    try:
        logger.info("Attempting to start Flask app...")
        flask_process = start_process(
            process_configs["Flask App"]["cmd"],
            "Flask App",
            capture_output=process_configs["Flask App"]["capture_output"]
        )
        logger.info(f"Flask app started with PID {flask_process.pid}")
    except Exception as e:
        logger.error(f"Failed to start Flask app: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # Give Flask app time to start
    logger.info("Waiting for Flask app to initialize...")
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
    
    try:
        logger.info("Attempting to start Celery worker...")
        celery_worker_process = start_process(
            process_configs["Celery Worker"]["cmd"],
            "Celery Worker",
            capture_output=process_configs["Celery Worker"]["capture_output"],
            env=process_configs["Celery Worker"]["env"]
        )
        logger.info(f"Celery worker started with PID {celery_worker_process.pid}")
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {str(e)}")
        logger.error(traceback.format_exc())
        # Continue with the rest of the startup, as Flask can still run without Celery
    
    # Check if Celery worker started properly
    logger.info("Waiting for Celery worker to initialize...")
    time.sleep(2)
    if celery_worker_process.poll() is not None:
        logger.error(f"Celery worker failed to start (exit code {celery_worker_process.returncode})")
        logger.error("Check the celery_worker.log file in the logs directory for details")
        # Continue with the rest of the startup, as Flask can still run without Celery
    
    # Start Celery beat
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("STARTING CELERY BEAT")
    logger.info("=" * 80)
    
    try:
        logger.info("Attempting to start Celery beat...")
        celery_beat_process = start_process(
            process_configs["Celery Beat"]["cmd"],
            "Celery Beat",
            capture_output=process_configs["Celery Beat"]["capture_output"],
            env=process_configs["Celery Beat"]["env"]
        )
        logger.info(f"Celery beat started with PID {celery_beat_process.pid}")
    except Exception as e:
        logger.error(f"Failed to start Celery beat: {str(e)}")
        logger.error(traceback.format_exc())
        # Continue with the rest of the startup, as Flask can still run without Celery Beat
    
    # Check if Celery beat started properly
    logger.info("Waiting for Celery beat to initialize...")
    time.sleep(2)
    if celery_beat_process.poll() is not None:
        logger.error(f"Celery beat failed to start (exit code {celery_beat_process.returncode})")
        logger.error("Check the celery_beat.log file in the logs directory for details")
        # Continue with the rest of the startup, as Flask can still run without Celery Beat
    
    # Start Flower
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("STARTING FLOWER")
    logger.info("=" * 80)
    
    try:
        logger.info("Attempting to start Flower...")
        flower_process = start_process(
            process_configs["Flower"]["cmd"],
            "Flower",
            capture_output=process_configs["Flower"]["capture_output"],
            env=process_configs["Flower"]["env"]
        )
        logger.info(f"Flower started with PID {flower_process.pid}")
    except Exception as e:
        logger.error(f"Failed to start Flower: {str(e)}")
        logger.error(traceback.format_exc())
        # Continue with the rest of the startup, as Flask can still run without Flower
    
    # Start React dev server if in dev mode
    if react_available and REACT_DEV_MODE:
        logger.info("\n")
        logger.info("=" * 80)
        logger.info("STARTING REACT DEV SERVER")
        logger.info("=" * 80)
        
        try:
            logger.info("Attempting to start React dev server...")
            react_process = start_process(
                process_configs["React Dev Server"]["cmd"],
                "React Dev Server",
                cwd=process_configs["React Dev Server"]["cwd"],
                capture_output=process_configs["React Dev Server"]["capture_output"]
            )
            logger.info(f"React dev server started with PID {react_process.pid}")
        except Exception as e:
            logger.error(f"Failed to start React dev server: {str(e)}")
            logger.error(traceback.format_exc())
            # Continue with the rest of the startup, as the app can run without React
    
    # Display information
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("ALL COMPONENTS STARTED")
    logger.info("=" * 80)
    logger.info(f"Flask app:     http://{HOST}:{PORT}")
    logger.info(f"Flower:        http://{HOST}:5555")
    if react_available and REACT_DEV_MODE:
        logger.info(f"React app:     http://{HOST}:3000")
    logger.info("=" * 80)
    
    # Log the number of processes being monitored
    logger.info(f"Monitoring {len(processes)} processes...")
    if processes:
        for i, (name, (process, _)) in enumerate(processes.items()):
            logger.info(f"  {i+1}. {name} (PID {process.pid})")
    else:
        logger.warning("No processes are being monitored! This is likely an error.")
        logger.warning("Check if start_process() is correctly adding processes to the global processes list.")
    
    try:
        # Monitor processes
        logger.info("Starting process monitoring...")
        monitor_processes(process_configs)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
        cleanup()
        # Use os._exit instead of sys.exit for more forceful termination
        logger.info("Using os._exit(0) to ensure application termination")
        os._exit(0)
    except Exception as e:
        logger.error(f"Error in monitor_processes: {str(e)}")
        logger.error(traceback.format_exc())
        cleanup()
        # Use os._exit instead of sys.exit for more forceful termination
        logger.info("Using os._exit(1) to ensure application termination")
        os._exit(1)

# Signal handler for graceful shutdown
def handle_shutdown(signum, frame):
    """Handle shutdown signals by cleaning up and exiting."""
    logger.info(f"Received signal {signum}. Shutting down gracefully...")
    try:
        # Call cleanup to terminate all processes
        cleanup()
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    finally:
        logger.info("Exiting application...")
        # Force exit to avoid any potential hanging
        try:
            # Forcibly terminate any remaining threads
            import threading
            for thread in threading.enumerate():
                if thread is not threading.current_thread():
                    logger.info(f"Force terminating thread: {thread.name}")
                    try:
                        # We can't actually force-terminate threads in Python,
                        # but we can at least log which threads are still running
                        if hasattr(thread, "daemon"):
                            thread.daemon = True
                    except Exception as e:
                        logger.warning(f"Error setting thread as daemon: {e}")
            
            # Ensure we exit no matter what
            import os
            logger.info("Using os._exit(0) to ensure application termination")
            os._exit(0)  # This is a more forceful exit that doesn't call cleanup handlers
        except Exception as e:
            logger.error(f"Error during forced exit: {e}")
            # If all else fails, use the highest force exit
            os._exit(1)


if __name__ == "__main__":
    main() 