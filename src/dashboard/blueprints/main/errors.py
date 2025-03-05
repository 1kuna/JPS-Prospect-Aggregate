"""Error handlers for the main blueprint."""

from flask import render_template
from . import main

@main.errorhandler(404)
def page_not_found(error):
    """Handle 404 errors."""
    return render_template('main/errors/404.html'), 404

@main.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors."""
    return render_template('main/errors/500.html'), 500 