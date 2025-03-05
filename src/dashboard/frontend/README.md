# JPS Proposal Forecast Aggregator Frontend

This is the Vue.js frontend for the JPS Proposal Forecast Aggregator.

## Project Setup

```bash
# Install dependencies
npm install
```

### Compiles and hot-reloads for development
```bash
npm run serve
```

### Compiles and minifies for production
```bash
npm run build
```

### Lints and fixes files
```bash
npm run lint
```

## Development

The frontend is built with Vue.js 3 and Vuetify 3. It communicates with the Flask backend API.

### Environment Variables

Create a `.env` file in the frontend directory with the following variables:

```
VUE_APP_API_URL=http://localhost:5001/api
```

### Project Structure

- `src/components`: Reusable Vue components
- `src/views`: Page components
- `src/router`: Vue Router configuration
- `src/store`: Vuex store for state management
- `src/assets`: Static assets like images and styles

## Production Deployment

When building for production, the Vue.js app will be built to the Flask static directory and served by the Flask application.

1. Run `npm run build` to build the Vue.js app
2. The built files will be placed in `src/dashboard/static/vue`
3. The Flask application will serve the Vue.js app from this directory 