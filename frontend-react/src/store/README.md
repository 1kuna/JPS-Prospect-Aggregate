# State Management

This directory contains our Zustand-based state management solution.

## Structure

```
store/
├── api.ts              # API client and normalized request/response handling
├── middleware/         # Custom Zustand middleware
├── selectors.ts        # Central repository of selectors
├── slices/             # Domain-focused store slices
│   ├── dataSourcesSlice.ts
│   ├── proposalsSlice.ts
│   ├── analyticsSlice.ts
│   ├── systemSlice.ts
│   └── uiSlice.ts
├── types.ts            # Type definitions for store state
├── usePersistedStore.ts # Persistent state store
└── useStore.ts         # Main store definition
```

## Core Principles

1. **Domain-Based Organization**: Store slices are organized by domain entity rather than technical concern.
2. **Centralized Selectors**: All selectors are defined in `selectors.ts` for a single source of truth.
3. **Normalized API Layer**: All API interactions go through the standardized client in `api.ts`.
4. **Separation of Concerns**: UI state is separate from domain data.

## Creating a New Slice

To create a new slice:

1. Add a new file in the `slices/` directory, e.g. `someFeatureSlice.ts`
2. Define your slice with proper typing:

```typescript
import { StateCreator } from 'zustand';
import { StoreState } from '../types';

export interface SomeFeatureSlice {
  // State
  someFeatureData: any[];
  someFeatureLoading: boolean;
  someFeatureError: Error | null;
  
  // Actions
  fetchSomeFeature: () => Promise<void>;
  updateSomeFeature: (id: string, data: any) => Promise<void>;
}

export const someFeatureSlice: StateCreator<StoreState> = (set, get) => ({
  // Initial state
  someFeatureData: [],
  someFeatureLoading: false,
  someFeatureError: null,
  
  // Actions
  fetchSomeFeature: async () => {
    set({ someFeatureLoading: true });
    try {
      const response = await api.fetchSomeFeature();
      set({ 
        someFeatureData: response.data,
        someFeatureLoading: false,
        someFeatureError: null
      });
    } catch (error) {
      set({ 
        someFeatureLoading: false,
        someFeatureError: error instanceof Error ? error : new Error(String(error))
      });
    }
  },
  
  updateSomeFeature: async (id, data) => {
    set({ someFeatureLoading: true });
    try {
      const response = await api.updateSomeFeature(id, data);
      
      // Update the store with the updated item
      set(state => ({ 
        someFeatureData: state.someFeatureData.map(item => 
          item.id === id ? response.data : item
        ),
        someFeatureLoading: false,
        someFeatureError: null
      }));
    } catch (error) {
      set({ 
        someFeatureLoading: false,
        someFeatureError: error instanceof Error ? error : new Error(String(error))
      });
    }
  }
});
```

3. Update the `types.ts` file to include your new slice interface:

```typescript
export interface StoreState extends 
  DataSourcesSlice,
  ProposalsSlice,
  AnalyticsSlice,
  SystemSlice,
  UISlice,
  SomeFeatureSlice {
  // Add any additional global state here
}
```

4. Add your slice to the main store in `useStore.ts`:

```typescript
import { someFeatureSlice } from './slices/someFeatureSlice';

// ...

const createStore = () => {
  return create<StoreState>()(
    // ...middleware
    (...args) => ({
      ...dataSourcesSlice(...args),
      ...proposalsSlice(...args),
      ...uiSlice(...args),
      ...analyticsSlice(...args),
      ...systemSlice(...args),
      ...someFeatureSlice(...args), // Add your new slice here
    })
  );
};
```

5. Add selectors for your new state in `selectors.ts`:

```typescript
// Base selectors
export const selectSomeFeatureData = (state: StoreState) => state.someFeatureData;
export const selectSomeFeatureLoading = (state: StoreState) => state.someFeatureLoading;
export const selectSomeFeatureError = (state: StoreState) => state.someFeatureError;

// Derived selectors
export const selectActiveSomeFeatureItems = createSelector(
  [selectSomeFeatureData],
  (items) => items.filter(item => item.status === 'active')
);
```

## Using the Store

To access your store data in components, use the hooks provided in the `hooks` directory:

```tsx
import { useData } from '@/hooks';
import { selectSomeFeatureData, selectSomeFeatureLoading, selectSomeFeatureError } from '@/store/selectors';

function SomeFeatureComponent() {
  const { data, loading, error, refetch } = useData({
    store: {
      selector: selectSomeFeatureData,
      loadingSelector: selectSomeFeatureLoading,
      errorSelector: selectSomeFeatureError,
      action: (state) => state.fetchSomeFeature,
    }
  });
  
  // Use the data in your component
}
```

## Best Practices

1. **Keep Slices Focused**: Each slice should handle a specific domain of the application.
2. **Use Selectors**: Always use selectors to access state, not direct store access.
3. **Normalize Data**: Store data in a normalized form to avoid duplication.
4. **Use TypeScript**: Ensure full type safety for your store.
5. **Handle Errors**: Always handle errors properly in your async actions.
6. **Document State Shape**: Add JSDoc comments to explain complex state properties.
7. **Use Middleware Judiciously**: Only add middleware that provides tangible benefits.
8. **Use Immutable Updates**: Always use immutable patterns for state updates. 