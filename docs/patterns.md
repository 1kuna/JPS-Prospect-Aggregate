# Development Patterns

This document describes the development patterns used in the JPS-Prospect-Aggregate project.

## Table of Contents

- [State Management](#state-management)
  - [Local Component State](#local-component-state)
  - [React Context](#react-context)
  - [Zustand](#zustand)
  - [Best Practices](#state-management-best-practices)
- [Data Fetching](#data-fetching)
  - [Custom Hooks](#custom-hooks)
  - [Loading States](#loading-states)
  - [Pagination](#pagination)
  - [Caching](#caching)
  - [Best Practices](#data-fetching-best-practices)
- [Error Handling](#error-handling)
  - [Centralized Error Handling](#centralized-error-handling)
  - [Error Boundaries](#error-boundaries)
  - [API Error Handling](#api-error-handling)
  - [Form Validation Errors](#form-validation-errors)
  - [Best Practices](#error-handling-best-practices)
- [Form Handling](#form-handling)
  - [React Hook Form](#react-hook-form)
  - [Zod Validation](#zod-validation)
  - [FormWrapper Component](#formwrapper-component)
  - [Form Field Components](#form-field-components)
  - [Best Practices](#form-handling-best-practices)

## State Management

### Overview

The project uses a combination of state management approaches:

1. **Local Component State**: For component-specific state
2. **React Context**: For shared state within a feature
3. **Zustand**: For global application state

### Local Component State

Use local component state (via `useState` or `useReducer`) when:

- State is only relevant to a single component
- State doesn't need to be shared with other components
- State is simple and doesn't require complex logic

Example:
```tsx
function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}
```

### React Context

Use React Context when:

- State needs to be shared between multiple components
- State is specific to a feature or section of the app
- You want to avoid prop drilling

Example:
```tsx
// 1. Create context
const ThemeContext = createContext({ theme: 'light', toggleTheme: () => {} });

// 2. Create provider
function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  
  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };
  
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

// 3. Use context in components
function ThemedButton() {
  const { theme, toggleTheme } = useContext(ThemeContext);
  
  return (
    <button 
      className={`btn-${theme}`}
      onClick={toggleTheme}
    >
      Toggle Theme
    </button>
  );
}
```

### Zustand

Use Zustand for global state management when:

- State needs to be accessed by many components across the app
- State requires complex logic or middleware
- You need to persist state across sessions

Example:
```tsx
// 1. Create store
import { create } from 'zustand';

interface AppState {
  count: number;
  increment: () => void;
  decrement: () => void;
}

const useStore = create<AppState>((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 })),
  decrement: () => set((state) => ({ count: state.count - 1 })),
}));

// 2. Use store in components
function Counter() {
  const { count, increment, decrement } = useStore();
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={increment}>Increment</button>
      <button onClick={decrement}>Decrement</button>
    </div>
  );
}
```

### State Management Best Practices

1. **Start Simple**: Begin with local state and only move to more complex solutions when needed
2. **Colocate State**: Keep state as close as possible to where it's used
3. **Avoid Redundant State**: Don't duplicate state that can be derived from existing state
4. **Use Selectors**: When using Zustand, use selectors to only re-render when necessary
5. **Separate UI and Domain State**: Keep UI state (like form values) separate from domain state (like user data)

#### Do's and Don'ts

##### Do's
- ✅ Use TypeScript to type your state
- ✅ Keep state normalized when dealing with relational data
- ✅ Use immutable patterns for updating state
- ✅ Split large stores into smaller, focused ones

##### Don'ts
- ❌ Put everything in global state
- ❌ Create deeply nested state objects
- ❌ Mutate state directly
- ❌ Store derived state that can be calculated from existing state

## Data Fetching

### Overview

The project uses a consistent approach to data fetching with the following patterns:

1. **Custom Hooks**: Encapsulate data fetching logic in reusable hooks
2. **Loading States**: Handle loading, error, and success states consistently
3. **Pagination**: Standardized approach to paginated data
4. **Caching**: Simple caching strategy for frequently accessed data

### Custom Hooks

The primary data fetching hook is `useDataFetching`, which provides a consistent interface for all API calls:

```tsx
const {
  data,
  isLoading,
  error,
  fetchData,
  pagination,
  setPagination,
  lastUpdated
} = useDataFetching({
  url: '/api/users',
  params: { status: 'active' },
  transformResponse: (response) => response.data.users
});
```

#### Key Features

- Consistent loading, error, and success states
- Pagination support
- Automatic and manual fetching
- Response transformation
- TypeScript support

### Loading States

All data fetching follows a consistent pattern for handling loading states:

```tsx
function UserList() {
  const { data: users, isLoading, error } = useDataFetching({ url: '/api/users' });
  
  if (isLoading) {
    return <PageSkeleton />;
  }
  
  if (error) {
    return <ErrorMessage message={error.message} />;
  }
  
  return (
    <div>
      {users.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  );
}
```

### Pagination

Pagination is handled consistently across the application:

```tsx
function UserList() {
  const {
    data: users,
    pagination,
    setPagination
  } = useDataFetching({
    url: '/api/users',
    params: { page: 1, perPage: 10 }
  });
  
  const handlePageChange = (page) => {
    setPagination({ page, perPage: pagination.perPage });
  };
  
  return (
    <div>
      <DataTable
        data={users}
        // ...other props
        pagination={pagination}
        onPageChange={handlePageChange}
      />
    </div>
  );
}
```

### Caching

Simple caching is implemented for frequently accessed data:

```tsx
// In a store or context
const cache = new Map();

function fetchWithCache(url, params) {
  const cacheKey = `${url}?${new URLSearchParams(params)}`;
  
  if (cache.has(cacheKey)) {
    const { data, timestamp } = cache.get(cacheKey);
    const isStale = Date.now() - timestamp > CACHE_TTL;
    
    if (!isStale) {
      return Promise.resolve(data);
    }
  }
  
  return fetch(url, params)
    .then(response => response.json())
    .then(data => {
      cache.set(cacheKey, { data, timestamp: Date.now() });
      return data;
    });
}
```

### Data Fetching Best Practices

1. **Use Custom Hooks**: Encapsulate data fetching logic in reusable hooks
2. **Handle All States**: Always handle loading, error, and success states
3. **Consistent Error Handling**: Use a consistent approach to error handling
4. **Avoid Redundant Fetches**: Implement caching for frequently accessed data
5. **Optimize Pagination**: Only fetch the data needed for the current page

#### Do's and Don'ts

##### Do's
- ✅ Use TypeScript to type API responses
- ✅ Implement proper error handling
- ✅ Show loading states to improve user experience
- ✅ Transform API responses to match component needs

##### Don'ts
- ❌ Fetch data directly in components
- ❌ Ignore error states
- ❌ Fetch more data than needed
- ❌ Duplicate data fetching logic across components

## Error Handling

### Overview

The project uses a consistent approach to error handling with the following patterns:

1. **Centralized Error Handling**: Common error handling logic in reusable components
2. **Error Boundaries**: React error boundaries for component errors
3. **API Error Handling**: Consistent approach to API errors
4. **Form Validation Errors**: Standardized form validation error handling

### Centralized Error Handling

Common error handling logic is centralized in reusable components:

```tsx
function ErrorAlert({ error }) {
  if (!error) return null;
  
  const message = typeof error === 'string' ? error : error.message;
  
  return (
    <Alert variant="destructive">
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
```

### Error Boundaries

React error boundaries are used to catch JavaScript errors in components:

```tsx
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to an error reporting service
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong.</h2>
          <p>{this.state.error.message}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

Usage:

```tsx
<ErrorBoundary>
  <MyComponent />
</ErrorBoundary>
```

### API Error Handling

API errors are handled consistently across the application:

```tsx
async function fetchData() {
  try {
    const response = await fetch('/api/data');
    
    if (!response.ok) {
      // Handle HTTP error status
      const errorData = await response.json();
      throw new Error(errorData.message || `Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    // Handle network errors or errors thrown above
    console.error('API Error:', error);
    throw error; // Re-throw for component to handle
  }
}
```

In components:

```tsx
function DataComponent() {
  const { data, error, isLoading } = useDataFetching({ url: '/api/data' });
  
  if (isLoading) return <Loading />;
  if (error) return <ErrorAlert error={error} />;
  
  return <DataDisplay data={data} />;
}
```

### Form Validation Errors

Form validation errors are handled using Zod and react-hook-form:

```tsx
const schema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

function LoginForm() {
  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      email: '',
      password: '',
    },
  });
  
  const onSubmit = async (data) => {
    try {
      await login(data);
    } catch (error) {
      form.setError('root', { message: error.message });
    }
  };
  
  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      {form.formState.errors.root && (
        <ErrorAlert error={form.formState.errors.root.message} />
      )}
      
      <FormField
        control={form.control}
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
      
      {/* Other form fields */}
      
      <Button type="submit">Login</Button>
    </form>
  );
}
```

### Error Handling Best Practices

1. **Be Specific**: Provide specific error messages that help users understand what went wrong
2. **Graceful Degradation**: Design components to gracefully handle errors
3. **Centralize Logic**: Use common components for error display
4. **Log Errors**: Log errors for debugging and monitoring
5. **Recover When Possible**: Provide retry mechanisms when appropriate

#### Do's and Don'ts

##### Do's
- ✅ Use error boundaries for component errors
- ✅ Provide user-friendly error messages
- ✅ Log errors for debugging
- ✅ Handle different types of errors appropriately

##### Don'ts
- ❌ Show technical error details to users
- ❌ Ignore errors
- ❌ Use generic error messages for all errors
- ❌ Let errors crash the entire application

## Form Handling

### Overview

The project uses a consistent approach to form handling with the following patterns:

1. **React Hook Form**: For form state management and validation
2. **Zod**: For schema validation
3. **FormWrapper**: A reusable component for consistent form styling and behavior
4. **Controlled Components**: For form inputs

### React Hook Form

[React Hook Form](https://react-hook-form.com/) is used for form state management:

```tsx
import { useForm } from 'react-hook-form';

function SimpleForm() {
  const { register, handleSubmit, formState: { errors } } = useForm();
  
  const onSubmit = (data) => {
    console.log(data);
  };
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name', { required: 'Name is required' })} />
      {errors.name && <span>{errors.name.message}</span>}
      
      <button type="submit">Submit</button>
    </form>
  );
}
```

### Zod Validation

[Zod](https://github.com/colinhacks/zod) is used for schema validation:

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  age: z.number().min(18, 'You must be at least 18 years old'),
});

function ValidatedForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });
  
  const onSubmit = (data) => {
    console.log(data);
  };
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name')} />
      {errors.name && <span>{errors.name.message}</span>}
      
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
      
      <input type="number" {...register('age', { valueAsNumber: true })} />
      {errors.age && <span>{errors.age.message}</span>}
      
      <button type="submit">Submit</button>
    </form>
  );
}
```

### FormWrapper Component

The `FormWrapper` component provides a consistent interface for forms:

```tsx
import { FormWrapper } from '@/components/forms';

function UserForm() {
  const handleSubmit = (data) => {
    console.log(data);
  };
  
  return (
    <FormWrapper
      title="User Information"
      description="Enter your personal information"
      schema={userSchema}
      defaultValues={{ name: '', email: '', age: 18 }}
      onSubmit={handleSubmit}
      onCancel={() => console.log('Cancelled')}
      submitLabel="Save User"
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
      
      {/* Other form fields */}
    </FormWrapper>
  );
}
```

### Form Field Components

Form fields are implemented using the shadcn/ui form components:

```tsx
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';

function FormFieldExample() {
  const form = useForm({
    defaultValues: {
      username: '',
    },
  });
  
  return (
    <Form {...form}>
      <form>
        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input placeholder="Enter username" {...field} />
              </FormControl>
              <FormDescription>
                This is your public display name.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
      </form>
    </Form>
  );
}
```

### Form Handling Best Practices

1. **Use Schema Validation**: Always validate form inputs with a schema
2. **Consistent Error Display**: Display validation errors consistently
3. **Disable During Submission**: Disable form controls during submission
4. **Show Feedback**: Provide feedback on form submission status
5. **Optimize Validation**: Use validation modes that balance UX and performance

#### Do's and Don'ts

##### Do's
- ✅ Use controlled components for form inputs
- ✅ Provide clear validation messages
- ✅ Handle submission errors gracefully
- ✅ Use appropriate input types for different data

##### Don'ts
- ❌ Use uncontrolled components without a good reason
- ❌ Validate only on submission
- ❌ Ignore accessibility in forms
- ❌ Create overly complex validation rules 