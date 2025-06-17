"""
Utility functions for working with user data across separate databases.
"""

from app.database import db
from app.database.user_models import User

def get_user_by_id(user_id):
    """Get user data from the user database by ID."""
    return db.session.query(User).filter_by(id=user_id).first()

def get_users_by_ids(user_ids):
    """Get multiple users from the user database by IDs."""
    if not user_ids:
        return {}
    
    users = db.session.query(User).filter(User.id.in_(user_ids)).all()
    return {user.id: user for user in users}

def get_user_data_dict(user):
    """Convert user object to dictionary if it exists."""
    return user.to_dict() if user else None