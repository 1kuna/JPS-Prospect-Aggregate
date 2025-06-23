"""Routes for the web dashboard."""

import os
from flask import Blueprint, current_app, send_from_directory

# Create blueprints
main = Blueprint('web_main', __name__)

@main.route('/', defaults={'path': ''})
@main.route('/<path:path>')
def index(path):
    """Serve the React SPA."""
    # Get the React build directory - fix the path to be relative to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    react_build_dir = os.path.join(project_root, 'frontend-react', 'dist')
    
    current_app.logger.info(f"Serving React SPA from {react_build_dir} for path: {path}")
    
    # Check if the build directory exists
    if not os.path.exists(react_build_dir):
        current_app.logger.error(f"React build directory not found at {react_build_dir}")
        return {"error": "React application not built. Please run 'npm run build' in the frontend-react directory."}, 500
    
    # Special case for API routes - should be handled by the API blueprint
    if path.startswith('api/'):
        return {"error": "Not found"}, 404
    
    # Handle assets directory requests (with or without leading ./)
    if path.startswith(('assets/', './assets/')):
        # Strip the leading ./ if present
        clean_path = path[2:] if path.startswith('./') else path
        file_path = os.path.join(react_build_dir, clean_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            current_app.logger.info(f"Serving asset file: {clean_path}")
            directory, filename = os.path.split(file_path)
            return send_from_directory(directory, filename)
    
    # Check if this is a direct request for a static file
    if path.startswith(('js/', 'css/', 'img/', 'fonts/')):
        file_path = os.path.join(react_build_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            current_app.logger.info(f"Serving static file: {path}")
            directory, filename = os.path.split(file_path)
            return send_from_directory(directory, filename)
    
    # Check for specific file extensions that should be served directly
    if path and '.' in path:
        extension = path.split('.')[-1].lower()
        if extension in ['js', 'css', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico', 'woff', 'woff2', 'ttf', 'eot']:
            # Handle paths with or without leading ./
            clean_path = path[2:] if path.startswith('./') else path
            file_path = os.path.join(react_build_dir, clean_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                current_app.logger.info(f"Serving static file: {clean_path}")
                directory, filename = os.path.split(file_path)
                return send_from_directory(directory, filename)
    
    # For all other routes, serve the index.html file from the React build
    index_path = os.path.join(react_build_dir, 'index.html')
    if os.path.exists(index_path):
        current_app.logger.info(f"Serving index.html for path: {path}")
        return send_from_directory(react_build_dir, 'index.html')
    
    # If index.html is not found, return a 500 error
    current_app.logger.error(f"React index.html not found at {index_path}")
    return {"error": "React application index not found. Please check the build directory."}, 500

