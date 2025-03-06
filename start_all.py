#!/usr/bin/env python
"""
Start script for JPS Prospect Aggregate application.
This script starts the Flask app, Celery worker, Celery beat processes, and Vue.js frontend.
It also handles Memurai (Redis for Windows) setup and connection.
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
import socket
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
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

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
# Track restart attempts for each process
restart_counts = {}
# Maximum number of restart attempts before giving up
MAX_RESTART_ATTEMPTS = 3
# Delay between restart attempts (in seconds)
RESTART_DELAY = 2

def start_process(cmd, name, cwd=None, capture_output=False):
    """Start a subprocess and return the process object."""
    logger.info(f"Starting {name}...")
    
    # Create log file for process output
    process_log_file = os.path.join(logs_dir, f"{name.lower().replace(' ', '_')}.log")
    log_file_handle = open(process_log_file, 'a')
    
    if sys.platform == 'win32':
        # Windows needs shell=True and different creation flags
        if capture_output:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=log_file_handle,
                stderr=log_file_handle,
                cwd=cwd
            )
        else:
            process = subprocess.Popen(
                cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=cwd
            )
    else:
        # Unix-like systems
        if capture_output:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=log_file_handle,
                stderr=log_file_handle,
                preexec_fn=os.setsid,
                cwd=cwd
            )
        else:
            process = subprocess.Popen(
                cmd,
                shell=True,
                preexec_fn=os.setsid,
                cwd=cwd
            )
    
    # Initialize restart count for this process
    restart_counts[process.pid] = 0
    
    processes.append((process, name, log_file_handle if capture_output else None))
    logger.info(f"{name} started with PID {process.pid}")
    logger.info(f"Output is being logged to {process_log_file}" if capture_output else "")
    return process

def cleanup():
    """Terminate all processes on exit."""
    logger.info("\nShutting down all processes...")
    for process, name, log_handle in processes:
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
        
        # Close log file handle if it exists
        if log_handle:
            log_handle.close()
            
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

def check_memurai():
    """
    Check if Memurai is installed and running on Windows.
    If not running, attempt to start it.
    Returns True if Memurai is running, False otherwise.
    """
    if sys.platform != 'win32':
        logger.info("Not on Windows, skipping Memurai check")
        return True
    
    logger.info("Checking Memurai (Redis for Windows) status...")
    
    # First, try to connect to Redis to see if it's already running
    redis_running = test_redis_connection()
    if redis_running:
        logger.info("Redis/Memurai is already running")
        return True
    
    # If Redis is not running, try to start Memurai
    logger.info("Redis/Memurai is not running. Attempting to start Memurai...")
    
    # Check if Memurai service exists
    try:
        service_check = subprocess.run(
            ['sc', 'query', 'Memurai'], 
            capture_output=True, 
            text=True
        )
        
        if service_check.returncode == 0:
            # Memurai service exists, try to start it
            logger.info("Memurai service found. Attempting to start it...")
            
            # Check if service is already running
            if "RUNNING" in service_check.stdout:
                logger.info("Memurai service is already running")
            else:
                # Try to start the service
                start_result = subprocess.run(
                    ['net', 'start', 'Memurai'],
                    capture_output=True,
                    text=True
                )
                
                if start_result.returncode == 0:
                    logger.info("Memurai service started successfully")
                else:
                    logger.warning(f"Failed to start Memurai service: {start_result.stderr}")
                    logger.warning("Will try to start Memurai executable directly")
        else:
            logger.info("Memurai service not found. Will try to start Memurai executable directly")
            
        # Check if Memurai executable exists (as a fallback)
        memurai_paths = [
            "C:\\Program Files\\Memurai\\memurai.exe",
            "C:\\Program Files (x86)\\Memurai\\memurai.exe"
        ]
        
        memurai_exe = None
        for path in memurai_paths:
            if os.path.exists(path):
                memurai_exe = path
                break
        
        if memurai_exe:
            logger.info(f"Found Memurai executable at {memurai_exe}. Attempting to start it...")
            # Start Memurai executable
            subprocess.Popen([memurai_exe], creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Wait for Memurai to start
            logger.info("Waiting for Memurai to start...")
            for _ in range(10):  # Try for 10 seconds
                time.sleep(1)
                if test_redis_connection():
                    logger.info("Memurai started successfully")
                    return True
            
            logger.error("Memurai started but Redis connection test failed")
            return False
        else:
            logger.error("Memurai executable not found")
    except Exception as e:
        logger.error(f"Error checking/starting Memurai: {str(e)}")
    
    # If we got here, we couldn't start Memurai
    logger.error("Failed to start Memurai. Please install Memurai or start it manually.")
    logger.error("Download Memurai from: https://www.memurai.com/get-memurai")
    return False

def test_redis_connection():
    """Test connection to Redis/Memurai."""
    try:
        # Parse Redis URL to get host and port
        if REDIS_URL.startswith('redis://'):
            parts = REDIS_URL.replace('redis://', '').split(':')
            host = parts[0] or 'localhost'
            port_db = parts[1].split('/')
            port = int(port_db[0])
        else:
            host = 'localhost'
            port = 6379
        
        # Try to connect to Redis
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((host, port))
        s.close()
        
        logger.info(f"Successfully connected to Redis/Memurai at {host}:{port}")
        return True
    except Exception as e:
        logger.warning(f"Failed to connect to Redis/Memurai: {str(e)}")
        return False

def ensure_env_file():
    """
    Ensure .env file exists with Redis configuration.
    If .env doesn't exist, create it from .env.example or with default values.
    If .env exists but doesn't have Redis config, add it.
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.example')
    
    # If .env doesn't exist, create it
    if not os.path.exists(env_path):
        logger.info(".env file not found. Creating one...")
        
        if os.path.exists(example_path):
            # Copy from example
            shutil.copy(example_path, env_path)
            logger.info("Created .env file from .env.example")
        else:
            # Create with default values
            with open(env_path, 'w') as f:
                f.write("""# Application settings
HOST=0.0.0.0
PORT=5001
DEBUG=False

# Database settings
DATABASE_URL=sqlite:///data/proposals.db
SQL_ECHO=False

# Scheduler settings
SCRAPE_INTERVAL_HOURS=24
HEALTH_CHECK_INTERVAL_MINUTES=10

# Celery settings
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Vue.js settings
VUE_DEV_MODE=True  # Set to False for production
""")
            logger.info("Created .env file with default values")
    else:
        # Check if .env has Redis config
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        redis_configs = [
            "REDIS_URL=",
            "CELERY_BROKER_URL=",
            "CELERY_RESULT_BACKEND="
        ]
        
        missing_configs = [config for config in redis_configs if config not in env_content]
        
        if missing_configs:
            logger.info("Adding missing Redis configuration to .env file...")
            
            with open(env_path, 'a') as f:
                f.write("\n# Added by start_all.py\n")
                for config in missing_configs:
                    f.write(f"{config}redis://localhost:6379/0\n")
            
            logger.info("Updated .env file with Redis configuration")
    
    # Reload environment variables
    load_dotenv(env_path, override=True)

