import { createEntityHooks } from './useApi';
import { DataSource } from '@/types';

// @ts-ignore // Suppress TS2347
export const useDataSources = (createEntityHooks as any)<DataSource>(
  'data-sources',
  {
    staleTime: 5 * 60 * 1000,
  }
);

// Health check hook
export const useDataSourceHealth = (id: string | number) => {
  // @ts-ignore // Suppress TS2347
  return (useDataSources.useQuery as any)<{ status: string; lastCheck: string }>(
    ['health', { id }],
    `/${id}/health`,
  );
};

// Pull data mutation hook
export const usePullDataSource = (id: string | number) => {
  // @ts-ignore // Suppress TS2347
  return (useDataSources.useMutation as any)<{ status: string }>(
    `/${id}/pull`,
    {
      method: 'POST',
      successMessage: 'Data source pull initiated',
      errorMessage: 'Failed to initiate pull',
    },
  );
};