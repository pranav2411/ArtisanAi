#!/usr/bin/env python3
"""
Environment Configuration Checker

This script checks if all required environment variables are set and have valid values.
It helps ensure that the application is properly configured before starting.
"""

import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define required environment variables and their validation rules
REQUIRED_ENV_VARS = {
    # Flask
    'FLASK_APP': {
        'required': True,
        'default': 'app.py',
        'description': 'The name of the Flask application file',
    },
    'FLASK_ENV': {
        'required': True,
        'default': 'development',
        'allowed': ['development', 'testing', 'production'],
        'description': 'The environment to run the Flask app in (development, testing, production)',
    },
    'FLASK_SECRET_KEY': {
        'required': True,
        'min_length': 32,
        'description': 'A secret key for securely signing the session cookie and other security related needs',
    },
    
    # Firebase
    'FIREBASE_API_KEY': {
        'required': True,
        'description': 'Firebase API key for authentication',
    },
    'FIREBASE_AUTH_DOMAIN': {
        'required': True,
        'pattern': r'.+\.firebaseapp\.com$',
        'description': 'Firebase authentication domain',
    },
    'FIREBASE_PROJECT_ID': {
        'required': True,
        'description': 'Firebase project ID',
    },
    'FIREBASE_STORAGE_BUCKET': {
        'required': True,
        'pattern': r'.+\.appspot\.com$',
        'description': 'Firebase Storage bucket name',
    },
    'FIREBASE_MESSAGING_SENDER_ID': {
        'required': True,
        'description': 'Firebase messaging sender ID',
    },
    'FIREBASE_APP_ID': {
        'required': True,
        'description': 'Firebase app ID',
    },
    'FIREBASE_MEASUREMENT_ID': {
        'required': False,
        'description': 'Firebase measurement ID for Google Analytics',
    },
    'GOOGLE_APPLICATION_CREDENTIALS': {
        'required': True,
        'file': True,
        'description': 'Path to the Firebase service account key JSON file',
    },
    
    # Google AI
    'GOOGLE_AI_API_KEY': {
        'required': True,
        'description': 'Google AI API key for accessing AI services',
    },
    
    # Email
    'MAIL_SERVER': {
        'required': True,
        'default': 'smtp.gmail.com',
        'description': 'Mail server hostname',
    },
    'MAIL_PORT': {
        'required': True,
        'default': '587',
        'type': int,
        'description': 'Mail server port',
    },
    'MAIL_USE_TLS': {
        'required': True,
        'default': 'True',
        'type': bool,
        'description': 'Enable TLS for mail',
    },
    'MAIL_USERNAME': {
        'required': True,
        'description': 'Mail server username',
    },
    'MAIL_PASSWORD': {
        'required': True,
        'description': 'Mail server password or app password',
    },
    'MAIL_DEFAULT_SENDER': {
        'required': True,
        'description': 'Default sender email address',
    },
    
    # Application
    'APP_NAME': {
        'required': True,
        'default': 'Artisan AI',
        'description': 'Name of the application',
    },
    'APP_URL': {
        'required': True,
        'default': 'http://localhost:5000',
        'description': 'Base URL of the application',
    },
    'ADMIN_EMAIL': {
        'required': True,
        'description': 'Admin email address for system notifications',
    },
    
    # Security
    'SECURITY_PASSWORD_SALT': {
        'required': True,
        'description': 'Salt for password hashing',
    },
    'RATELIMIT_DEFAULT': {
        'required': True,
        'default': '200 per day;50 per hour',
        'description': 'Default rate limiting rules',
    },
}

def check_environment():
    """Check if all required environment variables are set and valid."""
    print("🔍 Checking environment configuration...\n")
    
    errors = []
    warnings = []
    env_vars = {}
    
    # Check each required environment variable
    for var_name, rules in REQUIRED_ENV_VARS.items():
        value = os.environ.get(var_name)
        
        # If value is not set, use default if available
        if value is None and 'default' in rules:
            value = rules['default']
            os.environ[var_name] = str(value) if value is not None else ''
        
        # Check if required but not set
        if rules.get('required', False) and not value:
            errors.append(f"❌ {var_name}: Required but not set")
            continue
        
        # Skip further checks if value is not set and not required
        if not value:
            continue
        
        # Type conversion and validation
        if 'type' in rules:
            try:
                if rules['type'] == int:
                    value = int(value)
                elif rules['type'] == bool:
                    value = value.lower() in ('true', '1', 't', 'y', 'yes')
            except (ValueError, TypeError):
                errors.append(f"❌ {var_name}: Expected {rules['type'].__name__} but got '{value}'")
                continue
        
        # Check minimum length
        if 'min_length' in rules and len(str(value)) < rules['min_length']:
            errors.append(f"❌ {var_name}: Must be at least {rules['min_length']} characters long")
        
        # Check against allowed values
        if 'allowed' in rules and value not in rules['allowed']:
            errors.append(f"❌ {var_name}: Must be one of {', '.join(rules['allowed'])} (got '{value}')")
        
        # Check pattern match
        if 'pattern' in rules and not re.match(rules['pattern'], str(value)):
            errors.append(f"❌ {var_name}: Does not match required pattern")
        
        # Check if file exists
        if rules.get('file', False) and not Path(value).is_file():
            errors.append(f"❌ {var_name}: File not found at '{value}'")
        
        # Store the value for output
        env_vars[var_name] = value
    
    # Check for sensitive data in .env
    check_sensitive_data_exposure()
    
    # Print results
    if errors:
        print("\n❌ Found errors in environment configuration:")
        for error in errors:
            print(f"  {error}")
    else:
        print("✅ All required environment variables are properly configured")
    
    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"  {warning}")
    
    # Print environment summary
    print("\n📋 Environment Summary:")
    print(f"  Environment: {os.environ.get('FLASK_ENV', 'Not set')}")
    print(f"  App Name: {os.environ.get('APP_NAME', 'Not set')}")
    print(f"  App URL: {os.environ.get('APP_URL', 'Not set')}")
    print(f"  Debug Mode: {os.environ.get('FLASK_DEBUG', 'Not set')}")
    
    # Check if running in production with debug mode on
    if os.environ.get('FLASK_ENV') == 'production' and os.environ.get('FLASK_DEBUG', '').lower() in ('true', '1', 't'):
        warnings.append("⚠️  WARNING: Debug mode is enabled in production. This is a security risk!")
    
    # Check if using default secret key in production
    if os.environ.get('FLASK_ENV') == 'production' and os.environ.get('FLASK_SECRET_KEY', '').strip() in ('', 'dev', 'change-this-in-production'):
        errors.append("❌ SECURITY RISK: Using default or empty secret key in production")
    
    # Return appropriate exit code
    if errors:
        print("\n❌ Please fix the above errors before starting the application")
        return 1
    
    print("\n✅ Environment is ready. You can start the application.")
    return 0

