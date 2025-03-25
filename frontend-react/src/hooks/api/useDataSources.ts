import { createEntityHooks } from '../use-query';
import { DataSource } from '@/types';

export const useDataSources = createEntityHooks<DataSource>(
  'dataSources',
  '/api/data-sources',
);

// Add custom data source specific hooks
export const useDataSourceHealth = (id: string | number) => {
  const { useQuery } = useDataSources;
  return useQuery<{ status: string; lastCheck: string }>(
    ['dataSourceHealth', { id }],
    `/api/data-sources/${id}/health`
  );
};

export const usePullDataSource = (id: string | number) => {
  const { useMutation } = useDataSources;
  return useMutation<{ status: string }>(
    `/api/data-sources/${id}/pull`,
    'post',
    {
      successMessage: 'Data source pull initiated successfully',
      invalidateQueries: ['dataSources', 'dataSourceHealth']
    }
  );
}; 