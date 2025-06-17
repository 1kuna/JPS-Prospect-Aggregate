"""
Separate database instance for user authentication data.

This provides security isolation between user authentication data
and business prospect data.
"""

from flask_sqlalchemy import SQLAlchemy

# Import the main db instance and use binds instead of separate instance
from app.database import db

# Use the main db instance with a bind key for user data
user_db = db

def init_user_db(app):
    """Initialize the user database with the Flask app using binds."""
    # Configure the user database as a bind
    if 'SQLALCHEMY_BINDS' not in app.config:
        app.config['SQLALCHEMY_BINDS'] = {}
    
    app.config['SQLALCHEMY_BINDS']['users'] = app.config['USER_DATABASE_URI']
    
    return user_db