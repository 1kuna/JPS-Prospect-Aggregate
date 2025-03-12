# Common Components

This directory contains reusable components that are used throughout the application. The goal is to reduce duplication and make the codebase more maintainable.

## Layout Components

### PageLayout

A standard page layout with title, description, actions, and error handling.

```tsx
import { PageLayout } from '@/components';

function MyPage() {
  return (
    <PageLayout
      title="My Page"
      description="This is my page description"
      lastUpdated={new Date()}
      onRefresh={handleRefresh}
      isLoading={loading}
      error={error}
      actions={<Button>Custom Action</Button>}
    >
      {/* Page content goes here */}
    </PageLayout>
  );
}
```

### PageSkeleton

A loading skeleton for pages.

```tsx
import { PageSkeleton } from '@/components';

function LoadingState() {
  return <PageSkeleton cardCount={3} />;
}
```

## Data Display Components

### DataTable

A reusable table component with pagination.

```tsx
import { DataTable } from '@/components';

function MyTable() {
  const columns = [
    { header: 'Name', accessor: 'name' },
    { header: 'Email', accessor: 'email' },
    { 
      header: 'Actions', 
      accessor: (item) => (
        <Button onClick={() => handleEdit(item.id)}>Edit</Button>
      ) 
    },
  ];

  return (
    <DataTable
      title="Users"
      description="List of all users"
      data={users}
      columns={columns}
      keyField="id"
      pagination={{
        page: 1,
        perPage: 10,
        totalPages: 5,
        totalItems: 50,
      }}
      onPageChange={handlePageChange}
      emptyMessage={{
        title: 'No users found',
        description: 'There are no users to display.',
      }}
    />
  );
}
```

### StatsCard and StatsGrid

Components for displaying statistics in a card layout.

```tsx
import { StatsCard, StatsGrid } from '@/components';

function MyStats() {
  return (
    <StatsGrid columns={3}>
      <StatsCard
        title="Summary"
        description="Overview of all data"
        stats={[
          { label: 'Total Users', value: 100 },
          { label: 'Active Users', value: 50 },
          { label: 'Inactive Users', value: 50 },
        ]}
      />
      
      <StatsCard
        title="Status"
        description="Current system status"
        stats={[
          { 
            label: 'System Status', 
            value: 'Running',
            className: 'text-green-500'
          },
          { label: 'Active Jobs', value: 5 },
        ]}
      />
    </StatsGrid>
  );
}
```

## Form Components

### FormWrapper

A wrapper component for forms with standardized layout and error handling.

```tsx
import { FormWrapper, FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage, Input } from '@/components';
import * as z from 'zod';

// Define the form schema with Zod
const formSchema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
});

function MyForm() {
  return (
    <FormWrapper
      schema={formSchema}
      defaultValues={{ name: '', email: '' }}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      submitLabel="Save"
      isSubmitting={isSubmitting}
      error={error}
      successMessage={successMessage}
      title="My Form"
      description="Fill out this form"
    >
      <FormField
        name="name"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Name</FormLabel>
            <FormControl>
              <Input {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      
      <FormField
        name="email"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Email</FormLabel>
            <FormControl>
              <Input {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </FormWrapper>
  );
}
```

## Hooks

### useDataFetching

A hook for fetching data with loading, error, and pagination handling.

```tsx
import { useDataFetching } from '@/hooks';

function MyComponent() {
  const {
    data,
    isLoading,
    error,
    fetchData,
    pagination,
    setPagination,
    lastUpdated,
  } = useDataFetching({
    url: '/api/users',
    params: { status: 'active' },
    autoFetch: true,
  });

  const handlePageChange = (page: number) => {
    setPagination({ page, perPage: 10 });
  };

  return (
    <div>
      {isLoading && <div>Loading...</div>}
      {error && <div>Error: {error.message}</div>}
      {data && (
        <DataTable
          data={data}
          // ...other props
          pagination={pagination}
          onPageChange={handlePageChange}
        />
      )}
    </div>
  );
}
``` 