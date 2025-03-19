# Components

This directory contains all the React components used throughout the application, organized by purpose and responsibility.

## Directory Structure

```
components/
├── ui/                  # Reusable UI components
│   ├── button.tsx       # Button variants
│   ├── form.tsx         # Form components
│   ├── feedback.tsx     # Feedback components (alerts, toasts)
│   ├── DataTable.tsx    # Table with sorting, pagination, virtualization
│   ├── DataLoader.tsx   # Data loading component with loading/error states
│   └── ...
├── layout/              # Layout components
│   ├── Header.tsx       # App header
│   ├── Sidebar.tsx      # Navigation sidebar
│   └── ...
├── forms/               # Form-specific components
│   ├── DataSourceForm.tsx
│   └── ...
├── data-display/        # Data visualization components
│   ├── Charts.tsx       # Chart components
│   └── ...
├── dashboard/           # Dashboard-specific components
│   ├── StatCard.tsx     # Dashboard stat cards
│   └── ...
└── ErrorBoundary.tsx    # Application error boundary
```

## Component Patterns

### 1. UI Components

These are the building blocks of our interface, designed to be reusable across the application.

#### Best Practices:

- Make components fully controlled where possible
- Use TypeScript for props with appropriate default values
- Keep components focused on a single responsibility
- Document props with JSDoc comments
- Use composition over inheritance
- Export variants from a single file (e.g., `button.tsx` exports `Button`, `ButtonIcon`, etc.)

#### Example:

```tsx
// ui/button.tsx
import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'underline-offset-4 hover:underline text-primary',
      },
      size: {
        default: 'h-10 py-2 px-4',
        sm: 'h-9 px-3 rounded-md',
        lg: 'h-11 px-8 rounded-md',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

### 2. Data Loading Components

These components handle fetching, loading states, error states, and empty states.

#### Best Practices:

- Use DataLoader for consistent loading/error/empty states
- Implement virtualization for large datasets
- Keep data fetching logic in hooks
- Use React Query or the useData hook for API interactions
- Handle all edge cases (loading, error, empty, success)

#### Example:

```tsx
// example usage of DataLoader
import { DataLoader } from '@/components/ui/DataLoader';
import { useData } from '@/hooks';

function DataSourcesList() {
  const { data, loading, error, refetch } = useData({
    api: {
      url: '/api/data-sources',
      cacheTime: 60000,
    },
  });

  return (
    <DataLoader
      data={data}
      isLoading={loading}
      error={error}
      onRetry={refetch}
      emptyComponent={
        <EmptyState
          title="No data sources found"
          description="Create your first data source to get started"
          action={<Button onClick={() => setOpenModal(true)}>Create Data Source</Button>}
        />
      }
    >
      {(dataSources) => (
        <DataTable
          data={dataSources}
          columns={columns}
          rowKey={(item) => item.id}
          virtualized={dataSources.length > 100}
          height={500}
        />
      )}
    </DataLoader>
  );
}
```

### 3. Form Components

These components handle user input and form submission.

#### Best Practices:

- Use the useForm hook for form state management
- Implement proper validation
- Provide clear feedback for validation errors
- Group related form fields together
- Use appropriate input types
- Support keyboard navigation

#### Example:

```tsx
// example of a form component
import { useForm } from '@/hooks';
import { Button } from '@/components/ui/button';
import { Form, FormField, FormItem, FormLabel, FormError } from '@/components/ui/form';
import { Input } from '@/components/ui/input';

function DataSourceForm({ onSubmit, initialData = {} }) {
  const form = useForm({
    defaultValues: {
      name: initialData.name || '',
      url: initialData.url || '',
      description: initialData.description || '',
    },
    validationSchema: {
      name: { required: 'Name is required' },
      url: { 
        required: 'URL is required',
        pattern: {
          value: /^https?:\/\/.+/,
          message: 'URL must be valid and start with http:// or https://'
        }
      },
    },
    onSubmit: (values) => {
      onSubmit(values);
    },
  });

  return (
    <Form {...form}>
      <FormField
        name="name"
        label="Name"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Name</FormLabel>
            <Input {...field} placeholder="Enter data source name" />
            <FormError />
          </FormItem>
        )}
      />
      
      <FormField
        name="url"
        label="URL"
        render={({ field }) => (
          <FormItem>
            <FormLabel>URL</FormLabel>
            <Input {...field} placeholder="https://example.com/api" />
            <FormError />
          </FormItem>
        )}
      />
      
      <FormField
        name="description"
        label="Description"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Description</FormLabel>
            <Textarea {...field} placeholder="Optional description" />
            <FormError />
          </FormItem>
        )}
      />
      
      <div className="flex justify-end gap-2 mt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={form.isSubmitting}>
          {initialData.id ? 'Update' : 'Create'}
        </Button>
      </div>
    </Form>
  );
}
```

### 4. Layout Components

These components define the structure of the application.

#### Best Practices:

- Keep layouts simple and focused on structure
- Make layouts responsive
- Use CSS Grid and Flexbox for positioning
- Extract reusable layout patterns

## Advanced Component Techniques

### 1. Component Composition

Use composition to build complex components from simpler ones.

```tsx
// Good example
function Card({ title, children, footer }) {
  return (
    <div className="card">
      {title && <div className="card-header">{title}</div>}
      <div className="card-body">{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
}

// Usage
<Card 
  title={<h2>My Card</h2>}
  footer={<Button>Action</Button>}
>
  <p>Card content goes here</p>
</Card>
```

### 2. Performance Optimization

- Use `React.memo` for components that don't need frequent updates
- Use `useCallback` and `useMemo` for expensive calculations
- Implement virtualization for long lists (DataTable supports this)
- Use proper keys for lists
- Avoid unnecessary re-renders

### 3. Error Handling

Always wrap components that might error in an ErrorBoundary:

```tsx
// In a page component
return (
  <ErrorBoundary fallback={<ErrorFallback onRetry={refetch} />}>
    <DataComponent />
  </ErrorBoundary>
);
```

## Accessibility

- Use semantic HTML elements
- Add proper ARIA attributes where needed
- Ensure keyboard navigation works
- Maintain proper contrast for text
- Test with screen readers

## Testing Components

- Write unit tests for UI components
- Write integration tests for forms and interactive components
- Test loading, error, and empty states
- Test edge cases 