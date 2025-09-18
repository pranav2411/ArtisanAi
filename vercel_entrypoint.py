"""
Vercel Serverless Function Entry Point
This file is used as the entry point for Vercel serverless functions.
"""
import os
import sys
import json
import base64
import logging
import traceback
from functools import wraps
from io import BytesIO
from urllib.parse import parse_qs, urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    app = create_app()
    application = app  # For WSGI compatibility
except ImportError as e:
    logger.error(f"Failed to import application: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, X-CSRF-Token',
    'Access-Control-Allow-Credentials': 'true',
}

def handle_errors(f):
    """Decorator to handle errors in the handler function."""
    @wraps(f)
    def wrapper(event, context):
        try:
            return f(event, context)
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
                    'request_id': context.aws_request_id if context else None
                })
            }
    return wrapper

def parse_body(event):
    """Parse the request body based on content type."""
    content_type = event.get('headers', {}).get('content-type', '').lower()
    
    if not event.get('body'):
        return {}
        
    body = event['body']
    
    # Handle base64 encoded body
    if event.get('isBase64Encoded', False):
        body = base64.b64decode(body).decode('utf-8')
    
    # Parse JSON body
    if 'application/json' in content_type:
        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON body")
            return {}
    
    # Parse form data
    elif 'application/x-www-form-urlencoded' in content_type:
        return {k: v[0] if len(v) == 1 else v 
                for k, v in parse_qs(body).items()}
    
    # For multipart/form-data, we'll handle it in the route
    elif content_type.startswith('multipart/form-data'):
        return {}
        
    return body

def create_wsgi_environ(event, context):
    """Create a WSGI environment from the API Gateway event."""
    # Parse the request URL
    url = f"https://{event.get('requestContext', {}).get('domainName', '')}{event.get('path', '')}"
    if event.get('queryStringParameters'):
        url = f"{url}?{'&'.join([f'{k}={v}' for k, v in event['queryStringParameters'].items()])}"
    
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Build the WSGI environment
    environ = {
        'REQUEST_METHOD': event.get('httpMethod', 'GET'),
        'SCRIPT_NAME': '',
        'PATH_INFO': parsed_url.path,
        'QUERY_STRING': parsed_url.query or '',
        'SERVER_NAME': parsed_url.hostname or 'localhost',
        'SERVER_PORT': parsed_url.port or '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.url_scheme': parsed_url.scheme or 'http',
        'wsgi.input': BytesIO(event.get('body', '').encode('utf-8') 
                             if event.get('body') and not event.get('isBase64Encoded') 
                             else b''),
        'wsgi.errors': sys.stderr,
        'wsgi.version': (1, 0),
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
        'CONTENT_TYPE': event.get('headers', {}).get('content-type', ''),
        'CONTENT_LENGTH': str(len(event.get('body', '') or '')),
        'HTTP_COOKIE': event.get('headers', {}).get('cookie', ''),
    }
    
    # Add HTTP headers
    for key, value in (event.get('headers') or {}).items():
        if key.lower() == 'content-type':
            environ['CONTENT_TYPE'] = value
        elif key.lower() == 'content-length':
            environ['CONTENT_LENGTH'] = value
        else:
            # Convert header name to WSGI format (HTTP_X_FORWARDED_FOR, etc.)
            header_name = 'HTTP_' + key.upper().replace('-', '_')
            environ[header_name] = value
    
    # Add Vercel-specific headers
    environ.update({
        'vercel.request_id': event.get('requestContext', {}).get('requestId', ''),
        'vercel.stage': event.get('requestContext', {}).get('stage', '$default'),
        'vercel.identity': json.dumps(event.get('requestContext', {}).get('identity', {})),
    })
    
    return environ

@handle_errors
def handler(event, context):
    """Handle Vercel serverless function requests."""
    logger.info(f"Processing request: {event.get('httpMethod')} {event.get('path')}")
    
    # Handle preflight requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Max-Age': '3600'
            },
            'body': ''
        }
    
    # Convert Vercel event to WSGI environment
    environ = {
        'REQUEST_METHOD': event.get('httpMethod', 'GET'),
        'PATH_INFO': event.get('path', '/'),
        'QUERY_STRING': '&'.join([f"{k}={v}" for k, v in event.get('queryStringParameters', {}).items()]),
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https' if event.get('headers', {}).get('x-forwarded-proto') == 'https' else 'http',
        'wsgi.input': BytesIO(event.get('body', '').encode() if event.get('body') else b''),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
    }
    
    # Add headers
    for key, value in event.get('headers', {}).items():
        key = key.upper().replace('-', '_')
        if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            key = 'HTTP_' + key
        environ[key] = value
    
    # Start response
    response_headers = []
    response_status = []
    response_body = []
    
    def start_response(status, headers, exc_info=None):
        nonlocal response_status, response_headers
        response_status = status
        response_headers = dict(headers)
        return response_body.append
    
    # Process the request
    result = application(environ, start_response)
    
    # Get the response body
    try:
        response_body = []
        for chunk in result:
            response_body.append(chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk)
        
        if hasattr(result, 'close'):
            result.close()
        
        # Build the response
        response = {
            'statusCode': int(response_status.split(' ')[0]) if response_status else 200,
            'headers': response_headers,
            'body': ''.join(response_body)
        }
        
        # Add CORS headers
        response['headers']['Access-Control-Allow-Origin'] = '*'
        response['headers']['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['headers']['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': '{"error": "Internal Server Error", "message": "Error processing response"}'
        }

# For local testing
if __name__ == "__main__":
    from werkzeug.serving import run_simple
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
