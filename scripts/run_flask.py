#!/usr/bin/env python3
"""
Utility script to start the Flask development server.

This script initializes and runs the Flask web application.
"""

import os
from app import create_app
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create Flask application instance
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    app.run(debug=True) 