import { useState, useEffect, useCallback, useRef } from 'react';
import { useStore } from '@/store/useStore';
import { api, ApiResponse, ApiError } from '@/store/api';
import { useQueryClient } from '@tanstack/react-query';

/**
 * A unified data hook that can fetch from both the store and direct API calls
 * with built-in caching, loading states, and error handling
 */

// Options for the hook
export interface UseDataOptions<T, P extends any[] = any[]> {
  /**
   * API options (when fetching directly from API)
   */
  api?: {
    /**
     * The URL to fetch data from
     */
    url: string;
    
    /**
     * HTTP method to use
     */
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    
    /**
     * Body data for POST/PUT/PATCH requests
     */
    body?: any;
    
    /**
     * Query parameters for the request
     */
    params?: Record<string, any>;
    
    /**
     * Transform function for the response
     */
    transform?: (response: ApiResponse<any>) => T;
    
    /**
     * Cache time in milliseconds (0 to disable)
     */
    cacheTime?: number;
    
    /**
     * Optional cache key, if not provided will be auto-generated
     */
    cacheKey?: string;
    
    /**
     * Whether to use the React Query cache instead of a local cache
     */
    useQueryCache?: boolean;
  };
  
  /**
   * Store options (when fetching from Zustand store)
   */
  store?: {
    /**
     * Selector function to get data from the store
     */
    selector: (state: any) => T;
    
    /**
     * Selector for loading state
     */
    loadingSelector?: (state: any) => boolean;
    
    /**
     * Selector for error state
     */
    errorSelector?: (state: any) => Error | null;
    
    /**
     * Action to fetch/update data
     */
    action?: (...args: P) => Promise<any>;
    
    /**
     * Parameters to pass to the action function
     */
    actionParams?: P;
  };
  
  /**
   * Initial data to use before the fetch completes
   */
  initialData?: T;
  
  /**
   * Whether to fetch on mount
   */
  fetchOnMount?: boolean;
  
  /**
   * Skip fetching entirely
   */
  skip?: boolean;
  
  /**
   * Dependencies that will trigger a refetch when changed
   */
  dependencies?: any[];
  
  /**
   * Callback when fetch succeeds
   */
  onSuccess?: (data: T) => void;
  
  /**
   * Callback when fetch fails
   */
  onError?: (error: Error) => void;
}

// Results returned by the hook
export interface UseDataResult<T, P extends any[] = any[]> {
  /**
   * The data returned from the fetch
   */
  data: T | null;
  
  /**
   * Whether the data is currently loading
   */
  loading: boolean;
  
  /**
   * Any error that occurred
   */
  error: Error | null;
  
  /**
   * Function to manually trigger a refetch
   */
  refetch: (...args: P) => Promise<T>;
  
  /**
   * Function to manually update the data
   */
  setData: React.Dispatch<React.SetStateAction<T | null>>;
}

// Local cache for API responses
const cache: Record<string, { data: any; timestamp: number }> = {};

