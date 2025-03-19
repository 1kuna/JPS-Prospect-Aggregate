import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { proposalsSlice } from './slices/proposalsSlice';
import { dataSourcesSlice } from './slices/dataSourcesSlice';
import { uiSlice } from './slices/uiSlice';
import { analyticsSlice } from './slices/analyticsSlice';
import { systemSlice } from './slices/systemSlice';
import { StoreState } from './types';
import { logger, perfMonitor } from './middleware/logger';
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

// Function to create the store with middleware composition
const createStore = () => {
  // Define the middleware chain for the store
  // Order matters: the first middleware in the array is the outermost wrapper
  return create<StoreState>()(
    // Development tools for debugging (only in non-production)
    process.env.NODE_ENV !== 'production'
      ? devtools(
          // Logger for tracking state changes (innermost)
          logger<StoreState>('MainStore')(
            // Performance monitoring
            perfMonitor<StoreState>('MainStore')(
              // Combine all slices
              (...args) => ({
                ...proposalsSlice(...args),
                ...dataSourcesSlice(...args),
                ...uiSlice(...args),
                ...analyticsSlice(...args),
                ...systemSlice(...args),
              })
            )
          ),
          { name: 'JPSProspectStore', enabled: true }
        )
      : // In production, skip the dev middlewares
        (...args) => ({
          ...proposalsSlice(...args),
          ...dataSourcesSlice(...args),
          ...uiSlice(...args),
          ...analyticsSlice(...args),
          ...systemSlice(...args),
        })
  );
};

// Create the store
export const useStore = createStore();

// Helper function to create a toast notification
// This is exported for backwards compatibility
export const createToast = (
  title: string, 
  description: string, 
  variant?: 'default' | 'destructive' | 'success', 
  duration?: number
) => {
  useStore.getState().addToast({ title, description, variant, duration });
};

// Export selectors for components to use
export const selectProposals = (state: StoreState) => state.proposals;
export const selectProposalsPagination = (state: StoreState) => state.proposalsPagination;

export const selectDataSources = (state: StoreState) => state.dataSources;
export const selectPullingProgress = (state: StoreState) => state.pullingProgress;

export const selectDashboardData = (state: StoreState) => state.dashboardData;
export const selectStatistics = (state: StoreState) => state.statistics;

export const selectToasts = (state: StoreState) => state.toasts;
export const selectNavOpen = (state: StoreState) => state.isNavOpen;

export const selectBackups = (state: StoreState) => state.backups;
export const selectLastUpdated = (state: StoreState) => state.lastUpdated;

// Loading selectors
export const selectLoadingProposals = (state: StoreState) => state.loading.proposals;
export const selectLoadingDataSources = (state: StoreState) => state.loading.dataSources;
export const selectLoadingDashboard = (state: StoreState) => state.loading.dashboard;
export const selectLoadingStatistics = (state: StoreState) => state.loading.statistics;
export const selectLoadingDatabaseOperations = (state: StoreState) => state.loading.databaseOperations;

// Error selectors
export const selectErrorsProposals = (state: StoreState) => state.errors.proposals;
export const selectErrorsDataSources = (state: StoreState) => state.errors.dataSources;
export const selectErrorsDashboard = (state: StoreState) => state.errors.dashboard;
export const selectErrorsStatistics = (state: StoreState) => state.errors.statistics;
export const selectErrorsDatabaseOperations = (state: StoreState) => state.errors.databaseOperations;

