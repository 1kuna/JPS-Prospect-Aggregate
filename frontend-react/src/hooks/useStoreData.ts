import { useEffect, useCallback } from 'react';
import { useStore } from '@/store/useStore';

export function useStoreData<T>({
  dataSelector,
  loadingSelector,
  errorSelector,
  fetchAction,
  fetchParams = {},
  dependencies = []
}: {
  dataSelector: (state: any) => T;
  loadingSelector: (state: any) => boolean;
  errorSelector: (state: any) => any;
  fetchAction: (state: any) => (...args: any[]) => Promise<any>;
  fetchParams?: Record<string, any>;
  dependencies?: any[];
}) {
  // Select state from store
  const data = useStore(dataSelector);
  const loading = useStore(loadingSelector);
  const errors = useStore(errorSelector);
  const fetchData = useStore(fetchAction);
  
  // Create memoized refresh handler
  const refresh = useCallback(() => {
    return fetchData(fetchParams).catch((error: Error) => {
      console.error('Error refreshing data:', error);
    });
  }, [fetchData, fetchParams]);
  
  // Fetch data on component mount if not already loaded
  useEffect(() => {
    if (!data || (Array.isArray(data) && !data.length)) {
      refresh();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencies, fetchData]);
  
  return {
    data,
    loading,
    errors,
    refresh
  };
} 