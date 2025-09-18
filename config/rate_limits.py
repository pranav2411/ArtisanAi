"""
Rate Limit Configuration

This module defines rate limiting configurations for different parts of the application.
"""

# Rate limits are defined as (requests, seconds)
RATE_LIMITS = {
    # Public endpoints (e.g., landing page, public API)
    'public': (100, 60),  # 100 requests per minute per IP
    
    # Authentication endpoints
    'auth': {
        'login': (5, 60),          # 5 login attempts per minute per IP
        'register': (3, 60),       # 3 registration attempts per minute per IP
        'password_reset': (3, 60), # 3 password reset attempts per minute per IP
    },
    
    # API endpoints
    'api': {
        'default': (1000, 3600),    # 1000 requests per hour per user
        'public': (100, 60),        # 100 requests per minute per IP
        'authenticated': (500, 300), # 500 requests per 5 minutes per user
    },
    
    # Sensitive operations (e.g., checkout, profile updates)
    'sensitive': (10, 60),  # 10 requests per minute per user
    
    # File uploads
    'uploads': (20, 300),  # 20 uploads per 5 minutes per user
    
    # Admin endpoints
    'admin': (200, 60),  # 200 requests per minute per admin user
    
    # Search endpoints (to prevent abuse)
    'search': (30, 60),  # 30 searches per minute per user
}

def get_rate_limit(category: str, subcategory: str = None) -> tuple[int, int]:
    """Get the rate limit for a category and optional subcategory.
    
    Args:
        category: The main rate limit category.
        subcategory: Optional subcategory for more specific rate limiting.
        
    Returns:
        A tuple of (limit, seconds) for the rate limit.
        
    Raises:
        KeyError: If the category or subcategory doesn't exist.
    """
    if category not in RATE_LIMITS:
        raise KeyError(f"Unknown rate limit category: {category}")
    
    limits = RATE_LIMITS[category]
    
    # If it's a nested dictionary, get the subcategory
    if isinstance(limits, dict):
        if subcategory not in limits:
            if 'default' in limits:
                return limits['default']
            raise KeyError(
                f"Unknown rate limit subcategory '{subcategory}' "
                f"for category '{category}'"
            )
        return limits[subcategory]
    
    # Otherwise, return the direct limit
    return limits

def get_rate_limit_for_endpoint(endpoint: str) -> tuple[int, int]:
    """Get the rate limit for a specific endpoint.
    
    This is a convenience function that maps endpoints to rate limit categories.
    
    Args:
        endpoint: The endpoint path (e.g., 'auth.login', 'api.v1.products').
        
    Returns:
        A tuple of (limit, seconds) for the rate limit.
    """
    # Default rate limit
    default_limit = (100, 60)  # 100 requests per minute
    
    # Map endpoints to rate limit categories
    endpoint_map = {
        # Auth endpoints
        'auth.login': get_rate_limit('auth', 'login'),
        'auth.register': get_rate_limit('auth', 'register'),
        'auth.forgot_password': get_rate_limit('auth', 'password_reset'),
        'auth.reset_password': get_rate_limit('auth', 'password_reset'),
        
        # API endpoints
        'api.v1.': get_rate_limit('api', 'default'),
        'api.public.': get_rate_limit('api', 'public'),
        
        # Admin endpoints
        'admin.': get_rate_limit('admin'),
        
        # Upload endpoints
        'upload.': get_rate_limit('uploads'),
        
        # Search endpoints
        'search.': get_rate_limit('search'),
    }
    
    # Find the most specific match
    for prefix, limit in endpoint_map.items():
        if endpoint.startswith(prefix):
            return limit
    
    return default_limit
