"""Error handlers for the API blueprint."""

from flask import jsonify, current_app
from . import api
from src.exceptions import (
    BaseAppException, ResourceNotFoundError, ValidationError, 
    DatabaseError, ScraperError, NetworkError, TimeoutError,
    ConnectionError, ParsingError, DataIntegrityError,
    AuthenticationError, AuthorizationError, TaskError
)
import traceback

@api.errorhandler(ResourceNotFoundError)
def handle_resource_not_found(error):
    """Handle ResourceNotFoundError for API endpoints."""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@api.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle ValidationError for API endpoints."""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@api.errorhandler(DatabaseError)
def handle_database_error(error):
    """Handle DatabaseError for API endpoints."""
    # Log the error
    current_app.logger.error(f"Database error: {error.message}")
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@api.errorhandler(NetworkError)
def handle_network_error(error):
    """Handle NetworkError for API endpoints."""
    # Log the error
    current_app.logger.error(f"Network error: {error.message}")
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@api.errorhandler(BaseAppException)
def handle_base_app_exception(error):
    """Handle any BaseAppException for API endpoints."""
    # Log the error
    current_app.logger.error(f"Application error ({error.__class__.__name__}): {error.message}")
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@api.errorhandler(404)
def resource_not_found(error):
    """Handle 404 errors for API endpoints."""
    response = jsonify({
        'status': 'error',
        'message': 'Resource not found',
        'error_code': 'RESOURCE_NOT_FOUND'
    })
    response.status_code = 404
    return response

@api.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors for API endpoints."""
    response = jsonify({
        'status': 'error',
        'message': 'Method not allowed',
        'error_code': 'METHOD_NOT_ALLOWED'
    })
    response.status_code = 405
    return response

@api.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors for API endpoints."""
    # Log the error
    current_app.logger.error(f"API error: {str(error)}")
    
    response = jsonify({
        'status': 'error',
        'message': 'An internal server error occurred',
        'error_code': 'INTERNAL_ERROR'
    })
    response.status_code = 500
    return response

@api.errorhandler(Exception)
def handle_exception(error):
    """Handle unhandled exceptions for API endpoints."""
    # Log the error with traceback
    current_app.logger.error(f"Unhandled API exception: {str(error)}")
    current_app.logger.error(traceback.format_exc())
    
    # In production, don't expose the actual error message to clients
    if current_app.config.get('DEBUG', False):
        message = str(error)
        details = {
            'exception_type': error.__class__.__name__,
            'traceback': traceback.format_exc().split('\n')
        }
    else:
        message = 'An unexpected error occurred'
        details = None
    
    response = jsonify({
        'status': 'error',
        'message': message,
        'error_code': 'INTERNAL_ERROR',
        'details': details
    })
    response.status_code = 500
    return response 