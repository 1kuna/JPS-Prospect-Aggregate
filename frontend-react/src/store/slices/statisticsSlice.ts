import { StateCreator } from 'zustand';
import { fetchStatistics, fetchDashboardData } from '../api';

export interface StatisticsState {
  statistics: any | null;
  dashboardData: any | null;
  loading: { 
    statistics: boolean;
    dashboard: boolean;
  };
  errors: { 
    statistics: any | null;
    dashboard: any | null;
  };
  
  // Actions
  fetchStatistics: () => Promise<void>;
  fetchDashboardData: (params?: { page?: number; perPage?: number }) => Promise<void>;
}

export const statisticsSlice: StateCreator<StatisticsState> = (set, get) => ({
  statistics: null,
  dashboardData: null,
  loading: { 
    statistics: false,
    dashboard: false
  },
  errors: { 
    statistics: null,
    dashboard: null
  },
  
  fetchStatistics: async () => {
    set((state) => ({ loading: { ...state.loading, statistics: true } }));
    try {
      const data = await fetchStatistics();
      set({ 
        statistics: data, 
        loading: { ...get().loading, statistics: false },
        errors: { ...get().errors, statistics: null }
      });
      return data;
    } catch (error: any) {
      set({ 
        loading: { ...get().loading, statistics: false },
        errors: { ...get().errors, statistics: { message: error.message } }
      });
      throw error;
    }
  },
  
  fetchDashboardData: async (params = {}) => {
    set((state) => ({ loading: { ...state.loading, dashboard: true } }));
    try {
      const data = await fetchDashboardData(params);
      set({ 
        dashboardData: data.data, 
        loading: { ...get().loading, dashboard: false },
        errors: { ...get().errors, dashboard: null }
      });
      return data.data;
    } catch (error: any) {
      console.error('Error fetching dashboard data:', error);
      set({ 
        loading: { ...get().loading, dashboard: false },
        errors: { ...get().errors, dashboard: { message: error.message } }
      });
      throw error;
    }
  }
}); 