export function useData<T, P extends any[] = any[]>(
  options: UseDataOptions<T, P>
): UseDataResult<T, P> {
  // Extract options
  const {
    api: apiOptions,
    store: storeOptions,
    initialData = null,
    fetchOnMount = true,
    skip = false,
    dependencies = [],
    onSuccess,
    onError
  } = options;
  
  // Set up local state for direct API calls
  const [localData, setLocalData] = useState<T | null>(initialData);
  const [localLoading, setLocalLoading] = useState<boolean>(false);
  const [localError, setLocalError] = useState<Error | null>(null);
  
  // Get React Query client for caching if needed
  const queryClient = useQueryClient();
  
  // Keep track of component mounted state
  const isMounted = useRef<boolean>(true);
  
  // Get store values if using store
  const storeData = storeOptions?.selector ? useStore(storeOptions.selector) : null;
  const storeLoading = storeOptions?.loadingSelector ? useStore(storeOptions.loadingSelector) : false;
  const storeError = storeOptions?.errorSelector ? useStore(storeOptions.errorSelector) : null;
  const storeAction = storeOptions?.action ? useStore(state => storeOptions.action) : null;
  
  // Decide which state to use
  const data = storeOptions?.selector ? storeData : localData;
  const loading = storeOptions?.loadingSelector ? storeLoading : localLoading;
  const error = storeOptions?.errorSelector ? storeError : localError;
  
  // Generate cache key for API requests
  const getCacheKey = useCallback(() => {
    if (!apiOptions) return null;
    if (apiOptions.cacheKey) return apiOptions.cacheKey;
    
    const { url, method = 'GET', params } = apiOptions;
    if (method !== 'GET') return null;
    
    const queryString = params ? new URLSearchParams(params).toString() : '';
    return `${url}?${queryString}`;
  }, [apiOptions]);
  
  // Function to fetch data
  const fetchData = useCallback(async (...args: P): Promise<T> => {
    // If using store action
    if (storeAction) {
      try {
        const result = await storeAction(...(args.length ? args : (storeOptions?.actionParams || [] as unknown as P)));
        onSuccess?.(result);
        return result as T;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        onError?.(error);
        throw error;
      }
    }
    // If using API
    else if (apiOptions) {
      const { url, method = 'GET', body, params, transform, cacheTime = 0, useQueryCache = false } = apiOptions;
      
      // Check cache first
      const cacheKey = getCacheKey();
      if (cacheKey && cacheTime > 0) {
        // If using React Query cache
        if (useQueryCache) {
          const cachedData = queryClient.getQueryData<T>(cacheKey);
          if (cachedData) {
            if (isMounted.current) {
              setLocalData(cachedData);
              onSuccess?.(cachedData);
            }
            return cachedData;
          }
        } 
        // Otherwise use local cache
        else {
          const cachedData = cache[cacheKey];
          if (cachedData && Date.now() - cachedData.timestamp < cacheTime) {
            if (isMounted.current) {
              setLocalData(cachedData.data);
              onSuccess?.(cachedData.data);
            }
            return cachedData.data;
          }
        }
      }
      
      // If not cached or cache expired, fetch from API
      if (isMounted.current) {
        setLocalLoading(true);
        setLocalError(null);
      }
      
      try {
        // Handle different HTTP methods
        let response: ApiResponse<any>;
        
        switch (method) {
          case 'GET':
            response = await api.get(url, { params: { ...params, ...args[0] } });
            break;
          case 'POST':
            response = await api.post(url, body || args[0]);
            break;
          case 'PUT':
            response = await api.put(url, body || args[0]);
            break;
          case 'DELETE':
            response = await api.delete(url);
            break;
          case 'PATCH':
            response = await api.post(url, body || args[0], { method: 'PATCH' });
            break;
          default:
            response = await api.get(url, { params });
        }
        
        // Transform the response if needed
        const transformedData = transform ? transform(response) : response.data as T;
        
        // Only update state if component is still mounted
        if (isMounted.current) {
          setLocalData(transformedData);
          setLocalLoading(false);
        }
        
        // Cache the result if needed
        if (cacheKey && cacheTime > 0) {
          if (useQueryCache) {
            queryClient.setQueryData(cacheKey, transformedData);
          } else {
            cache[cacheKey] = {
              data: transformedData,
              timestamp: Date.now()
            };
          }
        }
        
        onSuccess?.(transformedData);
        return transformedData;
      } catch (err) {
        const error = err instanceof ApiError 
          ? err 
          : new Error(err instanceof Error ? err.message : String(err));
        
        if (isMounted.current) {
          setLocalError(error);
          setLocalLoading(false);
        }
        
        onError?.(error);
        throw error;
      }
    }
    
    // If neither store nor API is configured
    throw new Error('Either store or API options must be provided');
  }, [storeAction, storeOptions?.actionParams, apiOptions, getCacheKey, queryClient, onSuccess, onError]);
  
  // Clean up on unmount
  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);
  
  // Fetch on mount or when dependencies change
  useEffect(() => {
    if (!skip && fetchOnMount) {
      fetchData(...(storeOptions?.actionParams || [] as unknown as P));
    }
  }, [skip, fetchOnMount, fetchData, ...dependencies]);
  
  return { 
    data, 
    loading, 
    error, 
    refetch: fetchData,
    setData: setLocalData
  };
}

export default useData; 