import { StateCreator } from 'zustand';
import { api } from '../api';
import { createAsyncSlice } from '../middleware/createAsyncSlice';

/**
 * Statistics related to the platform data
 */
export interface Statistics {
  total_data_sources: number;
  total_proposals: number;
  active_data_sources: number;
  recent_proposals: number;
  proposals_by_month: { month: string; count: number }[];
  proposals_by_agency: { agency: string; count: number }[];
  [key: string]: any;
}

/**
 * Dashboard overview data
 */
export interface DashboardData {
  recent_proposals: any[];
  recent_data_sources: any[];
  statistics: Partial<Statistics>;
  [key: string]: any;
}

/**
 * Analytics state type for both statistics and dashboard
 */
export interface AnalyticsState {
  // Statistics data
  statistics: Statistics | null;
  statisticsLoading: boolean;
  statisticsError: { message: string } | null;
  
  // Dashboard data
  dashboardData: DashboardData | null;
  dashboardDataLoading: boolean;
  dashboardDataError: { message: string } | null;
  
  // Actions
  fetchStatistics: () => Promise<Statistics>;
  fetchDashboardData: (params?: { page?: number; perPage?: number }) => Promise<DashboardData>;
  
  // Combined actions
  fetchAnalyticsData: () => Promise<{ statistics: Statistics; dashboard: DashboardData }>;
}

/**
 * Combined slice for statistics and dashboard data
 */
export const analyticsSlice: StateCreator<AnalyticsState> = (set, get) => {
  // Create statistics async slice
  const statisticsAsync = createAsyncSlice<Statistics, AnalyticsState>(
    'statistics',
    {
      fetchStatistics: async () => {
        const response = await api.fetchStatistics();
        return response.data;
      }
    },
    null
  )(set, get);
  
  // Create dashboard data async slice
  const dashboardAsync = createAsyncSlice<DashboardData, AnalyticsState>(
    'dashboardData',
    {
      fetchDashboardData: async (params = {}) => {
        const response = await api.fetchDashboardData(params);
        return response.data || null;
      }
    },
    null
  )(set, get);
  
  // Combined fetch function
  const fetchAnalyticsData = async () => {
    const [statistics, dashboard] = await Promise.all([
      get().fetchStatistics(),
      get().fetchDashboardData()
    ]);
    
    return { statistics, dashboard };
  };
  
  return {
    // Combine both async slices
    ...statisticsAsync,
    ...dashboardAsync,
    
    // Add combined action
    fetchAnalyticsData
  };
}; 