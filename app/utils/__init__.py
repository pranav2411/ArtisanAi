"""
Utility functions and classes for the Artisan AI application.
"""

from .firebase_utils import FirebaseService, firebase_service, init_firebase
from .error_handlers import register_error_handlers
from .rate_limiter import (
    RateLimitExceeded,
    rate_limited,
    get_rate_limit as get_rate_limit_config,
    RATE_LIMITS
)
from .decorators import (
    rate_limit,
    require_auth,
    require_role,
    validate_json
)

__all__ = [
    # Firebase
    'FirebaseService',
    'firebase_service',
    'init_firebase',
    
    # Error Handling
    'register_error_handlers',
    'RateLimitExceeded',
    
    # Rate Limiting
    'rate_limited',
    'rate_limit',
    'get_rate_limit_config',
    'RATE_LIMITS',
    
    # Decorators
    'require_auth',
    'require_role',
    'validate_json'
]
