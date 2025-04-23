"""
Application Factory Pattern for Flask app.

This module creates and configures the Flask application.
"""

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from app.config import config_by_name as config
from app.database import db  # Import the db instance from database.py
# Logging is configured automatically on import of app.utils.logger

# Setup logging as early as possible
# Logging is configured automatically on import of app.utils.logger
# setup_logging()

def create_app(config_name='default'):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    # config[config_name].init_app(app) # Config classes don't have init_app

    # Initialize extensions
    CORS(app, resources={r'/api/*': {'origins': '*'}}) # Configure origins properly for production
    db.init_app(app) # Initialize SQLAlchemy with the app

    # Register blueprints
    from app.api import api as api_blueprint
    app.register_blueprint(api_blueprint)

    # Register error handlers if defined in api.errors
    try:
        from .api.errors import register_error_handlers
        register_error_handlers(app)
    except ImportError:
        pass # No custom error handlers defined or file doesn't exist

    return app
