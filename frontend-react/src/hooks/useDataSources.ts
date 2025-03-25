import { createApiHooks } from '../lib/create-api-hooks';
import type { DataSource } from '../types/data-source';

const dataSourcesHooks = createApiHooks<DataSource>({
  basePath: '/api/data-sources',
  queryKey: ['dataSources'],
});

export const useDataSources = () => {
  const { useList, useGet, useCreate, useUpdate, useDelete } = dataSourcesHooks;
  
  // Get all data sources
  const list = useList();
  
  // Create a new data source
  const create = useCreate({
    onSuccess: () => {
      list.refetch();
    },
  });
  
  // Update a data source
  const update = useUpdate({
    onSuccess: () => {
      list.refetch();
    },
  });
  
  // Delete a data source
  const remove = useDelete({
    onSuccess: () => {
      list.refetch();
    },
  });

  return {
    list,
    get: useGet,
    create,
    update,
    remove,
  };
};

// Custom hook for data source health check
export const useDataSourceHealth = (id: string | number) => {
  const { useGet } = dataSourcesHooks;
  return useGet(id, {
    queryKey: ['dataSources', id, 'health'],
  });
};

// Custom hook for pulling data from a source
export const usePullDataSource = (id: string | number) => {
  const { useUpdate } = dataSourcesHooks;
  return useUpdate(id, {
    queryKey: ['dataSources', id, 'pull'],
  });
}; 