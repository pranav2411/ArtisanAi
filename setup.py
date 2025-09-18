#!/usr/bin/env python3
"""
Artisan AI Setup Script

This script helps set up the development environment for the Artisan AI project.
It creates a virtual environment, installs dependencies, and helps configure the environment.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e.stderr}")
        sys.exit(1)

def setup_virtual_environment():
    """Set up a Python virtual environment."""
    venv_dir = Path("venv")
    
    if not venv_dir.exists():
        print("Creating virtual environment...")
        run_command(f"{sys.executable} -m venv venv")
        print("Virtual environment created.")
    else:
        print("Virtual environment already exists.")

def install_dependencies():
    """Install Python dependencies."""
    print("Installing dependencies...")
    
    # Determine the correct pip command based on the OS
    pip_cmd = "venv\\Scripts\\pip" if os.name == 'nt' else "venv/bin/pip"
    
    # Upgrade pip
    run_command(f"{pip_cmd} install --upgrade pip")
    
    # Install dependencies
    run_command(f"{pip_cmd} install -r requirements.txt")
    
    print("Dependencies installed successfully.")

def setup_environment():
    """Set up the environment variables."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        print("\nSetting up environment variables...")
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print(f"Created .env file from .env.example")
            print("\nPlease update the .env file with your configuration.")
        else:
            print("Error: .env.example file not found.")
            sys.exit(1)
    else:
        print("\n.env file already exists. Skipping creation.")

def setup_firebase():
    """Guide the user through Firebase setup."""
    print("\n=== Firebase Setup ===")
    print("1. Go to https://console.firebase.google.com/")
    print("2. Create a new project or select an existing one")
    print("3. Go to Project Settings > Service Accounts")
    print("4. Click 'Generate New Private Key'")
    print("5. Save the JSON file as 'firebase-service-account-key.json' in the project root")
    print("6. Go to Project Settings > General")
    print("7. Under 'Your apps', add a web app if you haven't already")
    print("8. Copy the Firebase configuration and update your .env file\n")

def main():
    print("=== Artisan AI Setup ===\n")
    
    # Set up virtual environment
    setup_virtual_environment()
    
    # Install dependencies
    install_dependencies()
    
    # Set up environment variables
    setup_environment()
    
    # Guide through Firebase setup
    setup_firebase()
    
    print("\n=== Setup Complete! ===")
    print("1. Update the .env file with your configuration")
    print("2. Add your Firebase service account key as 'firebase-service-account-key.json'")
    print("3. Run the application with 'flask run'\n")
    
    # Activate command based on OS
    if os.name == 'nt':  # Windows
        print("To activate the virtual environment, run:")
        print("  venv\\Scripts\\activate")
    else:  # Unix/Linux/Mac
        print("To activate the virtual environment, run:")
        print("  source venv/bin/activate")

if __name__ == "__main__":
    main()
