"""
Pytest configuration and shared fixtures.
"""

import pytest

from app import create_app
from app.database import db as _db


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def db(app, request):
    """Session-wide test database. Creates all tables."""

    def teardown():
        _db.drop_all()

    # _db.app = app # This is done by Flask-SQLAlchemy's init_app
    with app.app_context():  # Ensure operations are within app context
        _db.create_all()

    request.addfinalizer(teardown)
    return _db


@pytest.fixture(scope="function")
def db_session(db):  # Depends on the session-scoped db fixture
    """
    Provides a SQLAlchemy session for a test, ensuring test isolation
    by using a nested transaction that's rolled back.
    """
    # The db fixture ensures that the database tables are created.
    # _db.session is the session managed by Flask-SQLAlchemy, typically a scoped session.

    # Start a nested transaction (uses SAVEPOINT)
    nested = _db.session.begin_nested()

    try:
        yield _db.session
    finally:
        if nested.is_active:
            nested.rollback()
        _db.session.expire_all()

    # The main session used by Flask-SQLAlchemy is typically managed per request or per thread.
    # For tests, simple rollback of the nested transaction is often sufficient.
    # If full session cleanup beyond rollback is needed (e.g., expunge all), it can be added here.
    # However, Flask-SQLAlchemy's scoped session usually handles this.
    # For extra safety, ensure session is clean, though rollback should handle it.
    # _db.session.remove() # This might be too aggressive if session scope is broader than function.


@pytest.fixture()
def client(app):
    """Create a test client for the app."""
    return app.test_client()


# Global deterministic seeding for stable tests
@pytest.fixture(scope="session", autouse=True)
def seed_random():
    import random

    random.seed(12345)
    try:
        import numpy as np

        np.random.seed(12345)
    except Exception:
        pass

    # Reset factory counters for each test session
    from tests.factories import reset_counters

    reset_counters()


@pytest.fixture
def auth_client(client):
    """Create an authenticated test client with configurable role.

    Usage:
        def test_user_access(auth_client):
            # Default user role
            response = auth_client.get('/api/protected')

        def test_admin_access(auth_client):
            # Configure for admin role
            auth_client.set_role('admin')
            response = auth_client.get('/api/admin')
    """

    class AuthenticatedClient:
        def __init__(self, client):
            self.client = client
            self.set_role("user")

        def set_role(self, role: str) -> None:
            user_map = {
                "user": ("test-user-123", "testuser"),
                "admin": ("test-admin-456", "testadmin"),
                "super-admin": ("test-super-789", "testsuperadmin"),
            }
            user_id, username = user_map.get(role, user_map["user"])
            with self.client.session_transaction() as session:
                session["user_id"] = user_id
                session["user_email"] = f"{username}@example.com"
                session["user_first_name"] = username
                session["user_role"] = role

        def __getattr__(self, name):
            return getattr(self.client, name)

    return AuthenticatedClient(client)


@pytest.fixture
def admin_client(auth_client):
    """Create a pre-configured admin client."""
    auth_client.set_role("admin")
    return auth_client


@pytest.fixture
def super_admin_client(auth_client):
    """Create a pre-configured super-admin client."""
    auth_client.set_role("super-admin")
    return auth_client
