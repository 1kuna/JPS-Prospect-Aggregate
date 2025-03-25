import { createEntityHooks } from './useApi';
import { DataSource } from '@/types';

// Create base CRUD hooks using our entity hooks factory
export const useDataSources = createEntityHooks<DataSource>(
  'dataSources',
  '/api/data-sources',
);

// Add custom data source specific hooks
export const useDataSourceHealth = (id: string | number) => {
  return useDataSources.useQuery<{ status: string; lastCheck: string }>(
    ['health', { id }],
    `/${id}/health`,
  );
};

export const usePullDataSource = (id: string | number) => {
  return useDataSources.useMutation<{ status: string }>(
    `/${id}/pull`,
    'post',
    {
      successMessage: 'Data source pull initiated successfully',
      invalidateQueries: [['dataSources'], ['dataSources', 'health']],
    },
  );
}; 