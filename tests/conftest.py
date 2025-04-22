"""
Pytest configuration and shared fixtures.
"""

import pytest
from flask import Flask
from app import create_app
from app.database import db as _db
from app.config import TestConfig

class TestConfig(Config):
    """Test configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

@pytest.fixture(scope='session')
def app(request):
    """Session-wide test Flask application."""
    flask_app = create_app(config_class=TestConfig)

    # Establish an application context before running the tests.
    ctx = flask_app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return flask_app

@pytest.fixture(scope='session')
def db(app, request):
    """Session-wide test database."""
    def teardown():
        _db.drop_all()

    _db.app = app
    _db.create_all()

    request.addfinalizer(teardown)
    return _db

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()
