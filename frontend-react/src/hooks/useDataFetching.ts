import { useState, useEffect, useCallback } from 'react';
import axios, { AxiosRequestConfig, AxiosError } from 'axios';

interface FetchOptions<T> {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  params?: Record<string, any>;
  body?: any;
  initialData?: T;
  onSuccess?: (data: T) => void;
  onError?: (error: Error | AxiosError) => void;
  autoFetch?: boolean;
  transformResponse?: (data: any) => T;
}

interface PaginationParams {
  page: number;
  perPage: number;
}

interface PaginationInfo extends PaginationParams {
  totalPages: number;
  totalItems: number;
}

interface UseDataFetchingResult<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  fetchData: (options?: { params?: Record<string, any>; body?: any }) => Promise<T | null>;
  pagination?: PaginationInfo;
  setPagination: (params: PaginationParams) => void;
  lastUpdated: Date | null;
}

export function useDataFetching<T>({
  url,
  method = 'GET',
  params = {},
  body,
  initialData = null,
  onSuccess,
  onError,
  autoFetch = true,
  transformResponse,
}: FetchOptions<T>): UseDataFetchingResult<T> {
  const [data, setData] = useState<T | null>(initialData);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [pagination, setPagination] = useState<PaginationInfo | undefined>(undefined);
  const [paginationParams, setPaginationParams] = useState<PaginationParams | undefined>(
    params.page && params.perPage ? { page: params.page, perPage: params.perPage } : undefined
  );
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(
    async (options?: { params?: Record<string, any>; body?: any }) => {
      setIsLoading(true);
      setError(null);

      try {
        const requestConfig: AxiosRequestConfig = {
          url,
          method,
          params: {
            ...params,
            ...paginationParams,
            ...options?.params,
          },
        };

        if (method !== 'GET') {
          requestConfig.data = options?.body || body;
        }

        const response = await axios(requestConfig);
        
        let processedData: T;
        
        if (transformResponse) {
          processedData = transformResponse(response.data);
        } else {
          // Default transformation assuming a standard API response format
          processedData = response.data.data || response.data;
        }

        // Check if the response contains pagination information
        if (response.data.pagination) {
          setPagination({
            page: response.data.pagination.page || 1,
            perPage: response.data.pagination.per_page || 10,
            totalPages: response.data.pagination.total_pages || 1,
            totalItems: response.data.pagination.total_items || 0,
          });
        }

        setData(processedData);
        setLastUpdated(new Date());
        
        if (onSuccess) {
          onSuccess(processedData);
        }
        
        return processedData;
      } catch (err) {
        const error = err as Error | AxiosError;
        setError(error);
        
        if (onError) {
          onError(error);
        }
        
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [url, method, params, body, paginationParams, onSuccess, onError, transformResponse]
  );

  const handlePaginationChange = useCallback((newPaginationParams: PaginationParams) => {
    setPaginationParams(newPaginationParams);
  }, []);

  useEffect(() => {
    if (autoFetch) {
      fetchData();
    }
  }, [fetchData, autoFetch, paginationParams]);

  return {
    data,
    isLoading,
    error,
    fetchData,
    pagination,
    setPagination: handlePaginationChange,
    lastUpdated,
  };
} 