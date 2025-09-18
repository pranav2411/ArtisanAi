#!/bin/bash

# Install Python dependencies
pip install -r requirements-vercel.txt

# Create necessary directories
mkdir -p app/static/uploads

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Run database migrations
python manage.py db upgrade

echo "Build completed successfully"
