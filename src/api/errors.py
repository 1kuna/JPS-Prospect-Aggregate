"""Error handlers for the API module."""

from flask import jsonify, current_app, Blueprint
from sqlalchemy.exc import SQLAlchemyError
from src.exceptions import (
    ValidationError, ResourceNotFoundError, BaseAppException,
    ScraperError, DatabaseError, NetworkError, TimeoutError,
    ParsingError, DataIntegrityError, RetryableError,
    AuthenticationError, AuthorizationError
)

# Define error handler functions
def handle_validation_error(error):
    """Handle validation errors."""
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 400

def handle_not_found_error(error):
    """Handle resource not found errors."""
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 404

def handle_database_error(error):
    """Handle database errors."""
    current_app.logger.error(f"Database error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 500

def handle_sqlalchemy_error(error):
    """Handle SQLAlchemy errors."""
    current_app.logger.error(f"SQLAlchemy error: {str(error)}")
    return jsonify({"status": "error", "message": "Database error", "error_code": "DATABASE_ERROR"}), 500

def handle_scraper_error(error):
    """Handle scraper errors."""
    current_app.logger.error(f"Scraper error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 500

def handle_network_error(error):
    """Handle network errors."""
    current_app.logger.error(f"Network error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 503

def handle_timeout_error(error):
    """Handle timeout errors."""
    current_app.logger.error(f"Timeout error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 504

def handle_parsing_error(error):
    """Handle parsing errors."""
    current_app.logger.error(f"Parsing error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 500

def handle_data_integrity_error(error):
    """Handle data integrity errors."""
    current_app.logger.error(f"Data integrity error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 400

def handle_retryable_error(error):
    """Handle retryable errors."""
    current_app.logger.error(f"Retryable error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 503

def handle_authentication_error(error):
    """Handle authentication errors."""
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 401

def handle_authorization_error(error):
    """Handle authorization errors."""
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 403

def handle_app_exception(error):
    """Handle base application exceptions."""
    current_app.logger.error(f"Application error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), error.status_code

def handle_unexpected_error(error):
    """Handle unexpected errors."""
    current_app.logger.error(f"Unexpected error: {str(error)}")
    return jsonify({"status": "error", "message": "An unexpected error occurred", "error_code": "INTERNAL_ERROR"}), 500

def init_error_handlers(blueprint_or_app):
    """Register error handlers with the Flask app or blueprint."""
    blueprint_or_app.register_error_handler(ValidationError, handle_validation_error)
    blueprint_or_app.register_error_handler(ResourceNotFoundError, handle_not_found_error)
    blueprint_or_app.register_error_handler(DatabaseError, handle_database_error)
    blueprint_or_app.register_error_handler(SQLAlchemyError, handle_sqlalchemy_error)
    blueprint_or_app.register_error_handler(ScraperError, handle_scraper_error)
    blueprint_or_app.register_error_handler(NetworkError, handle_network_error)
    blueprint_or_app.register_error_handler(TimeoutError, handle_timeout_error)
    blueprint_or_app.register_error_handler(ParsingError, handle_parsing_error)
    blueprint_or_app.register_error_handler(DataIntegrityError, handle_data_integrity_error)
    blueprint_or_app.register_error_handler(RetryableError, handle_retryable_error)
    blueprint_or_app.register_error_handler(AuthenticationError, handle_authentication_error)
    blueprint_or_app.register_error_handler(AuthorizationError, handle_authorization_error)
    blueprint_or_app.register_error_handler(BaseAppException, handle_app_exception)
    blueprint_or_app.register_error_handler(Exception, handle_unexpected_error) 