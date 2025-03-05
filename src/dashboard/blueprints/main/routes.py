"""Routes for the main blueprint."""

from flask import render_template, current_app
from . import main

@main.route('/')
def index():
    """Render the dashboard homepage."""
    return render_template('main/index.html') 