const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('Starting Vercel build...');

// Create a minimal requirements file with only essential packages
const essentialPackages = [
  'Flask==2.3.3',
  'Werkzeug==2.3.7',
  'gunicorn==21.2.0',
  'python-dotenv==1.0.0',
  'firebase-admin==6.2.0',
  'google-cloud-firestore==2.11.1',
  'google-generativeai==0.3.2',
  'Flask-SQLAlchemy==3.1.1',
  'Flask-Login==0.6.2',
  'Flask-Cors==4.0.0',
  'PyJWT==2.8.0',
  'requests==2.31.0',
  'python-dateutil==2.8.2',
  'pytz==2023.3.post1',
  'gevent==23.7.0',
  'greenlet==2.0.2',
  'sentry-sdk[flask]==1.34.0'
];

// Write minimal requirements file
fs.writeFileSync('requirements-minimal.txt', essentialPackages.join('\n'));

// Install only essential packages
console.log('Installing essential dependencies...');
execSync('pip install --no-cache-dir -r requirements-minimal.txt', { stdio: 'inherit' });

// Clean up Python cache
console.log('Cleaning up Python cache...');
const cleanDirs = [
  '__pycache__',
  'app/__pycache__',
  'app/api/__pycache__',
  'app/auth/__pycache__',
  'venv',
  '.pytest_cache',
  '.mypy_cache'
];

cleanDirs.forEach(dir => {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch (err) {
    // Ignore if directory doesn't exist
  }
});

// Remove large files that might have been included
const largeFiles = [
  '*.pyc',
  '*.pyo',
  '*.pyd',
  '*.so',
  '*.dll',
  '*.egg-info',
  '*.egg',
  '*.log',
  '*.sqlite',
  '*.sqlite3',
  '*.db',
  '*.db3'
];

largeFiles.forEach(pattern => {
  try {
    execSync(`find . -name "${pattern}" -type f -delete`);
  } catch (err) {
    // Ignore if no files match
  }
});

console.log('Build completed successfully');
