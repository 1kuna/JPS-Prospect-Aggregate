import { useCallback, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { DataSource } from '@/store/slices/dataSourcesSlice';
import { toast } from '@/hooks/use-toast';

export interface UseDataSourcesOptions {
  autoFetch?: boolean;
  onError?: (error: Error) => void;
}

/**
 * Custom hook that provides access to data sources with simplified interface
 */
export function useDataSources(options: UseDataSourcesOptions = {}) {
  const { autoFetch = true, onError } = options;
  
  // Get data and actions from store
  const dataSources = useStore(state => state.dataSources);
  const isLoading = useStore(state => state.dataSourcesLoading);
  const error = useStore(state => state.dataSourcesError);
  const fetchDataSources = useStore(state => state.fetchDataSources);
  const createDataSource = useStore(state => state.createDataSource);
  const updateDataSource = useStore(state => state.updateDataSource);
  const deleteDataSource = useStore(state => state.deleteDataSource);
  const pullDataSource = useStore(state => state.pullDataSource);
  const pullingProgress = useStore(state => state.pullingProgress);
  
  // Handle fetch with error handling
  const fetchWithErrorHandling = useCallback(async () => {
    try {
      await fetchDataSources();
    } catch (err) {
      const error = err as Error;
      if (onError) {
        onError(error);
      } else {
        toast({
          title: 'Error fetching data',
          description: error.message,
          variant: 'destructive',
        });
      }
    }
  }, [fetchDataSources, onError]);
  
  // Create a data source with error handling
  const create = useCallback(async (data: Omit<DataSource, 'id'>) => {
    try {
      const result = await createDataSource(data);
      toast({
        title: 'Success',
        description: `Data source "${data.name}" created successfully`,
        variant: 'constructive',
      });
      return result;
    } catch (err) {
      const error = err as Error;
      toast({
        title: 'Error creating data source',
        description: error.message,
        variant: 'destructive',
      });
      throw error;
    }
  }, [createDataSource]);
  
  // Update a data source with error handling
  const update = useCallback(async (id: number | string, data: Partial<DataSource>) => {
    try {
      const result = await updateDataSource(id, data);
      toast({
        title: 'Success',
        description: `Data source updated successfully`,
        variant: 'constructive',
      });
      return result;
    } catch (err) {
      const error = err as Error;
      toast({
        title: 'Error updating data source',
        description: error.message,
        variant: 'destructive',
      });
      throw error;
    }
  }, [updateDataSource]);
  
  // Delete a data source with error handling
  const remove = useCallback(async (id: number | string) => {
    try {
      const result = await deleteDataSource(id);
      toast({
        title: 'Success',
        description: `Data source deleted successfully`,
        variant: 'constructive',
      });
      return result;
    } catch (err) {
      const error = err as Error;
      toast({
        title: 'Error deleting data source',
        description: error.message,
        variant: 'destructive',
      });
      throw error;
    }
  }, [deleteDataSource]);
  
  // Pull data from a source with error handling
  const pull = useCallback(async (id: number | string) => {
    try {
      const result = await pullDataSource(id);
      toast({
        title: 'Success',
        description: `Data pull initiated successfully`,
        variant: 'constructive',
      });
      return result;
    } catch (err) {
      const error = err as Error;
      toast({
        title: 'Error pulling data',
        description: error.message,
        variant: 'destructive',
      });
      throw error;
    }
  }, [pullDataSource]);
  
  // Auto-fetch data on component mount
  useEffect(() => {
    if (autoFetch) {
      fetchWithErrorHandling();
    }
  }, [autoFetch, fetchWithErrorHandling]);
  
  // Return data and actions
  return {
    // Data
    dataSources,
    isLoading,
    error,
    isPulling: (id?: number | string) => id ? !!pullingProgress[id] : Object.values(pullingProgress).some(Boolean),
    
    // Actions
    fetch: fetchWithErrorHandling,
    create,
    update,
    remove,
    pull,
  };
} 