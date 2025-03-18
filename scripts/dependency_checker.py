"""
Dependency checking utilities for the JPS Prospect Aggregate application.

This module provides functions for checking system dependencies such as
Redis/Memurai, Node.js, npm, and other required components.
"""

import os
import sys
import socket
import subprocess
import importlib.util
from typing import Tuple, Optional
from dotenv import load_dotenv
from src.utils.logger import logger
from src.utils.file_utils import ensure_directory

# Get component-specific logger
logger = logger.bind(name="dependency_checker")

# Platform detection
IS_WINDOWS = sys.platform == 'win32'


def test_redis_connection() -> bool:
    """
    Test connection to Redis/Memurai.
    
    Attempts to connect to the Redis server specified in the REDIS_URL
    environment variable.
    
    Returns:
        True if connection successful, False otherwise
    """
    # Get Redis URL from environment
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    try:
        # Parse Redis URL to get host and port
        if redis_url.startswith('redis://'):
            parts = redis_url.replace('redis://', '').split(':')
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


def check_memurai() -> bool:
    """
    Check if Memurai (Redis for Windows) is installed and running.
    
    Returns:
        True if Memurai is installed and running, False otherwise
    """
    if not IS_WINDOWS:
        logger.warning("check_memurai() called on non-Windows platform")
        return False
    
    try:
        # Check if Memurai service is running
        result = subprocess.run(
            ['sc', 'query', 'Memurai'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if "RUNNING" in result.stdout:
            logger.info("Memurai service is running")
            return True
        
        # If not running, try to start it
        logger.warning("Memurai service is not running. Attempting to start...")
        start_result = subprocess.run(
            ['sc', 'start', 'Memurai'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if "START_PENDING" in start_result.stdout or "RUNNING" in start_result.stdout:
            logger.info("Successfully started Memurai service")
            return True
        
        logger.error(f"Failed to start Memurai service: {start_result.stdout}")
        return False
    except Exception as e:
        logger.error(f"Error checking Memurai: {str(e)}")
        return False


def check_server_py() -> bool:
    """
    Check if server.py exists and is executable.
    
    Returns:
        True if server.py exists and is executable, False otherwise
    """
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'server.py')
    if not os.path.exists(app_path):
        logger.error(f"server.py not found at {app_path}")
        return False
    
    try:
        # Check if server.py is a valid Python file by importing it as a module
        # This is safer than executing it with --help
        spec = importlib.util.spec_from_file_location("server_module", app_path)
        if spec is None:
            logger.error(f"Failed to load server.py as a module")
            return False
            
        # Try to compile the module to check for syntax errors
        with open(app_path, 'r') as f:
            source = f.read()
        try:
            compile(source, app_path, 'exec')
            logger.info(f"server.py successfully validated")
            return True
        except SyntaxError as e:
            logger.error(f"server.py contains syntax errors: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Error checking server.py: {str(e)}")
        return False


def check_node_npm() -> bool:
    """
    Check if Node.js and npm are installed.
    
    Returns:
        True if Node.js and npm are installed, False otherwise
    """
    try:
        # Check Node.js
        node_result = subprocess.run(
            ['node', '--version'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if node_result.returncode != 0:
            logger.warning("Node.js is not installed or not in PATH")
            return False
        
        # Check npm
        npm_result = subprocess.run(
            ['npm', '--version'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if npm_result.returncode != 0:
            logger.warning("npm is not installed or not in PATH")
            return False
        
        logger.info(f"Node.js {node_result.stdout.strip()} and npm {npm_result.stdout.strip()} are installed")
        return True
    except Exception as e:
        logger.error(f"Error checking Node.js and npm: {str(e)}")
        return False


def frontend_needs_rebuild() -> bool:
    """
    Check if the frontend needs to be rebuilt.
    
    Returns:
        True if the frontend needs to be rebuilt, False otherwise
    """
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Check if the frontend directory exists
        frontend_dir = os.path.join(project_root, 'frontend-react')
        if not os.path.exists(frontend_dir):
            logger.warning("Frontend directory not found")
            return False
        
        # Check if the dist directory exists
        dist_dir = os.path.join(frontend_dir, 'dist')
        if not os.path.exists(dist_dir):
            logger.info("Frontend dist directory not found, rebuild needed")
            return True
        
        # Check if package.json is newer than the dist directory
        package_json = os.path.join(frontend_dir, 'package.json')
        if not os.path.exists(package_json):
            logger.warning("package.json not found")
            return False
        
        package_json_mtime = os.path.getmtime(package_json)
        dist_mtime = os.path.getmtime(dist_dir)
        
        if package_json_mtime > dist_mtime:
            logger.info("package.json is newer than dist directory, rebuild needed")
            return True
        
        # Check if src directory is newer than the dist directory
        src_dir = os.path.join(frontend_dir, 'src')
        if not os.path.exists(src_dir):
            logger.warning("src directory not found")
            return False
        
        # Check if any file in src is newer than the dist directory
        for root, _, files in os.walk(src_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_mtime = os.path.getmtime(file_path)
                
                if file_mtime > dist_mtime:
                    logger.info(f"File {file_path} is newer than dist directory, rebuild needed")
                    return True
        
        logger.info("Frontend does not need to be rebuilt")
        return False
    except Exception as e:
        logger.error(f"Error checking if frontend needs rebuild: {str(e)}")
        return False


def ensure_env_file() -> None:
    """
    Ensure .env file exists with Redis configuration.
    
    If .env file doesn't exist, create it from .env.example.
    If .env file exists but doesn't have Redis configuration, add it.
    """
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if .env file exists
    env_path = os.path.join(project_root, '.env')
    env_example_path = os.path.join(project_root, '.env.example')
    
    if not os.path.exists(env_path):
        # If .env doesn't exist, create it from .env.example if available
        if os.path.exists(env_example_path):
            logger.info(f".env file not found. Creating from .env.example...")
            with open(env_example_path, 'r') as src, open(env_path, 'w') as dst:
                dst.write(src.read())
            logger.info(f"Created .env file from .env.example")
        else:
            # If .env.example doesn't exist, create a minimal .env file
            logger.info(f"Neither .env nor .env.example found. Creating minimal .env file...")
            with open(env_path, 'w') as f:
                f.write("# Created by run_app.py\n")
                f.write("REDIS_URL=redis://localhost:6379/0\n")
                f.write("CELERY_BROKER_URL=redis://localhost:6379/0\n")
                f.write("CELERY_RESULT_BACKEND=redis://localhost:6379/0\n")
            logger.info(f"Created minimal .env file")
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
                f.write("\n# Added by run_app.py\n")
                for config in missing_configs:
                    f.write(f"{config}redis://localhost:6379/0\n")
            
            logger.info("Updated .env file with Redis configuration")
    
    # Reload environment variables
    load_dotenv(env_path, override=True) 