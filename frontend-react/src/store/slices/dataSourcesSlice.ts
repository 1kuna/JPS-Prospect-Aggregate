import { StateCreator } from 'zustand';
import { api } from '../api';
import { createAsyncSlice } from '../middleware/createAsyncSlice';

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

interface ErrorType {
  message: string;
  [key: string]: any;
}

export interface DataSourcesState {
  // Data state
  dataSources: DataSource[];
  dataSourcesLoading: boolean;
  dataSourcesError: ErrorType | null;
  
  // Pull progress state
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

// Transform data sources from API format to client format
const transformDataSources = (data: any[]): DataSource[] => {
  return data.map((source: any) => ({
    ...source,
    lastChecked: source.last_checked || source.lastChecked,
    lastScraped: source.last_scraped || source.lastScraped,
    proposalCount: source.proposal_count || source.proposalCount || 0
  }));
};

export const dataSourcesSlice: StateCreator<DataSourcesState> = (set, get) => {
  // Create the async slice for data sources
  const dataSourcesAsync = createAsyncSlice<DataSource[], DataSourcesState>(
    'dataSources',
    {
      fetchDataSources: async () => {
        console.log('Store: Fetching data sources from API...');
        const response = await api.fetchDataSources();
        
        if (!response || !response.data) {
          throw new Error('Invalid response format from API');
        }
        
        return transformDataSources(response.data);
      },
      
      createDataSource: async (data: any) => {
        const response = await api.createDataSource(data);
        await get().fetchDataSources();
        return response;
      },
      
      updateDataSource: async (id: string | number, data: any) => {
        const response = await api.updateDataSource(id, data);
        await get().fetchDataSources();
        return response;
      },
      
      deleteDataSource: async (id: string | number) => {
        const response = await api.deleteDataSource(id);
        await get().fetchDataSources();
        return response;
      }
    },
    [] // Initial empty array
  )(set, get);
  
  return {
    // Include the async slice
    ...dataSourcesAsync,
    
    // Additional state
    pullingProgress: {},
    
    // Additional actions
    pullDataSource: async (id) => {
      set((state) => ({
        pullingProgress: {
          ...state.pullingProgress,
          [id]: true
        }
      }));
      
      try {
        const response = await api.pullDataSource(id);
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
        return await api.getScraperStatus(id);
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
  };
}; 