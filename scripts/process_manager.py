"""
Process management utilities for the JPS Prospect Aggregate application.

This module provides functions for starting, monitoring, and managing
subprocesses for the various components of the application.
"""

import os
import sys
import subprocess
import time
import signal
import logging
import datetime
from typing import List, Tuple, Dict, Any, Optional, IO
import traceback
import atexit
import psutil

# Add the parent directory to the Python path to import project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import logger
from src.utils.file_utils import ensure_directory

# Platform detection
IS_WINDOWS = sys.platform == 'win32'

# Constants
MAX_RESTART_ATTEMPTS = 3
RESTART_DELAY = 2

# Process tracking
processes = {}
restart_counts = {}

# Set up logger using the centralized utility
logger = logger.bind(name="scripts.process_manager")

def start_process(cmd: Any, name: str, cwd: Optional[str] = None, 
                 capture_output: bool = False, logs_dir: str = 'logs', env: Optional[Dict[str, str]] = None) -> subprocess.Popen:
    """
    Start a process with the specified command.
    
    Args:
        cmd: Command to run (list or string)
        name: A name for the process (for logging)
        cwd: The working directory for the process
        capture_output: Whether to capture and log the process output
        logs_dir: Directory to store log files
        env: Environment variables to pass to the subprocess
        
    Returns:
        The process object
    """
    global processes
    
    # Create log file for this process
    ensure_directory(logs_dir)
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
            process = subprocess.Popen(
                cmd,
                shell=True if isinstance(cmd, str) else False,
                cwd=cwd,
                stdout=log_handle if capture_output else None,
                stderr=log_handle if capture_output else None,
                text=True,
                env=env
            )
        else:
            # On Unix-like systems, we can use shell=False for better security
            if isinstance(cmd, str):
                process = subprocess.Popen(
                    cmd.split(),
                    cwd=cwd,
                    stdout=log_handle if capture_output else None,
                    stderr=log_handle if capture_output else None,
                    text=True,
                    env=env
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=log_handle if capture_output else None,
                    stderr=log_handle if capture_output else None,
                    text=True,
                    env=env
                )
        
        # Store the process, its name, and log handle for later cleanup
        processes[name] = (process, log_handle)
        
        # Initialize restart count for this process
        restart_counts[name] = 0
        
        # Log process ID
        logger.info(f"{name} started with PID {process.pid}")
        
        return process
    except Exception as e:
        logger.error(f"Failed to start {name}: {str(e)}")
        if log_handle:
            log_handle.write(f"\n\nERROR STARTING PROCESS: {str(e)}\n")
            log_handle.close()
        raise


