import { createApiHooks } from '../../lib/create-api-hooks';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import type { Proposal } from '@/types';

interface ProposalFilters {
  status?: string;
  dataSourceId?: number;
  startDate?: string;
  endDate?: string;
  search?: string;
}

const proposalsHooks = createApiHooks<Proposal>({
  basePath: '/api/proposals',
  queryKey: ['proposals'],
});

export const useProposals = () => {
  const { useList, useGet, useCreate, useUpdate, useDelete } = proposalsHooks;
  
  return {
    list: useList(),
    get: useGet,
    create: useCreate(),
    update: useUpdate(),
    delete: useDelete(),
  };
};

// Hook for infinite loading with filters
export const useInfiniteProposals = (filters: ProposalFilters = {}) => {
  return useInfiniteQuery({
    queryKey: ['proposals', 'infinite', filters],
    queryFn: async ({ pageParam = 1 }) => {
      const response = await apiClient.get('/api/proposals', {
        params: { ...filters, page: pageParam },
      });
      return response.data;
    },
    getNextPageParam: (lastPage) => {
      if (!lastPage.pagination) return undefined;
      return lastPage.pagination.page < lastPage.pagination.total_pages
        ? lastPage.pagination.page + 1
        : undefined;
    },
  });
};

// Hook for proposal statistics
export const useProposalStatistics = () => {
  return useQuery({
    queryKey: ['proposals', 'statistics'],
    queryFn: async () => {
      const response = await apiClient.get('/api/proposals/statistics');
      return response.data;
    },
  });
};

// Hook for recent proposals
export const useRecentProposals = (limit: number = 5) => {
  return useQuery({
    queryKey: ['proposals', 'recent', { limit }],
    queryFn: async () => {
      const response = await apiClient.get('/api/proposals/recent', {
        params: { limit },
      });
      return response.data;
    },
  });
}; 