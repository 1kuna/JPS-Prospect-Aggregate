import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { 
  fetchDashboardData, 
  fetchDataSources,
  createDataSource,
  updateDataSource,
  deleteDataSource
} from './api';

interface LoadingState {
  dashboard: boolean;
  dataSources: boolean;
}

interface ErrorState {
  [key: string]: {
    message: string;
    timestamp: number;
    retryCount: number;
  } | null;
}

interface AppState {
  // Data
  dashboardData: any | null;
  dataSources: any[];
  lastUpdated: Date | null;
  
  // UI state
  loading: LoadingState;
  errors: ErrorState;
  
  // Actions
  setLoading: (resource: keyof LoadingState, isLoading: boolean) => void;
  setError: (resource: string, error: Error | null) => void;
  setDashboardData: (data: any) => void;
  setDataSources: (sources: any[]) => void;
  
  // Async actions
  fetchDashboardData: (params?: { page?: number; perPage?: number }) => Promise<void>;
  fetchDataSources: () => Promise<void>;
  createDataSource: (data: any) => Promise<any>;
  updateDataSource: (id: string, data: any) => Promise<any>;
  deleteDataSource: (id: string) => Promise<any>;
}

export const useStore = create<AppState>()(
  devtools(
    (set, get) => ({
      // Initial state
      dashboardData: null,
      dataSources: [],
      lastUpdated: null,
      
      loading: {
        dashboard: false,
        dataSources: false,
      },
      
      errors: {},
      
      // Synchronous actions
      setLoading: (resource, isLoading) => 
        set((state) => ({
          loading: {
            ...state.loading,
            [resource]: isLoading
          }
        })),
        
      setError: (resource, error) => 
        set((state) => ({
          errors: {
            ...state.errors,
            [resource]: error ? {
              message: error.message,
              timestamp: Date.now(),
              retryCount: (state.errors[resource]?.retryCount || 0) + 1
            } : null
          }
        })),
        
      setDashboardData: (data) => 
        set({
          dashboardData: data,
          lastUpdated: new Date()
        }),
        
      setDataSources: (sources) => 
        set({ dataSources: sources }),
      
      // Async actions
      fetchDashboardData: async (params = {}) => {
        const { page = 1, perPage = 50 } = params;
        const { setLoading, setError, setDashboardData } = get();
        
        try {
          setLoading('dashboard', true);
          setError('dashboard', null);
          
          const data = await fetchDashboardData({ page, perPage });
          setDashboardData(data);
          
          return data;
        } catch (error) {
          setError('dashboard', error as Error);
          throw error;
        } finally {
          setLoading('dashboard', false);
        }
      },
      
      fetchDataSources: async () => {
        const { setLoading, setError, setDataSources } = get();
        
        try {
          setLoading('dataSources', true);
          setError('dataSources', null);
          
          const sources = await fetchDataSources();
          setDataSources(sources);
          
          return sources;
        } catch (error) {
          setError('dataSources', error as Error);
          throw error;
        } finally {
          setLoading('dataSources', false);
        }
      },
      
      createDataSource: async (data) => {
        const { setLoading, setError, fetchDataSources } = get();
        
        try {
          setLoading('dataSources', true);
          setError('dataSources', null);
          
          const result = await createDataSource(data);
          await fetchDataSources();
          
          return result;
        } catch (error) {
          setError('dataSources', error as Error);
          throw error;
        } finally {
          setLoading('dataSources', false);
        }
      },
      
      updateDataSource: async (id, data) => {
        const { setLoading, setError, fetchDataSources } = get();
        
        try {
          setLoading('dataSources', true);
          setError('dataSources', null);
          
          const result = await updateDataSource(id, data);
          await fetchDataSources();
          
          return result;
        } catch (error) {
          setError('dataSources', error as Error);
          throw error;
        } finally {
          setLoading('dataSources', false);
        }
      },
      
      deleteDataSource: async (id) => {
        const { setLoading, setError, fetchDataSources } = get();
        
        try {
          setLoading('dataSources', true);
          setError('dataSources', null);
          
          const result = await deleteDataSource(id);
          await fetchDataSources();
          
          return result;
        } catch (error) {
          setError('dataSources', error as Error);
          throw error;
        } finally {
          setLoading('dataSources', false);
        }
      },
    }),
    { name: 'app-store' }
  )
); 