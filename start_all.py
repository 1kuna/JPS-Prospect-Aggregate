#!/usr/bin/env python
"""
Start script for JPS Prospect Aggregate application.
This script starts the Flask app, Celery worker, and Celery beat processes.
"""

import os
import sys
import subprocess
import time
import signal
import atexit
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration from environment
HOST = os.getenv('HOST', '0.0.0.0')
PORT = os.getenv('PORT', '5000')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Process tracking
processes = []

def start_process(cmd, name):
    """Start a subprocess and return the process object."""
    print(f"Starting {name}...")
    if sys.platform == 'win32':
        # Windows needs shell=True and different creation flags
        process = subprocess.Popen(
            cmd,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        # Unix-like systems
        process = subprocess.Popen(
            cmd,
            shell=True,
            preexec_fn=os.setsid
        )
    processes.append((process, name))
    print(f"{name} started with PID {process.pid}")
    return process

def cleanup():
    """Terminate all processes on exit."""
    print("\nShutting down all processes...")
    for process, name in processes:
        print(f"Terminating {name} (PID: {process.pid})...")
        if sys.platform == 'win32':
            # Windows
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
        else:
            # Unix-like systems
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except OSError:
                pass
    print("All processes terminated.")

def main():
    """Start all components of the application."""
    # Register cleanup handler
    atexit.register(cleanup)
    
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
    
    print("\nAll services started!")
    print(f"- Flask app running at http://{HOST}:{PORT}")
    print("- Celery worker processing tasks")
    print("- Celery beat scheduling tasks")
    print("- Flower monitoring available at http://localhost:5555")
    print("\nPress Ctrl+C to stop all services")
    
    try:
        # Keep the script running until interrupted
        while True:
            time.sleep(1)
            
            # Check if any process has terminated unexpectedly
            for i, (process, name) in enumerate(processes):
                if process.poll() is not None:
                    print(f"{name} terminated unexpectedly with code {process.returncode}")
                    # Restart the process
                    if name == "Flask App":
                        new_process = start_process(flask_cmd, name)
                    elif name == "Celery Worker":
                        new_process = start_process(worker_cmd, name)
                    elif name == "Celery Beat":
                        new_process = start_process(beat_cmd, name)
                    elif name == "Flower":
                        new_process = start_process(flower_cmd, name)
                    
                    # Replace the terminated process in the list
                    processes[i] = (new_process, name)
                    
    except KeyboardInterrupt:
        print("Keyboard interrupt received, shutting down...")
        # cleanup will be called by atexit

if __name__ == "__main__":
    main() 