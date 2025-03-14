"""API blueprint for the dashboard API endpoints.

NOTE: THIS BLUEPRINT IS CURRENTLY DISABLED DUE TO CONFLICTS WITH src/api
To prevent duplicate route conflicts, we're using the main API blueprint instead.
"""

from flask import Blueprint

# Removed url_prefix to prevent conflicts with main API
api = Blueprint('dashboard_api', __name__)  # Renamed and disabled by removing url_prefix

# These imports are commented out to prevent any routes from being registered
# from . import routes, errors 