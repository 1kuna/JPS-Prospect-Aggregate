import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import type { DashboardData, Statistics } from '@/types';

// Hook for dashboard data
export const useDashboard = () => {
  return useQuery({
    queryKey: ['analytics', 'dashboard'],
    queryFn: async () => {
      const response = await apiClient.get('/api/analytics/dashboard');
      return response.data;
    },
  });
};

// Hook for overall statistics
export const useStatistics = () => {
  return useQuery({
    queryKey: ['analytics', 'statistics'],
    queryFn: async () => {
      const response = await apiClient.get('/api/analytics/statistics');
      return response.data;
    },
  });
};

// Hook for time-series data
export const useTimeSeries = (metric: string, timeRange: string = '7d') => {
  return useQuery({
    queryKey: ['analytics', 'timeSeries', { metric, timeRange }],
    queryFn: async () => {
      const response = await apiClient.get('/api/analytics/time-series', {
        params: { metric, timeRange },
      });
      return response.data;
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