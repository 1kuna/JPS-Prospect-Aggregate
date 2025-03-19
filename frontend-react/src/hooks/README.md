# Data Fetching Hooks

This directory contains hooks for data fetching, form handling, and other common UI patterns.

## useData

The `useData` hook is our primary data fetching hook, providing a unified API for both direct API calls and store-based data fetching.

### API

```typescript
function useData<T, P extends any[] = any[]>(
  options: UseDataOptions<T, P>
): UseDataResult<T, P>
```

### Options

The hook accepts a flexible options object that supports both API and store-based fetching:

```typescript
interface UseDataOptions<T, P extends any[] = any[]> {
  // API options (when fetching directly from API)
  api?: {
    url: string;
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    body?: any;
    params?: Record<string, any>;
    transform?: (response: ApiResponse<any>) => T;
    cacheTime?: number;
    cacheKey?: string;
    useQueryCache?: boolean;
  };
  
  // Store options (when fetching from Zustand store)
  store?: {
    selector: (state: any) => T;
    loadingSelector?: (state: any) => boolean;
    errorSelector?: (state: any) => Error | null;
    action?: (...args: P) => Promise<any>;
    actionParams?: P;
  };
  
  initialData?: T;
  fetchOnMount?: boolean;
  skip?: boolean;
  dependencies?: any[];
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}
```

### Return Value

```typescript
interface UseDataResult<T, P extends any[] = any[]> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: (...args: P) => Promise<T>;
  setData: React.Dispatch<React.SetStateAction<T | null>>;
}
```

## Examples

### Direct API Call

```tsx
import { useData } from '@/hooks';

function DataSourcesList() {
  const { data, loading, error, refetch } = useData({
    api: {
      url: '/api/data-sources',
      method: 'GET',
      cacheTime: 5 * 60 * 1000, // 5 minutes
    },
    onSuccess: (data) => console.log('Data loaded:', data),
    onError: (error) => console.error('Failed to load data:', error)
  });

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;
  
  return (
    <div>
      <button onClick={() => refetch()}>Refresh</button>
      <ul>
        {data?.map(source => (
          <li key={source.id}>{source.name}</li>
        ))}
      </ul>
    </div>
  );
}
```

### Store-Based Fetching

```tsx
import { useData } from '@/hooks';
import { selectDataSources, selectLoadingDataSources, selectErrorDataSources } from '@/store/selectors';

function DataSourcesList() {
  const { data, loading, error, refetch } = useData({
    store: {
      selector: selectDataSources,
      loadingSelector: selectLoadingDataSources,
      errorSelector: selectErrorDataSources,
      action: (state) => state.fetchDataSources,
    },
    dependencies: [], // Empty array means fetch only on mount
  });

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;
  
  return (
    <div>
      <button onClick={() => refetch()}>Refresh</button>
      <ul>
        {data?.map(source => (
          <li key={source.id}>{source.name}</li>
        ))}
      </ul>
    </div>
  );
}
```

### Combined API and Store

```tsx
import { useData } from '@/hooks';
import { selectDataSourceById, selectLoadingDataSources, selectErrorDataSources } from '@/store/selectors';

function DataSourceDetail({ id }) {
  const { data, loading, error } = useData({
    // First try to get from store
    store: {
      selector: (state) => selectDataSourceById(id)(state),
      loadingSelector: selectLoadingDataSources,
      errorSelector: selectErrorDataSources,
    },
    // If not in store or needs refresh, fetch from API
    api: {
      url: `/api/data-sources/${id}`,
      cacheTime: 60000, // 1 minute
    },
    // Only fetch from API if data is not in store
    skip: (data) => !!data,
  });

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;
  if (!data) return <p>No data found</p>;
  
  return (
    <div>
      <h1>{data.name}</h1>
      <p>{data.description}</p>
    </div>
  );
}
```

### With React Query Integration

```tsx
import { useData } from '@/hooks';

function DataSourcesList() {
  const { data, loading, error } = useData({
    api: {
      url: '/api/data-sources',
      cacheTime: 5 * 60 * 1000, // 5 minutes
      useQueryCache: true, // Use React Query's cache
      cacheKey: ['dataSources'], // React Query cache key
    },
  });

  // ... rest of the component
}
```

## Migration from Legacy Hooks

If you're migrating from `useDataFetching` or `useStoreData`, you can use adapter functions for a smoother transition:

```tsx
import { useDataFetchingAdapter, useStoreDataAdapter } from '@/hooks';

// Convert from useDataFetching
const result1 = useDataFetchingAdapter({
  url: '/api/data-sources',
  // other useDataFetching options
});

// Convert from useStoreData
const result2 = useStoreDataAdapter({
  selector: selectDataSources,
  action: state => state.fetchDataSources,
  // other useStoreData options
});
```

## Other Hooks

- `useForm`: For form handling with validation
- `useReactQuery`: For advanced data fetching with React Query
- `useToast`: For toast notifications 