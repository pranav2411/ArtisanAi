#!/usr/bin/env python3
"""
Artisan AI Management Script

This script helps manage the Artisan AI application with various commands
for development, testing, and deployment.
"""

import os
import sys
import subprocess
import click
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path
PROJECT_ROOT = str(Path(__file__).parent)
sys.path.insert(0, PROJECT_ROOT)

# Import Flask app after environment is loaded
from app import create_app

# Create Flask application
app = create_app()

@click.group()
def cli():
    """Management script for the Artisan AI application."""
    pass

@cli.command()
def run():
    """Run the development server."""
    # Check environment first
    if os.system('python scripts/check_env.py check') != 0:
        click.echo("❌ Environment check failed. Please fix the issues above.", err=True)
        sys.exit(1)
    
    # Set debug mode based on environment
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    # Run the Flask development server
    app.run(debug=debug, host='0.0.0.0', port=5000)

@cli.command()
def shell():
    """Start a Python shell with the application context."""
    import code
    from flask.cli import Shell
    from app import db  # Import any models you want available in the shell
    
    def make_shell_context():
        return dict(app=app, db=db)
    
    with app.app_context():
        shell = Shell(make_context=make_shell_context)
        shell()

@cli.command()
@click.option('--coverage/--no-coverage', default=False, help='Enable code coverage')
def test(coverage):
    """Run the unit tests."""
    import unittest
    
    if coverage:
        try:
            import coverage
            cov = coverage.coverage(branch=True, include='app/*')
            cov.start()
        except ImportError:
            click.echo("Coverage.py is not installed. Install with: pip install coverage")
            sys.exit(1)
    
    # Discover and run tests
    tests = unittest.TestLoader().discover('tests')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    
    if coverage:
        cov.stop()
        cov.save()
        click.echo("\nCoverage Summary:")
        cov.report()
        cov.html_report(directory='coverage')
        click.echo("HTML version: file://%s/coverage/index.html" % os.getcwd())
    
    sys.exit(not result.wasSuccessful())

@cli.command()
@click.option('--port', default=5000, help='Port to run the production server on')
def gunicorn(port):
    """Run the production server with Gunicorn."""
    # Check environment first
    if os.system('python scripts/check_env.py check') != 0:
        click.echo("❌ Environment check failed. Please fix the issues above.", err=True)
        sys.exit(1)
    
    # Ensure Gunicorn is installed
    try:
        import gunicorn
    except ImportError:
        click.echo("Gunicorn is not installed. Install with: pip install gunicorn")
        sys.exit(1)
    
    # Start Gunicorn
    cmd = f"gunicorn -b 0.0.0.0:{port} --access-logfile - --error-logfile - 'app:create_app()'"
    os.execlp('gunicorn', 'gunicorn', '-b', f'0.0.0.0:{port}', '--access-logfile', '-', '--error-logfile', '-', 'app:create_app()')

@cli.command()
def check():
    """Check the environment configuration."""
    return os.system('python scripts/check_env.py check')

@cli.command()
@click.option('--force', is_flag=True, help='Force generation even if file exists')
def generate_env(force):
    """Generate a .env.example file."""
    if os.path.exists('.env') and not force:
        click.confirm('A .env file already exists. Do you want to overwrite it?', abort=True)
    
    return os.system('python scripts/check_env.py generate')

@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=5000, help='Port to bind to')
@click.option('--public', is_flag=True, help='Make the server publicly available')
def dev(host, port, public):
    """Run the development server with live reloading."""
    if public:
        host = '0.0.0.0'
    
    # Set environment variables for development
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    
    # Run Flask development server
    app.run(host=host, port=port, debug=True, use_reloader=True)

@cli.command()
@click.argument('command', nargs=-1)
def compose(command):
    """Run docker-compose commands with the project's docker-compose.yml."""
    compose_file = os.path.join(PROJECT_ROOT, 'docker-compose.yml')
    
    if not os.path.exists(compose_file):
        click.echo("docker-compose.yml not found.", err=True)
        sys.exit(1)
    
    cmd = ['docker-compose', '-f', compose_file] + list(command)
    os.execvp('docker-compose', cmd)

@cli.command()
def init_db():
    """Initialize the database."""
    with app.app_context():
        from app.extensions import db
        click.echo("Creating database tables...")
        db.create_all()
        click.echo("Database initialized.")

@cli.command()
@click.option('--drop', is_flag=True, help='Drop existing database tables')
def reset_db(drop):
    """Reset the database to a clean state."""
    with app.app_context():
        from app.extensions import db
        
        if drop:
            click.confirm('This will drop all database tables. Are you sure?', abort=True)
            click.echo("Dropping all tables...")
            db.drop_all()
        
        click.echo("Creating all tables...")
        db.create_all()
        click.echo("Database reset complete.")

@cli.command()
@click.argument('path', default='app')
def lint(path):
    """Run code linter."""
    try:
        import flake8
    except ImportError:
        click.echo("Flake8 is not installed. Install with: pip install flake8")
        sys.exit(1)
    
    return os.system(f'flake8 {path}')

@cli.command()
def format():
    """Format code using Black."""
    try:
        import black
    except ImportError:
        click.echo("Black is not installed. Install with: pip install black")
        sys.exit(1)
    
    return os.system('black .')

@cli.command()
@click.option('--port', default=5000, help='Port to expose the debugger on')
@click.option('--host', default='0.0.0.0', help='Host to expose the debugger on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
def debug(port, host, no_browser):
    """Start the application in debug mode with VS Code debugging."""
    # Set environment variables for debugging
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    
    # Open browser if not disabled
    if not no_browser:
        import webbrowser
        webbrowser.open(f'http://{host}:{port}')
    
    # Run the Flask development server
    app.run(host=host, port=port, debug=True, use_debugger=True, use_reloader=True)

@cli.command()
@click.argument('email')
@click.option('--admin/--no-admin', default=False, help='Make the user an admin')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='User password')
def create_user(email, admin, password):
    """Create a new user."""
    with app.app_context():
        from app.models.user import User
        from app.extensions import db
        
        if User.query.filter_by(email=email).first():
            click.echo(f"User with email {email} already exists.", err=True)
            sys.exit(1)
        
        user = User(
            email=email,
            is_admin=admin,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        click.echo(f"User {email} created successfully.")

if __name__ == '__main__':
    cli()
