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
- Vue.js frontend (development server or production build)

Features:
- Cross-platform compatibility (Windows and Unix-like systems)
- Automatic Redis/Memurai detection and configuration
- Process monitoring and automatic restart on failure
- Comprehensive logging
- Environment configuration management

Usage:
    python start_all.py

Requirements:
    - Python 3.10+
    - Redis (Unix) or Memurai (Windows)
    - Node.js and npm (for Vue.js frontend)
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

# Constants
MAX_RESTART_ATTEMPTS = 3
RESTART_DELAY = 2

# Platform detection
IS_WINDOWS = sys.platform == 'win32'
IS_UNIX = not IS_WINDOWS

# Process tracking
processes = []
restart_counts = {}

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
logger.info(f"Platform: {'Windows' if IS_WINDOWS else 'Unix-like'}")
logger.info("==========================================")

# Clean up old log files if log manager is available
if log_manager_available:
    cleanup_results = cleanup_all_logs(logs_dir, keep_count=3)
    for log_type, count in cleanup_results.items():
        if count > 0:
            logger.info(f"Cleaned up {count} old {log_type} log files")


def start_process(cmd, name, cwd=None, capture_output=False):
    """
    Start a subprocess and return the process object.
    
    Args:
        cmd (str): The command to run
        name (str): A name for the process (for logging)
        cwd (str, optional): The working directory for the process
        capture_output (bool, optional): Whether to capture and log the process output
        
    Returns:
        subprocess.Popen: The process object
    """
    global processes
    
    # Create log file for this process
    log_file = os.path.join(logs_dir, f"{name.lower().replace(' ', '_')}.log")
    log_handle = open(log_file, 'a')
    
    # Add timestamp to log
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_handle.write(f"\n\n{'=' * 80}\n")
    log_handle.write(f"PROCESS STARTED: {timestamp}\n")
    log_handle.write(f"COMMAND: {cmd}\n")
    if cwd:
        log_handle.write(f"WORKING DIRECTORY: {cwd}\n")
    log_handle.write(f"{'=' * 80}\n\n")
    log_handle.flush()
    
    # Start the process
    logger.info(f"Starting {name}...")
    
    try:
        if IS_WINDOWS:
            # On Windows, we need to use shell=True to run commands with arguments
            process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=cwd,
                stdout=log_handle if capture_output else None,
                stderr=log_handle if capture_output else None,
                text=True
            )
        else:
            # On Unix-like systems, we can use shell=False for better security
            process = subprocess.Popen(
                cmd.split(),
                cwd=cwd,
                stdout=log_handle if capture_output else None,
                stderr=log_handle if capture_output else None,
                text=True
            )
        
        # Store the process, its name, and log handle for later cleanup
        processes.append((process, name, log_handle))
        
        # Initialize restart count for this process
        restart_counts[name] = 0
        
        # Log process ID
        logger.info(f"{name} started with PID {process.pid}")
        
        # For Flask app, add a note about where to find the logs
        if name == "Flask App":
            logger.info(f"Flask app logs will be written to {log_file}")
            logger.info("If you encounter frontend issues, check these logs for details")
        
        return process
    except Exception as e:
        logger.error(f"Error starting {name}: {e}")
        log_handle.write(f"Error starting process: {e}\n")
        log_handle.close()
        raise


