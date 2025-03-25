"""
Application factory for the JPS Prospect Aggregate application.
This module creates and configures the Flask and Celery applications.
"""

from flask import Flask
from celery import Celery
from app.config import Config

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    from app.database import init_db
    init_db(app)

    # Register blueprints
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.web import bp as web_bp
    app.register_blueprint(web_bp)

    return app

def create_celery_app(app=None):
    """Create and configure the Celery application."""
    celery = Celery(
        'jps_prospect_aggregate',
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND
    )
    
    if app is not None:
        celery.conf.update(app.config)
    
    return celery
