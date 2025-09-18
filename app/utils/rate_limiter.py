"""
Rate Limiting Utilities

This module provides rate limiting functionality for the application.
"""

import time
from functools import wraps
from typing import Callable, Dict, Optional, Tuple, Union

from flask import request, jsonify, current_app
from werkzeug.exceptions import TooManyRequests

# In-memory storage for rate limiting (replace with Redis in production)
_rate_limits: Dict[str, Dict[str, Tuple[float, int]]] = {}

class RateLimitExceeded(TooManyRequests):
    """Exception raised when a rate limit is exceeded."""
    
    def __init__(self, retry_after: int):
        """Initialize the rate limit exception.
        
        Args:
            retry_after: Number of seconds after which the client can retry the request.
        """
        self.retry_after = retry_after
        headers = {
            'X-RateLimit-Limit': '0',
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': str(int(time.time()) + retry_after),
            'Retry-After': str(retry_after)
        }
        super().__init__(description=f'Rate limit exceeded. Try again in {retry_after} seconds.', response=None, headers=headers)

def get_ratelimit_key() -> str:
    """Get the rate limit key for the current request.
    
    Returns:
        A string that uniquely identifies the client for rate limiting purposes.
    """
    # Use the client's IP address by default
    key = request.remote_addr or 'unknown'
    
    # If the user is authenticated, use their user ID
    if hasattr(request, 'user') and request.user and hasattr(request.user, 'uid'):
        key = f"user:{request.user.uid}"
    
    # Include the endpoint in the key to rate limit endpoints separately
    endpoint = request.endpoint or 'unknown'
    return f"{key}:{endpoint}"

def clear_expired_limits():
    """Clear expired rate limit entries."""
    current_time = time.time()
    expired_keys = [
        key for key, (expiry, _) in _rate_limits.items() 
        if expiry <= current_time
    ]
    for key in expired_keys:
        _rate_limits.pop(key, None)

def rate_limited(
    limit: int = 100, 
    per: int = 60, 
    key_func: Optional[Callable[[], str]] = None,
    error_message: Optional[str] = None
):
    """Decorator to rate limit a Flask route.
    
    Args:
        limit: Maximum number of requests allowed in the time window.
        per: Time window in seconds.
        key_func: Function that returns a key to identify the client.
                 Defaults to get_ratelimit_key.
        error_message: Custom error message to return when rate limit is exceeded.
        
    Returns:
        The decorated function.
    """
    if key_func is None:
        key_func = get_ratelimit_key
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip rate limiting in testing mode
            if current_app.config.get('TESTING'):
                return f(*args, **kwargs)
                
            # Clear expired rate limits
            clear_expired_limits()
            
            # Get the rate limit key
            key = key_func()
            current_time = time.time()
            
            # Get or initialize the rate limit entry
            expiry, count = _rate_limits.get(key, (current_time + per, 0))
            
            # Check if the time window has expired
            if current_time > expiry:
                count = 0
                expiry = current_time + per
            
            # Check if the rate limit has been exceeded
            if count >= limit:
                retry_after = int(expiry - current_time) + 1
                raise RateLimitExceeded(retry_after=retry_after)
            
            # Update the rate limit counter
            count += 1
            _rate_limits[key] = (expiry, count)
            
            # Add rate limit headers to the response
            response = f(*args, **kwargs)
            remaining = max(0, limit - count)
            reset = int(expiry)
            
            if not isinstance(response, tuple):
                response = (response, 200, {})
            elif len(response) == 2:
                response = (response[0], response[1], {})
            
            headers = response[2] if len(response) > 2 else {}
            headers.update({
                'X-RateLimit-Limit': str(limit),
                'X-RateLimit-Remaining': str(remaining),
                'X-RateLimit-Reset': str(reset)
            })
            
            return response[0], response[1], headers
        
        return decorated_function
    
    return decorator

# Rate limit categories with default values
RATE_LIMITS = {
    'public': (100, 60),  # 100 requests per minute
    'auth': (10, 60),     # 10 requests per minute for authentication endpoints
    'api': (1000, 3600),  # 1000 requests per hour for API endpoints
    'strict': (5, 60),    # 5 requests per minute for sensitive operations
}

def get_rate_limit(category: str) -> Tuple[int, int]:
    """Get the rate limit for a category.
    
    Args:
        category: The rate limit category.
        
    Returns:
        A tuple of (limit, per_seconds).
    """
    return RATE_LIMITS.get(category, (100, 60))  # Default to 100 requests per minute
