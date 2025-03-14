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

# Platform detection
IS_WINDOWS = sys.platform == 'win32'

# Constants
MAX_RESTART_ATTEMPTS = 3
RESTART_DELAY = 2

# Process tracking
processes = []
restart_counts = {}

# Set up logging
logger = logging.getLogger(__name__)


def start_process(cmd: Any, name: str, cwd: Optional[str] = None, 
                 capture_output: bool = False, logs_dir: str = 'logs', env: Optional[Dict[str, str]] = None) -> subprocess.Popen:
    """
    Start a subprocess and return the process object.
    
    Args:
        cmd: The command to run, either as a string or list of arguments
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
    os.makedirs(logs_dir, exist_ok=True)
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
        processes.append((process, name, log_handle))
        
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
            logger.error(f"Error terminating {name}: {str(e)}")


def restart_process(process_config: Dict[str, Any], i: int, 
                   process: subprocess.Popen, name: str, 
                   log_handle: Optional[IO]) -> None:
    """
    Restart a process that has terminated unexpectedly.
    
    Args:
        process_config: Configuration for the process
        i: Index of the process in the processes list
        process: The process object
        name: Name of the process
        log_handle: Log file handle
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
        processes[i] = (new_process, name, log_handle)
    except Exception as e:
        logger.error(f"Failed to restart {name}: {e}")
        # Remove the process from the list
        processes.pop(i)


def monitor_processes(process_configs: Dict[str, Dict[str, Any]]) -> None:
    """
    Monitor running processes and restart them if they terminate unexpectedly.
    
    Args:
        process_configs: Dictionary of process configurations
    """
    try:
        while True:
            # Check each process
            for i, (process, name, log_handle) in enumerate(list(processes)):
                # Check if the process has terminated
                if process.poll() is not None:
                    # Process has terminated
                    restart_process(process_configs.get(name, {}), i, process, name, log_handle)
            
            # Sleep for a bit to avoid high CPU usage
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
        cleanup() 