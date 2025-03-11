import { create } from 'zustand';
import { 
  fetchDashboardData, 
  fetchDataSources,
  fetchProposals,
  createDataSource,
  updateDataSource,
  deleteDataSource
} from './api';

interface LoadingState {
  dashboard: boolean;
  dataSources: boolean;
  proposals: boolean;
}

interface ErrorType {
  message: string;
  [key: string]: any;
}

interface AppState {
  // Data
  dashboardData: any | null;
  dataSources: any[];
  proposals: any[];
  proposalsPagination: {
    page: number;
    perPage: number;
    totalCount: number;
    totalPages: number;
  } | null;
  lastUpdated: Date | null;
  
  // UI state
  loading: LoadingState;
  errors: Record<string, ErrorType | null>;
  
  // Async actions
  fetchDashboardData: (params?: { page?: number; perPage?: number }) => Promise<void>;
  fetchDataSources: () => Promise<void>;
  fetchProposals: (params?: { page?: number; perPage?: number; sortBy?: string; sortOrder?: string }) => Promise<void>;
  createDataSource: (data: any) => Promise<any>;
  updateDataSource: (id: string, data: any) => Promise<any>;
  deleteDataSource: (id: string) => Promise<any>;
}

export const useStore = create<AppState>((set) => ({
  // Initial state
  dashboardData: null,
  dataSources: [],
  proposals: [],
  proposalsPagination: null,
  lastUpdated: null,
  
  loading: {
    dashboard: false,
    dataSources: false,
    proposals: false,
  },
  
  errors: {},
  
  // Async actions
  fetchDashboardData: async (params = {}) => {
    set(state => ({ loading: { ...state.loading, dashboard: true }, errors: { ...state.errors, dashboard: null } }));
    try {
      const data = await fetchDashboardData(params);
      set({ 
        dashboardData: data.data,
        lastUpdated: new Date()
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      set(state => ({ errors: { ...state.errors, dashboard: { message: errorMessage } } }));
    } finally {
      set(state => ({ loading: { ...state.loading, dashboard: false } }));
    }
  },
  
  fetchProposals: async (params = {}) => {
    set(state => ({ loading: { ...state.loading, proposals: true }, errors: { ...state.errors, proposals: null } }));
    try {
      const response = await fetchProposals(params);
      if (response && response.status === 'success' && Array.isArray(response.data)) {
        set({ 
          proposals: response.data,
          proposalsPagination: {
            page: response.pagination.page,
            perPage: response.pagination.per_page,
            totalCount: response.pagination.total_count,
            totalPages: response.pagination.total_pages
          },
          lastUpdated: new Date()
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      set(state => ({ errors: { ...state.errors, proposals: { message: errorMessage } } }));
    } finally {
      set(state => ({ loading: { ...state.loading, proposals: false } }));
    }
  },
  
  fetchDataSources: async () => {
    set(state => ({ loading: { ...state.loading, dataSources: true }, errors: { ...state.errors, dataSources: null } }));
    try {
      const response = await fetchDataSources();
      if (response && response.status === 'success' && Array.isArray(response.data)) {
        set({ 
          dataSources: response.data,
          lastUpdated: new Date()
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      set(state => ({ errors: { ...state.errors, dataSources: { message: errorMessage } } }));
    } finally {
      set(state => ({ loading: { ...state.loading, dataSources: false } }));
    }
  },
  
  createDataSource: async (data) => {
    try {
      const response = await createDataSource(data);
      if (response && response.status === 'success') {
        set(state => ({ 
          dataSources: [...state.dataSources, response.data],
          lastUpdated: new Date()
        }));
      }
      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      set(state => ({ errors: { ...state.errors, createDataSource: { message: errorMessage } } }));
      throw error;
    }
  },
  
  updateDataSource: async (id, data) => {
    try {
      const response = await updateDataSource(id, data);
      if (response && response.status === 'success') {
        set(state => ({ 
          dataSources: state.dataSources.map(source => 
            source.id === id ? response.data : source
          ),
          lastUpdated: new Date()
        }));
      }
      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      set(state => ({ errors: { ...state.errors, updateDataSource: { message: errorMessage } } }));
      throw error;
    }
  },
  
  deleteDataSource: async (id) => {
    try {
      const response = await deleteDataSource(id);
      if (response && response.status === 'success') {
        set(state => ({ 
          dataSources: state.dataSources.filter(source => source.id !== id),
          lastUpdated: new Date()
        }));
      }
      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      set(state => ({ errors: { ...state.errors, deleteDataSource: { message: errorMessage } } }));
      throw error;
    }
  }
})); 