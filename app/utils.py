import os
import uuid
from functools import wraps
from flask import jsonify, request, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime, timedelta
import re

# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, folder='uploads'):
    """
    Save an uploaded file to the specified folder.
    Returns the file path if successful, None otherwise.
    """
    if not file or file.filename == '':
        return None
        
    if not allowed_file(file.filename):
        return None
    
    # Create a secure filename
    filename = secure_filename(file.filename)
    # Add a unique identifier to prevent filename collisions
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    
    # Create the upload folder if it doesn't exist
    upload_folder = os.path.join(current_app.root_path, 'static', folder)
    os.makedirs(upload_folder, exist_ok=True)
    
    # Save the file
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    
    # Return the relative path for web access
    return os.path.join('static', folder, unique_filename)

def json_response(data=None, status=200, message=None, **kwargs):
    """Create a standardized JSON response."""
    response = {
        'success': 200 <= status < 300,
        'status': status,
    }
    
    if message:
        response['message'] = message
        
    if data is not None:
        response['data'] = data
        
    # Add any additional kwargs to the response
    response.update(kwargs)
    
    return jsonify(response), status

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate phone number format (supports international numbers)."""
    pattern = r'^\+?[1-9]\d{1,14}$'  # E.164 format
    return re.match(pattern, phone) is not None

def format_currency(amount, currency='INR'):
    """Format a number as currency."""
    try:
        amount = float(amount)
        if currency == 'INR':
            return f'₹{amount:,.2f}'.replace('.00', '')
        elif currency == 'USD':
            return f'${amount:,.2f}'
        else:
            return f'{amount:,.2f} {currency}'
    except (ValueError, TypeError):
        return str(amount)

def paginate(query, page=1, per_page=10):
    """Paginate a SQLAlchemy query."""
    return query.paginate(page=page, per_page=per_page, error_out=False)

def handle_file_upload():
    """Decorator to handle file uploads with error handling."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'file' not in request.files:
                return json_response(
                    {'error': 'No file part'}, 
                    status=400
                )
                
            file = request.files['file']
            
            if file.filename == '':
                return json_response(
                    {'error': 'No selected file'}, 
                    status=400
                )
                
            if not allowed_file(file.filename):
                return json_response(
                    {'error': 'File type not allowed'}, 
                    status=400
                )
                
            try:
                # Check file size
                if request.content_length > MAX_CONTENT_LENGTH:
                    return json_response(
                        {'error': 'File too large'}, 
                        status=413
                    )
                    
                return f(file, *args, **kwargs)
                
            except RequestEntityTooLarge:
                return json_response(
                    {'error': 'File too large'}, 
                    status=413
                )
                
        return decorated_function
    return decorator

def generate_otp(length=6):
    """Generate a random OTP of specified length."""
    import random
    numbers = '0123456789'
    return ''.join(random.choice(numbers) for _ in range(length))

def is_safe_redirect(target):
    """Check if the redirect target is safe."""
    from urllib.parse import urlparse, urljoin
    from flask import request
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

def get_pagination_params():
    """Get pagination parameters from request args."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 items per page
    return page, per_page

def to_camel_case(snake_str):
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])
