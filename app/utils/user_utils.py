"""Utility functions for working with user data across separate databases."""

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


def is_admin(user):
    """Check if a user has admin role."""
    return user and user.role == "admin"


def get_user_by_email(email):
    """Get user data from the user database by email."""
    return db.session.query(User).filter_by(email=email).first()


def promote_user_to_admin(user_id):
    """Promote a user to admin role."""
    user = get_user_by_id(user_id)
    if user:
        user.role = "admin"
        db.session.commit()
        return True
    return False


def demote_admin_to_user(user_id):
    """Demote an admin to regular user role."""
    user = get_user_by_id(user_id)
    if user:
        user.role = "user"
        db.session.commit()
        return True
    return False


def update_user_role(user_id, new_role):
    """Update a user's role to any valid role."""
    if new_role not in ["user", "admin", "super_admin"]:
        return False

    user = get_user_by_id(user_id)
    if user:
        user.role = new_role
        db.session.commit()
        return True
    return False