def cleanup() -> None:
    """
    Clean up resources before exiting.
    
    This function:
    1. Terminates all running processes
    2. Closes all log file handles
    3. Ensures any lingering Celery processes are properly terminated
    """
    global processes
    logger.info("Starting cleanup process...")
    
    # Make a copy of the processes list to avoid modification during iteration
    processes_to_cleanup = list(processes.values())
    
    # Terminate all processes
    logger.info(f"Terminating {len(processes_to_cleanup)} managed processes...")
    for i, (process, log_handle) in enumerate(processes_to_cleanup):
        try:
            logger.info(f"[{i+1}/{len(processes_to_cleanup)}] Terminating process (PID {process.pid})...")
            
            # Close log handle to release file resources
            if log_handle is not None:
                try:
                    log_handle.flush()
                    log_handle.close()
                except Exception as e:
                    logger.warning(f"Error closing log handle: {str(e)}")
            
            # Terminate the process
            if process.poll() is None:  # Only if process is still running
                # Send SIGTERM (graceful shutdown)
                process.terminate()
                
                # Give the process time to terminate gracefully
                for _ in range(10):  # Wait up to 1 second
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                
                # If still running, force kill with SIGKILL
                if process.poll() is None:
                    logger.warning(f"Process PID {process.pid} did not respond to SIGTERM, sending SIGKILL...")
                    process.kill()

        except Exception as e:
            logger.error(f"Error terminating process: {str(e)}")
            logger.error(traceback.format_exc())
    
    # Additional cleanup to ensure Celery processes are terminated
    logger.info("Looking for lingering Celery processes...")
    try:
        if not IS_WINDOWS:
            # On Unix-like systems, find and kill any lingering Celery processes
            try:
                # Find celery worker PIDs
                ps_output = subprocess.check_output(
                    ["ps", "aux"], 
                    universal_newlines=True
                )
                celery_pids = []
                for line in ps_output.split("\n"):
                    if "celery" in line and ("worker" in line or "beat" in line or "flower" in line) and "python" in line:
                        try:
                            pid = int(line.split()[1])
                            celery_pids.append(pid)
                        except (IndexError, ValueError):
                            continue
                
                if celery_pids:
                    logger.info(f"Found {len(celery_pids)} lingering Celery processes: {celery_pids}")
                    
                    # Kill found Celery processes
                    for pid in celery_pids:
                        logger.info(f"Killing lingering Celery process with PID {pid}")
                        try:
                            # Send SIGTERM
                            os.kill(pid, signal.SIGTERM)
                            time.sleep(0.5)
                            
                            # Check if still running
                            try:
                                os.kill(pid, 0)  # 0 is a signal check
                                # Process still exists, try SIGKILL
                                logger.warning(f"Celery process {pid} did not terminate gracefully, force killing...")
                                os.kill(pid, signal.SIGKILL)
                            except OSError:
                                # Process no longer exists
                                logger.info(f"Celery process {pid} terminated successfully")
                        except OSError as e:
                            logger.warning(f"Error killing Celery process {pid}: {e}")
                else:
                    logger.info("No lingering Celery processes found")
            except Exception as e:
                logger.error(f"Error finding or killing Celery processes: {e}")
        else:
            # On Windows, use taskkill to find and kill any Celery processes
            logger.info("Using taskkill to terminate any lingering Celery processes on Windows")
            try:
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'celery.exe'], 
                    check=False, 
                    capture_output=True
                )
            except Exception as e:
                logger.error(f"Error killing Celery processes on Windows: {e}")
    except Exception as e:
        logger.error(f"Error in additional Celery cleanup: {e}")
    
    # Clear the processes list
    processes.clear()
    
    logger.info("Cleanup complete")


def restart_process(process_config: Dict[str, Any], name: str, process: subprocess.Popen, 
                 log_handle: Optional[IO]) -> None:
    """
    Restart a process that has terminated unexpectedly.
    
    Args:
        process_config: Process configuration
        name: Process name
        process: Process object
        log_handle: Log file handle
    """
    # Check if we've reached the maximum number of restart attempts
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
    if log_handle and not log_handle.closed:
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
        processes[name] = (new_process, log_handle)
    except Exception as e:
        logger.error(f"Failed to restart {name}: {e}")
        # Remove the process from the list
        processes.pop(name)


def monitor_processes(process_configs: Dict[str, Dict[str, Any]]) -> None:
    """
    Monitor running processes and restart them if they terminate unexpectedly.
    
    Args:
        process_configs: Dictionary of process configurations
    """
    logger.info("Starting process monitoring...")
    try:
        while True:
            # Check each process
            for name, (process, log_handle) in list(processes.items()):
                # Check if the process has terminated
                if process.poll() is not None:
                    # Process has terminated
                    logger.info(f"Process {name} (PID {process.pid}) has terminated with exit code {process.returncode}")
                    
                    # Get the process configuration
                    process_config = process_configs.get(name, {})
                    
                    # Restart the process
                    restart_process(process_config, name, process, log_handle)
            
            # Sleep to avoid high CPU usage
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received in monitor_processes. Initiating cleanup...")
        cleanup()
        logger.info("Cleanup completed after keyboard interrupt. Exiting...")
        # Use os._exit instead of sys.exit for more forceful termination
        logger.info("Using os._exit(0) to ensure termination")
        os._exit(0)
    except Exception as e:
        logger.error(f"Unexpected error in monitor_processes: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.info("Initiating cleanup due to error...")
        cleanup()
        logger.info("Cleanup completed after error. Exiting...")
        # Use os._exit instead of sys.exit for more forceful termination
        logger.info("Using os._exit(1) to ensure termination")
        os._exit(1) 