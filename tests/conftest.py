"""
Pytest configuration and shared fixtures.
"""

import pytest
from app import create_app, create_celery_app
from app.config import Config

class TestConfig(Config):
    """Test configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache'
    CELERY_CACHE_BACKEND = 'memory'

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app(TestConfig)
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()

@pytest.fixture
def celery_app(app):
    """Create a Celery app instance for testing."""
    return create_celery_app(app)
