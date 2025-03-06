"""Custom exceptions for the application."""

class BaseAppException(Exception):
    """Base exception for all application exceptions."""
    status_code = 500
    error_code = "INTERNAL_ERROR"
    
    def __init__(self, message=None, status_code=None, error_code=None, payload=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = 'error'
        rv['error_code'] = self.error_code
        return rv

class ResourceNotFoundError(BaseAppException):
    """Exception raised when a requested resource is not found."""
    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"
    
class ValidationError(BaseAppException):
    """Exception raised when input validation fails."""
    status_code = 400
    error_code = "VALIDATION_ERROR"

class ScraperError(BaseAppException):
    """Exception raised when a scraper fails."""
    status_code = 500
    error_code = "SCRAPER_ERROR"

class DatabaseError(BaseAppException):
    """Exception raised when a database operation fails."""
    status_code = 500
    error_code = "DATABASE_ERROR"

# Network related exceptions
class NetworkError(BaseAppException):
    """Exception raised when a network operation fails."""
    status_code = 503
    error_code = "NETWORK_ERROR"
    
class TimeoutError(NetworkError):
    """Exception raised when a network operation times out."""
    status_code = 504
    error_code = "TIMEOUT_ERROR"

class ConnectionError(NetworkError):
    """Exception raised when a connection cannot be established."""
    status_code = 503
    error_code = "CONNECTION_ERROR"

# Data related exceptions
class ParsingError(BaseAppException):
    """Exception raised when parsing data fails."""
    status_code = 500
    error_code = "PARSING_ERROR"
    
class DataIntegrityError(BaseAppException):
    """Exception raised when data integrity is violated."""
    status_code = 400
    error_code = "DATA_INTEGRITY_ERROR"

# Task related exceptions
class TaskError(BaseAppException):
    """Exception raised when a background task fails."""
    status_code = 500
    error_code = "TASK_ERROR"
    
class RetryableError(BaseAppException):
    """Exception raised when an operation should be retried."""
    status_code = 503
    error_code = "RETRYABLE_ERROR"

# Authentication and Authorization exceptions
class AuthenticationError(BaseAppException):
    """Exception raised when authentication fails."""
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"

class AuthorizationError(BaseAppException):
    """Exception raised when authorization fails."""
    status_code = 403
    error_code = "AUTHORIZATION_ERROR" 