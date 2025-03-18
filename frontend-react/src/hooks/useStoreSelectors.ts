import { useStore } from '@/store/useStore';
import { StoreState } from '@/store/types';

// Data sources selectors
export const useDataSourcesSelectors = () => {
  const dataSources = useStore((state: StoreState) => state.dataSources);
  const loading = useStore((state: StoreState) => state.loading.dataSources);
  const errors = useStore((state: StoreState) => state.errors.dataSources);
  const fetchDataSources = useStore((state: StoreState) => state.fetchDataSources);
  const createDataSource = useStore((state: StoreState) => state.createDataSource);
  const updateDataSource = useStore((state: StoreState) => state.updateDataSource);
  const deleteDataSource = useStore((state: StoreState) => state.deleteDataSource);
  const pullDataSource = useStore((state: StoreState) => state.pullDataSource);
  const pullingProgress = useStore((state: StoreState) => state.pullingProgress);
  const getScraperStatus = useStore((state: StoreState) => state.getScraperStatus);
  
  return {
    dataSources,
    loading,
    errors,
    fetchDataSources,
    createDataSource,
    updateDataSource,
    deleteDataSource,
    pullDataSource,
    pullingProgress,
    getScraperStatus
  };
};

// Proposals selectors
export const useProposalsSelectors = () => {
  const proposals = useStore((state: StoreState) => state.proposals);
  const pagination = useStore((state: StoreState) => state.proposalsPagination);
  const loading = useStore((state: StoreState) => state.loading.proposals);
  const errors = useStore((state: StoreState) => state.errors.proposals);
  const fetchProposals = useStore((state: StoreState) => state.fetchProposals);
  
  return {
    proposals,
    pagination,
    loading,
    errors,
    fetchProposals
  };
};

// UI selectors
export const useUISelectors = () => {
  const toasts = useStore((state: StoreState) => state.toasts);
  const isNavOpen = useStore((state: StoreState) => state.isNavOpen);
  const addToast = useStore((state: StoreState) => state.addToast);
  const removeToast = useStore((state: StoreState) => state.removeToast);
  const clearToasts = useStore((state: StoreState) => state.clearToasts);
  const setNavOpen = useStore((state: StoreState) => state.setNavOpen);
  const toggleNav = useStore((state: StoreState) => state.toggleNav);
  
  return {
    toasts,
    isNavOpen,
    addToast,
    removeToast,
    clearToasts,
    setNavOpen,
    toggleNav
  };
};

// Statistics selectors
export const useStatisticsSelectors = () => {
  const statistics = useStore((state: StoreState) => state.statistics);
  const dashboardData = useStore((state: StoreState) => state.dashboardData);
  const loadingStats = useStore((state: StoreState) => state.loading.statistics);
  const loadingDashboard = useStore((state: StoreState) => state.loading.dashboard);
  const errorsStats = useStore((state: StoreState) => state.errors.statistics);
  const errorsDashboard = useStore((state: StoreState) => state.errors.dashboard);
  const fetchStatistics = useStore((state: StoreState) => state.fetchStatistics);
  const fetchDashboardData = useStore((state: StoreState) => state.fetchDashboardData);
  
  return {
    statistics,
    dashboardData,
    loading: {
      statistics: loadingStats,
      dashboard: loadingDashboard
    },
    errors: {
      statistics: errorsStats,
      dashboard: errorsDashboard
    },
    fetchStatistics,
    fetchDashboardData
  };
};

// System selectors
export const useSystemSelectors = () => {
  const backups = useStore((state: StoreState) => state.backups);
  const loading = useStore((state: StoreState) => state.loading.databaseOperations);
  const errors = useStore((state: StoreState) => state.errors.databaseOperations);
  const lastUpdated = useStore((state: StoreState) => state.lastUpdated);
  const rebuildDatabase = useStore((state: StoreState) => state.rebuildDatabase);
  const initializeDatabase = useStore((state: StoreState) => state.initializeDatabase);
  const resetEverything = useStore((state: StoreState) => state.resetEverything);
  const manageBackups = useStore((state: StoreState) => state.manageBackups);
  
  return {
    backups,
    loading,
    errors,
    lastUpdated,
    rebuildDatabase,
    initializeDatabase,
    resetEverything,
    manageBackups
  };
};

// Computed selectors
export const useActiveDataSources = () => 
  useStore((state: StoreState) => state.dataSources.filter(source => source.status === 'active'));

export const useTotalProposalsCount = () => 
  useStore((state: StoreState) => state.dataSources.reduce((acc, source) => acc + (source.proposalCount || 0), 0)); 