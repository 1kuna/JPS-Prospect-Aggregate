"""Error handlers for the data sources blueprint."""

from flask import render_template, current_app
from . import data_sources

@data_sources.errorhandler(404)
def page_not_found(error):
    """Handle 404 errors."""
    return render_template('data_sources/errors/404.html'), 404

@data_sources.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors."""
    # Log the error
    current_app.logger.error(f"Data sources error: {str(error)}")
    return render_template('data_sources/errors/500.html'), 500 