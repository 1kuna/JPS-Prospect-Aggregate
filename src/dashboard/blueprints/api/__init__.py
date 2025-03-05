"""API blueprint for the dashboard API endpoints."""

from flask import Blueprint

api = Blueprint('api', __name__, url_prefix='/api')

from . import routes, errors 