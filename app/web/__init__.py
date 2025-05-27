"""Flask application factory for the dashboard."""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from app.utils.logger import logger
from app.api.errors import register_error_handlers

# Set up logging with the centralized utility
logger = logger.bind(name="dashboard.factory")

def create_app(config=None):
    """Application factory for creating Flask app instances."""
    # Create and configure the app
    app = Flask(__name__)
    
    # Configure Flask to redirect URLs with trailing slashes to URLs without trailing slashes
    app.url_map.strict_slashes = False
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Load default configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())
    
    # Apply any custom configuration
    if config:
        app.config.update(config)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Path to the React build directory - fix the path to be relative to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    react_build_dir = os.path.join(project_root, 'frontend-react/dist')
    
    logger.info(f"React build directory: {react_build_dir}")
    
    # Check if the build directory exists
    if not os.path.exists(react_build_dir):
        logger.error(f"React build directory not found at {react_build_dir}")
    else:
        logger.info(f"React build directory found at {react_build_dir}")
        # List files in the build directory
        logger.info(f"Files in build directory: {os.listdir(react_build_dir)}")
    
    # Add routes for serving static files from React build
    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        """Serve asset files from the React build directory."""
        try:
            logger.info(f"Serving asset: {filename}")
            return send_from_directory(os.path.join(react_build_dir, 'assets'), filename)
        except Exception as e:
            logger.error(f"Error serving asset {filename}: {str(e)}")
            return "", 404
    
    @app.route('/vite.svg')
    def serve_vite_svg():
        """Serve the Vite SVG icon."""
        try:
            return send_from_directory(react_build_dir, 'vite.svg')
        except Exception as e:
            logger.error(f"Error serving vite.svg: {str(e)}")
            return "", 404
    
    return app

def register_blueprints(app):
    """Register Flask blueprints."""
    # Import blueprints
    from app.web.routes import main
    from app.api import api  # This is the main API blueprint we're using
    from app.web.routes import data_sources
    
    # Initialize API error handlers before registering the blueprint
    from app.api.errors import init_error_handlers
    init_error_handlers(api)
    
    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(api)  # Register the main API blueprint
    app.register_blueprint(data_sources)
    
    logger.info('Blueprints registered')