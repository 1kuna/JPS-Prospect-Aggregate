# Store Slices

This directory contains domain-focused slices for the Zustand store. Each slice represents a specific domain entity and contains the state, actions, and logic related to that entity.

## Slice Structure

A well-structured slice should follow this pattern:

1. **Import Dependencies**: Import necessary types and API functions
2. **Define Slice Interface**: Create a TypeScript interface that defines the state and actions
3. **Implement Slice**: Create a function that returns the state and actions
4. **Include Helper Functions**: Define any helper functions that are used in the slice

## Example Slice

Here's an example of a well-structured slice for a posts feature:

```typescript
// postsSlice.ts
import { StateCreator } from 'zustand';
import { StoreState } from '../types';
import { api, ApiError } from '../api';

// 1. Define types for the slice's state
export interface Post {
  id: number;
  title: string;
  body: string;
  author: string;
  created_at: string;
  updated_at: string;
  tags: string[];
}

// 2. Define the slice interface
export interface PostsSlice {
  // State
  posts: Post[];
  currentPost: Post | null;
  postsLoading: boolean;
  postsError: Error | null;
  
  // Pagination
  postsPagination: {
    page: number;
    perPage: number;
    totalCount: number;
    totalPages: number;
  };
  
  // Filters
  postsFilter: {
    tag?: string;
    author?: string;
    searchTerm?: string;
  };
  
  // Actions
  fetchPosts: (params?: { 
    page?: number; 
    perPage?: number;
    tag?: string;
    author?: string;
    searchTerm?: string;
  }) => Promise<void>;
  
  fetchPostById: (id: number) => Promise<void>;
  createPost: (post: Omit<Post, 'id' | 'created_at' | 'updated_at'>) => Promise<Post>;
  updatePost: (id: number, data: Partial<Post>) => Promise<Post>;
  deletePost: (id: number) => Promise<void>;
  setPostsFilter: (filter: Partial<PostsSlice['postsFilter']>) => void;
  resetPostsFilter: () => void;
}

// 3. Default state values
const DEFAULT_PAGINATION = {
  page: 1,
  perPage: 20,
  totalCount: 0,
  totalPages: 0
};

const DEFAULT_FILTER = {
  tag: undefined,
  author: undefined,
  searchTerm: undefined
};

// 4. Implement the slice
export const postsSlice: StateCreator<StoreState> = (set, get) => ({
  // Initial state
  posts: [],
  currentPost: null,
  postsLoading: false,
  postsError: null,
  postsPagination: DEFAULT_PAGINATION,
  postsFilter: DEFAULT_FILTER,
  
  // Actions
  fetchPosts: async (params = {}) => {
    // Start loading
    set({ postsLoading: true });
    
    try {
      // Build query parameters
      const queryParams = {
        page: params.page || get().postsPagination.page,
        per_page: params.perPage || get().postsPagination.perPage,
        tag: params.tag !== undefined ? params.tag : get().postsFilter.tag,
        author: params.author !== undefined ? params.author : get().postsFilter.author,
        search: params.searchTerm !== undefined ? params.searchTerm : get().postsFilter.searchTerm
      };
      
      // Make API request
      const response = await api.get<Post[]>('/posts', { params: queryParams });
      
      // Update state with response
      set({ 
        posts: response.data,
        postsLoading: false,
        postsError: null,
        postsPagination: {
          page: queryParams.page,
          perPage: queryParams.per_page,
          totalCount: response.pagination?.total_items || 0,
          totalPages: response.pagination?.total_pages || 0
        },
        postsFilter: {
          tag: queryParams.tag,
          author: queryParams.author,
          searchTerm: queryParams.search
        }
      });
    } catch (error) {
      // Handle error
      const errorObj = error instanceof Error 
        ? error 
        : new Error(String(error));
        
      set({ 
        postsLoading: false,
        postsError: errorObj
      });
      
      // Create toast notification for error
      get().addToast({
        title: 'Error',
        description: `Failed to fetch posts: ${errorObj.message}`,
        variant: 'destructive'
      });
    }
  },
  
  fetchPostById: async (id) => {
    set({ postsLoading: true });
    
    try {
      const response = await api.get<Post>(`/posts/${id}`);
      
      set({ 
        currentPost: response.data,
        postsLoading: false,
        postsError: null
      });
    } catch (error) {
      const errorObj = error instanceof Error 
        ? error 
        : new Error(String(error));
        
      set({ 
        postsLoading: false,
        postsError: errorObj
      });
      
      get().addToast({
        title: 'Error',
        description: `Failed to fetch post: ${errorObj.message}`,
        variant: 'destructive'
      });
    }
  },
  
  createPost: async (post) => {
    set({ postsLoading: true });
    
    try {
      const response = await api.post<Post>('/posts', post);
      
      // Update posts array with new post
      set(state => ({ 
        posts: [response.data, ...state.posts],
        currentPost: response.data,
        postsLoading: false,
        postsError: null
      }));
      
      get().addToast({
        title: 'Success',
        description: 'Post created successfully',
        variant: 'success'
      });
      
      return response.data;
    } catch (error) {
      const errorObj = error instanceof Error 
        ? error 
        : new Error(String(error));
        
      set({ 
        postsLoading: false,
        postsError: errorObj
      });
      
      get().addToast({
        title: 'Error',
        description: `Failed to create post: ${errorObj.message}`,
        variant: 'destructive'
      });
      
      throw errorObj;
    }
  },
  
  updatePost: async (id, data) => {
    set({ postsLoading: true });
    
    try {
      const response = await api.put<Post>(`/posts/${id}`, data);
      
      // Update posts array and current post with updated post
      set(state => ({ 
        posts: state.posts.map(post => 
          post.id === id ? response.data : post
        ),
        currentPost: state.currentPost?.id === id 
          ? response.data 
          : state.currentPost,
        postsLoading: false,
        postsError: null
      }));
      
      get().addToast({
        title: 'Success',
        description: 'Post updated successfully',
        variant: 'success'
      });
      
      return response.data;
    } catch (error) {
      const errorObj = error instanceof Error 
        ? error 
        : new Error(String(error));
        
      set({ 
        postsLoading: false,
        postsError: errorObj
      });
      
      get().addToast({
        title: 'Error',
        description: `Failed to update post: ${errorObj.message}`,
        variant: 'destructive'
      });
      
      throw errorObj;
    }
  },
  
  deletePost: async (id) => {
    set({ postsLoading: true });
    
    try {
      await api.delete(`/posts/${id}`);
      
      // Remove post from posts array and clear current post if it's the deleted one
      set(state => ({ 
        posts: state.posts.filter(post => post.id !== id),
        currentPost: state.currentPost?.id === id 
          ? null 
          : state.currentPost,
        postsLoading: false,
        postsError: null
      }));
      
      get().addToast({
        title: 'Success',
        description: 'Post deleted successfully',
        variant: 'success'
      });
    } catch (error) {
      const errorObj = error instanceof Error 
        ? error 
        : new Error(String(error));
        
      set({ 
        postsLoading: false,
        postsError: errorObj
      });
      
      get().addToast({
        title: 'Error',
        description: `Failed to delete post: ${errorObj.message}`,
        variant: 'destructive'
      });
      
      throw errorObj;
    }
  },
  
  setPostsFilter: (filter) => {
    set(state => ({
      postsFilter: {
        ...state.postsFilter,
        ...filter
      }
    }));
    
    // Fetch posts with new filter
    get().fetchPosts({ page: 1 }); // Reset to page 1 when filter changes
  },
  
  resetPostsFilter: () => {
    set({ postsFilter: DEFAULT_FILTER });
    
    // Fetch posts with reset filter
    get().fetchPosts({ page: 1 });
  }
});

// 5. Export helper functions if needed
export const isPostOwner = (post: Post, currentUser: string) => {
  return post.author === currentUser;
};

export const getPostsByTag = (posts: Post[], tag: string) => {
  return posts.filter(post => post.tags.includes(tag));
};
```