def check_app_py():
    """Check if app.py exists and is executable."""
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
    if not os.path.exists(app_path):
        logger.error(f"app.py not found at {app_path}")
        logger.error("Please make sure you're running this script from the project root directory")
        return False
    
    # Try to run app.py with --help to see if it's executable
    try:
        result = subprocess.run(['python', app_path, '--help'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"app.py exists but may have errors: {result.stderr}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking app.py: {str(e)}")
        return False

def main():
    """Start all components of the application."""
    # Register cleanup handler
    atexit.register(cleanup)
    
    # Ensure .env file exists with Redis configuration
    ensure_env_file()
    
    # Check and start Memurai on Windows
    if sys.platform == 'win32':
        if not check_memurai():
            logger.error("Cannot start Celery without Redis/Memurai. Exiting.")
            sys.exit(1)
    else:
        # On non-Windows platforms, just test Redis connection
        if not test_redis_connection():
            logger.warning("Redis connection failed. Celery may not work properly.")
            logger.warning("Please ensure Redis is installed and running.")
    
    # Check if app.py exists and is executable
    if not check_app_py():
        logger.error("Cannot start Flask app. Please check app.py for errors.")
        sys.exit(1)
    
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
    
    # Start Flask app with output capture
    flask_cmd = f"python app.py"
    flask_process = start_process(flask_cmd, "Flask App", capture_output=True)
    
    # Give Flask app time to start
    time.sleep(5)
    
    # Check if Flask app is still running
    if flask_process.poll() is not None:
        logger.error(f"Flask app failed to start (exit code {flask_process.returncode})")
        logger.error("Check the flask_app.log file in the logs directory for details")
        sys.exit(1)
    
    # Start Celery worker with output capture
    worker_cmd = "celery -A src.celery_app worker --loglevel=info"
    worker_process = start_process(worker_cmd, "Celery Worker", capture_output=True)
    
    # Start Celery beat with output capture
    beat_cmd = "celery -A src.celery_app beat --loglevel=info"
    beat_process = start_process(beat_cmd, "Celery Beat", capture_output=True)
    
    # Optional: Start Flower for monitoring with output capture
    flower_cmd = "celery -A src.celery_app flower --port=5555"
    flower_process = start_process(flower_cmd, "Flower", capture_output=True)
    
    # Start Vue.js development server if in dev mode
    if VUE_DEV_MODE and vue_available:
        frontend_dir = os.path.join('src', 'dashboard', 'frontend')
        vue_cmd = "npm run serve"
        vue_process = start_process(vue_cmd, "Vue.js Dev Server", cwd=frontend_dir, capture_output=True)
    
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
            for i, (process, name, log_handle) in enumerate(processes):
                if process.poll() is not None:
                    pid = process.pid
                    exit_code = process.returncode
                    
                    # Check if we've reached the maximum number of restart attempts
                    if restart_counts.get(pid, 0) >= MAX_RESTART_ATTEMPTS:
                        logger.error(f"{name} terminated unexpectedly with code {exit_code}")
                        logger.error(f"Maximum restart attempts ({MAX_RESTART_ATTEMPTS}) reached for {name}")
                        logger.error(f"Check the {name.lower().replace(' ', '_')}.log file for details")
                        continue
                    
                    # Increment restart count
                    restart_counts[pid] = restart_counts.get(pid, 0) + 1
                    
                    logger.warning(f"{name} terminated unexpectedly with code {exit_code} (attempt {restart_counts[pid]}/{MAX_RESTART_ATTEMPTS})")
                    
                    # Wait before restarting
                    time.sleep(RESTART_DELAY)
                    
                    # Close log file handle if it exists
                    if log_handle:
                        log_handle.close()
                    
                    # Restart the process
                    if name == "Flask App":
                        new_process = start_process(flask_cmd, name, capture_output=True)
                    elif name == "Celery Worker":
                        new_process = start_process(worker_cmd, name, capture_output=True)
                    elif name == "Celery Beat":
                        new_process = start_process(beat_cmd, name, capture_output=True)
                    elif name == "Flower":
                        new_process = start_process(flower_cmd, name, capture_output=True)
                    elif name == "Vue.js Dev Server" and VUE_DEV_MODE and vue_available:
                        frontend_dir = os.path.join('src', 'dashboard', 'frontend')
                        new_process = start_process(vue_cmd, name, cwd=frontend_dir, capture_output=True)
                    
                    # Replace the terminated process in the list
                    processes[i] = (new_process, name, log_handle)
                    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        # cleanup will be called by atexit

if __name__ == "__main__":
    main() 