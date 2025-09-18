#!/bin/bash
set -e

# Clean up any existing build artifacts
echo "Cleaning up..."
rm -rf __pycache__ app/__pycache__ app/*/__pycache__
find . -type d -name "__pycache__" -exec rm -rf {} + || true

# Install only production dependencies
echo "Installing production dependencies..."
pip install --upgrade pip
pip install --no-cache-dir -r requirements-vercel.txt

# Clean up pip cache
echo "Cleaning up pip cache..."
rm -rf ~/.cache/pip

# Create necessary directories
echo "Creating required directories..."
mkdir -p app/static/uploads

# Clean up unnecessary files
echo "Removing unnecessary files..."
find . -type f -name '*.py[co]' -delete
find . -type d -name '*.egg-info' | xargs rm -rf
find . -type d -name '__pycache__' -exec rm -rf {} +

# Optimize Python files
echo "Optimizing Python files..."
python -m compileall -f .

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

# Print build info
echo "Build completed successfully"
echo "Build size:"
du -sh .

# List large files (for debugging)
echo "Large files:"
find . -type f -size +1M -exec ls -lh {} \; | sort -k 5 -hr | head -n 20 || true
