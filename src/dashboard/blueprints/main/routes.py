"""Routes for the main blueprint."""

import os
from flask import render_template, current_app, send_from_directory, request, abort
from . import main

@main.route('/', defaults={'path': ''})
@main.route('/<path:path>')
def index(path):
    """Serve the React SPA."""
    # Get the React build directory
    react_build_dir = os.path.join(current_app.root_path, '..', '..', '..', 'frontend-react', 'dist')
    
    # Check if this is a direct request for a static file
    if path.startswith(('js/', 'css/', 'img/', 'fonts/')):
        file_path = os.path.join(react_build_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            directory, filename = os.path.split(file_path)
            return send_from_directory(directory, filename)
    
    # Check for specific file extensions that should be served directly
    if path and '.' in path:
        extension = path.split('.')[-1].lower()
        if extension in ['js', 'css', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico', 'woff', 'woff2', 'ttf', 'eot']:
            file_path = os.path.join(react_build_dir, path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                directory, filename = os.path.split(file_path)
                return send_from_directory(directory, filename)
    
    # For all other routes, serve the index.html from React build
    # This is crucial for client-side routing to work with page refreshes
    try:
        index_path = os.path.join(react_build_dir, 'index.html')
        if os.path.exists(index_path):
            current_app.logger.info(f"Serving React SPA for path: {path}")
            return send_from_directory(react_build_dir, 'index.html')
        else:
            current_app.logger.warning(f"React index.html not found in {react_build_dir}")
            # Fallback to the template if React build is not available
            return render_template('main/index.html')
    except Exception as e:
        # Log the error
        current_app.logger.error(f"Error serving React SPA: {str(e)}")
        # Fallback to the template if React build is not available
        return render_template('main/index.html') 