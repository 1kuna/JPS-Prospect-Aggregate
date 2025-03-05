"""Error handlers for the API blueprint."""

from flask import jsonify, current_app
from . import api

@api.errorhandler(404)
def resource_not_found(error):
    """Handle 404 errors for API endpoints."""
    response = jsonify({
        'status': 'error',
        'message': 'Resource not found'
    })
    response.status_code = 404
    return response

@api.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors for API endpoints."""
    # Log the error
    current_app.logger.error(f"API error: {str(error)}")
    
    response = jsonify({
        'status': 'error',
        'message': 'An internal server error occurred'
    })
    response.status_code = 500
    return response

@api.errorhandler(Exception)
def handle_exception(error):
    """Handle unhandled exceptions for API endpoints."""
    # Log the error
    current_app.logger.error(f"Unhandled API exception: {str(error)}")
    
    response = jsonify({
        'status': 'error',
        'message': 'An unexpected error occurred'
    })
    response.status_code = 500
    return response 