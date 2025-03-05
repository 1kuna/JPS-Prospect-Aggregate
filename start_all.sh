#!/bin/bash

echo "Starting JPS Prospect Aggregate with Celery..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Make the script executable if it's not already
chmod +x start_all.py

# Start the application
python start_all.py

# If the script exits, deactivate the virtual environment
deactivate 