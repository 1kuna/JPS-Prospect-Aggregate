#!/usr/bin/env python3
"""
Main entry point for the JPS Prospect Aggregate application.
This script initializes and runs both the Flask web application and Celery worker.
"""

import os
from app import create_app, create_celery_app
from app.config import Config

def main():
    """Initialize and run the application."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Create Flask application
    app = create_app()
    
    # Create Celery application
    celery_app = create_celery_app(app)

    # Run the application
    if __name__ == '__main__':
        app.run(
            host=Config.FLASK_HOST,
            port=Config.FLASK_PORT,
            debug=Config.DEBUG
        )

if __name__ == '__main__':
    main() 