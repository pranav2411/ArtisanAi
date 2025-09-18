#!/bin/bash
set -e

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements-vercel.txt

# Create necessary directories
echo "Creating required directories..."
mkdir -p app/static/uploads

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Run database migrations if manage.py exists
if [ -f "manage.py" ]; then
    echo "Running database migrations..."
    python manage.py db upgrade
else
    echo "No manage.py found, skipping database migrations"
fi

echo "Build completed successfully"
