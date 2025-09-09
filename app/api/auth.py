"""Authentication API endpoints for JPS Prospect Aggregate.

Provides simple email-based authentication without passwords.
"""

import datetime
from datetime import timezone
UTC = timezone.utc

from flask import request, session
from sqlalchemy.exc import IntegrityError

from app.api.factory import (
    api_route,
    create_blueprint,
    error_response,
    login_required,
    admin_required,
    super_admin_required,
    success_response,
)
from app.database import db
from app.database.user_models import User

auth_bp, logger = create_blueprint("auth", "/api/auth")

# Auth decorators are now imported from factory module

# Add session debugging in production
import os
if os.getenv("ENVIRONMENT") == "production":
    @auth_bp.before_request
    def log_session_before():
        """Debug session issues in production."""
        logger.debug(f"Session before request to {request.endpoint}: {dict(session)}")
        logger.debug(f"Session cookie: {request.cookies.get('session', 'none')[:50] if request.cookies.get('session') else 'none'}...")
    
    @auth_bp.after_request
    def log_session_after(response):
        """Debug session issues in production."""
        logger.debug(f"Session after request to {request.endpoint}: {dict(session)}")
        return response


@api_route(auth_bp, "/signup", methods=["POST"])
def signup():
    """Create a new user account with email and first name only."""
    try:
        data = request.get_json()
        if not data:
            return error_response(400, "Request body is required")

        email = data.get("email", "").strip().lower()
        first_name = data.get("first_name", "").strip()

        if not email or not first_name:
            return error_response(400, "Email and first name are required")

        # Validate email format (basic validation)
        if "@" not in email or "." not in email:
            return error_response(400, "Invalid email format")

        # Check if user already exists
        existing_user = db.session.query(User).filter_by(email=email).first()
        if existing_user:
            return error_response(409, "User with this email already exists")

        # Create new user
        user = User(email=email, first_name=first_name)

        db.session.add(user)
        db.session.commit()

        # Log user in
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_first_name"] = user.first_name
        session["user_role"] = user.role

        logger.info(f"New user signed up: {email}")

        return success_response(
            data={"user": user.to_dict()},
            message="Account created successfully"
        )

    except IntegrityError:
        db.session.rollback()
        return error_response(409, "User with this email already exists")
    except Exception as e:
        logger.error(f"Error in signup: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to create account")


@api_route(auth_bp, "/signin", methods=["POST"])
def signin():
    """Sign in user with email only."""
    try:
        data = request.get_json()
        if not data:
            return error_response(400, "Request body is required")

        email = data.get("email", "").strip().lower()

        if not email:
            return error_response(400, "Email is required")

        # Find user by email
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            return error_response(404, "No account found with this email address")

        # Update last login
        user.last_login_at = datetime.datetime.now(UTC)
        db.session.commit()

        # Log user in
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_first_name"] = user.first_name
        session["user_role"] = user.role

        logger.info(f"User signed in: {email}")

        return success_response(
            data={"user": user.to_dict()},
            message="Sign in successful"
        )

    except Exception as e:
        logger.error(f"Error in signin: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to sign in")


@api_route(auth_bp, "/signout", methods=["POST"])
def signout():
    """Sign out the current user."""
    user_email = session.get("user_email", "unknown")
    session.clear()
    logger.info(f"User signed out: {user_email}")
    return success_response(message="Sign out successful")


@api_route(auth_bp, "/session", methods=["GET"], auth="login")
def get_session():
    """Get current session info."""
    user_id = session.get("user_id")
    user = db.session.query(User).filter_by(id=user_id).first()
    
    if not user:
        session.clear()
        return error_response(401, "Session expired")
    
    return success_response(data={"user": user.to_dict()})


@api_route(auth_bp, "/users", methods=["GET"], auth="super_admin")
def get_users():
    """Get all users (super admin only)."""
    try:
        users = db.session.query(User).all()
        return success_response(
            data={"users": [user.to_dict() for user in users]}
        )
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}", exc_info=True)
        return error_response(500, "Failed to get users")


@api_route(auth_bp, "/users/<int:user_id>/role", methods=["PUT"], auth="super_admin")
def update_user_role(user_id):
    """Update user role (super admin only)."""
    try:
        data = request.get_json()
        if not data:
            return error_response(400, "Request body is required")

        new_role = data.get("role", "").strip().lower()
        if new_role not in ["user", "admin", "super_admin"]:
            return error_response(400, "Invalid role. Must be 'user', 'admin', or 'super_admin'")

        # Prevent modifying own role
        if user_id == session.get("user_id"):
            return error_response(400, "Cannot modify your own role")

        user = db.session.query(User).filter_by(id=user_id).first()
        if not user:
            return error_response(404, "User not found")

        old_role = user.role
        user.role = new_role
        user.updated_at = datetime.datetime.now(UTC)
        db.session.commit()

        logger.info(f"User role updated: {user.email} from {old_role} to {new_role}")

        return success_response(
            data={"user": user.to_dict()},
            message=f"User role updated to {new_role}"
        )

    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to update user role")


@api_route(auth_bp, "/users/<int:user_id>", methods=["DELETE"], auth="super_admin")
def delete_user(user_id):
    """Delete a user (super admin only)."""
    try:
        # Prevent deleting own account
        if user_id == session.get("user_id"):
            return error_response(400, "Cannot delete your own account")

        user = db.session.query(User).filter_by(id=user_id).first()
        if not user:
            return error_response(404, "User not found")

        user_email = user.email
        db.session.delete(user)
        db.session.commit()

        logger.info(f"User deleted: {user_email}")

        return success_response(message="User deleted successfully")

    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        db.session.rollback()
        return error_response(500, "Failed to delete user")