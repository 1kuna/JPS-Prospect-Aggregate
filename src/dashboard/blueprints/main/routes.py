"""Routes for the main blueprint."""

import os
from flask import render_template, current_app, send_from_directory, request, abort
from . import main

@main.route('/', defaults={'path': ''})
@main.route('/<path:path>')
def index(path):
    """Serve the React SPA."""
    # Get the React build directory - fix the path to be relative to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
    react_build_dir = os.path.join(project_root, 'frontend-react', 'dist')
    
    current_app.logger.info(f"Serving React SPA from {react_build_dir} for path: {path}")
    
    # Check if the build directory exists
    if not os.path.exists(react_build_dir):
        current_app.logger.error(f"React build directory not found at {react_build_dir}")
        return render_template('main/index.html')
    
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
                current_app.logger.info(f"Serving file with extension {extension}: {clean_path}")
                directory, filename = os.path.split(file_path)
                return send_from_directory(directory, filename)
    
    # For all other routes, serve the index.html from React build
    # This is crucial for client-side routing to work with page refreshes
    try:
        index_path = os.path.join(react_build_dir, 'index.html')
        if os.path.exists(index_path):
            current_app.logger.info(f"Serving index.html for path: {path}")
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

@main.route('/debug')
def debug():
    """Debug page for testing API endpoints."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>API Debug</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                padding: 20px;
                max-width: 800px;
                margin: 0 auto;
            }
            pre {
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 5px;
                overflow: auto;
            }
            button {
                padding: 8px 16px;
                margin-right: 10px;
                margin-bottom: 10px;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            button:hover {
                background-color: #3a80d2;
            }
            .result {
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <h1>API Debug Tool</h1>
        
        <div>
            <button id="fetchProposals">Fetch Proposals</button>
            <button id="fetchDataSources">Fetch Data Sources</button>
            <button id="fetchDashboard">Fetch Dashboard</button>
            <button id="clearResults">Clear Results</button>
        </div>
        
        <div class="result">
            <h2>Results:</h2>
            <pre id="results"></pre>
        </div>

        <script>
            const resultsEl = document.getElementById('results');
            
            function log(message, data) {
                const timestamp = new Date().toISOString();
                const formattedData = typeof data === 'object' ? JSON.stringify(data, null, 2) : data;
                resultsEl.innerHTML += `[${timestamp}] ${message}\\n${formattedData ? formattedData + '\\n\\n' : '\\n'}`;
                console.log(message, data);
            }
            
            async function fetchAPI(url, params = {}) {
                try {
                    log(`Fetching ${url} with params:`, params);
                    
                    // Build query string
                    const queryParams = new URLSearchParams();
                    Object.entries(params).forEach(([key, value]) => {
                        queryParams.append(key, value);
                    });
                    
                    const fullUrl = `/api${url}${Object.keys(params).length ? '?' + queryParams.toString() : ''}`;
                    log(`Full URL: ${fullUrl}`);
                    
                    const response = await fetch(fullUrl);
                    const data = await response.json();
                    
                    log(`Response from ${url}:`, data);
                    return data;
                } catch (error) {
                    log(`Error fetching ${url}:`, error.message);
                    throw error;
                }
            }
            
            document.getElementById('fetchProposals').addEventListener('click', async () => {
                try {
                    await fetchAPI('/proposals', {
                        page: 1,
                        per_page: 10,
                        sort_by: 'release_date',
                        sort_order: 'desc'
                    });
                } catch (error) {
                    log('Failed to fetch proposals');
                }
            });
            
            document.getElementById('fetchDataSources').addEventListener('click', async () => {
                try {
                    await fetchAPI('/data-sources');
                } catch (error) {
                    log('Failed to fetch data sources');
                }
            });
            
            document.getElementById('fetchDashboard').addEventListener('click', async () => {
                try {
                    await fetchAPI('/dashboard');
                } catch (error) {
                    log('Failed to fetch dashboard data');
                }
            });
            
            document.getElementById('clearResults').addEventListener('click', () => {
                resultsEl.innerHTML = '';
            });
            
            // Initial log
            log('Debug tool loaded. Click a button to test an API endpoint.');
        </script>
    </body>
    </html>
    """ 