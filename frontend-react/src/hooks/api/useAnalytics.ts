import { useApiQuery } from './useApi';
import type { DashboardData, Statistics } from '@/types';

interface TimeSeriesData {
  timestamp: string;
  value: number;
}

// Hook for dashboard data
export const useDashboard = () => {
  return useApiQuery<DashboardData>({
    queryKey: ['analytics', 'dashboard'],
    endpoint: '/api/analytics/dashboard',
    options: {
      staleTime: 60 * 1000, // 1 minute
    },
  });
};

// Hook for overall statistics
export const useStatistics = () => {
  return useApiQuery<Statistics>({
    queryKey: ['analytics', 'statistics'],
    endpoint: '/api/analytics/statistics',
    options: {
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  });
};

// Hook for time-series data
export const useTimeSeries = (metric: string, timeRange: string = '7d') => {
  return useApiQuery<TimeSeriesData[]>({
    queryKey: ['analytics', 'timeSeries', { metric, timeRange }],
    endpoint: '/api/analytics/time-series',
    params: { metric, timeRange },
    options: {
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  });
};

// Combined hook for dashboard overview
export const useAnalyticsOverview = () => {
  const dashboard = useDashboard();
  const statistics = useStatistics();

  return {
    dashboard: dashboard.data?.data,
    statistics: statistics.data?.data,
    isLoading: dashboard.isLoading || statistics.isLoading,
    isError: dashboard.isError || statistics.isError,
    error: dashboard.error || statistics.error,
  };
}; 