def check_sensitive_data_exposure():
    """Check for sensitive data exposure in .env file."""
    env_file = Path('.env')
    if not env_file.is_file():
        return
    
    sensitive_terms = [
        'key', 'secret', 'password', 'token', 'credential',
        'api_key', 'api_secret', 'private_key', 'access_key', 'auth'
    ]
    
    with open(env_file, 'r') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Check for unquoted values with spaces
            if '=' in line and not line.split('=')[1].strip().startswith(('"', "'")) and ' ' in line.split('=', 1)[1]:
                print(f"⚠️  Line {i}: Unquoted value with spaces: {line.split('=')[0]}")
            
            # Check for potentially sensitive variable names
            var_name = line.split('=')[0].lower()
            if any(term in var_name for term in sensitive_terms) and 'example' not in var_name:
                print(f"⚠️  Line {i}: Potentially sensitive variable: {var_name}")

def generate_env_example():
    """Generate a .env.example file with all required variables."""
    example_lines = [
        "# Application Settings",
        f"FLASK_APP={REQUIRED_ENV_VARS['FLASK_APP'].get('default', '')}",
        f"FLASK_ENV={REQUIRED_ENV_VARS['FLASK_ENV'].get('default', 'development')}",
        "FLASK_SECRET_KEY=change-this-to-a-secure-random-string",
        "",
        "# Firebase Configuration",
        "FIREBASE_API_KEY=your-firebase-api-key",
        "FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com",
        "FIREBASE_PROJECT_ID=your-project-id",
        "FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com",
        "FIREBASE_MESSAGING_SENDER_ID=your-messaging-sender-id",
        "FIREBASE_APP_ID=your-app-id",
        "FIREBASE_MEASUREMENT_ID=G-XXXXXXXXXX",
        "GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json",
        "",
        "# Google AI",
        "GOOGLE_AI_API_KEY=your-google-ai-api-key",
        "",
        "# Email Configuration",
        "MAIL_SERVER=smtp.gmail.com",
        "MAIL_PORT=587",
        "MAIL_USE_TLS=True",
        "MAIL_USERNAME=your-email@gmail.com",
        "MAIL_PASSWORD=your-app-password",
        "MAIL_DEFAULT_SENDER=your-email@gmail.com",
        "",
        "# Application Settings",
        "APP_NAME=Artisan AI",
        "APP_URL=http://localhost:5000",
        "ADMIN_EMAIL=admin@example.com",
        "",
        "# Security",
        "SECURITY_PASSWORD_SALT=change-this-to-a-secure-random-salt",
        "RATELIMIT_DEFAULT=200 per day;50 per hour",
        "",
        "# Optional: Database (if using SQLAlchemy)",
        "# DATABASE_URL=sqlite:///app.db",
        "# DATABASE_URL=postgresql://user:password@localhost:5432/dbname",
        "",
        "# Optional: Google Analytics",
        "# GOOGLE_ANALYTICS_ID=UA-XXXXXXXXX-X",
        "",
        "# Optional: Sentry (for error tracking)",
        "# SENTRY_DSN=https://your-sentry-dsn.ingest.sentry.io/1234567",
        "",
        "# Optional: AWS S3 (if using S3 for file storage)",
        "# AWS_ACCESS_KEY_ID=your-access-key",
        "# AWS_SECRET_ACCESS_KEY=your-secret-key",
        "# AWS_STORAGE_BUCKET_NAME=your-bucket-name",
        "# AWS_S3_REGION=us-east-1",
    ]
    
    with open('.env.example', 'w') as f:
        f.write('\n'.join(example_lines) + '\n')
    
    print("✅ Generated .env.example file")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Check and manage environment configuration')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check environment configuration')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate .env.example file')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        generate_env_example()
    else:
        sys.exit(check_environment())
