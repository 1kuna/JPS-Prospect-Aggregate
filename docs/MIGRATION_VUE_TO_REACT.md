# Vue to React Migration Guide

This document outlines the migration from Vue.js to React in the JPS Prospect Aggregate application.

## Migration Overview

The frontend of the JPS Prospect Aggregate application has been migrated from Vue.js to React with the following technology stack:

- **React 18+** - Modern React with functional components and hooks
- **Vite** - Fast build tool replacing Vue CLI
- **TypeScript** - Type safety for better developer experience
- **shadcn/ui** - Component library based on Tailwind CSS
- **TanStack Table** - Powerful data tables (formerly React Table)
- **Zustand** - Simple state management replacing Vuex
- **React Router** - Client-side routing replacing Vue Router

## Directory Structure Changes

### Old Structure (Vue.js)

```
src/
  dashboard/
    frontend/           # Vue.js frontend code
      src/
        components/     # Vue components
        views/          # Vue views
        router/         # Vue Router configuration
        store/          # Vuex store
        App.vue         # Main Vue component
        main.js         # Vue entry point
    static/
      vue/              # Vue.js build output
```

### New Structure (React)

```
frontend-react/         # React frontend code
  src/
    components/         # React components
      ui/               # shadcn/ui components
    context/            # React context providers
    hooks/              # Custom React hooks
    lib/                # Utility functions
    pages/              # Page components
    store/              # Zustand store
    utils/              # Utility functions
    App.tsx             # Main React component
    main.tsx            # React entry point
  dist/                 # React build output
```

## Key Components Migrated

| Vue Component | React Component | Notes |
|---------------|----------------|-------|
| `App.vue` | `App.tsx` | Main application component |
| `views/Dashboard.vue` | `pages/Dashboard.tsx` | Dashboard page |
| `views/DataSources.vue` | `pages/DataSources.tsx` | Data sources page with TanStack Table |
| Vuex store | Zustand store | Simplified state management |
| Vue Router | React Router | Client-side routing |
| Vuetify components | shadcn/ui components | UI component library |

## State Management Changes

### Vue (Vuex)

```javascript
// store/index.js
import { createStore } from 'vuex'

export default createStore({
  state: {
    loading: false,
    error: null,
    dashboardData: null
  },
  getters: {
    isLoading: state => state.loading
  },
  mutations: {
    SET_LOADING(state, loading) {
      state.loading = loading
    }
  },
  actions: {
    async fetchDashboardData({ commit }) {
      commit('SET_LOADING', true)
      // API call
      commit('SET_LOADING', false)
    }
  }
})
```

### React (Zustand)

```typescript
// store/useStore.ts
import { create } from 'zustand'

interface AppState {
  loading: { dashboard: boolean };
  setLoading: (resource: string, isLoading: boolean) => void;
  fetchDashboardData: () => Promise<void>;
}

export const useStore = create<AppState>((set, get) => ({
  loading: { dashboard: false },
  setLoading: (resource, isLoading) => 
    set(state => ({
      loading: { ...state.loading, [resource]: isLoading }
    })),
  fetchDashboardData: async () => {
    const { setLoading } = get()
    setLoading('dashboard', true)
    // API call
    setLoading('dashboard', false)
  }
}))
```

## API Integration Changes

The API integration has been updated to use a more modular approach with dedicated API functions in `src/store/api.ts`.

## Error Handling Improvements

The new React implementation includes:

- React Error Boundaries for component-level error handling
- Centralized error state in Zustand store
- Consistent error UI components

## Loading State Management

The new React implementation includes:

- React Suspense for component-level loading states
- Centralized loading state in Zustand store
- Skeleton components for loading UI

## Performance Improvements

The new React implementation includes:

- Code splitting with React.lazy and dynamic imports
- Optimized rendering with React.memo and useMemo
- Virtualization for large data tables

## Build Process Changes

The build process has been updated to use Vite instead of Vue CLI, resulting in:

- Faster development builds
- Smaller production bundles
- Better developer experience

## Server Integration

The Flask server has been updated to serve the React build instead of the Vue.js build.

## Migration Scripts

A cleanup script (`cleanup_vue.py`) has been created to:

1. Remove Vue.js directories and files
2. Update references to Vue.js in the codebase
3. Update the build process to use React

## Future Considerations

- Further optimization of the React components
- Adding more comprehensive tests
- Enhancing the type safety with TypeScript
- Implementing more advanced features of TanStack Table 