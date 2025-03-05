"""Routes for the main blueprint."""

from flask import render_template, current_app, send_from_directory
from . import main

@main.route('/', defaults={'path': ''})
@main.route('/<path:path>')
def index(path):
    """Serve the Vue.js SPA."""
    # In development, this will be handled by the Vue dev server
    # In production, we serve the built Vue app
    try:
        # Try to serve files from the Vue build directory
        return send_from_directory(current_app.static_folder + '/vue', 'index.html')
    except:
        # Fallback to the template if Vue build is not available
        return render_template('main/index.html') 