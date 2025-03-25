import {
  useQuery as useReactQuery,
  useMutation as useReactMutation,
  useInfiniteQuery as useReactInfiniteQuery,
  UseQueryOptions,
  UseMutationOptions,
  UseInfiniteQueryOptions,
  QueryKey,
} from '@tanstack/react-query';
import { apiClient } from '../lib/api-client';
import { ApiResponse, ApiError, QueryConfig, MutationConfig } from '../types/api';
import { toast } from './use-toast';

type QueryKeyT = [string, Record<string, any>?];

interface QueryOptions<T> extends Omit<UseQueryOptions<ApiResponse<T>, ApiError>, 'queryKey' | 'queryFn'> {
  params?: Record<string, any>;
  showSuccessToast?: boolean;
  showErrorToast?: boolean;
  successMessage?: string;
  errorMessage?: string;
}

export function useQuery<T>(
  queryKey: QueryKeyT,
  path: string,
  {
    params,
    showSuccessToast = false,
    showErrorToast = true,
    successMessage = 'Data loaded successfully',
    errorMessage = 'Failed to load data',
    ...options
  }: QueryOptions<T> = {}
) {
  return useReactQuery<ApiResponse<T>, ApiError>({
    queryKey,
    queryFn: async () => {
      try {
        const response = await apiClient.get<T>(path, { params });
        
        if (showSuccessToast) {
          toast.success({ title: 'Success', description: successMessage });
        }
        
        return response;
      } catch (error) {
        if (showErrorToast && error instanceof ApiError) {
          toast.error({
            title: 'Error',
            description: error.message || errorMessage
          });
        }
        throw error;
      }
    },
    ...options,
  });
}

interface InfiniteQueryOptions<T> extends Omit<UseInfiniteQueryOptions<ApiResponse<T>, ApiError>, 'queryKey' | 'queryFn'> {
  params?: Record<string, any>;
  pageParam?: number;
}

export function useInfiniteQuery<T>(
  queryKey: QueryKeyT,
  path: string,
  {
    params,
    pageParam = 1,
    getNextPageParam,
    ...options
  }: InfiniteQueryOptions<T> = {}
) {
  return useReactInfiniteQuery<ApiResponse<T>, ApiError>({
    queryKey,
    queryFn: async ({ pageParam: page = pageParam }) => {
      return apiClient.get<T>(path, {
        params: {
          ...params,
          page
        }
      });
    },
    getNextPageParam: getNextPageParam || ((lastPage) => {
      const pagination = lastPage.pagination;
      if (!pagination) return undefined;
      return pagination.page < pagination.total_pages
        ? pagination.page + 1
        : undefined;
    }),
    ...options,
  });
}

interface MutationOptions<T, V> extends Omit<UseMutationOptions<ApiResponse<T>, ApiError, V>, 'mutationFn'> {
  showSuccessToast?: boolean;
  showErrorToast?: boolean;
  successMessage?: string;
  errorMessage?: string;
  invalidateQueries?: string[];
}

export function useMutation<T, V = any>(
  path: string,
  method: 'post' | 'put' | 'patch' | 'delete' = 'post',
  {
    showSuccessToast = true,
    showErrorToast = true,
    successMessage = 'Operation completed successfully',
    errorMessage = 'Operation failed',
    invalidateQueries = [],
    ...options
  }: MutationOptions<T, V> = {}
) {
  const queryClient = useQueryClient();

  return useReactMutation<ApiResponse<T>, ApiError, V>({
    mutationFn: async (variables) => {
      try {
        let response;
        
        switch (method) {
          case 'post':
            response = await apiClient.post<T>(path, variables);
            break;
          case 'put':
            response = await apiClient.put<T>(path, variables);
            break;
          case 'patch':
            response = await apiClient.patch<T>(path, variables);
            break;
          case 'delete':
            response = await apiClient.delete<T>(path);
            break;
          default:
            response = await apiClient.post<T>(path, variables);
        }
        
        if (showSuccessToast) {
          toast.success({
            title: 'Success',
            description: successMessage
          });
        }
        
        return response;
      } catch (error) {
        if (showErrorToast && error instanceof ApiError) {
          toast.error({
            title: 'Error',
            description: error.message || errorMessage
          });
        }
        throw error;
      }
    },
    ...options,
    onSuccess: async (data, variables, context) => {
      // Invalidate relevant queries
      for (const query of invalidateQueries) {
        await queryClient.invalidateQueries({ queryKey: [query] });
      }
      
      // Call the original onSuccess if provided
      if (options.onSuccess) {
        await options.onSuccess(data, variables, context);
      }
    },
  });
}

// Factory function to create entity-specific hooks
export function createEntityHooks<T, CreateT = Partial<T>, UpdateT = Partial<T>>(
  entityName: string,
  basePath: string
) {
  // Hook to fetch all entities
  const useGetAll = (params?: Record<string, any>, options?: QueryConfig<T[]>) =>
    useQuery<T[]>([entityName, params], basePath, { params, ...options });
  
  // Hook to fetch a single entity by ID
  const useGetById = (id: string | number, options?: QueryConfig<T>) =>
    useQuery<T>([entityName, { id }], `${basePath}/${id}`, options);
  
  // Hook to create a new entity
  const useCreate = (options?: MutationConfig<T, CreateT>) =>
    useMutation<T, CreateT>(basePath, 'post', {
      successMessage: `${entityName} created successfully`,
      invalidateQueries: [entityName],
      ...options
    });
  
  // Hook to update an entity
  const useUpdate = (id: string | number, options?: MutationConfig<T, UpdateT>) =>
    useMutation<T, UpdateT>(`${basePath}/${id}`, 'put', {
      successMessage: `${entityName} updated successfully`,
      invalidateQueries: [entityName],
      ...options
    });
  
  // Hook to delete an entity
  const useDelete = (id: string | number, options?: MutationConfig<null, void>) =>
    useMutation<null, void>(`${basePath}/${id}`, 'delete', {
      successMessage: `${entityName} deleted successfully`,
      invalidateQueries: [entityName],
      ...options
    });
  
  return {
    useGetAll,
    useGetById,
    useCreate,
    useUpdate,
    useDelete
  };
} 