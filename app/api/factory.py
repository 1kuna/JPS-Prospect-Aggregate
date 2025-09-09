"""API factory utilities for reducing boilerplate in Flask API modules.

Provides:
- Blueprint creation with automatic logger binding
- Standardized route decorator with auth and error handling
- Common response formatters
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from flask import Blueprint, jsonify, session
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    NotFoundError,
    ScraperError,
    ValidationError,
)
from app.utils.logger import get_logger


def create_blueprint(
    name: str, url_prefix: Optional[str] = None, **kwargs
) -> Tuple[Blueprint, Any]:
    """Create a Blueprint with automatic logger binding.
    
    Args:
        name: Blueprint name
        url_prefix: URL prefix for all routes (e.g., "/api/auth")
        **kwargs: Additional Blueprint arguments
        
    Returns:
        Tuple of (blueprint, bound_logger)
    """
    # Create the blueprint
    bp = Blueprint(name, __name__, url_prefix=url_prefix, **kwargs)
    
    # Create a bound logger for this API module
    logger = get_logger(f"api.{name}")
    
    return bp, logger


def api_route(
    bp: Blueprint,
    rule: str,
    methods: Optional[List[str]] = None,
    auth: Optional[str] = None,
    **options
):
    """Decorator for API routes with built-in auth and error handling.
    
    Args:
        bp: The Blueprint to register the route on
        rule: The URL rule string
        methods: List of HTTP methods (default ["GET"])
        auth: Auth level - None, "login", "admin", or "super_admin"
        **options: Additional route options
        
    Example:
        @api_route(bp, "/users", methods=["GET"], auth="admin")
        def get_users():
            return success_response(data={"users": []})
    """
    if methods is None:
        methods = ["GET"]
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Check authentication if required
            if auth:
                auth_error = _check_auth(auth)
                if auth_error:
                    return auth_error
            
            # Execute the route function with error handling
            try:
                return f(*args, **kwargs)
            except ValidationError as e:
                return error_response(e.status_code, e.message, error_type="validation_error")
            except NotFoundError as e:
                return error_response(e.status_code, e.message, error_type="not_found")
            except DatabaseError as e:
                base_logger.error(f"Database error in {f.__name__}: {str(e)}", exc_info=True)
                return error_response(e.status_code, e.message, error_type="database_error")
            except ScraperError as e:
                base_logger.error(f"Scraper error in {f.__name__}: {str(e)}", exc_info=True)
                return error_response(e.status_code, e.message, error_type="scraper_error")
            except AuthenticationError as e:
                return error_response(e.status_code, e.message, error_type="auth_error")
            except AuthorizationError as e:
                return error_response(e.status_code, e.message, error_type="authorization_error")
            except AppError as e:
                base_logger.error(f"Application error in {f.__name__}: {str(e)}", exc_info=True)
                return error_response(e.status_code, e.message, error_type="app_error")
            except SQLAlchemyError as e:
                base_logger.error(f"SQLAlchemy error in {f.__name__}: {str(e)}", exc_info=True)
                return error_response(500, "Database error", error_type="database_error")
            except Exception as e:
                base_logger.error(f"Unhandled exception in {f.__name__}: {str(e)}", exc_info=True)
                return error_response(500, "An unexpected error occurred", error_type="server_error")
        
        # Register the route with the blueprint
        bp.add_url_rule(rule, endpoint=f.__name__, view_func=wrapped, methods=methods, **options)
        return wrapped
    
    return decorator


def _check_auth(level: str) -> Optional[Tuple[Dict, int]]:
    """Check if the current session has the required authentication level.
    
    Args:
        level: Required auth level - "login", "admin", or "super_admin"
        
    Returns:
        Error response tuple if unauthorized, None if authorized
    """
    if "user_id" not in session:
        return jsonify({
            "status": "error",
            "message": "Authentication required"
        }), 401
    
    user_role = session.get("user_role", "user")
    
    if level == "admin" and user_role not in ["admin", "super_admin"]:
        return jsonify({
            "status": "error",
            "message": "Admin access required"
        }), 403
    
    if level == "super_admin" and user_role != "super_admin":
        return jsonify({
            "status": "error",
            "message": "Super admin access required"
        }), 403
    
    return None


# Response formatter functions
def success_response(
    data: Optional[Any] = None,
    message: Optional[str] = None,
    status_code: int = 200,
    **kwargs
) -> Tuple[Dict, int]:
    """Create a standardized success response.
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code (default 200)
        **kwargs: Additional response fields
        
    Returns:
        JSON response tuple
    """
    response = {"status": "success"}
    
    if message:
        response["message"] = message
    if data is not None:
        response["data"] = data
    
    # Add any additional fields
    response.update(kwargs)
    
    return jsonify(response), status_code


def error_response(
    status_code: int,
    message: str,
    error_type: Optional[str] = None,
    **kwargs
) -> Tuple[Dict, int]:
    """Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        error_type: Type of error for client handling
        **kwargs: Additional error details
        
    Returns:
        JSON response tuple
    """
    response = {
        "status": "error",
        "message": message,
        "status_code": status_code
    }
    
    if error_type:
        response["error"] = error_type
    
    # Add any additional fields
    response.update(kwargs)
    
    return jsonify(response), status_code


def paginated_response(
    items: List[Any],
    page: int,
    per_page: int,
    total_items: int,
    total_pages: int,
    **kwargs
) -> Tuple[Dict, int]:
    """Create a standardized paginated response.
    
    Args:
        items: List of items for current page
        page: Current page number
        per_page: Items per page
        total_items: Total number of items
        total_pages: Total number of pages
        **kwargs: Additional response fields
        
    Returns:
        JSON response tuple
    """
    response = {
        "status": "success",
        "data": {
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1 and total_items > 0
            }
        }
    }
    
    # Add any additional fields to data
    if kwargs:
        response["data"].update(kwargs)
    
    return jsonify(response), 200


# Backward compatibility exports for existing decorators
def login_required(f):
    """Backward compatibility wrapper for login_required decorator."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_error = _check_auth("login")
        if auth_error:
            return auth_error
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Backward compatibility wrapper for admin_required decorator."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_error = _check_auth("admin")
        if auth_error:
            return auth_error
        return f(*args, **kwargs)
    return decorated


def super_admin_required(f):
    """Backward compatibility wrapper for super_admin_required decorator."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_error = _check_auth("super_admin")
        if auth_error:
            return auth_error
        return f(*args, **kwargs)
    return decorated