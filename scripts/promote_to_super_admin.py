#!/usr/bin/env python3
"""Promote a user to super_admin role.
Usage: python scripts/promote_to_super_admin.py <email>
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app import create_app
from app.database import db
from app.database.user_models import User
from app.utils.logger import logger
from app.utils.user_utils import update_user_role


def promote_to_super_admin(email):
    """Promote a user to super_admin role by email."""
    app = create_app()

    with app.app_context():
        try:
            # Find user by email
            user = db.session.query(User).filter_by(email=email.lower()).first()

            if not user:
                logger.error(f"User with email '{email}' not found")
                return False

            # Check current role
            if user.role == "super_admin":
                logger.info(f"User '{email}' is already a super_admin")
                return True

            logger.info(f"Current role for '{email}': {user.role}")

            # Update role to super_admin
            success = update_user_role(user.id, "super_admin")

            if success:
                logger.success(f"✅ Successfully promoted '{email}' to super_admin!")
                logger.info(f"User ID: {user.id}, Name: {user.first_name}")
                return True
            else:
                logger.error(f"Failed to update role for '{email}'")
                return False

        except Exception as e:
            logger.error(f"Error promoting user: {str(e)}")
            db.session.rollback()
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to zcanepa@jps-online.com if no email provided
        email = "zcanepa@jps-online.com"
        logger.info(f"No email provided, using default: {email}")
    else:
        email = sys.argv[1]

    success = promote_to_super_admin(email)
    if not success:
        sys.exit(1)
