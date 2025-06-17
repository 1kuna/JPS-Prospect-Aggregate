"""
Application Factory Pattern for Flask app.

This module creates and configures the Flask application.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from app.config import active_config # Import active_config
from app.database import db  # Import the db instance from database.py
from app.database.user_db import init_user_db  # Import user database initialization
from app.middleware.maintenance import maintenance_middleware
# Logging is configured automatically on import of app.utils.logger

# Setup logging as early as possible
# Logging is configured automatically on import of app.utils.logger

def create_app(config_name='default'): # config_name is no longer used but kept for compatibility
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config.from_object(active_config) # Use active_config directly

    # Initialize extensions
    CORS(app, resources={r'/api/*': {'origins': '*'}}) # Configure origins properly for production
    
    # Configure user database bind BEFORE initializing db
    user_db = init_user_db(app) # Configure user database binds
    
    # Now initialize SQLAlchemy with the app (after binds are configured)
    db.init_app(app) # Initialize SQLAlchemy with the app
    
    # Initialize Flask-Migrate for business database
    Migrate(app, db)

    # Import models here to ensure they are registered with SQLAlchemy
    from app.database import models # noqa
    from app.database import user_models # noqa

    # Register blueprints
    from app.api.main import main_bp
    from app.api.data_sources import data_sources_bp
    from app.api.scrapers import scrapers_bp
    from app.api.prospects import prospects_bp # Import the new blueprint
    from app.api.llm_processing import llm_bp  # Import LLM processing blueprint
    from app.api.admin import admin_bp  # Import admin blueprint
    from app.api.auth import auth_bp  # Import auth blueprint
    from app.api.decisions import decisions_bp  # Import decisions blueprint
    from app.web.routes import main as web_main_bp # Import the web blueprint

    app.register_blueprint(web_main_bp) # Register the web blueprint
    app.register_blueprint(main_bp, url_prefix='/api')
    app.register_blueprint(data_sources_bp, url_prefix='/api/data-sources')
    app.register_blueprint(scrapers_bp, url_prefix='/api/data-sources') # Scraper routes are under data-sources
    app.register_blueprint(prospects_bp) # Register the new blueprint (uses url_prefix from its definition)
    app.register_blueprint(llm_bp)  # Register LLM processing blueprint (uses url_prefix='/api/llm' from its definition)
    app.register_blueprint(admin_bp)  # Register admin blueprint
    app.register_blueprint(auth_bp)  # Register auth blueprint
    app.register_blueprint(decisions_bp)  # Register decisions blueprint

    # Register maintenance middleware
    maintenance_middleware(app)

    # Register error handlers if defined in api.errors
    try:
        from .api.errors import register_error_handlers
        register_error_handlers(app)
    except ImportError:
        pass # No custom error handlers defined or file doesn't exist

    return app
