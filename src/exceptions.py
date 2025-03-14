"""
Custom exceptions for the JPS Prospect Aggregate application.

This module defines a hierarchy of custom exceptions used throughout the application.
All exceptions inherit from BaseAppException, which provides common functionality
such as status codes, error codes, and serialization to dictionaries.
"""

class BaseAppException(Exception):
    """
    Base exception for all application exceptions.
    
    This class provides common functionality for all application exceptions,
    including HTTP status codes, error codes, and serialization to dictionaries.
    
    Attributes:
        status_code (int): HTTP status code to return (default: 500)
        error_code (str): Error code for API responses (default: "INTERNAL_ERROR")
        message (str): Human-readable error message
        payload (dict): Additional data to include in the error response
    """
    status_code = 500
    error_code = "INTERNAL_ERROR"
    
    def __init__(self, message=None, status_code=None, error_code=None, payload=None):
        """
        Initialize the exception.
        
        Args:
            message (str, optional): Human-readable error message
            status_code (int, optional): HTTP status code to override the default
            error_code (str, optional): Error code to override the default
            payload (dict, optional): Additional data to include in the error response
        """
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.payload = payload
    
    def to_dict(self):
        """
        Convert the exception to a dictionary for API responses.
        
        Returns:
            dict: Dictionary representation of the exception
        """
        rv = dict(self.payload or {})
        rv['message'] = self.message
        rv['status'] = 'error'
        rv['error_code'] = self.error_code
        return rv


# -----------------------------------------------------------------------------
# Resource Exceptions
# -----------------------------------------------------------------------------

class ResourceNotFoundError(BaseAppException):
    """
    Exception raised when a requested resource is not found.
    
    This exception is typically raised when a resource with a specific ID
    or other identifier cannot be found in the database.
    """
    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"


# -----------------------------------------------------------------------------
# Validation Exceptions
# -----------------------------------------------------------------------------

class ValidationError(BaseAppException):
    """
    Exception raised when input validation fails.
    
    This exception is typically raised when user input or API request data
    fails validation checks.
    """
    status_code = 400
    error_code = "VALIDATION_ERROR"


class DataIntegrityError(BaseAppException):
    """
    Exception raised when data integrity is violated.
    
    This exception is typically raised when an operation would violate
    data integrity constraints, such as unique constraints or foreign keys.
    """
    status_code = 400
    error_code = "DATA_INTEGRITY_ERROR"


# -----------------------------------------------------------------------------
# Database Exceptions
# -----------------------------------------------------------------------------

class DatabaseError(BaseAppException):
    """
    Exception raised when a database operation fails.
    
    This exception is typically raised when a database operation fails
    due to an error in the database system.
    """
    status_code = 500
    error_code = "DATABASE_ERROR"


# -----------------------------------------------------------------------------
# Network Exceptions
# -----------------------------------------------------------------------------

class NetworkError(BaseAppException):
    """
    Exception raised when a network operation fails.
    
    This exception is typically raised when a network operation fails
    due to connectivity issues or other network-related problems.
    """
    status_code = 503
    error_code = "NETWORK_ERROR"


class TimeoutError(NetworkError):
    """
    Exception raised when a network operation times out.
    
    This exception is typically raised when a network operation takes
    too long to complete and exceeds the timeout threshold.
    """
    status_code = 504
    error_code = "TIMEOUT_ERROR"


# -----------------------------------------------------------------------------
# Scraper Exceptions
# -----------------------------------------------------------------------------

class ScraperError(BaseAppException):
    """
    Exception raised when a scraper fails.
    
    This exception is typically raised when a web scraper encounters an error
    while scraping data from a website.
    """
    status_code = 500
    error_code = "SCRAPER_ERROR"


class ParsingError(BaseAppException):
    """
    Exception raised when parsing data fails.
    
    This exception is typically raised when a scraper or data processor
    fails to parse data from a website or file.
    """
    status_code = 500
    error_code = "PARSING_ERROR"


# -----------------------------------------------------------------------------
# Operational Exceptions
# -----------------------------------------------------------------------------

class RetryableError(BaseAppException):
    """
    Exception raised when an operation should be retried.
    
    This exception is typically raised when an operation fails temporarily
    and should be retried after a delay.
    """
    status_code = 503
    error_code = "RETRYABLE_ERROR"


# -----------------------------------------------------------------------------
# Authentication and Authorization Exceptions
# -----------------------------------------------------------------------------

class AuthenticationError(BaseAppException):
    """
    Exception raised when authentication fails.
    
    This exception is typically raised when a user fails to authenticate
    due to invalid credentials or other authentication issues.
    """
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"


class AuthorizationError(BaseAppException):
    """
    Exception raised when authorization fails.
    
    This exception is typically raised when a user is not authorized to
    perform a specific action or access a specific resource.
    """
    status_code = 403
    error_code = "AUTHORIZATION_ERROR" 