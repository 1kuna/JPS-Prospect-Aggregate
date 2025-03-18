# Store Slices

This directory contains the feature-based slices for the Zustand store. Each slice encapsulates a specific area of state and its related actions.

## Slice Structure

Each slice follows the same basic structure:

```typescript
import { StateCreator } from 'zustand';
import { apiFunction1, apiFunction2 } from '../api';

// Define the state shape with TypeScript
export interface SliceState {
  data: DataType[];
  loading: { key: boolean };
  errors: { key: ErrorType | null };
  
  // Actions
  fetchData: () => Promise<void>;
  createData: (data: any) => Promise<any>;
  // ... other actions
}

// Define the slice implementation
export const mySlice: StateCreator<SliceState> = (set, get) => ({
  // Initial state
  data: [],
  loading: { key: false },
  errors: { key: null },
  
  // Action implementations
  fetchData: async () => {
    set((state) => ({ loading: { ...state.loading, key: true } }));
    try {
      const response = await apiFunction1();
      set({ 
        data: response.data,
        loading: { ...get().loading, key: false },
        errors: { ...get().errors, key: null }
      });
    } catch (error: any) {
      set({ 
        loading: { ...get().loading, key: false },
        errors: { ...get().errors, key: { message: error.message } }
      });
      throw error;
    }
  },
  
  // ... other action implementations
});
```

## Current Slices

### `dataSourcesSlice.ts`

Manages all state related to data sources, including fetching, creating, updating, and deleting data sources, as well as pulling data from sources.

### `proposalsSlice.ts`

Handles proposal data, including fetching, filtering, and pagination.

### `statisticsSlice.ts`

Manages statistics and dashboard data for analytics and reporting.

### `systemSlice.ts`

Handles system-wide operations like database rebuilding, initialization, backups, and resets.

### `uiSlice.ts`

Manages UI state such as toasts, navigation state, and modal visibility.

## Adding a New Slice

1. Create a new file in this directory named `[feature]Slice.ts`
2. Define the state interface, making it as specific as possible
3. Implement the slice functionality using the `StateCreator` pattern
4. Update the `StoreState` in `../types.ts` to include your new slice

```typescript
// types.ts
import { NewFeatureState } from './slices/newFeatureSlice';

export interface StoreState extends 
  // ... existing slices
  NewFeatureState 
{} 
```

5. Add the slice to the store creation in `../useStore.ts`:

```typescript
// useStore.ts
import { newFeatureSlice } from './slices/newFeatureSlice';

// ... in the store creation:
(...args) => ({
  // ... existing slices
  ...newFeatureSlice(...args),
})
```

## Best Practices

1. **Keep slices focused**: Each slice should handle a specific domain of the application
2. **Handle errors consistently**: All async actions should handle errors and update the error state
3. **Use TypeScript interfaces**: Define clear interfaces for state and action parameters
4. **Normalize data**: Use flat structures for collections rather than nested data
5. **Use selectors for derived data**: Don't compute derived data in components, use selectors instead
6. **Follow the loading/error pattern**: Each async operation should update loading and error states
7. **Use get() to access current state**: When you need the current state in an action, use `get()` rather than capturing state in closure variables 