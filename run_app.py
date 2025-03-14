#!/usr/bin/env python
"""
Wrapper script to start the JPS Prospect Aggregate application.
This script simply calls the main run_app.py script in the scripts directory.
"""

import os
import sys
import subprocess

def main():
    """Run the run_app.py script in the scripts directory."""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'run_app.py')
    
    # Check if the script exists
    if not os.path.exists(script_path):
        print(f"Error: Could not find run_app.py at {script_path}")
        return 1
    
    # Run the script with the same arguments
    process = subprocess.run([sys.executable, script_path] + sys.argv[1:])
    return process.returncode

if __name__ == "__main__":
    sys.exit(main()) 