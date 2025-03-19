import { useState, useEffect, useCallback } from 'react';
import { useStore } from '@/store/useStore';

/**
 * A flexible hook for fetching and managing data from the store
 */
export function useStoreData<T, P extends any[]>({
  selector,
  action,
  params = [] as unknown as P,
  dependencies = [],
  options = {}
}: {
  /**
   * Selector function to get data from the store
   */
  selector: (state: any) => T;
  
  /**
   * Action function to fetch data
   */
  action: (...args: P) => Promise<any>;
  
  /**
   * Parameters to pass to the action function
   */
  params?: P;
  
  /**
   * Dependencies array that will trigger a refetch when changed
   */
  dependencies?: any[];
  
  /**
   * Additional options for controlling the behavior
   */
  options?: {
    /**
     * Whether to skip the initial fetch when the hook mounts
     */
    skipInitialFetch?: boolean;
    
    /**
     * Callback to run when fetch succeeds
     */
    onSuccess?: (data: any) => void;
    
    /**
     * Callback to run when fetch fails
     */
    onError?: (error: Error) => void;
    
    /**
     * Selector for loading state
     */
    loadingSelector?: (state: any) => boolean;
    
    /**
     * Selector for error state
     */
    errorSelector?: (state: any) => Error | null;
  }
}): {
  /**
   * Data from the store
   */
  data: T;
  
  /**
   * Whether data is currently loading
   */
  loading: boolean;
  
  /**
   * Any error that occurred
   */
  error: Error | null;
  
  /**
   * Function to manually trigger a refetch
   */
  refetch: (...args: P) => Promise<any>;
} {
  // Get data from store through selector
  const data = useStore(selector);
  
  // Get loading and error states if selectors are provided
  const loading = options.loadingSelector 
    ? useStore(options.loadingSelector)
    : false;
    
  const error = options.errorSelector
    ? useStore(options.errorSelector)
    : null;
  
  // Get the action from store
  const storeAction = useStore(state => action);
  
  // Refetch function
  const refetch = useCallback(
    async (...args: P) => {
      try {
        const result = await storeAction(...(args.length ? args : params));
        options.onSuccess?.(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        options.onError?.(error);
        throw error;
      }
    },
    [storeAction, params, options]
  );
  
  // Fetch data on mount or when dependencies change
  useEffect(() => {
    if (!options.skipInitialFetch) {
      refetch(...params);
    }
  }, [refetch, ...dependencies]);
  
  return { data, loading, error, refetch };
} 