import os
import secrets
import json
from pathlib import Path

def generate_secret_key():
    """Generate a secure secret key."""
    return secrets.token_hex(32)

def generate_firebase_config():
    """Generate a template for Firebase configuration."""
    return {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "your-private-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR PRIVATE KEY HERE\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com",
        "client_id": "123456789012345678901",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40your-project-id.iam.gserviceaccount.com"
    }

def setup_environment():
    """Set up the environment variables file."""
    env_path = Path('.env')
    
    if env_path.exists():
        print("WARNING: .env file already exists. Creating a backup at .env.backup")
        with open(env_path, 'r') as f:
            with open('.env.backup', 'w') as backup:
                backup.write(f.read())
    
    # Get user input for configuration
    print("\n=== Artisan AI Configuration ===\n")
    
    # Firebase Configuration
    print("Firebase Configuration:")
    firebase_config = {
        'api_key': input("Firebase API Key: "),
        'auth_domain': input("Firebase Auth Domain (e.g., your-app.firebaseapp.com): "),
        'project_id': input("Firebase Project ID: "),
        'storage_bucket': input("Firebase Storage Bucket (e.g., your-app.appspot.com): "),
        'messaging_sender_id': input("Firebase Messaging Sender ID: "),
        'app_id': input("Firebase App ID: ")
    }
    
    # Google AI
    print("\nGoogle AI Configuration:")
    google_ai_key = input("Google AI API Key: ")
    
    # Email Configuration
    print("\nEmail Configuration:")
    email_config = {
        'address': input("Email Address (for sending emails): "),
        'password': input("App Password (generate at https://myaccount.google.com/apppasswords): ")
    }
    
    # Generate configuration
    config = f"""# --- API KEYS ---
GOOGLE_AI_API_KEY="{google_ai_key}"
GOOGLE_MAPS_API_KEY="{input('Google Maps API Key: ')}"

# --- EMAIL CONFIG ---
GMAIL_ADDRESS="{email_config['address']}"
GMAIL_APP_PASSWORD="{email_config['password']}"

# --- FIREBASE FRONT-END CONFIG ---
FIREBASE_API_KEY="{firebase_config['api_key']}"
FIREBASE_AUTH_DOMAIN="{firebase_config['auth_domain']}"
FIREBASE_PROJECT_ID="{firebase_config['project_id']}"
FIREBASE_STORAGE_BUCKET="{firebase_config['storage_bucket']}"
FIREBASE_MESSAGING_SENDER_ID="{firebase_config['messaging_sender_id']}"
FIREBASE_APP_ID="{firebase_config['app_id']}"

# --- FLASK ---
FLASK_SECRET_KEY="{generate_secret_key()}"
FLASK_DEBUG="False"

# --- FIREBASE SERVICE ACCOUNT ---
# Copy the contents of your Firebase service account JSON file here
# or set it as an environment variable in your deployment environment
# FIREBASE_SERVICE_ACCOUNT_JSON='{{"type":"service_account",...}}'"""
    
    # Write to .env file
    with open(env_path, 'w') as f:
        f.write(config)
    
    # Create firebase-service-account-key.json if it doesn't exist
    firebase_key_path = Path('firebase-service-account-key.json')
    if not firebase_key_path.exists():
        with open(firebase_key_path, 'w') as f:
            json.dump(generate_firebase_config(), f, indent=2)
    
    print("\n✅ Configuration complete!")
    print("A new .env file has been created with your configuration.")
    print("Please review the firebase-service-account-key.json file and update it with your Firebase Admin SDK credentials.")
    print("\nIMPORTANT: Add .env and firebase-service-account-key.json to .gitignore to prevent committing sensitive data.")

if __name__ == "__main__":
    setup_environment()
