"""Custom exceptions for the application."""

class BaseAppException(Exception):
    """Base exception for all application exceptions."""
    status_code = 500
    
    def __init__(self, message=None, status_code=None, payload=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = 'error'
        return rv

class ResourceNotFoundError(BaseAppException):
    """Exception raised when a requested resource is not found."""
    status_code = 404
    
class ValidationError(BaseAppException):
    """Exception raised when input validation fails."""
    status_code = 400

class ScraperError(BaseAppException):
    """Exception raised when a scraper fails."""
    status_code = 500

class DatabaseError(BaseAppException):
    """Exception raised when a database operation fails."""
    status_code = 500 