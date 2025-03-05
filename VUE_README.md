# Vue.js Frontend for JPS Proposal Forecast Aggregator

This project now includes a Vue.js frontend with Vuetify for a modern, responsive user interface.

## Development Setup

### Prerequisites

- Node.js (v14 or later)
- npm (v6 or later)

### Environment Variables

The Vue.js frontend uses the following environment variables:

- `VUE_DEV_MODE`: Set to `True` to run the Vue.js development server, or `False` to build for production (default: `True`)
- `VUE_APP_API_URL`: The URL of the API backend (default: `http://localhost:5001/api`)

### Development Mode

In development mode, the Vue.js frontend runs on a separate development server (usually on port 8080) and communicates with the Flask backend API. This provides hot-reloading and other development features.

To start the application in development mode:

1. Run one of the start scripts:
   - `python start_all.py`
   - `./start_all.sh` (Unix/Linux/macOS)
   - `start_all.bat` (Windows)

2. Access the frontend at http://localhost:8080

### Production Mode

In production mode, the Vue.js frontend is built and served by the Flask application. This is more efficient for production use.

To start the application in production mode:

1. Set `VUE_DEV_MODE=False` in your `.env` file
2. Run one of the start scripts:
   - `python start_all.py`
   - `./start_all.sh` (Unix/Linux/macOS)
   - `start_all.bat` (Windows)

3. Access the frontend at http://localhost:5001

### Manual Frontend Development

If you want to work on the frontend separately:

1. Navigate to the frontend directory:
   ```
   cd src/dashboard/frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run serve
   ```

4. Build for production:
   ```
   npm run build
   ```

## Frontend Structure

- `src/dashboard/frontend/src/components`: Reusable Vue components
- `src/dashboard/frontend/src/views`: Page components (Dashboard, DataSources)
- `src/dashboard/frontend/src/router`: Vue Router configuration
- `src/dashboard/frontend/src/store`: Vuex store for state management
- `src/dashboard/frontend/src/assets`: Static assets

## Features

- Modern, responsive UI with Vuetify components
- Dashboard view with summary cards and data tables
- Data Sources management interface
- State management with Vuex
- Routing with Vue Router 