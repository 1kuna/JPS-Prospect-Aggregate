import { 
  useQuery, 
  useMutation, 
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
  UseQueryResult,
  UseInfiniteQueryOptions,
  useInfiniteQuery
} from '@tanstack/react-query';
import { api, ApiResponse, ApiError } from '../store/api';
import { toast } from '@/hooks/use-toast';

type QueryKeyT = [string, Record<string, any>?];

// Custom hook for fetching data
export function useApiQuery<T>(
  queryKey: QueryKeyT, 
  url: string, 
  options?: UseQueryOptions<ApiResponse<T>, ApiError> & {
    params?: Record<string, any>;
    showSuccessToast?: boolean;
    showErrorToast?: boolean;
    successMessage?: string;
    errorMessage?: string;
  }
): UseQueryResult<T, ApiError> {
  const { 
    params, 
    showSuccessToast = false,
    showErrorToast = true,
    successMessage = 'Data loaded successfully',
    errorMessage = 'Failed to load data',
    ...queryOptions 
  } = options || {};

  return useQuery<ApiResponse<T>, ApiError>({
    queryKey,
    queryFn: async () => {
      try {
        const requestUrl = url.startsWith('/') ? url : `/${url}`;
        const response = await api.get(requestUrl, { params });
        
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
    ...queryOptions,
  });
}

// Custom hook for infinite queries (pagination)
export function useApiInfiniteQuery<T>(
  queryKey: QueryKeyT,
  url: string,
  options?: UseInfiniteQueryOptions<ApiResponse<T>, ApiError> & {
    params?: Record<string, any>;
    pageParam?: number;
    getNextPageParam?: (lastPage: ApiResponse<T>) => number | undefined;
  }
) {
  const { 
    params, 
    pageParam = 1, 
    getNextPageParam,
    ...restOptions 
  } = options || {};

  return useInfiniteQuery<ApiResponse<T>, ApiError>(
    queryKey,
    async ({ pageParam: page = pageParam }) => {
      return api.get<T>(url, { 
        params: { 
          ...params, 
          page 
        } 
      });
    },
    {
      getNextPageParam: getNextPageParam || ((lastPage) => {
        const pagination = lastPage.pagination;
        if (!pagination) return undefined;
        return pagination.page < pagination.total_pages 
          ? pagination.page + 1 
          : undefined;
      }),
      ...restOptions
    }
  );
}

// Custom hook for mutations (create, update, delete)
export function useApiMutation<T, V = any>(
  url: string,
  method: 'post' | 'put' | 'delete' = 'post',
  options?: UseMutationOptions<ApiResponse<T>, ApiError, V> & {
    showSuccessToast?: boolean;
    showErrorToast?: boolean;
    successMessage?: string;
    errorMessage?: string;
    invalidateQueries?: string[];
  }
) {
  const queryClient = useQueryClient();
  
  const { 
    showSuccessToast = true,
    showErrorToast = true,
    successMessage = 'Operation completed successfully',
    errorMessage = 'Operation failed',
    invalidateQueries = [],
    ...mutationOptions 
  } = options || {};

  return useMutation<ApiResponse<T>, ApiError, V>({
    mutationFn: async (variables) => {
      try {
        const requestUrl = url.startsWith('/') ? url : `/${url}`;
        let response;
        
        switch (method) {
          case 'post':
            response = await api.post(requestUrl, variables);
            break;
          case 'put':
            response = await api.put(requestUrl, variables);
            break;
          case 'delete':
            response = await api.delete(requestUrl);
            break;
          default:
            response = await api.post(requestUrl, variables);
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
    ...mutationOptions,
    onSuccess: async (data, variables, context) => {
      // Invalidate relevant queries
      for (const query of invalidateQueries) {
        await queryClient.invalidateQueries({ queryKey: [query] });
      }
      
      // Call the original onSuccess if provided
      if (mutationOptions.onSuccess) {
        await mutationOptions.onSuccess(data, variables, context);
      }
    },
  });
}

// Factory functions to create entity-specific hooks
export function createEntityHooks<T, CreateT = Partial<T>, UpdateT = Partial<T>>(
  entityName: string,
  baseUrl: string
) {
  // Hook to fetch all entities
  const useGetAll = (params?: Record<string, any>, options?: UseQueryOptions<ApiResponse<T[]>, ApiError>) => 
    useApiQuery<T[]>([entityName, params], baseUrl, { params, ...options });
  
  // Hook to fetch a single entity by ID
  const useGetById = (id: string | number, options?: UseQueryOptions<ApiResponse<T>, ApiError>) => 
    useApiQuery<T>([entityName, { id }], `${baseUrl}/${id}`, options);
  
  // Hook to create a new entity
  const useCreate = (options?: UseMutationOptions<ApiResponse<T>, ApiError, CreateT>) => 
    useApiMutation<T, CreateT>(baseUrl, 'post', {
      successMessage: `${entityName} created successfully`,
      invalidateQueries: [entityName],
      ...options
    });
  
  // Hook to update an entity
  const useUpdate = (id: string | number, options?: UseMutationOptions<ApiResponse<T>, ApiError, UpdateT>) => 
    useApiMutation<T, UpdateT>(`${baseUrl}/${id}`, 'put', {
      successMessage: `${entityName} updated successfully`,
      invalidateQueries: [entityName],
      ...options
    });
  
  // Hook to delete an entity
  const useDelete = (id: string | number, options?: UseMutationOptions<ApiResponse<null>, ApiError, void>) => 
    useApiMutation<null, void>(`${baseUrl}/${id}`, 'delete', {
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

// Create hooks for specific entities
export const dataSourcesHooks = createEntityHooks('dataSources', '/api/data-sources');
export const proposalsHooks = createEntityHooks('proposals', '/api/proposals');
