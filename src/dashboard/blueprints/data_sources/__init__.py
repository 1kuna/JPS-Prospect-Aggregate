"""Data sources blueprint for managing data sources."""

from flask import Blueprint

data_sources = Blueprint('data_sources', __name__, url_prefix='/data-sources', template_folder='templates')

from . import routes, errors 