@echo off
REM Vercel Build Script for Windows

echo Installing Python dependencies...
pip install -r requirements-vercel.txt

REM Create necessary directories
if not exist "app\static\uploads" mkdir "app\static\uploads"

REM Set environment variables
set FLASK_APP=app.py
set FLASK_ENV=production

REM Run database migrations
if exist "manage.py" (
    echo Running database migrations...
    python manage.py db upgrade
) else (
    echo No manage.py found, skipping database migrations
)

echo Build completed successfully
