import { useQuery, useMutation } from './use-query';

export interface Statistics {
  totalProposals: number;
  activeDataSources: number;
  proposalsTrend: {
    date: string;
    count: number;
  }[];
  dataSourcesHealth: {
    sourceId: number;
    status: 'healthy' | 'warning' | 'error';
    lastUpdate: string;
  }[];
}

export interface DashboardData {
  recentProposals: {
    id: number;
    title: string;
    dataSourceId: number;
    createdAt: string;
  }[];
  dataSourceStats: {
    sourceId: number;
    proposalCount: number;
    lastActivity: string;
  }[];
}

export function useStatistics(options = {}) {
  return useQuery<Statistics>(
    ['statistics'],
    '/statistics',
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
      ...options
    }
  );
}

export function useDashboardData(options = {}) {
  return useQuery<DashboardData>(
    ['dashboard'],
    '/dashboard',
    {
      staleTime: 1 * 60 * 1000, // 1 minute
      ...options
    }
  );
}

export function useAnalyticsData() {
  const statistics = useStatistics();
  const dashboard = useDashboardData();

  return {
    statistics: statistics.data?.data,
    dashboard: dashboard.data?.data,
    isLoading: statistics.isLoading || dashboard.isLoading,
    isError: statistics.isError || dashboard.isError,
    error: statistics.error || dashboard.error,
    refetch: async () => {
      await Promise.all([
        statistics.refetch(),
        dashboard.refetch()
      ]);
    }
  };
} 