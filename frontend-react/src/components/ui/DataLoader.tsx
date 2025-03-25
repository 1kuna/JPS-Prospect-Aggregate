import React from 'react';
import { useQuery, QueryKey } from '@tanstack/react-query';
import { ApiResponse, ApiError } from '@/types/api';
import { Alert } from './alert';
import { Button } from './button';

/**
 * Reusable component for handling loading, error, and empty states in data fetching
 */
interface DataLoaderProps<T> {
  /**
   * Query key for React Query
   */
  queryKey: QueryKey;
  
  /**
   * Query function that returns a Promise of ApiResponse<T>
   */
  queryFn: () => Promise<ApiResponse<T>>;
  
  /**
   * Function to render the data when loading is complete and no errors occurred
   */
  children: (data: T) => React.ReactNode;
  
  /**
   * Content to show while data is loading
   */
  loadingComponent?: React.ReactNode;
  
  /**
   * Content to show when an error occurs
   */
  errorComponent?: React.ReactNode | ((error: ApiError) => React.ReactNode);
  
  /**
   * Content to show when there is no data
   */
  emptyComponent?: React.ReactNode;
  
  /**
   * Function to determine if data is considered empty
   */
  isDataEmpty?: (data: T) => boolean;
  
  /**
   * Optional additional class name for the wrapper
   */
  className?: string;
  
  /**
   * Query options for React Query
   */
  options?: {
    staleTime?: number;
    cacheTime?: number;
    retry?: number | boolean;
    retryDelay?: number;
    enabled?: boolean;
  };
}

/**
 * A component that handles the common data loading patterns:
 * - Loading state
 * - Error state
 * - Empty state
 * - Success state
 */
export function DataLoader<T>({
  queryKey,
  queryFn,
  children,
  loadingComponent = <div className="flex justify-center py-4">Loading...</div>,
  errorComponent,
  emptyComponent = <div className="text-center py-4 text-gray-500">No data available</div>,
  isDataEmpty,
  className = '',
  options = {}
}: DataLoaderProps<T>) {
  const { 
    data, 
    isLoading, 
    isError, 
    error, 
    refetch 
  } = useQuery<ApiResponse<T>, ApiError>({
    queryKey,
    queryFn,
    ...options
  });

  // Show loading state
  if (isLoading) {
    return <div className={className}>{loadingComponent}</div>;
  }

  // Show error state
  if (isError) {
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
          <Button 
            onClick={() => refetch()} 
            variant="destructive"
            className="mt-2"
            size="sm"
          >
            Retry
          </Button>
        </Alert>
      </div>
    );
  }

  // Check if data is empty
  const isEmpty = isDataEmpty 
    ? isDataEmpty(data?.data as T)
    : !data?.data || (Array.isArray(data.data) && data.data.length === 0);

  // Show empty state
  if (isEmpty) {
    return <div className={className}>{emptyComponent}</div>;
  }

  // Show data
  return <div className={className}>{children(data.data)}</div>;
}

/**
 * Higher-order component that combines DataLoader with React Query
 */
export function withQuery<P extends object, T>(
  Component: React.ComponentType<P & { data: T }>,
  { 
    queryKey, 
    queryFn, 
    options = {} 
  }: { 
    queryKey: QueryKey; 
    queryFn: () => Promise<ApiResponse<T>>; 
    options?: DataLoaderProps<T>['options'] 
  }
) {
  return function WithQuery(props: Omit<P, 'data'>) {
    return (
      <DataLoader<T>
        queryKey={queryKey}
        queryFn={queryFn}
        options={options}
      >
        {(data) => <Component {...(props as P)} data={data} />}
      </DataLoader>
    );
  };
} 