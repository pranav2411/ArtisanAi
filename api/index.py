"""
Vercel Serverless Function
This file handles the Vercel serverless function requests.
"""
import os
import sys
import json
import logging
import traceback
from functools import wraps
from werkzeug.serving import run_simple
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wrappers import Response

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, X-CSRF-Token',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Max-Age': '86400',  # 24 hours
}

try:
    from app import create_app
    app = create_app()
    from serverless_wsgi import handle_request
    
    # Set up application context for background tasks
    app.app_context().push()
    
except Exception as e:
    logger.error(f"Failed to import application: {str(e)}")
    logger.error(traceback.format_exc())
    raise

def handle_errors(f):
    """Decorator to handle errors in the handler function."""
    @wraps(f)
    def wrapper(event, context):
        try:
            return f(event, context)
        except HTTPException as e:
            logger.error(f"HTTP Error {e.code}: {e.name} - {e.description}")
            return {
                'statusCode': e.code,
                'headers': {
                    'Content-Type': 'application/json',
                    **CORS_HEADERS
                },
                'body': json.dumps({
                    'error': e.name,
                    'message': e.description,
                    'status': e.code
                })
            }
        except Exception as e:
            logger.error(f"Unhandled exception: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    **CORS_HEADERS
                },
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': 'An unexpected error occurred',
                    'request_id': context.aws_request_id if hasattr(context, 'aws_request_id') else None
                })
            }
    return wrapper

def create_response(status_code, body, headers=None):
    """Create a standardized response object."""
    if headers is None:
        headers = {}
    
    response_headers = {
        'Content-Type': 'application/json',
        **CORS_HEADERS,
        **headers
    }
    
    if not isinstance(body, str):
        body = json.dumps(body)
    
    return {
        'statusCode': status_code,
        'headers': response_headers,
        'body': body
    }

@handle_errors
def handler(event, context):
    """Handle Vercel serverless function requests."""
    logger.info(f"Processing request: {event.get('httpMethod')} {event.get('path')}")
    
    # Handle preflight requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }
    
    try:
        # Process the request using serverless-wsgi
        response = handle_request(app, event, context)
        
        # Ensure CORS headers are included in the response
        if 'headers' not in response:
            response['headers'] = {}
        
        # Merge CORS headers with any existing headers
        response['headers'] = {**CORS_HEADERS, **response.get('headers', {})}
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        return create_response(
            500,
            {
                'error': 'Internal Server Error',
                'message': 'An error occurred while processing your request',
                'details': str(e) if app.debug else None
            }
        )
    # Process the request
    response = handle_request(app, event, context)
    
    # Add CORS headers to the response
    if isinstance(response, dict) and 'headers' in response:
        headers = response.get('headers', {})
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response['headers'] = headers
    
    return response

# For local testing
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting development server on http://localhost:{port}")
    run_simple(
        '0.0.0.0', 
        port, 
        app, 
        use_reloader=True, 
        use_debugger=True, 
        use_evalex=True,
        threaded=True
    )
