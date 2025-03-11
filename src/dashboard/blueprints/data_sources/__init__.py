"""Data sources blueprint for managing data sources."""

from flask import Blueprint

# Change the URL prefix to avoid conflicts with the React router
data_sources = Blueprint('data_sources', __name__, url_prefix='/api/data-sources', template_folder='templates')

from . import routes, errors 