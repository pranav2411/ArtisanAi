"""
API Blueprint

This module contains the main API blueprint for the application.
"""

from flask import Blueprint

# Create the API blueprint
api_bp = Blueprint('api', __name__)

# Import routes after creating the blueprint to avoid circular imports
from . import routes  # noqa: F401, E402
