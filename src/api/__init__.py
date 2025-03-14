"""
API Module for JPS Prospect Aggregate.

This module contains the API routes and related functionality
for the JPS Prospect Aggregate application.
"""

from flask import Blueprint

# Create the API blueprint
api = Blueprint('api', __name__, url_prefix='/api')

# Import routes to register them with the blueprint
from src.api.routes import * 