from flask import Flask, session, jsonify
from flask_wtf.csrf import CSRFProtect
from config import config
import os
import logging
from logging.handlers import RotatingFileHandler

# Initialize extensions
csrf = CSRFProtect()

# Import utilities
from .utils import init_firebase, register_error_handlers as register_custom_error_handlers

# Configure logging
def configure_logging(app):
    """Configure application logging."""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(app.root_path, '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # File handler for errors
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'artisan_ai.log'),
        maxBytes=1024 * 1024 * 10,  # 10 MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Add handlers to app logger
    if not app.debug:
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Artisan AI startup')

def create_app(config_name='default'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Configure logging
    configure_logging(app)
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Initialize Firebase
    init_firebase(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register context processors
    register_context_processors(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register custom error handlers
    register_custom_error_handlers(app)
    
    return app

def register_blueprints(app):
    """Register Flask blueprints."""
    # Import blueprints here to avoid circular imports
    from .auth import auth_bp
    from .artisan import artisan_bp
    from .buyer import buyer_bp
    from .admin import admin_bp
    from .api import api_bp
    
    # Register blueprints with URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(artisan_bp, url_prefix='/artisan')
    app.register_blueprint(buyer_bp, url_prefix='/buyer')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

def register_context_processors(app):
    """Register template context processors."""
    @app.context_processor
    def inject_global_vars():
        from .security import generate_csrf_token
        return {
            'csrf_token': generate_csrf_token,
            'is_artisan': session.get('is_artisan', False),
            'is_authenticated': 'user_id' in session,
            'user_name': session.get('user_name', ''),
            'app_name': app.config.get('APP_NAME', 'Artisan AI')
        }

def register_error_handlers(app):
    """Register error handlers for both JSON and HTML responses."""
    from flask import request, render_template
    
    def wants_json_response():
        return request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']
    
    @app.errorhandler(400)
    def bad_request_error(error):
        if wants_json_response():
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Bad request',
                    'type': 'bad_request'
                }
            }), 400
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
