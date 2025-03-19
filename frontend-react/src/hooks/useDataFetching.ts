import { useState, useEffect, useCallback, useRef } from 'react';
import axios, { AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { useStore } from '@/store/useStore';

// Types for configuration options
export interface DataFetchingOptions<T, P> {
  /**
   * The URL to fetch data from
   */
  url?: string;
  
  /**
   * Method to use for the request
   */
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  
  /**
   * Initial data to use before the fetch completes
   */
  initialData?: T;
  
  /**
   * Function to fetch data from store
   */
  fetchFromStore?: (state: any) => (...args: any[]) => Promise<T>;
  
  /**
   * Parameters to pass to the store fetch function
   */
  storeParams?: P;
  
  /**
   * Selector function to get data from store
   */
  selector?: (state: any) => T;
  
  /**
   * Loading selector function to get loading state from store
   */
  loadingSelector?: (state: any) => boolean;
  
  /**
   * Error selector function to get error state from store
   */
  errorSelector?: (state: any) => Error | null;
  
  /**
   * Body data for POST/PUT/PATCH requests
   */
  data?: any;
  
  /**
   * Query parameters for the request
   */
  params?: Record<string, any>;
  
  /**
   * Additional request config options
   */
  config?: Omit<AxiosRequestConfig, 'url' | 'method' | 'data' | 'params'>;
  
  /**
   * Whether to fetch on mount
   */
  fetchOnMount?: boolean;
  
  /**
   * Skip the fetch entirely
   */
  skip?: boolean;
  
  /**
   * Transform function to apply to the response
   */
  transformResponse?: (response: AxiosResponse) => T;
  
  /**
   * Callback to run when fetch succeeds
   */
  onSuccess?: (data: T) => void;
  
  /**
   * Callback to run when fetch fails
   */
  onError?: (error: Error) => void;
  
  /**
   * Dependencies array that will trigger a refetch when changed
   */
  dependencies?: any[];
  
  /**
   * Request cache time in milliseconds
   */
  cacheTime?: number;
}

// Results returned by the hook
export interface DataFetchingResult<T> {
  /**
   * The data returned from the fetch
   */
  data: T | null;
  
  /**
   * Whether the fetch is currently loading
   */
  loading: boolean;
  
  /**
   * Any error that occurred during the fetch
   */
  error: Error | null;
  
  /**
   * Function to manually trigger a refetch
   */
  refetch: (params?: any) => Promise<T>;
  
  /**
   * Function to manually update the data
   */
  setData: React.Dispatch<React.SetStateAction<T | null>>;
}

// Cache object to store previous requests
const cache: Record<string, { data: any; timestamp: number }> = {};

/**
 * A flexible hook for data fetching that can work with both direct API calls and store-based data fetching
 */
export function useDataFetching<T = any, P = any>({
  url,
  method = 'GET',
  initialData = null,
  fetchFromStore,
  storeParams,
  selector,
  loadingSelector,
  errorSelector,
  data: bodyData,
  params,
  config = {},
  fetchOnMount = true,
  skip = false,
  transformResponse = (res: AxiosResponse) => res.data?.data || res.data,
  onSuccess,
  onError,
  dependencies = [],
  cacheTime = 0
}: DataFetchingOptions<T, P>): DataFetchingResult<T> {
  // Set up local state for direct API calls
  const [localData, setLocalData] = useState<T | null>(initialData);
  const [localLoading, setLocalLoading] = useState<boolean>(false);
  const [localError, setLocalError] = useState<Error | null>(null);
  
  // Track if component is mounted
  const isMounted = useRef<boolean>(true);
  
  // Get store state if using store
  const storeData = selector ? useStore(selector) : null;
  const storeLoading = loadingSelector ? useStore(loadingSelector) : false;
  const storeError = errorSelector ? useStore(errorSelector) : null;
  const storeFetch = fetchFromStore ? useStore(fetchFromStore) : null;
  
  // Decide which state to use (store or local)
  const data = selector ? storeData : localData;
  const loading = loadingSelector ? storeLoading : localLoading;
  const error = errorSelector ? storeError : localError;
  
  // Generate cache key for GET requests
  const getCacheKey = useCallback(() => {
    if (method !== 'GET' || !url) return null;
    const queryString = params ? new URLSearchParams(params).toString() : '';
    return `${url}?${queryString}`;
  }, [method, url, params]);
  
  // The main fetch function
  const fetchData = useCallback(async (overrideParams?: any): Promise<T> => {
    // If using store fetch
    if (storeFetch) {
      try {
        const result = await storeFetch(overrideParams || storeParams);
        onSuccess?.(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        onError?.(error);
        throw error;
      }
    } 
    // If using direct API
    else if (url) {
      // Check cache first
      const cacheKey = getCacheKey();
      if (cacheKey && cacheTime > 0) {
        const cachedData = cache[cacheKey];
        if (cachedData && Date.now() - cachedData.timestamp < cacheTime) {
          if (isMounted.current) {
            setLocalData(cachedData.data);
            onSuccess?.(cachedData.data);
          }
          return cachedData.data;
        }
      }
      
      // If not cached or cache expired, fetch from API
      if (isMounted.current) {
        setLocalLoading(true);
        setLocalError(null);
      }
      
      try {
        const mergedParams = { ...params, ...overrideParams };
        const response = await axios({
          url,
          method,
          data: bodyData,
          params: mergedParams,
          ...config
        });
        
        const transformedData = transformResponse(response) as T;
        
        // Only update state if component is still mounted
        if (isMounted.current) {
          setLocalData(transformedData);
          setLocalLoading(false);
        }
        
        // Cache GET requests
        if (cacheKey && cacheTime > 0) {
          cache[cacheKey] = {
            data: transformedData,
            timestamp: Date.now()
          };
        }
        
        onSuccess?.(transformedData);
        return transformedData;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        
        // Only update state if component is still mounted
        if (isMounted.current) {
          setLocalError(error);
          setLocalLoading(false);
        }
        
        onError?.(error);
        throw error;
      }
    } else {
      const error = new Error('No fetch method or URL provided');
      setLocalError(error);
      onError?.(error);
      throw error;
    }
  }, [
    url, 
    method, 
    bodyData, 
    params, 
    config, 
    storeFetch, 
    storeParams, 
    onSuccess, 
    onError, 
    getCacheKey, 
    cacheTime, 
    transformResponse
  ]);
  
  // Fetch data on mount or when dependencies change
  useEffect(() => {
    if (skip || !fetchOnMount) return;
    
    fetchData().catch((err) => {
      console.error('Error fetching data:', err);
    });
    
    return () => {
      isMounted.current = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchOnMount, skip, ...dependencies]);
  
  return {
    data,
    loading,
    error,
    refetch: fetchData,
    setData: setLocalData
  };
}

export default useDataFetching; 