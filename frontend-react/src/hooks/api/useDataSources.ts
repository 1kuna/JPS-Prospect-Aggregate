import { createEntityHooks } from './useApi';
import { DataSource } from '@/types';

// @ts-ignore // Suppress TS2347
export const useDataSources = (createEntityHooks as any)<DataSource>(
  'data-sources',
  {
    staleTime: 5 * 60 * 1000,
  }
);