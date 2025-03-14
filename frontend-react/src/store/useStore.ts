import { create } from 'zustand';
import { 
  fetchDashboardData, 
  fetchDataSources,
  fetchProposals,
  createDataSource,
  updateDataSource,
  deleteDataSource,
  pullDataSource,
  fetchStatistics,
  rebuildDatabase,
  initializeDatabase,
  resetEverything,
  manageBackups,
  getScraperStatus
} from './api';

interface LoadingState {
  dashboard: boolean;
  dataSources: boolean;
  proposals: boolean;
  statistics: boolean;
  databaseOperations: boolean;
  scraperStatus: boolean;
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
  statistics: any | null;
  backups: any[];
  lastUpdated: Date | null;
  
  // UI state
  loading: LoadingState;
  errors: Record<string, ErrorType | null>;
  pullingProgress: Record<number, boolean>;
  
  // Async actions
  fetchDashboardData: (params?: { page?: number; perPage?: number }) => Promise<void>;
  fetchDataSources: () => Promise<void>;
  fetchProposals: (params?: { page?: number; perPage?: number; sortBy?: string; sortOrder?: string }) => Promise<void>;
  fetchStatistics: () => Promise<void>;
  createDataSource: (data: any) => Promise<any>;
  updateDataSource: (id: string, data: any) => Promise<any>;
  deleteDataSource: (id: string) => Promise<any>;
  pullDataSource: (id: string) => Promise<any>;
  rebuildDatabase: () => Promise<any>;
  initializeDatabase: () => Promise<any>;
  resetEverything: () => Promise<any>;
  manageBackups: (action: 'create' | 'restore' | 'list', backupId?: string) => Promise<any>;
  getScraperStatus: (id: string) => Promise<any>;
  setPullingProgress: (sourceId: number, isLoading: boolean) => void;
}

// Helper function to create a toast notification
// This will be used by components that import the store
export const createToast = (title: string, description: string, variant?: 'default' | 'destructive' | 'success', duration?: number) => {
  // We'll use this function to create toast notifications from the store
  // The actual implementation will be in the components that use the store
  // This is just a placeholder to make the TypeScript compiler happy
  return { title, description, variant, duration };
};

