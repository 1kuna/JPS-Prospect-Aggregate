# Data Fetching Migration Guide

## Overview

We've consolidated our data fetching approach to use React Query consistently across the application. This guide explains the new patterns and how to migrate existing components.

## New Structure

```
frontend-react/src/
  ├── hooks/
  │   ├── api/                  # Centralized API hooks
  │   │   ├── index.ts         # Exports all entity hooks
  │   │   ├── useDataSources.ts
  │   │   ├── useProposals.ts
  │   │   └── useAnalytics.ts
  │   └── use-query.ts         # Base query hooks and utilities
```

## Key Changes

1. **Centralized API Hooks**
   - Entity-specific hooks are now in `hooks/api/`
   - Each entity has its own file with related hooks
   - Common patterns are abstracted through `createEntityHooks`

2. **Standardized Data Fetching**
   - All data fetching uses React Query
   - Consistent error handling and loading states
   - Built-in caching and revalidation
   - Automatic background updates

3. **Removed Store-Based Data Fetching**
   - Zustand store now only manages UI state
   - Server state managed entirely by React Query
   - Clearer separation of concerns

## Migration Steps

1. **Replace Store Selectors**

Before:
```typescript
const dataSources = useStore(state => state.dataSources);
const fetchDataSources = useStore(state => state.fetchDataSources);

useEffect(() => {
  fetchDataSources();
}, []);
```

After:
```typescript
const { data: dataSources, isLoading } = useDataSources.useGetAll();
```

2. **Update Mutations**

Before:
```typescript
const createDataSource = useStore(state => state.createDataSource);

const handleCreate = async (data) => {
  try {
    await createDataSource(data);
    // Manual store updates
  } catch (error) {
    // Error handling
  }
};
```

After:
```typescript
const { mutate: createDataSource } = useDataSources.useCreate();

const handleCreate = (data) => {
  createDataSource(data, {
    onSuccess: () => {
      // Success handling (optional)
    }
  });
};
```

3. **Use DataLoader Component**

Before:
```typescript
{loading ? (
  <Spinner />
) : error ? (
  <ErrorMessage error={error} />
) : !data ? (
  <EmptyState />
) : (
  <YourComponent data={data} />
)}
```

After:
```typescript
<DataLoader
  queryKey={['your-key']}
  queryFn={yourQueryFunction}
>
  {(data) => <YourComponent data={data} />}
</DataLoader>
```

## Best Practices

1. **Use Entity-Specific Hooks**
   - Import hooks from `@/hooks/api`
   - Use the appropriate hook for your entity
   - Create new entity hooks if needed

2. **Handle Loading States**
   - Use `isLoading` for initial load
   - Use `isFetching` for background updates
   - Show appropriate loading UI

3. **Error Handling**
   - Use built-in error handling from hooks
   - Show error messages using toast notifications
   - Provide retry functionality where appropriate

4. **Data Invalidation**
   - Use `invalidateQueries` after mutations
   - Group related queries by key prefix
   - Consider optimistic updates for better UX

## Example Usage

```typescript
import { useDataSources } from '@/hooks/api';

function DataSourcesList() {
  // Get all data sources
  const {
    data: dataSources,
    isLoading,
    error
  } = useDataSources.useGetAll();

  // Create mutation
  const { mutate: createDataSource } = useDataSources.useCreate();

  // Delete mutation
  const { mutate: deleteDataSource } = useDataSources.useDelete();

  return (
    <DataPageLayout
      title="Data Sources"
      data={dataSources?.data}
      loading={isLoading}
      error={error}
      renderContent={(data) => (
        <DataTable
          data={data}
          columns={columns}
          loading={isLoading}
        />
      )}
    />
  );
}
```

## Common Patterns

1. **Infinite Loading**
```typescript
const {
  data,
  fetchNextPage,
  hasNextPage
} = useProposals.useInfiniteList(filters);

// Flatten pages for display
const proposals = data?.pages.flatMap(page => page.data) ?? [];
```

2. **Combining Multiple Queries**
```typescript
const {
  dashboard,
  statistics,
  isLoading
} = useAnalytics.useOverview();
```

3. **Custom Entity Actions**
```typescript
const { mutate: pullDataSource } = usePullDataSource(sourceId);
```

## Need Help?

If you need assistance migrating your components or have questions about the new patterns, please:

1. Review the example components in:
   - `src/pages/DataSources.tsx`
   - `src/pages/Proposals.tsx`
   - `src/pages/Dashboard.tsx`

2. Check the React Query documentation for advanced patterns:
   - [React Query Docs](https://tanstack.com/query/latest)

3. Reach out to the team for help! 