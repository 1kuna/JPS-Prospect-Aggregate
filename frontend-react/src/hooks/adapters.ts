import { useData, UseDataOptions, UseDataResult } from './useData';
import { DataFetchingOptions, DataFetchingResult } from './useDataFetching';

/**
 * Adapter function to help migrate from useDataFetching to useData
 * This provides a backward-compatible API for useDataFetching
 */
export function useDataFetchingAdapter<T = any, P = any>(
  options: DataFetchingOptions<T, P>
): DataFetchingResult<T> {
  // Convert the old options format to the new one
  const newOptions: UseDataOptions<T, any[]> = {
    initialData: options.initialData,
    fetchOnMount: options.fetchOnMount,
    skip: options.skip,
    dependencies: options.dependencies,
    onSuccess: options.onSuccess,
    onError: options.onError
  };
  
  // If using store
  if (options.selector || options.fetchFromStore) {
    newOptions.store = {
      selector: options.selector || (state => null),
      loadingSelector: options.loadingSelector,
      errorSelector: options.errorSelector,
      action: options.fetchFromStore ? state => options.fetchFromStore!(state) : undefined,
      actionParams: options.storeParams ? [options.storeParams] : []
    };
  }
  
  // If using API
  if (options.url) {
    newOptions.api = {
      url: options.url,
      method: options.method,
      body: options.data,
      params: options.params,
      transform: options.transformResponse && (res => options.transformResponse!(res as any)),
      cacheTime: options.cacheTime
    };
  }
  
  const result = useData(newOptions);
  
  // Convert the result to match the old format
  return {
    data: result.data,
    loading: result.loading,
    error: result.error,
    refetch: async (params?: any) => result.refetch(params),
    setData: result.setData
  };
}

/**
 * Adapter function to help migrate from useStoreData to useData
 * This provides a backward-compatible API for useStoreData
 */
export function useStoreDataAdapter<T, P extends any[]>({
  selector,
  action,
  params = [] as unknown as P,
  dependencies = [],
  options = {}
}: {
  selector: (state: any) => T;
  action: (...args: P) => Promise<any>;
  params?: P;
  dependencies?: any[];
  options?: {
    skipInitialFetch?: boolean;
    onSuccess?: (data: any) => void;
    onError?: (error: Error) => void;
    loadingSelector?: (state: any) => boolean;
    errorSelector?: (state: any) => Error | null;
  }
}) {
  return useData<T, P>({
    store: {
      selector,
      loadingSelector: options.loadingSelector,
      errorSelector: options.errorSelector,
      action,
      actionParams: params
    },
    fetchOnMount: !options.skipInitialFetch,
    dependencies,
    onSuccess: options.onSuccess,
    onError: options.onError
  });
} 