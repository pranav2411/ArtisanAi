"""
Useful decorators for the application.
"""

from functools import wraps
from typing import Callable, Optional, Tuple, Union

from flask import request, current_app, jsonify
from werkzeug.exceptions import TooManyRequests

from .rate_limiter import rate_limited, get_rate_limit as get_app_rate_limit
from ..config.rate_limits import get_rate_limit_for_endpoint


def rate_limit(
    limit: Optional[Union[int, str]] = None,
    per: Optional[int] = None,
    key_func: Optional[Callable[[], str]] = None,
    error_message: Optional[str] = None,
    category: Optional[str] = None
):
    """Decorator to rate limit a route.
    
    This is a more user-friendly wrapper around the rate_limited decorator
    that integrates with the application's rate limiting configuration.
    
    Args:
        limit: Maximum number of requests allowed in the time window.
               If None, will be determined from the rate limit configuration.
        per: Time window in seconds. If None, will be determined from the 
             rate limit configuration.
        key_func: Function that returns a key to identify the client.
        error_message: Custom error message to return when rate limit is exceeded.
        category: Category to use for rate limiting. If not provided, will be
                 determined from the endpoint name.
    
    Returns:
        The decorated function.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip rate limiting in testing mode
            if current_app.config.get('TESTING'):
                return f(*args, **kwargs)
            
            # Get the endpoint name
            endpoint = request.endpoint or 'unknown'
            
            # Get rate limit from config if not explicitly provided
            if limit is None or per is None:
                if category:
                    # Use the provided category
                    config_limit = get_app_rate_limit(category)
                else:
                    # Determine category from endpoint
                    config_limit = get_rate_limit_for_endpoint(endpoint)
                
                # Override with explicit values if provided
                _limit = limit if limit is not None else config_limit[0]
                _per = per if per is not None else config_limit[1]
            else:
                _limit, _per = limit, per
            
            # Apply the rate limit
            return rate_limited(
                limit=_limit,
                per=_per,
                key_func=key_func,
                error_message=error_message
            )(f)(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'user') or not request.user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 401,
                    'message': 'Authentication required',
                    'type': 'authentication_required'
                }
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def require_role(role: str):
    """Decorator to require a specific role for a route.
    
    Args:
        role: The required role (e.g., 'admin', 'moderator').
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'user') or not request.user:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 401,
                        'message': 'Authentication required',
                        'type': 'authentication_required'
                    }
                }), 401
            
            # Check if user has the required role
            user_roles = getattr(request.user, 'roles', [])
            if role not in user_roles:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'Insufficient permissions',
                        'type': 'insufficient_permissions'
                    }
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def validate_json(schema):
    """Decorator to validate JSON request data against a schema.
    
    Args:
        schema: A marshmallow Schema class to validate against.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 400,
                        'message': 'Request must be JSON',
                        'type': 'invalid_content_type'
                    }
                }), 400
            
            try:
                data = request.get_json()
                result = schema().load(data)
                # Add the validated data to the request object
                request.validated_data = result
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 400,
                        'message': 'Invalid request data',
                        'type': 'validation_error',
                        'details': str(e)
                    }
                }), 400
        
        return decorated_function
    
    return decorator