export const useStore = create<AppState>((set) => ({
  // Initial state
  dashboardData: null,
  dataSources: [],
  proposals: [],
  proposalsPagination: null,
  statistics: null,
  backups: [],
  lastUpdated: null,
  
  loading: {
    dashboard: false,
    dataSources: false,
    proposals: false,
    statistics: false,
    databaseOperations: false,
    scraperStatus: false
  },
  
  errors: {
    dashboard: null,
    dataSources: null,
    proposals: null,
    statistics: null,
    databaseOperations: null,
    scraperStatus: null
  },
  
  pullingProgress: {},
  
  // Async actions
  fetchDashboardData: async (params = {}) => {
    set((state) => ({ loading: { ...state.loading, dashboard: true } }));
    try {
      const data = await fetchDashboardData(params);
      set({ 
        dashboardData: data.data, 
        lastUpdated: new Date(),
        loading: { ...useStore.getState().loading, dashboard: false },
        errors: { ...useStore.getState().errors, dashboard: null }
      });
    } catch (error: any) {
      console.error('Error fetching dashboard data:', error);
      set({ 
        loading: { ...useStore.getState().loading, dashboard: false },
        errors: { ...useStore.getState().errors, dashboard: error }
      });
    }
  },
  
  fetchDataSources: async () => {
    set((state) => ({ loading: { ...state.loading, dataSources: true } }));
    try {
      console.log('Store: Fetching data sources from API...');
      const data = await fetchDataSources();
      
      if (!data || !data.data) {
        throw new Error('Invalid response format from API');
      }
      
      console.log('Store: Data sources fetched successfully:', data.data);
      set({ 
        dataSources: data.data || [], 
        lastUpdated: new Date(),
        loading: { ...useStore.getState().loading, dataSources: false },
        errors: { ...useStore.getState().errors, dataSources: null }
      });
      return data.data;
    } catch (error: any) {
      console.error('Store: Error fetching data sources:', error);
      
      // Format the error message
      const errorMessage = error.response?.data?.message || error.message || 'Unknown error';
      const formattedError = { message: errorMessage };
      
      set({ 
        loading: { ...useStore.getState().loading, dataSources: false },
        errors: { ...useStore.getState().errors, dataSources: formattedError }
      });
      
      // Re-throw the error so it can be caught by the component
      throw error;
    }
  },
  
  fetchProposals: async (params = {}) => {
    set((state) => ({ loading: { ...state.loading, proposals: true } }));
    try {
      const data = await fetchProposals(params);
      // Normalize pagination data to ensure consistent property names
      const normalizedPagination = data.pagination ? {
        page: data.pagination.page,
        perPage: data.pagination.per_page,
        totalPages: data.pagination.total_pages,
        totalCount: data.pagination.total_items
      } : null;
      
      set({ 
        proposals: data.data || [], 
        proposalsPagination: normalizedPagination,
        lastUpdated: new Date(),
        loading: { ...useStore.getState().loading, proposals: false },
        errors: { ...useStore.getState().errors, proposals: null }
      });
      console.log('Proposals fetched:', data.data);
    } catch (error: any) {
      console.error('Error fetching proposals:', error);
      set({ 
        loading: { ...useStore.getState().loading, proposals: false },
        errors: { ...useStore.getState().errors, proposals: error }
      });
    }
  },
  
  fetchStatistics: async () => {
    set((state) => ({ loading: { ...state.loading, statistics: true } }));
    try {
      const data = await fetchStatistics();
      set({ 
        statistics: data, 
        lastUpdated: new Date(),
        loading: { ...useStore.getState().loading, statistics: false },
        errors: { ...useStore.getState().errors, statistics: null }
      });
    } catch (error: any) {
      set({ 
        loading: { ...useStore.getState().loading, statistics: false },
        errors: { ...useStore.getState().errors, statistics: { message: error.message } }
      });
    }
  },
  
  createDataSource: async (data) => {
    set((state) => ({ loading: { ...state.loading, dataSources: true } }));
    try {
      const response = await createDataSource(data);
      await useStore.getState().fetchDataSources();
      return response;
    } catch (error: any) {
      console.error('Error creating data source:', error);
      set((state) => ({
        errors: { ...state.errors, dataSources: { message: error.message } }
      }));
      throw error;
    }
  },
  
  updateDataSource: async (id, data) => {
    set((state) => ({ loading: { ...state.loading, dataSources: true } }));
    try {
      const response = await updateDataSource(id, data);
      await useStore.getState().fetchDataSources();
      return response;
    } catch (error: any) {
      console.error('Error updating data source:', error);
      set((state) => ({
        errors: { ...state.errors, dataSources: { message: error.message } }
      }));
      throw error;
    }
  },
  
  deleteDataSource: async (id) => {
    set((state) => ({ loading: { ...state.loading, dataSources: true } }));
    try {
      const response = await deleteDataSource(id);
      await useStore.getState().fetchDataSources();
      return response;
    } catch (error: any) {
      console.error('Error deleting data source:', error);
      set((state) => ({
        errors: { ...state.errors, dataSources: { message: error.message } }
      }));
      throw error;
    }
  },
  
  pullDataSource: async (id) => {
    try {
      const response = await pullDataSource(id);
      await useStore.getState().fetchDataSources();
      return response;
    } catch (error: any) {
      console.error('Error pulling data source:', error);
      set((state) => ({
        errors: { ...state.errors, dataSources: { message: error.message } }
      }));
      throw error;
    }
  },
  
  getScraperStatus: async (id) => {
    try {
      const response = await getScraperStatus(id);
      return response;
    } catch (error: any) {
      console.error('Error getting scraper status:', error);
      set((state) => ({
        errors: { ...state.errors, dataSources: { message: error.message } }
      }));
      throw error;
    }
  },
  
  rebuildDatabase: async () => {
    set((state) => ({ loading: { ...state.loading, databaseOperations: true } }));
    try {
      const response = await rebuildDatabase();
      set({ 
        loading: { ...useStore.getState().loading, databaseOperations: false },
        errors: { ...useStore.getState().errors, databaseOperations: null }
      });
      return response;
    } catch (error: any) {
      set({ 
        loading: { ...useStore.getState().loading, databaseOperations: false },
        errors: { ...useStore.getState().errors, databaseOperations: { message: error.message } }
      });
      throw error;
    }
  },
  
  initializeDatabase: async () => {
    set((state) => ({ loading: { ...state.loading, databaseOperations: true } }));
    try {
      const response = await initializeDatabase();
      set({ 
        loading: { ...useStore.getState().loading, databaseOperations: false },
        errors: { ...useStore.getState().errors, databaseOperations: null }
      });
      return response;
    } catch (error: any) {
      set({ 
        loading: { ...useStore.getState().loading, databaseOperations: false },
        errors: { ...useStore.getState().errors, databaseOperations: { message: error.message } }
      });
      throw error;
    }
  },
  
  resetEverything: async () => {
    set((state) => ({ loading: { ...state.loading, databaseOperations: true } }));
    try {
      const response = await resetEverything();
      set({ 
        loading: { ...useStore.getState().loading, databaseOperations: false },
        errors: { ...useStore.getState().errors, databaseOperations: null }
      });
      return response;
    } catch (error: any) {
      set({ 
        loading: { ...useStore.getState().loading, databaseOperations: false },
        errors: { ...useStore.getState().errors, databaseOperations: { message: error.message } }
      });
      throw error;
    }
  },
  
  manageBackups: async (action, backupId) => {
    set((state) => ({ loading: { ...state.loading, databaseOperations: true } }));
    try {
      const response = await manageBackups(action, backupId);
      if (action === 'list') {
        set({ backups: response.data || [] });
      }
      set({ 
        loading: { ...useStore.getState().loading, databaseOperations: false },
        errors: { ...useStore.getState().errors, databaseOperations: null }
      });
      return response;
    } catch (error: any) {
      set({ 
        loading: { ...useStore.getState().loading, databaseOperations: false },
        errors: { ...useStore.getState().errors, databaseOperations: { message: error.message } }
      });
      throw error;
    }
  },
  
  setPullingProgress: (sourceId: number, isLoading: boolean) => {
    set((state) => ({
      pullingProgress: {
        ...state.pullingProgress,
        [sourceId]: isLoading
      }
    }));
  }
})); 