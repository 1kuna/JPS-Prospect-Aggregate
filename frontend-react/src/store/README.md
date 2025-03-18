# JPS Prospect Aggregate State Management

This folder contains the state management system for JPS Prospect Aggregate, implemented using Zustand.

## Architecture

The state management is organized using a feature-based slices pattern, combined with middleware for enhanced functionality.

```
store/
├── slices/                 # Feature-based state slices
│   ├── dataSourcesSlice.ts # Data sources state and actions
│   ├── proposalsSlice.ts   # Proposals state and actions
│   ├── statisticsSlice.ts  # Statistics state and actions
│   ├── systemSlice.ts      # System operations state and actions
│   └── uiSlice.ts          # UI state and actions
├── middleware/             # Custom middleware
│   ├── logger.ts           # Logging middleware for debugging
│   ├── persist.ts          # Persistence utilities
│   └── websocketMiddleware.ts # WebSocket real-time updates
├── api.ts                  # API utilities for async operations
├── initializeWebSocket.ts  # WebSocket initialization
├── selectors.ts            # Reusable selectors and derived state
├── types.ts                # TypeScript types for the store
├── usePersistedStore.ts    # Persisted store for user preferences
└── useStore.ts             # Main store definition
```

## Usage

### Basic Usage

```typescript
import { useStore } from '@/store/useStore';

function MyComponent() {
  // Access state directly (not recommended for most cases)
  const dataSources = useStore(state => state.dataSources);
  const fetchDataSources = useStore(state => state.fetchDataSources);
  
  // Use state and actions
  return (
    <div>
      <button onClick={fetchDataSources}>Refresh</button>
      {dataSources.map(source => <div key={source.id}>{source.name}</div>)}
    </div>
  );
}
```

### Recommended: Use Selector Hooks

For better code organization and performance, use the selector hooks:

```typescript
import { useDataSourcesSelectors } from '@/hooks/useStoreSelectors';

function MyComponent() {
  const { dataSources, loading, errors, fetchDataSources } = useDataSourcesSelectors();
  
  return (
    <div>
      <button onClick={fetchDataSources} disabled={loading}>
        {loading ? 'Loading...' : 'Refresh'}
      </button>
      {errors && <div className="error">{errors.message}</div>}
      {dataSources.map(source => <div key={source.id}>{source.name}</div>)}
    </div>
  );
}
```

### Computed Values

For derived state, use the computed selectors:

```typescript
import { useDataSourcesHealth, useTotalProposalsCount } from '@/store/selectors';

function DashboardStats() {
  const health = useDataSourcesHealth();
  const totalProposals = useTotalProposalsCount();
  
  return (
    <div>
      <div>Data Sources: {health.healthy} healthy, {health.issues} with issues</div>
      <div>Total Proposals: {totalProposals}</div>
    </div>
  );
}
```

### Persisted User Preferences

For settings that should persist across sessions:

```typescript
import { usePersistedStore } from '@/store/usePersistedStore';

function SettingsPanel() {
  const theme = usePersistedStore(state => state.userPreferences.theme);
  const setTheme = usePersistedStore(state => state.setTheme);
  
  return (
    <div>
      <select value={theme} onChange={e => setTheme(e.target.value as any)}>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
        <option value="system">System</option>
      </select>
    </div>
  );
}
```

## Middleware

The store uses several middleware layers for enhanced functionality:

1. **DevTools**: Enables Redux DevTools integration (dev environment only)
2. **Logger**: Provides detailed logging of state updates (dev environment only)
3. **Performance Monitoring**: Logs performance metrics for state updates (dev environment only)
4. **Persistence**: Stores user preferences in localStorage

## WebSocket Implementation

Real-time updates are managed through WebSockets:

1. The socket is initialized in the app entry point with `initializeWebSocket()`
2. The WebSocket middleware handles socket events and updates the store accordingly
3. Components automatically receive updates through Zustand's subscriptions

## Adding New State

To add new state to the store:

1. Create a new slice or extend an existing slice based on the feature
2. Add the slice interface to the `StoreState` type in `types.ts`
3. Add new selectors to `selectors.ts` for derived state
4. Add new selector hooks to `hooks/useStoreSelectors.ts` for component usage

## Best Practices

1. Use selector hooks instead of direct store access for better performance and organization
2. Implement error handling in all async actions
3. Keep similar state grouped in the same slice
4. Use computed selectors for derived state to avoid recalculations
5. Use TypeScript interfaces for all state and actions 