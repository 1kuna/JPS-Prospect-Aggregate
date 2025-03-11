"""Error handlers for the API blueprint."""

from flask import jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
from . import api
from src.exceptions import (
    ValidationError, ResourceNotFoundError, BaseAppException,
    ScraperError, DatabaseError, NetworkError, TimeoutError,
    ParsingError, DataIntegrityError, RetryableError,
    AuthenticationError, AuthorizationError
)

@api.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle validation errors."""
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 400

@api.errorhandler(ResourceNotFoundError)
def handle_not_found_error(error):
    """Handle resource not found errors."""
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 404

@api.errorhandler(DatabaseError)
def handle_database_error(error):
    """Handle database errors."""
    current_app.logger.error(f"Database error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 500

@api.errorhandler(SQLAlchemyError)
def handle_sqlalchemy_error(error):
    """Handle SQLAlchemy database errors."""
    current_app.logger.error(f"Database error: {str(error)}")
    return jsonify({"status": "error", "message": "Database error occurred", "error_code": "DATABASE_ERROR"}), 500

@api.errorhandler(ScraperError)
def handle_scraper_error(error):
    """Handle scraper errors."""
    current_app.logger.error(f"Scraper error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 500

@api.errorhandler(NetworkError)
def handle_network_error(error):
    """Handle network errors."""
    current_app.logger.error(f"Network error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 503

@api.errorhandler(TimeoutError)
def handle_timeout_error(error):
    """Handle timeout errors."""
    current_app.logger.error(f"Timeout error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 504

@api.errorhandler(ParsingError)
def handle_parsing_error(error):
    """Handle parsing errors."""
    current_app.logger.error(f"Parsing error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 500

@api.errorhandler(DataIntegrityError)
def handle_data_integrity_error(error):
    """Handle data integrity errors."""
    current_app.logger.error(f"Data integrity error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 400

@api.errorhandler(RetryableError)
def handle_retryable_error(error):
    """Handle retryable errors."""
    current_app.logger.error(f"Retryable error: {str(error)}")
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 503

@api.errorhandler(AuthenticationError)
def handle_authentication_error(error):
    """Handle authentication errors."""
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 401

@api.errorhandler(AuthorizationError)
def handle_authorization_error(error):
    """Handle authorization errors."""
    return jsonify({"status": "error", "message": str(error), "error_code": error.error_code}), 403

@api.errorhandler(BaseAppException)
def handle_app_exception(error):
    """Handle application exceptions."""
    return jsonify(error.to_dict()), error.status_code

@api.errorhandler(Exception)
def handle_unexpected_error(error):
    """Handle unexpected errors."""
    current_app.logger.error(f"Unexpected error: {str(error)}")
    return jsonify({"status": "error", "message": "An unexpected error occurred", "error_code": "INTERNAL_ERROR"}), 500

def init_error_handlers(app):
    """Register error handlers with the Flask app."""
    app.register_error_handler(ValidationError, handle_validation_error)
    app.register_error_handler(ResourceNotFoundError, handle_not_found_error)
    app.register_error_handler(DatabaseError, handle_database_error)
    app.register_error_handler(SQLAlchemyError, handle_sqlalchemy_error)
    app.register_error_handler(ScraperError, handle_scraper_error)
    app.register_error_handler(NetworkError, handle_network_error)
    app.register_error_handler(TimeoutError, handle_timeout_error)
    app.register_error_handler(ParsingError, handle_parsing_error)
    app.register_error_handler(DataIntegrityError, handle_data_integrity_error)
    app.register_error_handler(RetryableError, handle_retryable_error)
    app.register_error_handler(AuthenticationError, handle_authentication_error)
    app.register_error_handler(AuthorizationError, handle_authorization_error)
    app.register_error_handler(BaseAppException, handle_app_exception)
    app.register_error_handler(Exception, handle_unexpected_error) 