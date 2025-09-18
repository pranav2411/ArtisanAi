"""
Error Handlers

This module contains error handlers for the application.
"""

import time

from flask import jsonify
from werkzeug.exceptions import (
    HTTPException, 
    BadRequest, 
    Unauthorized, 
    Forbidden, 
    NotFound, 
    InternalServerError,
    TooManyRequests
)

from .firebase_utils import (
    FirebaseServiceError,
    FirebaseAuthError,
    FirebaseNotFoundError,
    FirebaseValidationError
)


def register_error_handlers(app):
    """Register error handlers with the Flask application."""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors."""
        if isinstance(error, HTTPException):
            message = error.description
        else:
            message = 'Bad request.'
        
        response = jsonify({
            'success': False,
            'error': {
                'code': 400,
                'message': message,
                'type': 'bad_request'
            }
        })
        response.status_code = 400
        return response
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 Unauthorized errors."""
        if isinstance(error, HTTPException):
            message = error.description
        else:
            message = 'Authentication required.'
        
        response = jsonify({
            'success': False,
            'error': {
                'code': 401,
                'message': message,
                'type': 'unauthorized'
            }
        })
        response.status_code = 401
        response.headers['WWW-Authenticate'] = 'Bearer'
        return response
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors."""
        if isinstance(error, HTTPException):
            message = error.description
        else:
            message = 'You do not have permission to access this resource.'
        
        response = jsonify({
            'success': False,
            'error': {
                'code': 403,
                'message': message,
                'type': 'forbidden'
            }
        })
        response.status_code = 403
        return response
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        if isinstance(error, HTTPException):
            message = error.description
        else:
            message = 'The requested resource was not found.'
        
        response = jsonify({
            'success': False,
            'error': {
                'code': 404,
                'message': message,
                'type': 'not_found'
            }
        })
        response.status_code = 404
        return response
    
    @app.errorhandler(422)
    def unprocessable_entity_error(error):
        """Handle 422 Unprocessable Entity errors."""
        if hasattr(error, 'exc') and hasattr(error.exc, 'messages'):
            messages = error.exc.messages
        else:
            messages = ['Invalid request data.']
        
        response = jsonify({
            'success': False,
            'error': {
                'code': 422,
                'message': 'Validation error.',
                'type': 'validation_error',
                'details': messages
            }
        })
        response.status_code = 422
        return response
    
    @app.errorhandler(TooManyRequests)
    @app.errorhandler(429)
    def ratelimit_error(error):
        """Handle 429 Too Many Requests errors."""
        if hasattr(error, 'retry_after') and error.retry_after:
            message = f'Too many requests. Please try again in {error.retry_after} seconds.'
            headers = {
                'Retry-After': str(error.retry_after),
                'X-RateLimit-Reset': str(int(time.time()) + error.retry_after)
            }
        else:
            message = 'Too many requests. Please try again later.'
            headers = {}
        
        response = jsonify({
            'success': False,
            'error': {
                'code': 429,
                'message': message,
                'type': 'rate_limit_exceeded',
                'retry_after': getattr(error, 'retry_after', None)
            }
        })
        
        response.status_code = 429
        response.headers.update(headers)
        return response
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server errors."""
        # In production, don't expose the actual error message
        if app.config.get('DEBUG'):
            message = str(error) if str(error) else 'An internal server error occurred.'
        else:
            message = 'An internal server error occurred.'
        
        response = jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': message,
                'type': 'internal_server_error'
            }
        })
        response.status_code = 500
        return response
    
    # Firebase Error Handlers
    @app.errorhandler(FirebaseAuthError)
    def handle_firebase_auth_error(error):
        """Handle Firebase authentication errors."""
        response = jsonify({
            'success': False,
            'error': {
                'code': error.code,
                'message': error.message,
                'type': 'authentication_error',
                'details': error.details
            }
        })
        response.status_code = error.code
        return response
    
    @app.errorhandler(FirebaseNotFoundError)
    def handle_firebase_not_found_error(error):
        """Handle Firebase not found errors."""
        response = jsonify({
            'success': False,
            'error': {
                'code': error.code,
                'message': error.message,
                'type': 'not_found',
                'details': error.details
            }
        })
        response.status_code = error.code
        return response
    
    @app.errorhandler(FirebaseValidationError)
    def handle_firebase_validation_error(error):
        """Handle Firebase validation errors."""
        response = jsonify({
            'success': False,
            'error': {
                'code': error.code,
                'message': error.message,
                'type': 'validation_error',
                'details': error.details
            }
        })
        response.status_code = error.code
        return response
    
    @app.errorhandler(FirebaseServiceError)
    def handle_firebase_service_error(error):
        """Handle generic Firebase service errors."""
        response = jsonify({
            'success': False,
            'error': {
                'code': error.code,
                'message': error.message,
                'type': 'service_error',
                'details': error.details
            }
        })
        response.status_code = error.code
        return response
    
    # Default error handler for unhandled exceptions
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all other exceptions."""
        # Log the error
        app.logger.exception('Unhandled Exception: %s', error)
        
        # Return a generic error response
        response = jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'An unexpected error occurred.',
                'type': 'internal_server_error'
            }
        })
        response.status_code = 500
        return response
