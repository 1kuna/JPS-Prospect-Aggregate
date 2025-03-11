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
    python start_all.py

Requirements:
    - Python 3.10+
    - Redis (Unix) or Memurai (Windows)
    - Node.js and npm (for React frontend)
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
REACT_DEV_MODE = os.getenv('REACT_DEV_MODE', 'True').lower() == 'true'
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
        cmd (str or list): The command to run, either as a string or list of arguments
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
    
    # Format command for logging
    cmd_str = cmd if isinstance(cmd, str) else ' '.join(cmd)
    log_handle.write(f"COMMAND: {cmd_str}\n")
    
    if cwd:
        log_handle.write(f"WORKING DIRECTORY: {cwd}\n")
    log_handle.write(f"{'=' * 80}\n\n")
    log_handle.flush()
    
    # Start the process
    logger.info(f"Starting {name}...")
    
    try:
        if IS_WINDOWS:
            # On Windows, we need to use shell=True to run commands with arguments
            if isinstance(cmd, str):
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=cwd,
                    stdout=log_handle if capture_output else None,
                    stderr=log_handle if capture_output else None,
                    text=True
                )
            else:
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
            if isinstance(cmd, str):
                process = subprocess.Popen(
                    cmd.split(),
                    cwd=cwd,
                    stdout=log_handle if capture_output else None,
                    stderr=log_handle if capture_output else None,
                    text=True
                )
            else:
                process = subprocess.Popen(
                    cmd,
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
        logger.warning("Node.js or npm not found. Please install Node.js and npm to run the React frontend.")
        return False


def frontend_needs_rebuild():
    """
    Check if the frontend needs to be rebuilt by comparing file modification times.
    
    Returns:
        bool: True if frontend needs to be rebuilt, False otherwise
    """
    # Define all directories and files that should trigger a rebuild when modified
    react_dir = os.path.join('frontend-react')
    react_src_dir = os.path.join(react_dir, 'src')
    react_build_dir = os.path.join(react_dir, 'dist')
    
    # Important config files that should trigger a rebuild
    important_files = [
        os.path.join(react_dir, 'package.json'),
        os.path.join(react_dir, 'package-lock.json'),
        os.path.join(react_dir, 'vite.config.ts'),
        os.path.join(react_dir, 'tsconfig.json'),
        os.path.join(react_dir, '.env')
    ]
    
    # If React build directory doesn't exist, rebuild is needed
    if not os.path.exists(react_build_dir):
        logger.info("React build directory doesn't exist. Frontend rebuild needed.")
        return True
    
    # If index.html doesn't exist in React build directory, rebuild is needed
    index_html_path = os.path.join(react_build_dir, 'index.html')
    if not os.path.exists(index_html_path):
        logger.info("index.html doesn't exist in React build directory. Frontend rebuild needed.")
        return True
    
    # Get the most recent modification time of any file in the frontend source directory
    latest_frontend_mtime = 0
    latest_file = ""
    
    # Check all files in the src directory
    for root, _, files in os.walk(react_src_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                mtime = os.path.getmtime(file_path)
                if mtime > latest_frontend_mtime:
                    latest_frontend_mtime = mtime
                    latest_file = file_path
            except OSError as e:
                logger.warning(f"Error checking file {file_path}: {e}")
    
    # Check important config files
    for file_path in important_files:
        if os.path.exists(file_path):
            try:
                mtime = os.path.getmtime(file_path)
                if mtime > latest_frontend_mtime:
                    latest_frontend_mtime = mtime
                    latest_file = file_path
            except OSError as e:
                logger.warning(f"Error checking file {file_path}: {e}")
    
    # Get the most recent modification time of any file in the React build directory
    latest_static_mtime = 0
    if os.path.exists(react_build_dir):
        for root, _, files in os.walk(react_build_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(file_path)
                    if mtime > latest_static_mtime:
                        latest_static_mtime = mtime
                except OSError as e:
                    logger.warning(f"Error checking file {file_path}: {e}")
    
    # If frontend files are newer than static files, rebuild is needed
    if latest_frontend_mtime > latest_static_mtime:
        logger.info(f"Frontend files modified at {datetime.datetime.fromtimestamp(latest_frontend_mtime)}")
        logger.info(f"Most recently modified file: {latest_file}")
        logger.info(f"Static files last updated at {datetime.datetime.fromtimestamp(latest_static_mtime)}")
        logger.info("Frontend files are newer than static files. Rebuild needed.")
        return True
    
    logger.info("Frontend files are up to date. No rebuild needed.")
    return False


def build_react_frontend():
    """
    Build the React frontend for production.
    
    This function installs dependencies if needed and builds the React
    application for production deployment.
    
    Returns:
        bool: True if build was successful, False otherwise
    """
    react_dir = os.path.join('frontend-react')
    react_build_dir = os.path.join('frontend-react', 'dist')
    
    # Check if frontend needs to be rebuilt
    rebuild_needed = frontend_needs_rebuild()
    
    # Force rebuild if REACT_FORCE_REBUILD environment variable is set
    force_rebuild = os.getenv('REACT_FORCE_REBUILD', 'False').lower() == 'true'
    if force_rebuild:
        logger.info("REACT_FORCE_REBUILD is set to true. Forcing frontend rebuild.")
        rebuild_needed = True
    
    if not rebuild_needed:
        logger.info("Frontend is up to date. Skipping build.")
        return True
    
    # Print a clear header for the frontend build process
    logger.info("=" * 80)
    logger.info("STARTING REACT FRONTEND BUILD")
    logger.info("=" * 80)
    
    # Always run npm install to ensure dependencies are up to date
    logger.info("Step 1/4: Installing/updating React dependencies...")
    try:
        npm_install_process = subprocess.run(
            ['npm', 'install'], 
            cwd=react_dir, 
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
        
        # Build the React app for production
        logger.info("Step 2/4: Building React frontend for production...")
        
        # Set NODE_ENV to production to ensure consistent builds
        build_env = os.environ.copy()
        build_env['NODE_ENV'] = 'production'
        
        # Run the build process and capture output
        build_process = subprocess.run(
            ['npm', 'run', 'build'], 
            cwd=react_dir, 
            check=False,
            capture_output=True,
            text=True,
            env=build_env
        )
        
        # Check if build was successful
        if build_process.returncode != 0:
            logger.error(f"React build failed with code {build_process.returncode}")
            logger.error("Build error details:")
            
            # Display the full error output for better debugging
            logger.error("=== STDOUT ===")
            for line in build_process.stdout.splitlines():
                logger.error(f"  {line}")
                
            logger.error("=== STDERR ===")
            for line in build_process.stderr.splitlines():
                logger.error(f"  {line}")
                
            return False
        else:
            # Log build success and some output details
            logger.info("React build completed successfully")
            
            # Check for warnings in the output
            if "warning" in build_process.stdout.lower():
                logger.warning("Build completed with warnings:")
                
                # Extract and display ESLint warnings
                eslint_warnings = []
                in_eslint_section = False
                
                for line in build_process.stdout.splitlines():
                    if "[eslint]" in line:
                        in_eslint_section = True
                        eslint_warnings.append(line)
                    elif in_eslint_section and line.strip():
                        eslint_warnings.append(line)
                    elif in_eslint_section and not line.strip():
                        in_eslint_section = False
                
                if eslint_warnings:
                    logger.warning("ESLint warnings found (these won't prevent the build):")
                    for warning in eslint_warnings[:10]:  # Show only first 10 warnings
                        logger.warning(f"  {warning}")
                    
                    if len(eslint_warnings) > 10:
                        logger.warning(f"  ... and {len(eslint_warnings) - 10} more warnings")
            
            # Extract and log important parts of the build output
            output_lines = build_process.stdout.splitlines()
            build_summary = []
            
            # Find build summary section (file sizes)
            in_summary = False
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
        
        # Step 3: Verify the build output
        logger.info("Step 3/4: Verifying build output...")
        
        # Check if index.html exists in the React build directory
        index_html_path = os.path.join(react_build_dir, 'index.html')
        
        if os.path.exists(index_html_path):
            # Count files in the React build directory
            total_files = sum([len(files) for _, _, files in os.walk(react_build_dir)])
            
            logger.info(f"Found {total_files} files in {react_build_dir}")
            logger.info("=" * 80)
            logger.info("REACT FRONTEND BUILD COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            return True
        else:
            logger.error(f"index.html not found in {react_build_dir} after build!")
            logger.error("=" * 80)
            logger.error("REACT FRONTEND BUILD FAILED")
            logger.error("=" * 80)
            return False
        
    except subprocess.SubprocessError as e:
        logger.error(f"Error building React frontend: {e}")
        logger.error("=" * 80)
        logger.error("REACT FRONTEND BUILD FAILED")
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

# React settings
REACT_DEV_MODE=True  # Set to False for production
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


def check_server_py():
    """
    Check if server.py exists and is executable.
    
    Returns:
        bool: True if server.py exists and is executable, False otherwise
    """
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.py')
    if not os.path.exists(app_path):
        logger.error(f"server.py not found at {app_path}")
        return False
    
    try:
        # Try to run server.py with --help to see if it's executable
        result = subprocess.run([sys.executable, app_path, "--help"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"server.py exists but may have errors: {result.stderr}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking server.py: {str(e)}")
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
    
    # Check if server.py exists and is executable
    if not check_server_py():
        logger.error("Cannot start Flask app. Please check server.py for errors.")
        sys.exit(1)
    
    # Check if Node.js and npm are installed
    react_available = False
    frontend_built = False
    if check_node_npm():
        # Check if frontend needs to be rebuilt
        rebuild_needed = frontend_needs_rebuild()
        
        # Set REACT_FORCE_REBUILD if needed
        if os.getenv('REACT_FORCE_REBUILD') is None and rebuild_needed:
            os.environ['REACT_FORCE_REBUILD'] = 'true'
            logger.info("Setting REACT_FORCE_REBUILD=true because frontend changes were detected")
        
        # Always build the frontend first, regardless of mode
        logger.info("\n")
        logger.info("=" * 80)
        logger.info("FRONTEND BUILD PROCESS STARTING")
        logger.info("This may take a few minutes...")
        logger.info("=" * 80)
        logger.info("\n")
        
        build_success = build_react_frontend()
        
        if build_success:
            frontend_built = True
            logger.info("Frontend build completed successfully!")
        else:
            logger.error("Frontend build failed! The application may not work correctly.")
            logger.error("Please check the logs above for errors or other build issues.")
            logger.error("Common issues:")
            logger.error("1. ESLint errors in your TypeScript/React files")
            logger.error("2. Missing dependencies")
            logger.error("3. Syntax errors in your TypeScript/React code")
            
            logger.error("\nTo fix ESLint errors, you can:")
            logger.error("1. Fix the issues manually in the source files")
            logger.error("2. Run 'cd frontend-react && npm run lint --fix' to attempt automatic fixes")
            logger.error("3. Add '// eslint-disable-next-line' comments to ignore specific warnings")
            
            # Ask the user if they want to continue
            try:
                response = input("Do you want to continue starting the application anyway? (y/n): ")
                if response.lower() != 'y':
                    logger.info("Exiting as requested.")
                    sys.exit(1)
            except KeyboardInterrupt:
                logger.info("\nExiting as requested.")
                sys.exit(1)
        
        # We'll start the React dev server if in dev mode
        if REACT_DEV_MODE:
            react_available = True
    else:
        logger.warning("Warning: Node.js or npm not found. React frontend will not be built or started.")
    
    # Verify that the frontend static files exist
    react_build_dir = os.path.join('frontend-react', 'dist')
    index_html_path = os.path.join(react_build_dir, 'index.html')
    
    if not os.path.exists(index_html_path):
        logger.warning("WARNING: Frontend index.html not found!")
        logger.warning("The application may not work correctly.")
    
    # Define process configurations
    react_dir = os.path.join('frontend-react')
    process_configs = {
        "Flask App": {
            "cmd": ["python", "-m", "flask", "run", "--host", HOST, "--port", PORT],
            "capture_output": True
        },
        "Celery Worker": {
            "cmd": ["celery", "-A", "app.celery", "worker", "--loglevel=info"],
            "capture_output": True
        },
        "Celery Beat": {
            "cmd": ["celery", "-A", "app.celery", "beat", "--loglevel=info"],
            "capture_output": True
        },
        "Flower": {
            "cmd": ["celery", "-A", "app.celery", "flower", "--port=5555"],
            "capture_output": True
        },
        "React Dev Server": {
            "cmd": ["npm", "run", "dev"],
            "cwd": react_dir,
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
    
    # Start React development server if in dev mode
    if REACT_DEV_MODE and react_available:
        logger.info("\n")
        logger.info("=" * 80)
        logger.info("STARTING REACT DEVELOPMENT SERVER")
        logger.info("=" * 80)
        
        start_process(
            process_configs["React Dev Server"]["cmd"],
            "React Dev Server",
            cwd=process_configs["React Dev Server"]["cwd"],
            capture_output=process_configs["React Dev Server"]["capture_output"]
        )
    
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("ALL SERVICES STARTED!")
    logger.info("=" * 80)
    logger.info(f"- Flask app running at http://{HOST}:{PORT}")
    logger.info("- Celery worker processing tasks")
    logger.info("- Celery beat scheduling tasks")
    logger.info("- Flower monitoring available at http://localhost:5555")
    if REACT_DEV_MODE and react_available:
        logger.info("- React dev server running at http://localhost:3000")
    
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