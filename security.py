import functools
import os
import secrets
from flask import abort, flash, redirect, request, session, url_for
from functools import wraps

# CSRF Protection
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(16)
    return session['_csrf_token']

def csrf_protect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "POST":
            token = session.pop('_csrf_token', None)
            if not token or token != request.form.get('_csrf_token'):
                abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Authentication Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login_page', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def artisan_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login_page', next=request.url))
        if not session.get('is_artisan', False):
            flash('Artisan access required.', 'error')
            return redirect(url_for('marketplace'))
        return f(*args, **kwargs)
    return decorated_function

def buyer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login_page', next=request.url))
        if session.get('is_artisan', True):
            flash('Buyer access required.', 'error')
            return redirect(url_for('hub'))
        return f(*args, **kwargs)
    return decorated_function

# Input Validation
def validate_input(data, rules):
    """
    Validate input data against specified rules
    Example rules: {
        'username': {'type': 'string', 'required': True, 'min': 3, 'max': 50},
        'email': {'type': 'email', 'required': True},
        'age': {'type': 'integer', 'min': 18, 'max': 99}
    }
    """
    errors = {}
    
    for field, rule in rules.items():
        value = data.get(field)
        
        # Check required fields
        if rule.get('required', False) and (value is None or value == ''):
            errors[field] = f"{field.replace('_', ' ').title()} is required"
            continue
            
        # Skip further checks if field is empty and not required
        if value is None or value == '':
            continue
            
        # Type checking
        if rule.get('type') == 'email' and '@' not in value:
            errors[field] = "Invalid email format"
        elif rule.get('type') == 'integer':
            try:
                int_value = int(value)
                if 'min' in rule and int_value < rule['min']:
                    errors[field] = f"Must be at least {rule['min']}"
                if 'max' in rule and int_value > rule['max']:
                    errors[field] = f"Must be at most {rule['max']}"
            except (ValueError, TypeError):
                errors[field] = "Must be a valid number"
        elif rule.get('type') == 'string':
            if not isinstance(value, str):
                errors[field] = "Must be a string"
            else:
                if 'min' in rule and len(value) < rule['min']:
                    errors[field] = f"Must be at least {rule['min']} characters"
                if 'max' in rule and len(value) > rule['max']:
                    errors[field] = f"Must be at most {rule['max']} characters"
    
    return errors if errors else None

# Rate limiting (basic implementation)
class RateLimiter:
    def __init__(self, max_requests, window):
        self.max_requests = max_requests
        self.window = window  # in seconds
        self.requests = {}
    
    def is_rate_limited(self, identifier):
        current_time = time.time()
        
        # Clean up old entries
        self.requests[identifier] = [t for t in self.requests.get(identifier, []) 
                                   if current_time - t < self.window]
        
        # Check rate limit
        if len(self.requests.get(identifier, [])) >= self.max_requests:
            return True
        
        # Add current request
        if identifier not in self.requests:
            self.requests[identifier] = []
        self.requests[identifier].append(current_time)
        
        return False
