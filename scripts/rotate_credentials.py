#!/usr/bin/env python3
"""
Credential Rotation Script

This script helps rotate API keys and credentials securely.
It generates new secure values and updates the necessary configuration files.
"""

import os
import sys
import secrets
import string
import json
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import subprocess
import platform

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(message):
    """Print a formatted header message."""
    print(f"\n{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{message:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")

def print_success(message):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

def print_warning(message):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")

def print_error(message):
    """Print an error message and exit."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}", file=sys.stderr)
    sys.exit(1)

def generate_secure_string(length=64):
    """Generate a secure random string."""
    alphabet = string.ascii_letters + string.digits + "-_~"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_api_key(prefix='sk_'):
    """Generate a secure API key with an optional prefix."""
    return prefix + generate_secure_string(32)

def generate_password(length=24):
    """Generate a secure password with mixed case, numbers, and symbols."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure the password has at least one of each character type
        if (any(c.islower() for c in password) 
                and any(c.isupper() for c in password) 
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password

def update_env_file(updates, env_path='.env'):
    """Update key-value pairs in an environment file."""
    try:
        # Read the current content
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Track which keys we've updated
        updated_keys = set()
        
        # Update existing keys
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Split on first '=' only
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                if key in updates:
                    # Preserve comments after the value if they exist
                    value = updates[key]
                    comment = ''
                    if '#' in parts[1]:
                        value_part, comment = parts[1].split('#', 1)
                        comment = ' #' + comment
                    
                    lines[i] = f"{key}={value}{comment}\n"
                    updated_keys.add(key)
        
        # Add new keys that weren't in the file
        for key, value in updates.items():
            if key not in updated_keys:
                lines.append(f"{key}={value}\n")
        
        # Create a backup of the original file
        backup_path = f"{env_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(env_path, backup_path)
        
        # Write the updated content
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        return backup_path
        
    except Exception as e:
        print_error(f"Failed to update {env_path}: {str(e)}")

def rotate_flask_secret_key():
    """Generate a new Flask secret key."""
    return generate_secure_string(32)

def rotate_firebase_credentials():
    """Guide the user through rotating Firebase credentials."""
    print_header("Rotating Firebase Credentials")
    
    # Get the current service account file path from environment
    service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not service_account_path:
        print_warning("GOOGLE_APPLICATION_CREDENTIALS not set in .env")
        service_account_path = input("Enter path to save the new service account key: ")
    
    print("\nTo rotate Firebase credentials:")
    print("1. Go to Firebase Console > Project Settings > Service Accounts")
    print("2. Click 'Generate New Private Key'")
    print(f"3. Save the JSON file as '{service_account_path}'")
    
    if input("\nOpen Firebase Console in browser? [y/N]: ").lower() == 'y':
        import webbrowser
        webbrowser.open("https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk")
    
    input("\nPress Enter after you've downloaded the new service account key...")
    
    # Verify the file exists
    if not os.path.exists(service_account_path):
        print_warning(f"Service account key not found at {service_account_path}")
        return False
    
    # Read the new API key from the service account file
    try:
        with open(service_account_path, 'r') as f:
            service_account = json.load(f)
        
        # The API key is not in the service account JSON, we need to get it from the Firebase config
        print("\nTo get the new Firebase API key:")
        print("1. Go to Firebase Console > Project Settings > General")
        print("2. Under 'Your apps', select your web app")
        print("3. Copy the 'apiKey' value")
        
        new_api_key = input("\nEnter the new Firebase API key: ").strip()
        
        updates = {
            'FIREBASE_API_KEY': new_api_key,
            'GOOGLE_APPLICATION_CREDENTIALS': service_account_path
        }
        
        backup_path = update_env_file(updates)
        print_success(f"Updated .env file (backup saved to {backup_path})")
        return True
        
    except Exception as e:
        print_error(f"Failed to process service account file: {str(e)}")
        return False

def rotate_google_ai_key():
    """Guide the user through rotating the Google AI API key."""
    print_header("Rotating Google AI API Key")
    
    print("To get a new Google AI API key:")
    print("1. Go to Google AI Studio: https://makersuite.google.com/")
    print("2. Click on 'Get API key'")
    print("3. Create a new API key")
    
    new_key = input("\nEnter the new Google AI API key: ").strip()
    
    if not new_key:
        print_warning("No API key provided, skipping...")
        return False
    
    updates = {
        'GOOGLE_AI_API_KEY': new_key
    }
    
    backup_path = update_env_file(updates)
    print_success(f"Updated .env file with new Google AI API key (backup saved to {backup_path})")
    return True

def rotate_email_credentials():
    """Guide the user through rotating email credentials."""
    print_header("Rotating Email Credentials")
    
    print("To update email settings:")
    print("1. Go to your email provider's security settings")
    print("2. Generate a new app password")
    print("   - For Gmail: https://myaccount.google.com/apppasswords")
    
    new_email = input("\nEnter email address [press Enter to keep current]: ").strip()
    new_password = input("Enter new app password [press Enter to skip]: ").strip()
    
    updates = {}
    
    if new_email:
        updates['MAIL_USERNAME'] = new_email
        updates['MAIL_DEFAULT_SENDER'] = new_email
    
    if new_password:
        updates['MAIL_PASSWORD'] = new_password
    
    if updates:
        backup_path = update_env_file(updates)
        print_success(f"Updated email settings in .env (backup saved to {backup_path})")
        return True
    else:
        print_warning("No changes made to email settings")
        return False

def rotate_database_credentials():
    """Guide the user through rotating database credentials."""
    print_header("Rotating Database Credentials")
    
    current_db_url = os.getenv('DATABASE_URL', '')
    
    if not current_db_url:
        print_warning("DATABASE_URL not found in .env")
        new_db_url = input("Enter the new database URL (e.g., postgresql://user:password@localhost:5432/dbname): ").strip()
    else:
        print(f"Current database URL: {current_db_url}")
        print("\nTo rotate database credentials:")
        print("1. Connect to your database server")
        print("2. Create a new user with the same permissions")
        print("3. Update the password for the database user")
        
        new_db_url = input("\nEnter the new database URL [press Enter to skip]: ").strip()
    
    if not new_db_url:
        print_warning("No database URL provided, skipping...")
        return False
    
    # Validate the database URL format
    try:
        parsed = urlparse(new_db_url)
        if not all([parsed.scheme, parsed.path]):
            raise ValueError("Invalid database URL format")
    except Exception as e:
        print_error(f"Invalid database URL: {str(e)}")
        return False
    
    updates = {
        'DATABASE_URL': new_db_url
    }
    
    backup_path = update_env_file(updates)
    print_success(f"Updated database URL in .env (backup saved to {backup_path})")
    
    print("\nNote: You'll need to update the database credentials in your database server "
          "and ensure the application has the new credentials.")
    return True

def rotate_flask_config():
    """Rotate Flask configuration values."""
    print_header("Rotating Flask Configuration")
    
    updates = {
        'FLASK_SECRET_KEY': rotate_flask_secret_key(),
        'SECURITY_PASSWORD_SALT': generate_secure_string(32)
    }
    
    backup_path = update_env_file(updates)
    print_success(f"Updated Flask configuration in .env (backup saved to {backup_path})")
    return True

def rotate_all_credentials():
    """Rotate all credentials."""
    print_header("Rotating All Credentials")
    
    print("This will rotate all credentials. Make sure to update any external services "
          "with the new values.")
    
    if input("\nAre you sure you want to continue? [y/N]: ").lower() != 'y':
        print_warning("Credential rotation cancelled.")
        return
    
    # Rotate credentials in order of least to most disruptive
    rotate_flask_config()
    rotate_firebase_credentials()
    rotate_google_ai_key()
    rotate_email_credentials()
    rotate_database_credentials()
    
    print("\n" + "=" * 80)
    print("CREDENTIAL ROTATION COMPLETE")
    print("=" * 80)
    print("\nIMPORTANT: You must restart your application for the changes to take effect.")
    print("Make sure to update any external services with the new credentials.")

def main():
    """Main function for the credential rotation script."""
    try:
        # Check if .env exists
        if not os.path.exists('.env'):
            print_error(".env file not found. Please run this script from the project root directory.")
        
        print_header("Artisan AI - Credential Rotation Tool")
        
        while True:
            print("\nSelect an option:")
            print("1. Rotate Flask secret key and security salts")
            print("2. Rotate Firebase credentials")
            print("3. Rotate Google AI API key")
            print("4. Rotate email credentials")
            print("5. Rotate database credentials")
            print("6. Rotate ALL credentials")
            print("0. Exit")
            
            choice = input("\nEnter your choice (0-6): ").strip()
            
            if choice == '1':
                rotate_flask_config()
            elif choice == '2':
                rotate_firebase_credentials()
            elif choice == '3':
                rotate_google_ai_key()
            elif choice == '4':
                rotate_email_credentials()
            elif choice == '5':
                rotate_database_credentials()
            elif choice == '6':
                rotate_all_credentials()
                break  # Exit after rotating all credentials
            elif choice == '0':
                print("Exiting...")
                break
            else:
                print_warning("Invalid choice. Please try again.")
            
            # Pause before showing the menu again
            if choice not in ['0', '6']:
                input("\nPress Enter to continue...")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print_error(f"An error occurred: {str(e)}")
        if os.getenv('FLASK_DEBUG'):
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
