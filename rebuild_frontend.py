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
PROJECT_ROOT = Path(__file__).resolve().parent

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
    
    print("Frontend build completed successfully.")
    return True

def copy_build_to_static():
    """Copy the build files to the Flask static directory."""
    print("Copying build files to Flask static directory...")
    
    # Path to the build directory
    build_dir = FRONTEND_DIR / "dist"
    
    # Check if the build directory exists
    if not build_dir.exists():
        print(f"Error: Build directory not found at {build_dir}")
        return False
    
    # Create the static directory if it doesn't exist
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    # Create a 'react' directory in the static directory
    react_static_dir = STATIC_DIR / "react"
    os.makedirs(react_static_dir, exist_ok=True)
    
    # Copy the build files to the static directory
    try:
        # Copy static assets
        if (build_dir / "static").exists():
            if (react_static_dir / "static").exists():
                shutil.rmtree(react_static_dir / "static")
            shutil.copytree(build_dir / "static", react_static_dir / "static")
        
        # Copy index.html
        if (build_dir / "index.html").exists():
            shutil.copy2(build_dir / "index.html", react_static_dir / "index.html")
        
        # Copy any other files at the root level
        for item in build_dir.glob("*"):
            if item.is_file() and item.name != "index.html":
                shutil.copy2(item, react_static_dir / item.name)
        
        print("Build files copied successfully.")
        return True
    except Exception as e:
        print(f"Error copying build files: {e}")
        return False

def main():
    """Main function."""
    if not build_frontend():
        sys.exit(1)
    
    if not copy_build_to_static():
        sys.exit(1)
    
    print("Frontend rebuild completed successfully.")

if __name__ == "__main__":
    main() 