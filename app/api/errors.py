"""Error handlers for the API."""

from flask import jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
from app.exceptions import (
    AppError, ValidationError, NotFoundError, DatabaseError, 
    ScraperError, AuthenticationError, AuthorizationError
)

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
        current_app.logger.error(f"Database error: {str(error)}")
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        current_app.logger.error(f"SQLAlchemy error: {str(error)}")
        return jsonify({
            "error": "database_error",
            "message": "Database error",
            "status_code": 500
        }), 500
    
    @app.errorhandler(ScraperError)
    def handle_scraper_error(error):
        current_app.logger.error(f"Scraper error: {str(error)}")
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(AuthenticationError)
    def handle_auth_error(error):
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(error):
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(AppError)
    def handle_app_error(error):
        current_app.logger.error(f"Application error: {str(error)}")
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle unexpected exceptions."""
        current_app.logger.error(f"Unhandled exception: {str(error)}")
        response = {
            "error": "server_error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }
        return jsonify(response), 500 