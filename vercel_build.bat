@echo off
REM Vercel Build Script for Windows

REM Enable delayed expansion for variables in loops
setlocal enabledelayedexpansion

REM Set Python version if not set
if "%PYTHON_VERSION%"=="" set PYTHON_VERSION=3.9

echo === Starting Vercel Build Process (Python %PYTHON_VERSION%) ===

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip and setuptools
echo Upgrading pip and setuptools...
python -m pip install --upgrade pip setuptools wheel

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements-vercel.txt
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install Python dependencies
    exit /b 1
)

REM Create necessary directories
echo Creating required directories...
mkdir app\static\uploads 2>nul
mkdir app\static\js 2>nul
mkdir app\static\css 2>nul

REM Set environment variables
set FLASK_APP=app.py
set FLASK_ENV=production

REM Install Node.js dependencies if package.json exists
if exist "package.json" (
    echo Installing Node.js dependencies...
    call npm install
    if %ERRORLEVEL% NEQ 0 (
        echo Warning: Failed to install Node.js dependencies
    )
    
    REM Run build script if it exists
    findstr /i "build" package.json >nul
    if %ERRORLEVEL% EQU 0 (
        echo Running build script...
        call npm run build
        if %ERRORLEVEL% NEQ 0 (
            echo Warning: Build script failed
        )
    )
)

REM Run database migrations if manage.py exists
if exist "manage.py" (
    echo Running database migrations...
    python manage.py db upgrade
    if %ERRORLEVEL% NEQ 0 (
        echo Warning: Database migration failed
    )
) else (
    echo No manage.py found, skipping database migrations
)

REM List installed packages for debugging
echo === Installed Python Packages ===
pip list

REM Create a test file to verify build
echo Build Date: %date% %time%> app\static\build-info.txt
echo Python Version: >> app\static\build-info.txt
python --version >> app\static\build-info.txt 2>&1
echo Node Version: >> app\static\build-info.txt
node --version >> app\static\build-info.txt 2>&1 || echo Not installed >> app\static\build-info.txt

echo === Build completed successfully ===
