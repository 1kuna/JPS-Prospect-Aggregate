"""
Error handlers for the dashboard API blueprint.

NOTE: THIS FILE IS CURRENTLY DISABLED DUE TO CONFLICTS WITH src/api
The main API blueprint's error handlers are being used instead.
"""

# Importing the API blueprint, but all handlers are commented out to prevent registration
from . import api

'''
All error handlers have been commented out to prevent conflicts

For example:
@api.errorhandler(ResourceNotFoundError)
def handle_not_found_error(error):
    """Handle resource not found errors."""
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 404
'''

# The rest of the file has been intentionally disabled 