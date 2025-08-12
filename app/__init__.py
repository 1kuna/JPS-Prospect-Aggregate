"""Application Factory Pattern for Flask app.

This module creates and configures the Flask application.
"""

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from app.config import active_config  # Import active_config
from app.database import db  # Import the db instance from database.py
from app.database.user_db import init_user_db  # Import user database initialization
from app.middleware.maintenance import maintenance_middleware
from app.utils.logger import logger

# Setup logging as early as possible
# Logging is configured automatically on import of app.utils.logger


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config.from_object(active_config)  # Use active_config directly

    # Initialize extensions
    # Configure CORS with credentials support for authentication
    CORS(
        app, 
        resources={r"/api/*": {
            "origins": [
                "http://localhost:5173", 
                "http://localhost:5001", 
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:5173", 
                "http://127.0.0.1:5001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001"
            ],
            "allow_credentials": True,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }},
        supports_credentials=True
    )

    # Configure user database bind BEFORE initializing db
    init_user_db(app)  # Configure user database binds

    # Now initialize SQLAlchemy with the app (after binds are configured)
    db.init_app(app)  # Initialize SQLAlchemy with the app

    # Initialize Flask-Migrate for business database
    Migrate(app, db)

    # Import models here to ensure they are registered with SQLAlchemy
    from app.database import models  # noqa
    from app.database import user_models  # noqa
    
    # Automatic database initialization
    from app.utils.database_initializer import initialize_database
    if not initialize_database(app):
        logger.error("Database initialization failed - application may not function properly")
        # Continue anyway to allow debugging
    
    # Check for pending migrations after database initialization
    # Skip this check when running Flask CLI commands to avoid infinite recursion
    import os
    if os.environ.get('FLASK_RUN_FROM_CLI') != 'true':
        with app.app_context():
            from app.utils.migration_check import ensure_migration_tracking, check_pending_migrations
            
            # Ensure migration tracking is initialized
            ensure_migration_tracking()
            
            # Check for pending migrations
            if check_pending_migrations():
                logger.warning("⚠️  Database schema may be out of sync!")
                logger.warning("⚠️  Run 'flask db upgrade' to apply pending migrations")
                
                # In development, offer to auto-apply
                if active_config.DEBUG:
                    logger.info("Development mode: Consider running migrations to avoid schema issues")

    # Register blueprints
    from app.api.main import main_bp
    from app.api.data_sources import data_sources_bp
    from app.api.scrapers import scrapers_bp
    from app.api.prospects import prospects_bp  # Import the new blueprint
    from app.api.llm_processing import llm_bp  # Import LLM processing blueprint
    from app.api.admin import admin_bp  # Import admin blueprint
    from app.api.auth import auth_bp  # Import auth blueprint
    from app.api.decisions import decisions_bp  # Import decisions blueprint
    from app.api.tools import tools_bp  # Import tools blueprint
    from app.web.routes import main as web_main_bp  # Import the web blueprint

    app.register_blueprint(web_main_bp)  # Register the web blueprint
    app.register_blueprint(main_bp, url_prefix="/api")
    app.register_blueprint(data_sources_bp, url_prefix="/api/data-sources")
    app.register_blueprint(
        scrapers_bp, url_prefix="/api/data-sources"
    )  # Scraper routes are under data-sources
    app.register_blueprint(
        prospects_bp
    )  # Register the new blueprint (uses url_prefix from its definition)
    app.register_blueprint(
        llm_bp
    )  # Register LLM processing blueprint (uses url_prefix='/api/llm' from its definition)
    app.register_blueprint(admin_bp)  # Register admin blueprint
    app.register_blueprint(auth_bp)  # Register auth blueprint
    app.register_blueprint(decisions_bp)  # Register decisions blueprint
    app.register_blueprint(tools_bp)  # Register tools blueprint

    # Register maintenance middleware
    maintenance_middleware(app)

    # Initialize enhancement queue and cleanup utilities
    with app.app_context():
        from app.services.enhancement_queue import enhancement_queue  # noqa: F401
        from app.services.llm_service import llm_service  # noqa: F401
        from app.utils.enhancement_cleanup import cleanup_all_in_progress_enhancements
        from app.utils.scraper_cleanup import cleanup_all_working_scrapers

        # Database is already initialized above, so tables should exist
        # Run cleanup functions
        tables_exist = True
        try:
            # Verify tables exist with a simple query
            db.session.execute(
                db.text("SELECT COUNT(*) FROM prospects LIMIT 1")
            ).fetchone()
            db.session.execute(
                db.text("SELECT COUNT(*) FROM scraper_status LIMIT 1")
            ).fetchone()
        except Exception as e:
            logger.warning(
                f"Database tables check failed after initialization: {e}"
            )
            tables_exist = False

        if tables_exist:
            # Clean up any stuck enhancement statuses from previous server runs
            try:
                cleanup_count = cleanup_all_in_progress_enhancements()
                if cleanup_count > 0:
                    logger.info(
                        f"Cleaned up {cleanup_count} stuck enhancement requests on startup"
                    )
            except Exception as e:
                logger.warning(f"Failed to clean up stuck enhancements: {e}")

            # Clean up any stuck scraper statuses from previous server runs
            if active_config.SCRAPER_CLEANUP_ENABLED:
                try:
                    scraper_cleanup_count = cleanup_all_working_scrapers()
                    if scraper_cleanup_count > 0:
                        logger.info(
                            f"Cleaned up {scraper_cleanup_count} stuck scrapers on startup"
                        )
                except Exception as e:
                    logger.warning(f"Failed to clean up stuck scrapers: {e}")
        else:
            logger.info(
                "Skipping cleanup functions - database tables not available"
            )

        # Enhancement queue is ready for use (no worker thread needed in simplified version)

    # Register error handlers if defined in api.errors
    try:
        from .api.errors import register_error_handlers

        register_error_handlers(app)
    except ImportError:
        pass  # No custom error handlers defined or file doesn't exist

    return app
