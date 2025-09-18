#!/bin/bash

# Exit on error and print commands as they are executed
set -ex

# Set Python version if not set
PYTHON_VERSION=${PYTHON_VERSION:-3.9}

echo "=== Starting Vercel Build Process (Python $PYTHON_VERSION) ==="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip and setuptools
echo "Upgrading pip and setuptools..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements-vercel.txt

# Create necessary directories
echo "Creating required directories..."
mkdir -p app/static/uploads
mkdir -p app/static/js
mkdir -p app/static/css

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Install Node.js dependencies if package.json exists
if [ -f "package.json" ]; then
    echo "Installing Node.js dependencies..."
    npm install || echo "Warning: Failed to install Node.js dependencies"
    
    # Run build script if it exists
    if [ -f "package.json" ] && grep -q "build" package.json; then
        echo "Running build script..."
        npm run build || echo "Warning: Build script failed"
    fi
fi

# Run database migrations if manage.py exists
if [ -f "manage.py" ]; then
    echo "Running database migrations..."
    python manage.py db upgrade || echo "Warning: Database migration failed"
else
    echo "No manage.py found, skipping database migrations"
fi

# List installed packages for debugging
echo "=== Installed Python Packages ==="
pip list

# Set proper permissions
chmod -R 755 app/static

# Create a test file to verify build
cat > app/static/build-info.txt << EOL
Build Date: $(date)
Python Version: $(python --version)
Node Version: $(node --version 2>/dev/null || echo "Node.js not installed")
EOL

echo "=== Build completed successfully ==="
