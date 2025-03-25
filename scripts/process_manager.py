#!/usr/bin/env python
"""
Wrapper script to start the JPS Prospect Aggregate application.
This script simply calls the main run_app.py script in the scripts directory.
"""

import os
import sys
import signal
import subprocess
import time
import atexit

# Global variable to track the child process
child_process = None

def cleanup_child():
    """Clean up the child process on exit."""
    global child_process
    if child_process and child_process.poll() is None:
        print("Cleaning up child process on wrapper exit...")
        try:
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(child_process.pid)], 
                              check=False, capture_output=True)
            else:
                # Try SIGTERM first
                print(f"Sending SIGTERM to child process PID {child_process.pid}")
                child_process.terminate()
                
                # Wait a bit for graceful termination
                for i in range(5):
                    if child_process.poll() is not None:
                        print(f"Child process exited with code {child_process.returncode}")
                        return
                    time.sleep(0.5)
                
                # If still running, use SIGKILL
                if child_process.poll() is None:
                    print(f"Child process did not terminate gracefully, sending SIGKILL...")
                    child_process.kill()
        except Exception as e:
            print(f"Error terminating child process: {e}")

def signal_handler(sig, frame):
    """
    Handle signals by passing them to the child process.
    This ensures clean shutdown of the application.
    """
    global child_process
    if child_process and child_process.poll() is None:
        print(f"Received signal {sig}, forwarding to child process...")
        try:
            # On Windows, there's no os.kill that accepts signal
            if sys.platform == 'win32':
                # On Windows, we need to use taskkill to terminate the process tree
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(child_process.pid)], 
                              check=False, capture_output=True)
            else:
                # Send the signal to the child process
                os.kill(child_process.pid, sig)
            
            print("Waiting for child process to complete cleanup (this may take up to 10 seconds)...")
            # Wait for cleanup to complete (10 seconds)
            for i in range(10):
                if child_process.poll() is not None:
                    print(f"Child process exited with code {child_process.returncode}")
                    break
                time.sleep(1)
                if i % 5 == 4:  # Show status every 5 seconds
                    print(f"Still waiting for child process to exit... ({i+1}s)")
            
            # If still running after timeout, force kill
            if child_process.poll() is None:
                print("Child process did not terminate in time, force killing...")
                child_process.kill()
                
                # Wait a bit more to see if kill worked
                time.sleep(1)
                if child_process.poll() is None:
                    print("WARNING: Child process is not responding to kill. Forcing exit anyway.")
        except Exception as e:
            print(f"Error handling signal: {e}")
    
    # Force exit here to avoid any hanging
    print("Exiting wrapper application...")
    os._exit(0)

def main():
    """Run the run_app.py script in the scripts directory."""
    global child_process
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'run_app.py')
    
    # Check if the script exists
    if not os.path.exists(script_path):
        print(f"Error: Could not find run_app.py at {script_path}")
        return 1
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Register cleanup handler
    atexit.register(cleanup_child)
    
    # Run the script with the same arguments
    try:
        print(f"Starting child process: {sys.executable} {script_path}")
        child_process = subprocess.Popen(
            [sys.executable, script_path] + sys.argv[1:],
            # Ensure child process output is visible
            stdout=None,
            stderr=None
        )
        
        # Wait for the process to complete
        return_code = child_process.wait()
        print(f"Child process exited with code {return_code}")
        return return_code
    except KeyboardInterrupt:
        # This should be caught by the signal handler, but just in case
        print("Keyboard interrupt received in wrapper. Terminating child...")
        if child_process and child_process.poll() is None:
            try:
                child_process.terminate()
                try:
                    child_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("Force killing child process...")
                    child_process.kill()
            except Exception as e:
                print(f"Error terminating child process: {e}")
        return 1
    except Exception as e:
        print(f"Error running child process: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    # Use sys.exit here since we've already cleaned up the child process
    sys.exit(exit_code) 