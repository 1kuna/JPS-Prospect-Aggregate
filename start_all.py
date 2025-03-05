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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration from environment
HOST = os.getenv('HOST', '0.0.0.0')
PORT = os.getenv('PORT', '5000')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
VUE_DEV_MODE = os.getenv('VUE_DEV_MODE', 'True').lower() == 'true'

# Process tracking
processes = []

def start_process(cmd, name, cwd=None):
    """Start a subprocess and return the process object."""
    print(f"Starting {name}...")
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

def check_node_npm():
    """Check if Node.js and npm are installed."""
    try:
        # Check Node.js
        node_version = subprocess.check_output(['node', '--version'], text=True).strip()
        print(f"Node.js version: {node_version}")
        
        # Check npm
        npm_version = subprocess.check_output(['npm', '--version'], text=True).strip()
        print(f"npm version: {npm_version}")
        
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Node.js or npm not found. Please install Node.js and npm to run the Vue.js frontend.")
        return False

def build_vue_frontend():
    """Build the Vue.js frontend for production."""
    frontend_dir = os.path.join('src', 'dashboard', 'frontend')
    
    # Check if node_modules exists, if not run npm install
    if not os.path.exists(os.path.join(frontend_dir, 'node_modules')):
        print("Installing Vue.js dependencies...")
        subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
    
    # Build the Vue.js app
    print("Building Vue.js frontend for production...")
    subprocess.run(['npm', 'run', 'build'], cwd=frontend_dir, check=True)
    
    # Ensure the static/vue directory exists
    static_vue_dir = os.path.join('src', 'dashboard', 'static', 'vue')
    os.makedirs(static_vue_dir, exist_ok=True)
    
    print("Vue.js frontend built successfully!")

def main():
    """Start all components of the application."""
    # Register cleanup handler
    atexit.register(cleanup)
    
    # Check if Node.js and npm are installed if Vue dev mode is enabled
    if VUE_DEV_MODE:
        if not check_node_npm():
            print("Warning: Vue.js frontend will not be started.")
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
    
    print("\nAll services started!")
    print(f"- Flask app running at http://{HOST}:{PORT}")
    print("- Celery worker processing tasks")
    print("- Celery beat scheduling tasks")
    print("- Flower monitoring available at http://localhost:5555")
    if VUE_DEV_MODE and vue_available:
        print("- Vue.js dev server running at http://localhost:8080")
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
                    elif name == "Vue.js Dev Server" and VUE_DEV_MODE and vue_available:
                        frontend_dir = os.path.join('src', 'dashboard', 'frontend')
                        new_process = start_process(vue_cmd, name, cwd=frontend_dir)
                    
                    # Replace the terminated process in the list
                    processes[i] = (new_process, name)
                    
    except KeyboardInterrupt:
        print("Keyboard interrupt received, shutting down...")
        # cleanup will be called by atexit

if __name__ == "__main__":
    main() 