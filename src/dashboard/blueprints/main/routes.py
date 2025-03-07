"""Routes for the main blueprint."""

import os
from flask import render_template, current_app, send_from_directory, request, abort
from . import main

@main.route('/', defaults={'path': ''})
@main.route('/<path:path>')
def index(path):
    """Serve the Vue.js SPA."""
    # Get the static Vue directory
    static_vue_dir = os.path.join(current_app.static_folder, 'vue')
    
    # Check if this is a direct request for a static file
    if path.startswith(('js/', 'css/', 'img/', 'fonts/')):
        file_path = os.path.join(static_vue_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            directory, filename = os.path.split(file_path)
            return send_from_directory(directory, filename)
    
    # Check for specific file extensions that should be served directly
    if path and '.' in path:
        extension = path.split('.')[-1].lower()
        if extension in ['js', 'css', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico', 'woff', 'woff2', 'ttf', 'eot']:
            file_path = os.path.join(static_vue_dir, path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                directory, filename = os.path.split(file_path)
                return send_from_directory(directory, filename)
    
    # For all other routes, serve the index.html from Vue build
    # This is crucial for client-side routing to work with page refreshes
    try:
        index_path = os.path.join(static_vue_dir, 'index.html')
        if os.path.exists(index_path):
            current_app.logger.info(f"Serving Vue.js SPA for path: {path}")
            return send_from_directory(static_vue_dir, 'index.html')
        else:
            current_app.logger.warning(f"Vue.js index.html not found in {static_vue_dir}")
            # Fallback to the template if Vue build is not available
            return render_template('main/index.html')
    except Exception as e:
        # Log the error
        current_app.logger.error(f"Error serving Vue.js SPA: {str(e)}")
        # Fallback to the template if Vue build is not available
        return render_template('main/index.html') 