def cleanup():
    """
    Clean up resources before exiting.
    
    This function:
    1. Terminates all running processes
    2. Closes all log file handles
    3. Performs any other necessary cleanup
    """
    logger.info("Cleaning up resources...")
    
    # Terminate all processes
    for process, name, log_handle in processes:
        try:
            logger.info(f"Terminating {name} (PID {process.pid})...")
            
            if process.poll() is None:  # Process is still running
                if IS_WINDOWS:
                    # On Windows, we need to use taskkill to terminate the process tree
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                                  check=False, capture_output=True)
                else:
                    # On Unix-like systems, we can use process groups
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    
                # Give the process a moment to terminate gracefully
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # If the process doesn't terminate gracefully, force kill it
                    logger.warning(f"{name} did not terminate gracefully, force killing...")
                    if IS_WINDOWS:
                        subprocess.run(['taskkill', '/F', '/PID', str(process.pid)], 
                                      check=False, capture_output=True)
                    else:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            
            # Log the termination
            if log_handle and not log_handle.closed:
                log_handle.write(f"\n\n{'=' * 80}\n")
                log_handle.write(f"PROCESS TERMINATED BY CLEANUP: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_handle.write(f"{'=' * 80}\n\n")
                log_handle.close()
                
        except Exception as e:
            logger.error(f"Error terminating {name}: {e}")
            # Still try to close the log handle
            if log_handle and not log_handle.closed:
                try:
                    log_handle.close()
                except:
                    pass
    
    # Clear the processes list
    processes.clear()
    
    # Clean up log files if the log manager is available
    if log_manager_available:
        try:
            cleanup_all_logs()
        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")
    
    logger.info("Cleanup completed. Exiting.")
    
    # Flush all logging handlers to ensure logs are written
    for handler in logger.handlers:
        handler.flush()


def check_node_npm():
    """
    Check if Node.js and npm are installed.
    
    Returns:
        bool: True if both Node.js and npm are installed, False otherwise
    """
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
    """
    Build the Vue.js frontend for production.
    
    This function installs dependencies if needed and builds the Vue.js
    application for production deployment.
    """
    frontend_dir = os.path.join('src', 'dashboard', 'frontend')
    
    # Print a clear header for the frontend build process
    logger.info("=" * 80)
    logger.info("STARTING VUE.JS FRONTEND BUILD")
    logger.info("=" * 80)
    
    # Always run npm install to ensure dependencies are up to date
    logger.info("Step 1/4: Installing/updating Vue.js dependencies...")
    try:
        npm_install_process = subprocess.run(
            ['npm', 'install'], 
            cwd=frontend_dir, 
            check=False,
            capture_output=True,
            text=True
        )
        
        if npm_install_process.returncode != 0:
            logger.error(f"npm install failed with code {npm_install_process.returncode}")
            logger.error(f"Error output: {npm_install_process.stderr}")
            return False
        else:
            logger.info("npm install completed successfully")
        
        # Build the Vue.js app for production
        logger.info("Step 2/4: Building Vue.js frontend for production...")
        
        # Set NODE_ENV to production to ensure consistent builds
        build_env = os.environ.copy()
        build_env['NODE_ENV'] = 'production'
        
        # Run the build process and capture output
        build_process = subprocess.run(
            ['npm', 'run', 'build'], 
            cwd=frontend_dir, 
            check=False,
            capture_output=True,
            text=True,
            env=build_env
        )
        
        # Check if build was successful
        if build_process.returncode != 0:
            logger.error(f"Vue.js build failed with code {build_process.returncode}")
            logger.error("Build error details:")
            for line in build_process.stderr.splitlines():
                logger.error(f"  {line}")
            return False
        else:
            # Log build success and some output details
            logger.info("Vue.js build completed successfully")
            
            # Extract and log important parts of the build output
            output_lines = build_process.stdout.splitlines()
            build_summary = []
            warnings = []
            
            # Find build summary section
            in_summary = False
            in_warnings = False
            
            for line in output_lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Detect build summary section
                if "File" in line and "Size" in line and "Gzipped" in line:
                    in_summary = True
                    build_summary.append(line)
                    continue
                
                # Detect warnings section
                if "WARNING" in line or "warning" in line:
                    in_warnings = True
                    warnings.append(line)
                    continue
                
                # Collect build summary lines
                if in_summary and ("KiB" in line or "MiB" in line):
                    build_summary.append(line)
                
                # End of build summary
                if in_summary and "Build at:" in line:
                    in_summary = False
                    build_summary.append(line)
            
            # Log build summary
            if build_summary:
                logger.info("Build summary:")
                for line in build_summary:
                    logger.info(f"  {line}")
            
            # Log warnings (if any)
            if warnings:
                logger.warning("Build completed with warnings:")
                for line in warnings[:5]:  # Show only first 5 warnings to avoid log spam
                    logger.warning(f"  {line}")
                if len(warnings) > 5:
                    logger.warning(f"  ... and {len(warnings) - 5} more warnings")
        
        # Ensure the static/vue directory exists
        logger.info("Step 3/4: Preparing static directory...")
        static_vue_dir = os.path.join('src', 'dashboard', 'static', 'vue')
        os.makedirs(static_vue_dir, exist_ok=True)
        
        # Clear the static/vue directory to avoid stale files
        logger.info("Clearing existing static/vue directory...")
        for item in os.listdir(static_vue_dir):
            item_path = os.path.join(static_vue_dir, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        
        # Copy the built files from dist to static/vue
        logger.info("Step 4/4: Copying built files to Flask static directory...")
        dist_dir = os.path.join(frontend_dir, 'dist')
        
        if os.path.exists(dist_dir):
            # Count files to copy for progress reporting
            total_files = sum([len(files) for _, _, files in os.walk(dist_dir)])
            copied_files = 0
            
            # Copy all files from dist to static/vue
            for item in os.listdir(dist_dir):
                src_path = os.path.join(dist_dir, item)
                dst_path = os.path.join(static_vue_dir, item)
                
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                    copied_files += 1
                elif os.path.isdir(src_path):
                    if os.path.exists(dst_path):
                        shutil.rmtree(dst_path)
                    shutil.copytree(src_path, dst_path)
                    copied_files += sum([len(files) for _, _, files in os.walk(src_path)])
            
            logger.info(f"Copied {copied_files} of {total_files} files to {static_vue_dir}")
            logger.info("=" * 80)
            logger.info("VUE.JS FRONTEND BUILD COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
        else:
            logger.error(f"Build directory {dist_dir} does not exist after build!")
            logger.error("=" * 80)
            logger.error("VUE.JS FRONTEND BUILD FAILED")
            logger.error("=" * 80)
            return False
        
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Error building Vue.js frontend: {e}")
        logger.error("=" * 80)
        logger.error("VUE.JS FRONTEND BUILD FAILED")
        logger.error("=" * 80)
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Vue.js frontend build: {e}")
        logger.error("=" * 80)
        logger.error("VUE.JS FRONTEND BUILD FAILED")
        logger.error("=" * 80)
        return False


def check_memurai():
    """
    Check if Memurai is installed and running on Windows.
    If not running, attempt to start it.
    
    Returns:
        bool: True if Memurai is running, False otherwise
    """
    if not IS_WINDOWS:
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
    """
    Test connection to Redis/Memurai.
    
    Attempts to connect to the Redis server specified in the REDIS_URL
    environment variable.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
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
        
        # Use platform-specific terminology in log messages
        if IS_WINDOWS:
            logger.info(f"Successfully connected to Memurai (Redis for Windows) at {host}:{port}")
        else:
            logger.info(f"Successfully connected to Redis at {host}:{port}")
        
        return True
    except Exception as e:
        if IS_WINDOWS:
            logger.warning(f"Failed to connect to Memurai (Redis for Windows): {str(e)}")
        else:
            logger.warning(f"Failed to connect to Redis: {str(e)}")
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
    """
    Check if app.py exists and is executable.
    
    Returns:
        bool: True if app.py exists and is executable, False otherwise
    """
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


def restart_process(process_config, i, process, name, log_handle):
    """
    Restart a process that has terminated unexpectedly.
    
    Args:
        process_config (dict): Configuration for the process
        i (int): Index of the process in the processes list
        process (subprocess.Popen): The process object
        name (str): Name of the process
        log_handle (file): Log file handle
    """
    # Get the restart count for this process
    restart_count = restart_counts.get(name, 0)
    
    # Check if we've reached the maximum number of restart attempts
    if restart_count >= MAX_RESTART_ATTEMPTS:
        logger.error(f"{name} has failed {restart_count} times. Not restarting.")
        return
    
    # Increment the restart count
    restart_counts[name] = restart_count + 1
    
    # Log the restart
    logger.warning(f"{name} terminated unexpectedly (exit code {process.returncode}). Restarting...")
    
    # Close the log handle if it exists
    if log_handle:
        log_handle.write(f"\n\n{'=' * 80}\n")
        log_handle.write(f"PROCESS TERMINATED: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_handle.write(f"EXIT CODE: {process.returncode}\n")
        log_handle.write(f"RESTARTING PROCESS...\n")
        log_handle.write(f"{'=' * 80}\n\n")
        log_handle.close()
    
    # Wait a bit before restarting
    time.sleep(RESTART_DELAY)
    
    # Start the process again
    cmd = process_config.get("cmd", "")
    cwd = process_config.get("cwd", None)
    capture_output = process_config.get("capture_output", False)
    
    try:
        # Start the process again
        new_process = start_process(cmd, name, cwd, capture_output)
        
        # Update the processes list
        processes[i] = (new_process, name, log_handle)
    except Exception as e:
        logger.error(f"Failed to restart {name}: {e}")
        # Remove the process from the list
        processes.pop(i)


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
    
    # Check if app.py exists and is executable
    if not check_app_py():
        logger.error("Cannot start Flask app. Please check app.py for errors.")
        sys.exit(1)
    
    # Check if Node.js and npm are installed
    vue_available = False
    frontend_built = False
    if check_node_npm():
        # Always build the frontend first, regardless of mode
        logger.info("\n")
        logger.info("=" * 80)
        logger.info("FRONTEND BUILD PROCESS STARTING")
        logger.info("This may take a few minutes...")
        logger.info("=" * 80)
        logger.info("\n")
        
        build_success = build_vue_frontend()
        
        if build_success:
            frontend_built = True
            logger.info("Frontend build completed successfully!")
        else:
            logger.error("Frontend build failed! The application may not work correctly.")
            # Ask the user if they want to continue
            try:
                response = input("Do you want to continue starting the application anyway? (y/n): ")
                if response.lower() != 'y':
                    logger.info("Exiting as requested.")
                    sys.exit(1)
            except KeyboardInterrupt:
                logger.info("\nExiting as requested.")
                sys.exit(1)
        
        # We'll always use the built files, but we'll still start the Vue dev server if in dev mode
        # for hot reloading during development
        if VUE_DEV_MODE:
            vue_available = True
    else:
        logger.warning("Warning: Node.js or npm not found. Vue.js frontend will not be built or started.")
    
    # Verify that the frontend static files exist
    static_vue_dir = os.path.join('src', 'dashboard', 'static', 'vue')
    index_html_path = os.path.join(static_vue_dir, 'index.html')
    
    if not os.path.exists(index_html_path):
        logger.warning("=" * 80)
        logger.warning("WARNING: Frontend index.html not found!")
        logger.warning("The application may not work correctly.")
        logger.warning("=" * 80)
    
    # Define process configurations
    frontend_dir = os.path.join('src', 'dashboard', 'frontend')
    process_configs = {
        "Flask App": {
            "cmd": "python app.py",
            "capture_output": True
        },
        "Celery Worker": {
            "cmd": "celery -A src.celery_app worker --loglevel=info",
            "capture_output": True
        },
        "Celery Beat": {
            "cmd": "celery -A src.celery_app beat --loglevel=info --schedule=temp/celerybeat-schedule.db",
            "capture_output": True
        },
        "Flower": {
            "cmd": "celery -A src.celery_app flower --port=5555",
            "capture_output": True
        },
        "Vue.js Dev Server": {
            "cmd": "npm run serve",
            "cwd": frontend_dir,
            "capture_output": True
        }
    }
    
    # Start Flask app with output capture
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
    time.sleep(5)
    
    # Check if Flask app is still running
    if flask_process.poll() is not None:
        logger.error(f"Flask app failed to start (exit code {flask_process.returncode})")
        logger.error("Check the flask_app.log file in the logs directory for details")
        sys.exit(1)
    
    # Start Celery worker with output capture
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("STARTING CELERY WORKER")
    logger.info("=" * 80)
    
    start_process(
        process_configs["Celery Worker"]["cmd"],
        "Celery Worker",
        capture_output=process_configs["Celery Worker"]["capture_output"]
    )
    
    # Start Celery beat with output capture
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("STARTING CELERY BEAT")
    logger.info("=" * 80)
    
    start_process(
        process_configs["Celery Beat"]["cmd"],
        "Celery Beat",
        capture_output=process_configs["Celery Beat"]["capture_output"]
    )
    
    # Optional: Start Flower for monitoring with output capture
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("STARTING FLOWER MONITORING")
    logger.info("=" * 80)
    
    start_process(
        process_configs["Flower"]["cmd"],
        "Flower",
        capture_output=process_configs["Flower"]["capture_output"]
    )
    
    # Start Vue.js development server if in dev mode
    if VUE_DEV_MODE and vue_available:
        logger.info("\n")
        logger.info("=" * 80)
        logger.info("STARTING VUE.JS DEVELOPMENT SERVER")
        logger.info("=" * 80)
        
        start_process(
            process_configs["Vue.js Dev Server"]["cmd"],
            "Vue.js Dev Server",
            cwd=process_configs["Vue.js Dev Server"]["cwd"],
            capture_output=process_configs["Vue.js Dev Server"]["capture_output"]
        )
    
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("ALL SERVICES STARTED!")
    logger.info("=" * 80)
    logger.info(f"- Flask app running at http://{HOST}:{PORT}")
    logger.info("- Celery worker processing tasks")
    logger.info("- Celery beat scheduling tasks")
    logger.info("- Flower monitoring available at http://localhost:5555")
    if VUE_DEV_MODE and vue_available:
        logger.info("- Vue.js dev server running at http://localhost:8080")
    
    # Add frontend build status to the summary
    if frontend_built:
        logger.info("- Frontend was successfully built and deployed")
    else:
        logger.warning("- Frontend build was NOT successful - UI may not work correctly")
    
    logger.info("\nPress Ctrl+C to stop all services")
    
    try:
        # Keep the script running until interrupted
        while True:
            time.sleep(1)
            
            # Check if any process has terminated unexpectedly
            for i, (process, name, log_handle) in enumerate(processes):
                if process.poll() is not None:
                    # Get the process configuration
                    process_config = process_configs.get(name, {})
                    
                    # Only try to restart if we have a configuration for this process
                    if process_config:
                        restart_process(process_config, i, process, name, log_handle)
                    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        # cleanup will be called by atexit


if __name__ == "__main__":
    main() 