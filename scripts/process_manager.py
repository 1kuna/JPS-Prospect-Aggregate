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
    3. Ensures any lingering Celery processes are properly terminated
    """
    global processes
    logger.info("Starting cleanup process...")
    
    # Make a copy of the processes list to avoid modification during iteration
    processes_to_cleanup = list(processes)
    
    # Terminate all processes
    logger.info(f"Terminating {len(processes_to_cleanup)} managed processes...")
    for i, (process, name, log_handle) in enumerate(processes_to_cleanup):
        try:
            logger.info(f"[{i+1}/{len(processes_to_cleanup)}] Terminating {name} (PID {process.pid})...")
            
            if process.poll() is None:  # Process is still running
                if IS_WINDOWS:
                    # On Windows, we need to use taskkill to terminate the process tree
                    logger.info(f"Using taskkill to terminate {name} on Windows")
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                                  check=False, capture_output=True)
                else:
                    # On Unix-like systems, we can use process groups or direct termination
                    try:
                        logger.info(f"Sending SIGTERM to {name}")
                        process.terminate()
                    except Exception as inner_e:
                        logger.warning(f"Error terminating process directly: {inner_e}")
                    
                # Give the process a moment to terminate gracefully
                logger.info(f"Waiting for {name} to terminate gracefully...")
                try:
                    process.wait(timeout=2)
                    logger.info(f"{name} terminated gracefully")
                except subprocess.TimeoutExpired:
                    # If the process doesn't terminate gracefully, force kill it
                    logger.warning(f"{name} did not terminate gracefully, force killing...")
                    try:
                        logger.info(f"Sending SIGKILL to {name}")
                        process.kill()
                    except Exception as inner_e:
                        logger.warning(f"Error killing process directly: {inner_e}")
            else:
                logger.info(f"{name} was already terminated (exit code {process.returncode})")
            
            # Log the termination
            if log_handle and not log_handle.closed:
                log_handle.write(f"\n\n{'=' * 80}\n")
                log_handle.write(f"PROCESS TERMINATED BY CLEANUP: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_handle.write(f"{'=' * 80}\n\n")
                log_handle.close()
                logger.info(f"Closed log file for {name}")
        except Exception as e:
            logger.error(f"Error terminating {name}: {str(e)}")
    
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
    processes = []
    
    logger.info("Cleanup complete")


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
    logger.info("Starting process monitoring...")
    try:
        while True:
            # Check each process
            for i, (process, name, log_handle) in enumerate(list(processes)):
                # Check if the process has terminated
                if process.poll() is not None:
                    # Process has terminated
                    logger.info(f"Process {name} (PID {process.pid}) has terminated with exit code {process.returncode}")
                    restart_process(process_configs.get(name, {}), i, process, name, log_handle)
            
            # Sleep for a bit to avoid high CPU usage
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