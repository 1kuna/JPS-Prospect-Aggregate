"""
Pytest configuration and shared fixtures.
"""

import pytest
from flask import Flask
from app import create_app
from app.database import db as _db
# TestConfig is now sourced from active_config in create_app when FLASK_ENV='testing'
# from app.config import TestConfig # No longer directly needed here

# The local TestConfig class definition is removed as create_app uses active_config.
# Ensure FLASK_ENV is set to 'testing' in the test environment.

@pytest.fixture(scope='session')
def app(request):
    """Session-wide test Flask application."""
    # create_app will use active_config.
    # For tests, FLASK_ENV should be 'testing' so active_config is TestingConfig.
    flask_app = create_app() 

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
