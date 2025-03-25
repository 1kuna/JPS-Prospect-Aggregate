"""
Simplified exception handling for the application.
"""

class AppError(Exception):
    """Base exception for all application errors."""
    status_code = 500
    error_type = "server_error"
    
    def __init__(self, message=None, status_code=None, error_type=None):
        super().__init__(message or "An unexpected error occurred")
        self.message = message or "An unexpected error occurred"
        if status_code is not None:
            self.status_code = status_code
        if error_type is not None:
            self.error_type = error_type
    
    def to_dict(self):
        """Convert the exception to a dictionary for API responses."""
        return {
            "error": self.error_type,
            "message": self.message,
            "status_code": self.status_code
        }


class ValidationError(AppError):
    """Exception raised when input validation fails."""
    status_code = 400
    error_type = "validation_error"


class NotFoundError(AppError):
    """Exception raised when a requested resource is not found."""
    status_code = 404
    error_type = "not_found"


class DatabaseError(AppError):
    """Exception raised when a database operation fails."""
    status_code = 500
    error_type = "database_error"


class ScraperError(AppError):
    """Exception raised when a scraper operation fails."""
    status_code = 500
    error_type = "scraper_error"


class AuthenticationError(AppError):
    """Exception raised when authentication fails."""
    status_code = 401
    error_type = "authentication_error"


class AuthorizationError(AppError):
    """Exception raised when authorization fails."""
    status_code = 403
    error_type = "authorization_error" 