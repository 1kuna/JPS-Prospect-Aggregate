import { useApiQuery } from './useApi';
import type { DashboardData, Statistics } from '@/types';

interface TimeSeriesData {
  timestamp: string;
  value: number;
}

// Hook for dashboard data - Changed endpoint to match existing route
export const useDashboard = () => {
  return useApiQuery<DashboardData>({
    queryKey: ['dashboard'], // Simplified key
    endpoint: '/api/dashboard', // Changed from /api/analytics/dashboard
    options: {
      staleTime: 60 * 1000, // 1 minute
    },
  });
};

// Hook for overall statistics - NOTE: No direct /api/analytics/statistics endpoint exists.
// This might need adjustment or removal depending on what /api/dashboard returns.
// For now, let's comment it out in the combined hook.
export const useStatistics = () => {
  return useApiQuery<Statistics>({
    queryKey: ['analytics', 'statistics'],
    endpoint: '/api/analytics/statistics', // This endpoint does not exist
    options: {
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  });
};

// Hook for time-series data - This endpoint also likely doesn't exist
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
  // const statistics = useStatistics(); // Commenting out as endpoint doesn't exist

  // Adjust return based on available data from /api/dashboard
  // The original component expected dashboard.data and statistics.data
  // We only have dashboard data now.
  return {
    dashboard: dashboard.data?.data, // Assuming /api/dashboard returns { status: ..., data: ...}
    statistics: null, // Set statistics to null as we don't fetch them anymore
    // isLoading: dashboard.isLoading || statistics.isLoading,
    isLoading: dashboard.isLoading, // Only check dashboard loading
    // isError: dashboard.isError || statistics.isError,
    isError: dashboard.isError, // Only check dashboard error
    // error: dashboard.error || statistics.error,
    error: dashboard.error // Only report dashboard error
  };
};
