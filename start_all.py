#!/usr/bin/env python
"""
Start script for JPS Prospect Aggregate application.
This script starts the Flask app, Celery worker, Celery beat processes, and Vue.js frontend.
"""

import os
import sys
import subprocess
import time
import signal
import atexit
import shutil
import logging
import datetime
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the log manager
try:
    from src.utils.log_manager import cleanup_all_logs
    from src.config import LOGS_DIR, LOG_FORMAT, LOG_FILE_MAX_BYTES, LOG_FILE_BACKUP_COUNT
    log_manager_available = True
except ImportError:
    log_manager_available = False

# Load environment variables
load_dotenv()

# Get configuration from environment
HOST = os.getenv('HOST', '0.0.0.0')
PORT = os.getenv('PORT', '5001')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
VUE_DEV_MODE = os.getenv('VUE_DEV_MODE', 'True').lower() == 'true'

# Set up logging
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Use a consistent log file name with rotation instead of timestamp-based names
log_file = os.path.join(logs_dir, 'jps_startup.log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Clear existing handlers to avoid duplicates
if logger.handlers:
    logger.handlers.clear()

# Create handlers with rotation
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=5 * 1024 * 1024 if not log_manager_available else LOG_FILE_MAX_BYTES, 
    backupCount=3 if not log_manager_available else LOG_FILE_BACKUP_COUNT
)
console_handler = logging.StreamHandler()

# Create formatters and add them to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("==========================================")
logger.info("JPS Prospect Aggregate Auto-Setup & Launch")
logger.info("==========================================")
logger.info(f"Logging to: {log_file}")
logger.info(f"Started at: {datetime.datetime.now()}")
logger.info("==========================================")

# Clean up old log files if log manager is available
if log_manager_available:
    cleanup_results = cleanup_all_logs(logs_dir, keep_count=3)
    for log_type, count in cleanup_results.items():
        if count > 0:
            logger.info(f"Cleaned up {count} old {log_type} log files")

# Process tracking
processes = []

def start_process(cmd, name, cwd=None):
    """Start a subprocess and return the process object."""
    logger.info(f"Starting {name}...")
    if sys.platform == 'win32':
        # Windows needs shell=True and different creation flags
        process = subprocess.Popen(
            cmd,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=cwd
        )
    else:
        # Unix-like systems
        process = subprocess.Popen(
            cmd,
            shell=True,
            preexec_fn=os.setsid,
            cwd=cwd
        )
    processes.append((process, name))
    logger.info(f"{name} started with PID {process.pid}")
    return process

def cleanup():
    """Terminate all processes on exit."""
    logger.info("\nShutting down all processes...")
    for process, name in processes:
        logger.info(f"Terminating {name} (PID: {process.pid})...")
        if sys.platform == 'win32':
            # Windows
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
        else:
            # Unix-like systems
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except OSError:
                pass
    logger.info("All processes terminated.")

def check_node_npm():
    """Check if Node.js and npm are installed."""
    try:
        # Check Node.js
        node_version = subprocess.check_output(['node', '--version'], text=True).strip()
        logger.info(f"Node.js version: {node_version}")
        
        # Check npm
        npm_version = subprocess.check_output(['npm', '--version'], text=True).strip()
        logger.info(f"npm version: {npm_version}")
        
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Node.js or npm not found. Please install Node.js and npm to run the Vue.js frontend.")
        return False

def build_vue_frontend():
    """Build the Vue.js frontend for production."""
    frontend_dir = os.path.join('src', 'dashboard', 'frontend')
    
    # Check if node_modules exists, if not run npm install
    if not os.path.exists(os.path.join(frontend_dir, 'node_modules')):
        logger.info("Installing Vue.js dependencies...")
        subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
    
    # Build the Vue.js app
    logger.info("Building Vue.js frontend for production...")
    subprocess.run(['npm', 'run', 'build'], cwd=frontend_dir, check=True)
    
    # Ensure the static/vue directory exists
    static_vue_dir = os.path.join('src', 'dashboard', 'static', 'vue')
    os.makedirs(static_vue_dir, exist_ok=True)
    
    logger.info("Vue.js frontend built successfully!")

def main():
    """Start all components of the application."""
    # Register cleanup handler
    atexit.register(cleanup)
    
    # Check if Node.js and npm are installed if Vue dev mode is enabled
    if VUE_DEV_MODE:
        if not check_node_npm():
            logger.warning("Warning: Vue.js frontend will not be started.")
            vue_available = False
        else:
            vue_available = True
    else:
        # In production mode, build the Vue.js frontend
        if check_node_npm():
            build_vue_frontend()
        vue_available = False  # Don't start Vue dev server in production mode
    
    # Start Flask app
    flask_cmd = f"python app.py"
    flask_process = start_process(flask_cmd, "Flask App")
    
    # Give Flask app time to start
    time.sleep(2)
    
    # Start Celery worker
    worker_cmd = "celery -A src.celery_app worker --loglevel=info"
    worker_process = start_process(worker_cmd, "Celery Worker")
    
    # Start Celery beat
    beat_cmd = "celery -A src.celery_app beat --loglevel=info"
    beat_process = start_process(beat_cmd, "Celery Beat")
    
    # Optional: Start Flower for monitoring
    flower_cmd = "celery -A src.celery_app flower --port=5555"
    flower_process = start_process(flower_cmd, "Flower")
    
    # Start Vue.js development server if in dev mode
    if VUE_DEV_MODE and vue_available:
        frontend_dir = os.path.join('src', 'dashboard', 'frontend')
        vue_cmd = "npm run serve"
        vue_process = start_process(vue_cmd, "Vue.js Dev Server", cwd=frontend_dir)
    
    logger.info("\nAll services started!")
    logger.info(f"- Flask app running at http://{HOST}:{PORT}")
    logger.info("- Celery worker processing tasks")
    logger.info("- Celery beat scheduling tasks")
    logger.info("- Flower monitoring available at http://localhost:5555")
    if VUE_DEV_MODE and vue_available:
        logger.info("- Vue.js dev server running at http://localhost:8080")
    logger.info("\nPress Ctrl+C to stop all services")
    
    try:
        # Keep the script running until interrupted
        while True:
            time.sleep(1)
            
            # Check if any process has terminated unexpectedly
            for i, (process, name) in enumerate(processes):
                if process.poll() is not None:
                    logger.warning(f"{name} terminated unexpectedly with code {process.returncode}")
                    # Restart the process
                    if name == "Flask App":
                        new_process = start_process(flask_cmd, name)
                    elif name == "Celery Worker":
                        new_process = start_process(worker_cmd, name)
                    elif name == "Celery Beat":
                        new_process = start_process(beat_cmd, name)
                    elif name == "Flower":
                        new_process = start_process(flower_cmd, name)
                    elif name == "Vue.js Dev Server" and VUE_DEV_MODE and vue_available:
                        frontend_dir = os.path.join('src', 'dashboard', 'frontend')
                        new_process = start_process(vue_cmd, name, cwd=frontend_dir)
                    
                    # Replace the terminated process in the list
                    processes[i] = (new_process, name)
                    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        # cleanup will be called by atexit

if __name__ == "__main__":
    main() 