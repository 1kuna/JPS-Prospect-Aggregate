import { StateCreator } from 'zustand';
import { 
  fetchDataSources, 
  updateDataSource, 
  createDataSource, 
  deleteDataSource,
  pullDataSource,
  getScraperStatus
} from '../api';

export interface DataSource {
  id: number;
  name: string;
  url: string;
  description?: string;
  status?: string;
  lastChecked?: string | null;
  lastScraped?: string | null;
  proposalCount: number;
  [key: string]: any;
}

export interface DataSourcesState {
  dataSources: DataSource[];
  loading: { dataSources: boolean };
  errors: { dataSources: ErrorType | null };
  pullingProgress: Record<number, boolean>;
  
  // Actions
  fetchDataSources: () => Promise<DataSource[]>;
  createDataSource: (data: any) => Promise<any>;
  updateDataSource: (id: string | number, data: any) => Promise<any>;
  deleteDataSource: (id: string | number) => Promise<any>;
  pullDataSource: (id: string | number) => Promise<any>;
  getScraperStatus: (id: string | number) => Promise<any>;
  setPullingProgress: (sourceId: number, isLoading: boolean) => void;
}

interface ErrorType {
  message: string;
  [key: string]: any;
}

export const dataSourcesSlice: StateCreator<DataSourcesState> = (set, get) => ({
  dataSources: [],
  loading: { dataSources: false },
  errors: { dataSources: null },
  pullingProgress: {},
  
  fetchDataSources: async () => {
    set((state) => ({ loading: { ...state.loading, dataSources: true } }));
    try {
      console.log('Store: Fetching data sources from API...');
      const data = await fetchDataSources();
      
      if (!data || !data.data) {
        throw new Error('Invalid response format from API');
      }
      
      // Transform API field names to frontend field names
      const transformedData = data.data.map((source: any) => ({
        ...source,
        lastChecked: source.last_checked || source.lastChecked,
        lastScraped: source.last_scraped || source.lastScraped,
        proposalCount: source.proposalCount || 0
      }));
      
      set({ 
        dataSources: transformedData, 
        loading: { ...get().loading, dataSources: false },
        errors: { ...get().errors, dataSources: null }
      });
      return transformedData;
    } catch (error: any) {
      console.error('Store: Error fetching data sources:', error);
      
      // Format the error message
      const errorMessage = error.response?.data?.message || error.message || 'Unknown error';
      const formattedError = { message: errorMessage };
      
      set({ 
        loading: { ...get().loading, dataSources: false },
        errors: { ...get().errors, dataSources: formattedError }
      });
      
      throw error;
    }
  },
  
  createDataSource: async (data) => {
    set((state) => ({ loading: { ...state.loading, dataSources: true } }));
    try {
      const response = await createDataSource(data);
      await get().fetchDataSources();
      set({
        loading: { ...get().loading, dataSources: false },
        errors: { ...get().errors, dataSources: null }
      });
      return response;
    } catch (error: any) {
      console.error('Error creating data source:', error);
      const errorMessage = error.response?.data?.message || error.message || 'Unknown error';
      set((state) => ({
        loading: { ...state.loading, dataSources: false },
        errors: { ...state.errors, dataSources: { message: errorMessage } }
      }));
      throw error;
    }
  },
  
  updateDataSource: async (id, data) => {
    set((state) => ({ loading: { ...state.loading, dataSources: true } }));
    try {
      const response = await updateDataSource(id, data);
      await get().fetchDataSources();
      set({
        loading: { ...get().loading, dataSources: false },
        errors: { ...get().errors, dataSources: null }
      });
      return response;
    } catch (error: any) {
      console.error('Error updating data source:', error);
      const errorMessage = error.response?.data?.message || error.message || 'Unknown error';
      set((state) => ({
        loading: { ...state.loading, dataSources: false },
        errors: { ...state.errors, dataSources: { message: errorMessage } }
      }));
      throw error;
    }
  },
  
  deleteDataSource: async (id) => {
    set((state) => ({ loading: { ...state.loading, dataSources: true } }));
    try {
      const response = await deleteDataSource(id);
      await get().fetchDataSources();
      set({
        loading: { ...get().loading, dataSources: false },
        errors: { ...get().errors, dataSources: null }
      });
      return response;
    } catch (error: any) {
      console.error('Error deleting data source:', error);
      const errorMessage = error.response?.data?.message || error.message || 'Unknown error';
      set((state) => ({
        loading: { ...state.loading, dataSources: false },
        errors: { ...state.errors, dataSources: { message: errorMessage } }
      }));
      throw error;
    }
  },
  
  pullDataSource: async (id) => {
    set((state) => ({
      pullingProgress: {
        ...state.pullingProgress,
        [id]: true
      }
    }));
    
    try {
      const response = await pullDataSource(id);
      return response;
    } catch (error: any) {
      console.error('Error pulling data source:', error);
      throw error;
    } finally {
      set((state) => ({
        pullingProgress: {
          ...state.pullingProgress,
          [id]: false
        }
      }));
    }
  },
  
  getScraperStatus: async (id) => {
    try {
      return await getScraperStatus(id);
    } catch (error: any) {
      console.error('Error getting scraper status:', error);
      throw error;
    }
  },
  
  setPullingProgress: (sourceId: number, isLoading: boolean) => {
    set((state) => {
      if (state.pullingProgress[sourceId] === isLoading) {
        return state;
      }
      return {
        pullingProgress: {
          ...state.pullingProgress,
          [sourceId]: isLoading
        }
      };
    });
  },
}); 