"""Main blueprint for the dashboard homepage."""

from flask import Blueprint

main = Blueprint('main', __name__, template_folder='templates')

from . import routes, errors 