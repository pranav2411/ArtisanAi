#!/usr/bin/env python3
"""
Development Environment Setup Script

This script automates the setup of the Artisan AI development environment.
It creates a virtual environment, installs dependencies, and sets up the database.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
from urllib.request import urlretrieve

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

def run_command(command, cwd=None, shell=False):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command if shell else command.split(),
            cwd=cwd,
            check=True,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {e.cmd}\n{e.stderr}")

def check_python_version():
    """Check if the Python version is 3.8 or higher."""
    print_header("Checking Python Version")
    
    if sys.version_info < (3, 8):
        print_error(f"Python 3.8 or higher is required. Current version: {sys.version}")
    
    print_success(f"Using Python {sys.version.split()[0]}")

def setup_virtualenv():
    """Set up a Python virtual environment."""
    print_header("Setting Up Virtual Environment")
    
    venv_dir = Path("venv")
    
    if venv_dir.exists():
        print_warning(f"Virtual environment already exists at {venv_dir}")
        if input("Recreate virtual environment? [y/N]: ").lower() == 'y':
            shutil.rmtree(venv_dir)
        else:
            return
    
    print("Creating virtual environment...")
    run_command(f"{sys.executable} -m venv {venv_dir}")
    
    # Get the Python executable in the virtual environment
    python_bin = venv_dir / "Scripts" / "python.exe" if os.name == 'nt' else venv_dir / "bin" / "python"
    
    if not python_bin.exists():
        python_bin = venv_dir / "Scripts" / "python.exe" if os.name == 'nt' else venv_dir / "bin" / "python3"
    
    if not python_bin.exists():
        print_error(f"Could not find Python executable in {venv_dir}")
    
    print_success(f"Virtual environment created at {venv_dir}")
    return python_bin

def install_dependencies(python_bin):
    """Install Python dependencies."""
    print_header("Installing Dependencies")
    
    # Upgrade pip first
    run_command(f"{python_bin} -m pip install --upgrade pip")
    
    # Install requirements
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print_error(f"{requirements_file} not found")
    
    print("Installing dependencies from requirements.txt...")
    run_command(f"{python_bin} -m pip install -r {requirements_file}")
    
    print_success("Dependencies installed successfully")

def setup_environment():
    """Set up the environment variables."""
    print_header("Environment Setup")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_example.exists():
        print_error(".env.example not found")
    
    if env_file.exists():
        print_warning(".env file already exists")
        if input("Overwrite existing .env file? [y/N]: ").lower() != 'y':
            return
    
    # Copy .env.example to .env
    shutil.copy(env_example, env_file)
    print_success("Created .env file from .env.example")
    
    # Guide the user to edit the .env file
    print("\nPlease edit the .env file with your configuration:")
    print(f"  1. Update Firebase configuration")
    print(f"  2. Set up email settings")
    print(f"  3. Configure database connection")
    print(f"  4. Set admin credentials")
    print("\nYou can open the file in your default editor:")
    
    if input("Open .env file now? [Y/n]: ").lower() != 'n':
        if platform.system() == 'Windows':
            os.startswith(env_file.absolute())
        elif platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', str(env_file.absolute())])
        else:  # Linux
            subprocess.run(['xdg-open', str(env_file.absolute())])
    
    input("\nPress Enter to continue after you've updated the .env file...")

def setup_database(python_bin):
    """Set up the database."""
    print_header("Database Setup")
    
    # Check if we can import the app
    try:
        from app import create_app
        from app.extensions import db
    except ImportError as e:
        print_error(f"Failed to import app: {e}")
    
    # Create the app and push the application context
    app = create_app()
    with app.app_context():
        # Create database tables
        print("Creating database tables...")
        db.create_all()
        print_success("Database tables created")
        
        # Create admin user if not exists
        from app.models.user import User
        from app import db
        
        admin_email = os.getenv('ADMIN_EMAIL')
        admin_password = os.getenv('ADMIN_PASSWORD')
        admin_name = os.getenv('ADMIN_NAME', 'Admin User')
        
        if not admin_email or not admin_password:
            print_warning("ADMIN_EMAIL or ADMIN_PASSWORD not set in .env")
            return
        
        admin = User.query.filter_by(email=admin_email).first()
        if admin:
            print_warning(f"Admin user {admin_email} already exists")
        else:
            print(f"Creating admin user: {admin_email}")
            admin = User(
                email=admin_email,
                name=admin_name,
                is_admin=True,
                is_active=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print_success("Admin user created successfully")

def setup_firebase():
    """Set up Firebase configuration."""
    print_header("Firebase Setup")
    
    service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not service_account_path:
        print_warning("GOOGLE_APPLICATION_CREDENTIALS not set in .env")
        print("Please download the Firebase service account key JSON file and update .env")
        return
    
    service_account_path = Path(service_account_path)
    
    if not service_account_path.exists():
        print_warning(f"Firebase service account key not found at {service_account_path}")
        print("1. Go to Firebase Console > Project Settings > Service Accounts")
        print("2. Click 'Generate New Private Key'")
        print(f"3. Save the JSON file as '{service_account_path}'")
        
        if input("Open Firebase Console in browser? [y/N]: ").lower() == 'y':
            import webbrowser
            webbrowser.open("https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk")
        
        input("\nPress Enter after you've downloaded the service account key...")
        
        if not service_account_path.exists():
            print_warning("Skipping Firebase setup. Please set it up manually.")
            return
    
    print_success("Firebase service account key found")

def main():
    """Main setup function."""
    try:
        print_header("Artisan AI Development Environment Setup")
        
        # Check Python version
        check_python_version()
        
        # Set up virtual environment
        python_bin = setup_virtualenv()
        
        # Install dependencies
        install_dependencies(python_bin)
        
        # Set up environment variables
        setup_environment()
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Set up Firebase
        setup_firebase()
        
        # Set up database
        setup_database(python_bin)
        
        print_header("Setup Complete!")
        print("\n🎉 Your Artisan AI development environment is ready!")
        print("\nTo start the development server, run:")
        print(f"  {Colors.BOLD}python manage.py run{Colors.ENDC}")
        print("\nAccess the application at: http://localhost:5000")
        
        admin_email = os.getenv('ADMIN_EMAIL')
        if admin_email:
            print(f"\nAdmin login: {Colors.BOLD}{admin_email}{Colors.ENDC}")
        
        print(f"\nFor more commands, run: {Colors.BOLD}python manage.py --help{Colors.ENDC}")
        
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"An error occurred: {str(e)}")
        if os.getenv('FLASK_DEBUG'):
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
