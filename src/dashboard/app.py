"""Flask application factory for the dashboard."""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def create_app(config=None):
    """Application factory for creating Flask app instances."""
    # Create and configure the app
    app = Flask(__name__)
    
    # Load default configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())
    
    # Apply any custom configuration
    if config:
        app.config.update(config)
    
    # Set up logging
    configure_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app

def configure_logging(app):
    """Configure application logging."""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')
    
    # Configure logging
    handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    # Log application startup
    app.logger.info('Application starting up')

def register_blueprints(app):
    """Register Flask blueprints."""
    # Import blueprints
    from src.dashboard.blueprints.main import main
    from src.dashboard.blueprints.api import api
    from src.dashboard.blueprints.data_sources import data_sources
    
    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(data_sources)
    
    # Log registered routes for debugging
    app.logger.info('Registered routes:')
    for rule in app.url_map.iter_rules():
        app.logger.info(f"Route: {rule}, Endpoint: {rule.endpoint}")
    
    app.logger.info('Blueprints registered')

def register_error_handlers(app):
    """Register global error handlers."""
    # Note: Blueprint-specific error handlers take precedence over these global ones
    # These are fallbacks for routes not covered by blueprints
    
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('main/errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"Internal server error: {str(error)}")
        return render_template('main/errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_unhandled_exception(error):
        app.logger.error(f"Unhandled exception: {str(error)}")
        return render_template('main/errors/500.html'), 500
    
    app.logger.info('Error handlers registered') 