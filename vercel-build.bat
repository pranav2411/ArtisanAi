@echo off
REM Vercel Build Script for Windows

echo Cleaning up...
if exist __pycache__ rmdir /s /q __pycache__
if exist app\__pycache__ rmdir /s /q app\__pycache__
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

echo Installing production dependencies...
python -m pip install --upgrade pip
pip install --no-cache-dir -r requirements-vercel.txt

echo Cleaning up pip cache...
if exist %USERPROFILE%\AppData\Local\pip\Cache rmdir /s /q %USERPROFILE%\AppData\Local\pip\Cache

REM Create necessary directories
if not exist "app\static\uploads" mkdir "app\static\uploads"

echo Removing unnecessary files...
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
for /d /r . %%d in (*.egg-info) do @if exist "%%d" rmdir /s /q "%%d"

REM Optimize Python files
echo Optimizing Python files...
python -m compileall -f .

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
echo Build size:
for /f "tokens=*" %%i in ('dir /s /c /a:-d') do @echo %%i

echo Large files:
for /f "tokens=*" %%i in ('dir /s /a:-d /o:-s') do @echo %%i
