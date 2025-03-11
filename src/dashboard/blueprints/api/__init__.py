"""API blueprint for the dashboard API endpoints."""

from flask import Blueprint

api = Blueprint('api', __name__, url_prefix='/api')

# Import routes after creating the blueprint to avoid circular imports
from . import routes, errors 