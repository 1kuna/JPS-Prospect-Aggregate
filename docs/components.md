# Components

This document provides a comprehensive overview of all components available in the JPS-Prospect-Aggregate project.

## Table of Contents

- [UI Components](#ui-components)
  - [Button](#button)
  - [Card](#card)
  - [Table](#table)
  - [Pagination](#pagination)
  - [Form](#form)
  - [Input](#input)
  - [Label](#label)
  - [Dialog](#dialog)
  - [Alert](#alert)
  - [Skeleton](#skeleton)
- [Layout Components](#layout-components)
  - [PageLayout](#pagelayout)
  - [PageSkeleton](#pageskeleton)
- [Data Display Components](#data-display-components)
  - [DataTable](#datatable)
  - [StatsCard](#statscard)
  - [StatsGrid](#statsgrid)
- [Form Components](#form-components)
  - [FormWrapper](#formwrapper)
  - [DataSourceForm](#datasourceform)
- [Utility Components](#utility-components)
  - [ErrorBoundary](#errorboundary)
- [Hooks](#hooks)
  - [useDataFetching](#usedatafetching)
  - [useFormSubmit](#useformsubmit)
  - [useFetch](#usefetch)

## UI Components

This section describes the basic UI components available in the JPS-Prospect-Aggregate project. These components are the building blocks for more complex components and pages.

### Button

#### Purpose
A customizable button component with various styles, sizes, and states.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| variant | 'default' \| 'destructive' \| 'outline' \| 'secondary' \| 'ghost' \| 'link' \| 'success' \| 'warning' \| 'info' | No | 'default' | The visual style of the button |
| size | 'default' \| 'sm' \| 'md' \| 'lg' \| 'icon' | No | 'default' | The size of the button |
| asChild | boolean | No | false | Whether to render as a child component |
| className | string | No | undefined | Additional CSS classes |
| disabled | boolean | No | false | Whether the button is disabled |
| children | React.ReactNode | Yes | - | The content of the button |

#### Usage Examples
```jsx
<Button>Default Button</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline" size="sm">Small Outline</Button>
<Button variant="success" size="lg">Large Success</Button>
<Button variant="warning">Warning</Button>
<Button variant="info">Info</Button>
```

#### Implementation Details
The Button component is built on Radix UI's Slot primitive and uses Tailwind CSS for styling. It supports various variants and sizes, and can be disabled.

#### Related Components
- [Dialog](#dialog) (for button triggers)
- [Form](#form) (for form submission)

### Card

#### Purpose
A container component that groups related content with a consistent style.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| className | string | No | undefined | Additional CSS classes |
| children | React.ReactNode | Yes | - | The content of the card |

#### Sub-Components
- **CardHeader**: Container for the card title and description
- **CardTitle**: The title of the card
- **CardDescription**: A description or subtitle for the card
- **CardContent**: The main content area of the card
- **CardFooter**: Container for actions or additional information

#### Usage Examples
```jsx
<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description or subtitle</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Main content goes here</p>
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>
```

#### Implementation Details
The Card component and its sub-components use Tailwind CSS for styling and provide a consistent container for content with proper spacing and borders.

#### Related Components
- [StatsCard](#statscard) (uses Card internally)
- [FormWrapper](#formwrapper) (uses Card internally)

### Table

#### Purpose
A set of components for displaying tabular data with consistent styling.

#### Sub-Components
- **Table**: The root table component
- **TableHeader**: Container for table header rows
- **TableBody**: Container for table body rows
- **TableFooter**: Container for table footer rows
- **TableRow**: A table row
- **TableHead**: A table header cell
- **TableCell**: A table data cell
- **TableCaption**: A caption for the table

#### Usage Examples
```jsx
<Table>
  <TableCaption>List of users</TableCaption>
  <TableHeader>
    <TableRow>
      <TableHead>Name</TableHead>
      <TableHead>Email</TableHead>
      <TableHead>Role</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>John Doe</TableCell>
      <TableCell>john@example.com</TableCell>
      <TableCell>Admin</TableCell>
    </TableRow>
    <TableRow>
      <TableCell>Jane Smith</TableCell>
      <TableCell>jane@example.com</TableCell>
      <TableCell>User</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

#### Implementation Details
The Table components use Tailwind CSS for styling and provide a consistent way to display tabular data with proper spacing, borders, and hover states.

#### Related Components
- [DataTable](#datatable) (uses Table components internally)

### Pagination

#### Purpose
A set of components for creating pagination controls.

#### Sub-Components
- **Pagination**: The root pagination component
- **PaginationContent**: Container for pagination items
- **PaginationItem**: A pagination item
- **PaginationLink**: A pagination link
- **PaginationPrevious**: A link to the previous page
- **PaginationNext**: A link to the next page
- **PaginationEllipsis**: An ellipsis for skipped pages

#### Usage Examples
```jsx
<Pagination>
  <PaginationContent>
    <PaginationItem>
      <PaginationPrevious href="#" />
    </PaginationItem>
    <PaginationItem>
      <PaginationLink href="#">1</PaginationLink>
    </PaginationItem>
    <PaginationItem>
      <PaginationLink href="#" isActive>2</PaginationLink>
    </PaginationItem>
    <PaginationItem>
      <PaginationLink href="#">3</PaginationLink>
    </PaginationItem>
    <PaginationItem>
      <PaginationEllipsis />
    </PaginationItem>
    <PaginationItem>
      <PaginationLink href="#">10</PaginationLink>
    </PaginationItem>
    <PaginationItem>
      <PaginationNext href="#" />
    </PaginationItem>
  </PaginationContent>
</Pagination>
```

#### Implementation Details
The Pagination components use Tailwind CSS for styling and provide a consistent way to navigate through paginated content.

#### Related Components
- [DataTable](#datatable) (uses Pagination components internally)

### Form

#### Purpose
A set of components for building forms with validation and accessibility features.

#### Sub-Components
- **Form**: The root form component
- **FormItem**: Container for a form field
- **FormLabel**: Label for a form field
- **FormControl**: Container for form controls
- **FormDescription**: Description text for a form field
- **FormMessage**: Validation message for a form field
- **FormField**: Integration with react-hook-form

#### Usage Examples
```jsx
<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)}>
    <FormField
      control={form.control}
      name="username"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Username</FormLabel>
          <FormControl>
            <Input {...field} />
          </FormControl>
          <FormDescription>
            This is your public display name.
          </FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
    <Button type="submit">Submit</Button>
  </form>
</Form>
```

#### Implementation Details
The Form components are built on Radix UI's Form primitive and integrate with react-hook-form for form state management and validation.

#### Related Components
- [FormWrapper](#formwrapper) (uses Form components internally)
- [Input](#input)
- [Label](#label)

### Input

#### Purpose
A text input component for forms.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| type | string | No | 'text' | The type of input |
| className | string | No | undefined | Additional CSS classes |
| disabled | boolean | No | false | Whether the input is disabled |

#### Usage Examples
```jsx
<Input placeholder="Enter your name" />
<Input type="email" placeholder="Enter your email" />
<Input type="password" disabled />
```

#### Implementation Details
The Input component is a styled input element with consistent appearance across browsers.

#### Related Components
- [Form](#form)
- [FormWrapper](#formwrapper)

### Label

#### Purpose
A label component for form fields.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| htmlFor | string | No | undefined | ID of the associated form control |
| className | string | No | undefined | Additional CSS classes |
| children | React.ReactNode | Yes | - | The content of the label |

#### Usage Examples
```jsx
<Label htmlFor="email">Email</Label>
<Input id="email" type="email" />
```

#### Implementation Details
The Label component is built on Radix UI's Label primitive and provides consistent styling and accessibility features.

#### Related Components
- [Form](#form)
- [Input](#input)

### Dialog

#### Purpose
A dialog component for displaying content in a modal window.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| title | string | Yes | - | The title of the dialog |
| description | string | No | undefined | A short description or subtitle for the dialog |
| isOpen | boolean | Yes | - | Whether the dialog is open |
| onClose | () => void | Yes | - | Function to call when the dialog is closed |
| children | React.ReactNode | Yes | - | The content of the dialog |

#### Usage Examples
```jsx
<Dialog
  title="Confirm Deletion"
  description="Are you sure you want to delete this item?"
  isOpen={isConfirmationOpen}
  onClose={handleCloseConfirmation}
>
  <div className="space-y-4">
    <p>This action cannot be undone.</p>
    <div className="flex justify-end">
      <Button variant="destructive" onClick={handleDelete}>Delete</Button>
      <Button onClick={handleCloseConfirmation}>Cancel</Button>
    </div>
  </div>
</Dialog>
```

#### Implementation Details
The Dialog component provides a consistent structure for displaying content in a modal window with:
- A title and description
- Close button
- Container for the main content

#### Related Components
- [Button](#button) (for dialog triggers)

### Alert

#### Purpose
An alert component for displaying important messages to the user.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| variant | 'default' \| 'destructive' \| 'success' \| 'warning' \| 'info' | No | 'default' | The variant of the alert |
| children | React.ReactNode | Yes | - | The content of the alert |

#### Usage Examples
```jsx
<Alert variant="success">Data saved successfully!</Alert>
<Alert variant="warning">There was a problem with your request.</Alert>
```

#### Implementation Details
The Alert component provides a consistent structure for displaying important messages with:
- A variant indicating the type of message
- The content of the message

#### Related Components
- [Dialog](#dialog) (for displaying alerts)

### Skeleton

#### Purpose
A loading skeleton component that provides a visual placeholder while content is loading.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| cardCount | number | No | 3 | The number of skeleton cards to display |

#### Usage Examples
```jsx
<Skeleton cardCount={4} />
```

#### Implementation Details
The Skeleton component renders a grid of skeleton cards with animated loading effects. It's designed to match the layout of the actual content to minimize layout shifts when content loads.

#### Related Components
- [PageSkeleton](#pageskeleton)

## Layout Components

This section describes the layout components available in the JPS-Prospect-Aggregate project.

### PageLayout

#### Purpose
A standardized page layout component that provides consistent structure for all pages in the application.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| title | string | Yes | - | The main title of the page |
| description | string | No | undefined | A short description or subtitle for the page |
| lastUpdated | string \| Date \| null | No | undefined | Timestamp when the data was last updated |
| isLoading | boolean | No | false | Whether the page content is loading |
| error | { message: string } \| string \| null | No | null | Error object or message to display |
| onRefresh | () => void | No | undefined | Function to call when the refresh button is clicked |
| actions | React.ReactNode | No | undefined | Additional action buttons or elements to display in the header |
| children | React.ReactNode | Yes | - | The main content of the page |

#### Usage Examples
```jsx
<PageLayout 
  title="Dashboard" 
  description="Overview of key metrics"
  lastUpdated={new Date()}
  onRefresh={handleRefresh}
  isLoading={isLoading}
  error={error}
  actions={<Button onClick={handleExport}>Export</Button>}
>
  <YourPageContent />
</PageLayout>
```

#### Implementation Details
The PageLayout component provides a consistent structure for all pages with:
- A header section with title, description, and last updated timestamp
- Optional refresh button and custom action buttons
- Error alert display when errors occur
- Container for the main content

#### Related Components
- [PageSkeleton](#pageskeleton)

### PageSkeleton

#### Purpose
A loading skeleton component that provides a visual placeholder while page content is loading.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| cardCount | number | No | 3 | The number of skeleton cards to display |

#### Usage Examples
```jsx
<PageSkeleton cardCount={4} />
```

#### Implementation Details
The PageSkeleton component renders a grid of skeleton cards with animated loading effects. It's designed to match the layout of the actual content to minimize layout shifts when content loads.

#### Related Components
- [PageLayout](#pagelayout)

## Data Display Components

This section describes the data display components available in the JPS-Prospect-Aggregate project.

### DataTable

#### Purpose
A flexible table component for displaying tabular data with support for pagination.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| title | string | No | undefined | The title of the table |
| description | string | No | undefined | A description of the table content |
| data | T[] | Yes | - | The array of data to display |
| columns | Column<T>[] | Yes | - | Configuration for table columns |
| keyField | keyof T | Yes | - | The property to use as a unique key for each row |
| pagination | PaginationInfo | No | undefined | Pagination configuration |
| onPageChange | (page: number) => void | No | undefined | Function called when page changes |
| isLoading | boolean | No | false | Whether the table is in a loading state |
| emptyMessage | { title: string, description: string } | No | { title: 'No data found', description: 'There are no items to display.' } | Message to display when there's no data |

#### Column Configuration
| Prop | Type | Required | Description |
|------|------|----------|-------------|
| header | string | Yes | The column header text |
| accessor | keyof T \| ((item: T) => React.ReactNode) | Yes | Property name or function to get cell value |
| className | string | No | Additional CSS classes for the column |
| onClick | () => void | No | Function called when the header is clicked |

#### Pagination Configuration
| Prop | Type | Required | Description |
|------|------|----------|-------------|
| page | number | Yes | Current page number |
| perPage | number | Yes | Number of items per page |
| totalPages | number | Yes | Total number of pages |
| totalItems | number | No | Total number of items |

#### Usage Example
```jsx
const columns = [
  { header: 'Title', accessor: 'title' },
  { header: 'Agency', accessor: 'agency' },
  { header: 'Value', accessor: (item) => `$${item.estimated_value.toLocaleString()}` },
  { header: 'Status', accessor: 'status' }
];

<DataTable
  title="Proposals"
  description="List of all proposals"
  data={proposals}
  columns={columns}
  keyField="id"
  pagination={{
    page: 1,
    perPage: 10,
    totalPages: 5,
    totalItems: 45
  }}
  onPageChange={handlePageChange}
/>
```

#### Implementation Details
The DataTable component provides a flexible way to display tabular data with:
- Customizable columns with support for both simple property access and custom rendering
- Pagination controls with page size and navigation
- Loading state with skeleton placeholders
- Empty state messaging
- Card-based container with title and description

#### Related Components
- [StatsCard](#statscard)
- [StatsGrid](#statsgrid)

### StatsCard

#### Purpose
A card component for displaying a list of statistics with labels and values.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| title | string | Yes | - | The title of the stats card |
| description | string | No | undefined | A description of the stats |
| stats | StatItem[] | Yes | - | Array of statistics to display |
| className | string | No | undefined | Additional CSS classes |
| isLoading | boolean | No | false | Whether the card is in a loading state |

#### StatItem Configuration
| Prop | Type | Required | Description |
|------|------|----------|-------------|
| label | string | Yes | Label for the statistic |
| value | React.ReactNode | Yes | Value of the statistic |
| className | string | No | Additional CSS classes for the value |

#### Usage Example
```jsx
<StatsCard
  title="Proposal Statistics"
  description="Overview of proposal metrics"
  stats={[
    { label: 'Total Proposals', value: 120 },
    { label: 'Active Proposals', value: 45, className: 'text-green-600' },
    { label: 'Completed Proposals', value: 75, className: 'text-blue-600' }
  ]}
/>
```

#### Implementation Details
The StatsCard component displays a list of statistics in a card format with:
- A title and optional description
- Each statistic shown as a label-value pair
- Support for custom styling of values
- Loading skeleton state

#### Related Components
- [StatsGrid](#statsgrid)
- [DataTable](#datatable)

### StatsGrid

#### Purpose
A grid layout for organizing multiple StatsCard components.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| children | React.ReactNode | Yes | - | Child components (typically StatsCard) |
| columns | 1 \| 2 \| 3 \| 4 | No | 3 | Number of columns in the grid |
| className | string | No | undefined | Additional CSS classes |

#### Usage Example
```jsx
<StatsGrid columns={3}>
  <StatsCard title="Proposals" stats={proposalStats} />
  <StatsCard title="Data Sources" stats={dataSourceStats} />
  <StatsCard title="System Status" stats={systemStats} />
</StatsGrid>
```

#### Implementation Details
The StatsGrid component creates a responsive grid layout that:
- Adjusts columns based on screen size
- Provides consistent spacing between cards
- Allows for customization of the number of columns

#### Related Components
- [StatsCard](#statscard)

## Form Components

This section describes components used for building forms.

### FormWrapper

#### Purpose
A wrapper component for forms with built-in validation and error handling.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| onSubmit | (data: T) => void \| Promise<void> | Yes | - | Function called when form is submitted |
| schema | ZodSchema<T> | Yes | - | Zod schema for form validation |
| defaultValues | Partial<T> | No | {} | Default values for form fields |
| children | React.ReactNode | Yes | - | Form fields and controls |
| className | string | No | undefined | Additional CSS classes |

#### Usage Example
```jsx
import { z } from 'zod';

const formSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email address')
});

<FormWrapper
  schema={formSchema}
  onSubmit={handleSubmit}
  defaultValues={{ name: '', email: '' }}
>
  <div className="space-y-4">
    <div>
      <Label htmlFor="name">Name</Label>
      <Input id="name" name="name" />
    </div>
    <div>
      <Label htmlFor="email">Email</Label>
      <Input id="email" name="email" type="email" />
    </div>
    <Button type="submit">Submit</Button>
  </div>
</FormWrapper>
```

### DataSourceForm

#### Purpose
A specialized form for creating and editing data sources.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| onSubmit | (data: DataSourceFormData) => void \| Promise<void> | Yes | - | Function called when form is submitted |
| defaultValues | Partial<DataSourceFormData> | No | {} | Default values for form fields |
| isEdit | boolean | No | false | Whether the form is for editing an existing data source |

#### Usage Example
```jsx
<DataSourceForm
  onSubmit={handleCreateDataSource}
  defaultValues={{
    name: '',
    url: '',
    description: ''
  }}
/>
```

## Utility Components

This section describes utility components available in the JPS-Prospect-Aggregate project.

### ErrorBoundary

#### Purpose
A component for handling errors in a React application.

#### Props
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| children | React.ReactNode | Yes | - | The content of the error boundary |

#### Usage Example
```jsx
<ErrorBoundary>
  <YourComponent />
</ErrorBoundary>
```

#### Implementation Details
The ErrorBoundary component provides a way to handle errors in a React application. It can be used to catch and handle errors in a component tree.

## Hooks

This section describes custom React hooks available in the project.

### useDataFetching

#### Purpose
A hook for fetching data from the API with built-in loading, error, and pagination handling.

#### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | The API endpoint URL |
| options | FetchOptions | No | {} | Additional options for the fetch request |

#### FetchOptions
| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| method | 'GET' \| 'POST' \| 'PUT' \| 'DELETE' | No | 'GET' | HTTP method |
| body | object | No | undefined | Request body (for POST/PUT) |
| headers | Record<string, string> | No | {} | Additional request headers |
| params | Record<string, string \| number> | No | {} | URL query parameters |
| initialData | T | No | null | Initial data before fetch completes |
| onSuccess | (data: T) => void | No | undefined | Callback on successful fetch |
| onError | (error: Error) => void | No | undefined | Callback on fetch error |

#### Returns
| Property | Type | Description |
|----------|------|-------------|
| data | T \| null | The fetched data |
| loading | boolean | Whether the request is in progress |
| error | Error \| null | Any error that occurred |
| refetch | () => Promise<void> | Function to refetch the data |
| setData | React.Dispatch<React.SetStateAction<T \| null>> | Function to manually update the data |

#### Usage Example
```jsx
const { data, loading, error, refetch } = useDataFetching('/api/v1/proposals', {
  params: { page: 1, per_page: 10 },
  onSuccess: (data) => console.log('Data loaded:', data)
});
```

### useFormSubmit

#### Purpose
A hook for handling form submissions with loading and error states.

#### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| callback | (data: T) => Promise<void> | Yes | - | Function to call with form data |
| options | SubmitOptions | No | {} | Additional options |

#### SubmitOptions
| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| onSuccess | () => void | No | undefined | Callback on successful submission |
| onError | (error: Error) => void | No | undefined | Callback on submission error |

#### Returns
| Property | Type | Description |
|----------|------|-------------|
| handleSubmit | (data: T) => Promise<void> | Function to handle form submission |
| isSubmitting | boolean | Whether submission is in progress |
| error | Error \| null | Any error that occurred |

#### Usage Example
```jsx
const { handleSubmit, isSubmitting, error } = useFormSubmit(async (data) => {
  await fetch('/api/v1/data-sources', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
}, {
  onSuccess: () => {
    toast.success('Data source created successfully');
    router.push('/data-sources');
  }
});
```

### useFetch

#### Purpose
A lower-level hook for making fetch requests with type safety.

#### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| options | UseFetchOptions | No | {} | Configuration options |

#### UseFetchOptions
| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| baseUrl | string | No | '/api/v1' | Base URL for all requests |
| headers | Record<string, string> | No | {} | Default headers for all requests |

#### Returns
| Property | Type | Description |
|----------|------|-------------|
| get | <T>(url: string, options?: FetchOptions) => Promise<T> | Function for GET requests |
| post | <T>(url: string, data: any, options?: FetchOptions) => Promise<T> | Function for POST requests |
| put | <T>(url: string, data: any, options?: FetchOptions) => Promise<T> | Function for PUT requests |
| delete | <T>(url: string, options?: FetchOptions) => Promise<T> | Function for DELETE requests |

#### Usage Example
```jsx
const { get, post } = useFetch();

// GET request
const fetchProposals = async () => {
  const response = await get('/proposals', { params: { page: 1 } });
  setProposals(response.data);
};

// POST request
const createDataSource = async (data) => {
  await post('/data-sources', data);
  toast.success('Data source created');
};
``` 