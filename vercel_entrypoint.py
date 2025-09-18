""
Vercel Serverless Function Entry Point
This file is used as the entry point for Vercel serverless functions.
"""
from app import app as application

# This is required for Vercel to recognize the WSGI application
app = application

# For local testing
if __name__ == "__main__":
    app.run(debug=True)
