import { useQuery, useMutation, useQueryClient, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { toast } from '../use-toast';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface ApiConfig<TData = unknown, TError = ApiError> {
  queryKey?: string[];
  endpoint: string;
  method?: HttpMethod;
  params?: Record<string, unknown>;
  body?: unknown;
  successMessage?: string;
  errorMessage?: string;
  invalidateQueries?: string[][];
  options?: Omit<UseQueryOptions<TData, TError> | UseMutationOptions<TData, TError>, 'queryKey' | 'queryFn' | 'mutationFn'>;
}

export function useApiQuery<TData = unknown, TError = ApiError>({
  queryKey = [],
  endpoint,
  method = 'GET',
  params,
  options = {},
}: ApiConfig<TData, TError>) {
  return useQuery({
    queryKey: [...queryKey, endpoint, params],
    queryFn: async () => {
      try {
        const response = await apiClient.request({
          method,
          url: endpoint,
          params,
        });
        return response.data as TData;
      } catch (error) {
        if (error instanceof Error) {
          throw new ApiError(
            error.message,
            (error as any)?.response?.status,
            (error as any)?.response?.data?.code,
            (error as any)?.response?.data
          );
        }
        throw error;
      }
    },
    ...options,
  });
}

export function useApiMutation<TData = unknown, TVariables = unknown, TError = ApiError>({
  endpoint,
  method = 'POST',
  body,
  successMessage,
  errorMessage,
  invalidateQueries = [],
  options = {},
}: ApiConfig<TData, TError> & { body?: TVariables }) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (variables?: TVariables) => {
      try {
        const response = await apiClient.request({
          method,
          url: endpoint,
          data: variables || body,
        });
        return response.data as TData;
      } catch (error) {
        if (error instanceof Error) {
          throw new ApiError(
            error.message,
            (error as any)?.response?.status,
            (error as any)?.response?.data?.code,
            (error as any)?.response?.data
          );
        }
        throw error;
      }
    },
    onSuccess: () => {
      if (successMessage) {
        toast({
          title: 'Success',
          description: successMessage,
        });
      }
      // Invalidate specified queries
      invalidateQueries.forEach(queryKey => {
        queryClient.invalidateQueries({ queryKey });
      });
    },
    onError: (error: TError) => {
      toast({
        title: 'Error',
        description: errorMessage || `Operation failed: ${error instanceof Error ? error.message : String(error)}`,
        variant: 'destructive',
      });
    },
    ...options,
  });
}

// Helper function to create entity-specific hooks
export function createEntityHooks<TEntity, TFilters = Record<string, unknown>>(
  entityName: string,
  baseEndpoint: string
) {
  return {
    useQuery: (queryKey: string[], endpoint: string, options = {}) =>
      useApiQuery<TEntity>({
        queryKey: [entityName, ...queryKey],
        endpoint: `${baseEndpoint}${endpoint}`,
        options,
      }),

    useMutation: (
      endpoint: string,
      method: HttpMethod = 'POST',
      config: Omit<ApiConfig<TEntity>, 'endpoint' | 'method'> = {}
    ) =>
      useApiMutation<TEntity>({
        endpoint: `${baseEndpoint}${endpoint}`,
        method,
        ...config,
      }),

    useList: (filters?: TFilters, options = {}) =>
      useApiQuery<TEntity[]>({
        queryKey: [entityName, 'list', filters],
        endpoint: baseEndpoint,
        params: filters,
        options,
      }),

    useGet: (id: string | number, options = {}) =>
      useApiQuery<TEntity>({
        queryKey: [entityName, 'detail', id],
        endpoint: `${baseEndpoint}/${id}`,
        options,
      }),

    useCreate: (config: Omit<ApiConfig<TEntity>, 'endpoint' | 'method'> = {}) =>
      useApiMutation<TEntity>({
        endpoint: baseEndpoint,
        method: 'POST',
        ...config,
      }),

    useUpdate: (id: string | number, config: Omit<ApiConfig<TEntity>, 'endpoint' | 'method'> = {}) =>
      useApiMutation<TEntity>({
        endpoint: `${baseEndpoint}/${id}`,
        method: 'PUT',
        ...config,
      }),

    useDelete: (id: string | number, config: Omit<ApiConfig<TEntity>, 'endpoint' | 'method'> = {}) =>
      useApiMutation<void>({
        endpoint: `${baseEndpoint}/${id}`,
        method: 'DELETE',
        ...config,
      }),
  };
} 