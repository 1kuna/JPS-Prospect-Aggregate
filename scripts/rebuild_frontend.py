#!/usr/bin/env python3
"""
Script to rebuild the frontend and copy the build files to the static directory.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Get the absolute path of the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Path to the React frontend directory
FRONTEND_DIR = PROJECT_ROOT / "frontend-react"

# Path to the Flask static directory
STATIC_DIR = PROJECT_ROOT / "src" / "dashboard" / "static"

def run_command(command, cwd=None):
    """Run a shell command and print the output."""
    print(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(e.stderr)
        return False

def build_frontend():
    """Build the React frontend."""
    print("Building React frontend...")
    
    # Check if the frontend directory exists
    if not FRONTEND_DIR.exists():
        print(f"Error: Frontend directory not found at {FRONTEND_DIR}")
        return False
    
    # Install dependencies
    if not run_command(["npm", "install"], cwd=FRONTEND_DIR):
        return False
    
    # Build the frontend
    if not run_command(["npm", "run", "build"], cwd=FRONTEND_DIR):
        return False
    
    print("React frontend built successfully.")
    return True

def copy_to_static():
    """Copy the built frontend to the Flask static directory."""
    print("Copying built frontend to Flask static directory...")
    
    # Path to the React build directory
    build_dir = FRONTEND_DIR / "dist"
    
    # Check if the build directory exists
    if not build_dir.exists():
        print(f"Error: Build directory not found at {build_dir}")
        return False
    
    # Create the react directory in the static directory if it doesn't exist
    react_static_dir = STATIC_DIR / "react"
    react_static_dir.mkdir(exist_ok=True)
    
    # Remove existing files in the react static directory
    for item in react_static_dir.glob("*"):
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    
    # Copy all files from the build directory to the react static directory
    for item in build_dir.glob("*"):
        if item.is_file():
            shutil.copy2(item, react_static_dir)
        elif item.is_dir():
            shutil.copytree(item, react_static_dir / item.name, dirs_exist_ok=True)
    
    print("Frontend files copied successfully.")
    return True

def main():
    """Main function."""
    # Build the frontend
    if not build_frontend():
        print("Error: Failed to build frontend.")
        return 1
    
    # Copy the built frontend to the Flask static directory
    if not copy_to_static():
        print("Error: Failed to copy frontend files.")
        return 1
    
    print("Frontend rebuild completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 