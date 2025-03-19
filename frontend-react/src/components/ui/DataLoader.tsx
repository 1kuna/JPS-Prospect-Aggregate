import React, { ReactNode } from 'react';
import { Skeleton } from './skeleton';
import { Alert } from './alert';
import { Button } from './button';

/**
 * Reusable component for handling loading, error, and empty states in data fetching
 */
interface DataLoaderProps<T> {
  /**
   * The data to display when loading is complete and no errors occurred
   */
  data: T | null | undefined;
  
  /**
   * Whether the data is currently loading
   */
  isLoading: boolean;
  
  /**
   * Any error that occurred during data loading
   */
  error: Error | null | undefined;
  
  /**
   * Content to show while data is loading
   */
  loadingComponent?: ReactNode;
  
  /**
   * Content to show when an error occurs
   * Can be a React node or a function that takes the error and returns a React node
   */
  errorComponent?: ReactNode | ((error: Error) => ReactNode);
  
  /**
   * Content to show when there is no data
   */
  emptyComponent?: ReactNode;
  
  /**
   * Function to render the data when loading is complete and no errors occurred
   */
  children: (data: T) => ReactNode;
  
  /**
   * Function to call when retry button is clicked (if an error occurred)
   */
  onRetry?: () => void;
  
  /**
   * Optional additional class name for the wrapper
   */
  className?: string;
  
  /**
   * Custom skeleton configuration for loading state
   */
  skeleton?: {
    count?: number;
    height?: string;
    width?: string;
  };
  
  /**
   * Function to determine if data is considered empty
   */
  isDataEmpty?: (data: T) => boolean;
}

/**
 * A component that handles the common data loading patterns:
 * - Loading state
 * - Error state
 * - Empty state
 * - Success state
 */
export function DataLoader<T>({
  data,
  isLoading,
  error,
  loadingComponent,
  errorComponent,
  emptyComponent,
  children,
  onRetry,
  className = '',
  skeleton = { count: 4, height: 'h-10', width: 'w-full' },
  isDataEmpty
}: DataLoaderProps<T>) {
  // Check if data is empty
  const isEmpty = () => {
    if (isDataEmpty) {
      return isDataEmpty(data as T);
    }
    
    return !data || (Array.isArray(data) && data.length === 0);
  };
  
  // Show loading state
  if (isLoading) {
    return loadingComponent ? (
      <div className={className}>{loadingComponent}</div>
    ) : (
      <div className={`space-y-2 ${className}`}>
        {Array.from({ length: skeleton.count || 4 }).map((_, i) => (
          <Skeleton 
            key={i} 
            className={`${skeleton.height || 'h-10'} ${i === 0 ? 'w-2/3' : i === skeleton.count! - 1 ? 'w-4/5' : skeleton.width || 'w-full'}`} 
          />
        ))}
      </div>
    );
  }
  
  // Show error state
  if (error) {
    if (errorComponent) {
      return (
        <div className={className}>
          {typeof errorComponent === 'function' 
            ? errorComponent(error) 
            : errorComponent}
        </div>
      );
    }
    
    return (
      <div className={`my-4 ${className}`}>
        <Alert 
          variant="destructive" 
          title="Error loading data"
          description={error.message}
        >
          {onRetry && (
            <Button 
              onClick={onRetry} 
              variant="destructive"
              className="mt-2"
              size="sm"
            >
              Retry
            </Button>
          )}
        </Alert>
      </div>
    );
  }
  
  // Show empty state
  if (isEmpty()) {
    return emptyComponent ? (
      <div className={className}>{emptyComponent}</div>
    ) : (
      <div className={`text-center my-8 p-4 bg-gray-50 rounded-lg ${className}`}>
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }
  
  // Show data
  return <div className={className}>{children(data as T)}</div>;
}

/**
 * Higher-order component that combines DataLoader with a data fetching hook
 */
export function withDataFetching<P extends object, T>(
  Component: React.ComponentType<P & { data: T; loading: boolean; error: Error | null }>,
  options: {
    selector: (state: any) => T;
    fetchAction: (...args: any[]) => Promise<any>;
    loadingSelector: (state: any) => boolean;
    errorSelector: (state: any) => Error | null;
    fetchParams?: any[];
  }
) {
  return function WithDataFetching(props: Omit<P, 'data' | 'loading' | 'error'>) {
    // Use the store data hook
    const { data, loading, error, refetch } = useStoreData({
      selector: options.selector,
      action: options.fetchAction,
      params: options.fetchParams || [],
      dependencies: []
    });
    
    return (
      <Component
        {...(props as P)}
        data={data}
        loading={loading}
        error={error}
        refetch={refetch}
      />
    );
  };
} 