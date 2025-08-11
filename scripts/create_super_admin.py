#!/usr/bin/env python3
"""Create a super admin user.
Usage: python scripts/create_super_admin.py <email> <first_name>
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


def create_super_admin(email, first_name):
    """Create a new super admin user."""
    app = create_app()

    with app.app_context():
        try:
            # Check if user already exists
            existing_user = (
                db.session.query(User).filter_by(email=email.lower()).first()
            )

            if existing_user:
                if existing_user.role == "super_admin":
                    logger.info(f"User '{email}' already exists as super_admin")
                    return True
                else:
                    # Update existing user to super_admin
                    logger.info(
                        f"User '{email}' exists with role '{existing_user.role}', updating to super_admin"
                    )
                    existing_user.role = "super_admin"
                    db.session.commit()
                    logger.success(f"✅ Successfully updated '{email}' to super_admin!")
                    return True

            # Create new super admin user
            user = User(email=email.lower(), first_name=first_name, role="super_admin")

            db.session.add(user)
            db.session.commit()

            logger.success("✅ Successfully created super_admin user!")
            logger.info(f"Email: {email}")
            logger.info(f"Name: {first_name}")
            logger.info(f"User ID: {user.id}")

            return True

        except Exception as e:
            logger.error(f"Error creating super admin: {str(e)}")
            db.session.rollback()
            return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        # Default values
        email = "zcanepa@jps-online.com"
        first_name = "Zach"
        logger.info(f"Using default values: email={email}, name={first_name}")
    else:
        email = sys.argv[1]
        first_name = sys.argv[2]

    success = create_super_admin(email, first_name)
    if not success:
        sys.exit(1)
