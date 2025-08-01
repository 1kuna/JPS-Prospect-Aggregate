"""Error handlers for the API."""

from flask import jsonify  # current_app removed
from sqlalchemy.exc import SQLAlchemyError
from app.utils.logger import logger  # Import centralized logger
from app.exceptions import (
    AppError,
    ValidationError,
    NotFoundError,
    DatabaseError,
    ScraperError,
    AuthenticationError,
    AuthorizationError,
)

# Create a bound logger for error handlers
error_logger = logger.bind(name="api.error_handlers")


def error_response(status_code, message):
    """Create a standardized error response."""
    return jsonify(
        {"error": True, "message": message, "status_code": status_code}
    ), status_code


def bad_request(message):
    """Create a 400 Bad Request response."""
    return error_response(400, message)


def register_error_handlers(app):
    """Register error handlers with the Flask app."""

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(DatabaseError)
    def handle_database_error(error):
        error_logger.error(f"Database error: {str(error)}", exc_info=True)
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        error_logger.error(f"SQLAlchemy error: {str(error)}", exc_info=True)
        return jsonify(
            {"error": "database_error", "message": "Database error", "status_code": 500}
        ), 500

    @app.errorhandler(ScraperError)
    def handle_scraper_error(error):
        error_logger.error(f"Scraper error: {str(error)}", exc_info=True)
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(AuthenticationError)
    def handle_auth_error(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(AppError)
    def handle_app_error(error):
        error_logger.error(f"Application error: {str(error)}", exc_info=True)
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle unexpected exceptions."""
        error_logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
        response = {
            "error": "server_error",
            "message": "An unexpected error occurred",
            "status_code": 500,
        }
        return jsonify(response), 500