## Best Practices

1. **Domain-Based Organization**: Each slice should represent a specific domain entity (e.g., users, posts, comments, products).
2. **Immutable Updates**: Always use immutable patterns for updating state.
3. **Error Handling**: Implement comprehensive error handling in all async actions.
4. **Normalize Data**: Store data in a normalized form to avoid duplication.
5. **Default State**: Define default values for state to ensure consistent initialization.
6. **Optimistic Updates**: Consider implementing optimistic updates for better UX.
7. **Toast Feedback**: Use toast notifications to provide feedback to users.
8. **Type Safety**: Use TypeScript interfaces for complete type safety.
9. **JSDoc Comments**: Document complex state properties and functions with JSDoc comments.
10. **Keep Pure Functions Pure**: Don't mix side effects with pure functions.

## Combining Slices

Slices are combined in the main `useStore.ts` file to create the complete store. Each slice should focus on a specific domain aspect of the application, making the code more maintainable and easier to reason about.

## Current Slices

### `dataSourcesSlice.ts`

Manages all state related to data sources, including fetching, creating, updating, and deleting data sources, as well as pulling data from sources.

### `proposalsSlice.ts`

Handles proposal data, including fetching, filtering, and pagination.

### `analyticsSlice.ts`

Consolidates analytics functionality, including statistics and dashboard data for reporting, trends, and insights. Combines what was previously separate statistics and dashboard concerns into a unified slice.

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