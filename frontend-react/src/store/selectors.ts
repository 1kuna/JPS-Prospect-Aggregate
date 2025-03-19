import { useStore } from './useStore';
import { StoreState } from './types';
import { createSelector } from 'reselect';

// Base selectors - Single source of truth for state access
export const selectDataSources = (state: StoreState) => state.dataSources;
export const selectDataSourcesLoading = (state: StoreState) => state.dataSourcesLoading;
export const selectDataSourcesError = (state: StoreState) => state.dataSourcesError;

export const selectProposals = (state: StoreState) => state.proposals;
export const selectProposalsLoading = (state: StoreState) => state.proposalsLoading;
export const selectProposalsError = (state: StoreState) => state.proposalsError;

export const selectStatistics = (state: StoreState) => state.statistics;
export const selectStatisticsLoading = (state: StoreState) => state.statisticsLoading;
export const selectStatisticsError = (state: StoreState) => state.statisticsError;

export const selectUiState = (state: StoreState) => state.ui;
export const selectTheme = (state: StoreState) => state.ui.theme;
export const selectSidebarOpen = (state: StoreState) => state.ui.sidebarOpen;

export const selectSystemState = (state: StoreState) => state.system;
export const selectSystemStatus = (state: StoreState) => state.system.status;
export const selectIsConnected = (state: StoreState) => state.system.isConnected;

// Derived selectors - Computed values based on base selectors
export const selectActiveDataSources = createSelector(
  [selectDataSources],
  (dataSources) => dataSources.filter(source => source.status === 'active')
);

export const selectDataSourceById = (id: number) => 
  createSelector(
    [selectDataSources],
    (dataSources) => dataSources.find(source => source.id === id)
  );

export const selectProposalsByDataSource = (dataSourceId: number) => 
  createSelector(
    [selectProposals],
    (proposals) => proposals.filter(proposal => proposal.dataSourceId === dataSourceId)
  );

export const selectTotalProposals = createSelector(
  [selectProposals],
  (proposals) => proposals.length
);

export const selectTotalDataSources = createSelector(
  [selectDataSources],
  (dataSources) => dataSources.length
);

export const selectIsLoading = createSelector(
  [selectDataSourcesLoading, selectProposalsLoading, selectStatisticsLoading],
  (dataSourcesLoading, proposalsLoading, statisticsLoading) => 
    dataSourcesLoading || proposalsLoading || statisticsLoading
);

export const selectHasErrors = createSelector(
  [selectDataSourcesError, selectProposalsError, selectStatisticsError],
  (dataSourcesError, proposalsError, statisticsError) => 
    !!(dataSourcesError || proposalsError || statisticsError)
);

// Higher-order selector creator for common patterns
export const createFilterSelector = <T extends Record<string, any>>(
  baseSelector: (state: StoreState) => T[],
  filterFn: (item: T) => boolean
) => createSelector([baseSelector], (items) => items.filter(filterFn));

export const createSortSelector = <T extends Record<string, any>>(
  baseSelector: (state: StoreState) => T[],
  sortKey: keyof T,
  sortDirection: 'asc' | 'desc' = 'asc'
) => createSelector([baseSelector], (items) => {
  return [...items].sort((a, b) => {
    if (sortDirection === 'asc') {
      return a[sortKey] > b[sortKey] ? 1 : -1;
    } else {
      return a[sortKey] < b[sortKey] ? 1 : -1;
    }
  });
});

// Basic selectors (can be used both within other selectors and in components)
export const selectInactiveDataSources = (state: StoreState) => 
  state.dataSources.filter(source => source.status !== 'active');

export const selectTotalProposalsCount = (state: StoreState) => 
  state.dataSources.reduce((acc, source) => acc + (source.proposalCount || 0), 0);

export const selectRecentlyUpdatedSources = (state: StoreState) => {
  // Get sources updated in the last 24 hours
  const oneDayAgo = new Date();
  oneDayAgo.setDate(oneDayAgo.getDate() - 1);
  
  return state.dataSources.filter(source => {
    if (!source.lastChecked) return false;
    const lastCheckedDate = new Date(source.lastChecked);
    return lastCheckedDate > oneDayAgo;
  });
};

export const selectProposalsTrend = (state: StoreState) => {
  if (!state.statistics || !state.statistics.proposals_by_month) {
    return [];
  }
  
  // Sort by date
  return [...state.statistics.proposals_by_month]
    .sort((a, b) => new Date(a.month).getTime() - new Date(b.month).getTime())
    .map(item => ({
      month: new Date(item.month).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
      count: item.count
    }));
};

export const selectDataSourcesHealth = (state: StoreState) => {
  const total = state.dataSources.length;
  if (total === 0) return { healthy: 0, issues: 0, percentage: 0 };
  
  const healthy = state.dataSources.filter(source => 
    source.status === 'active' && source.lastScraped
  ).length;
  
  return {
    healthy,
    issues: total - healthy,
    percentage: Math.round((healthy / total) * 100)
  };
};

export const selectRecentProposals = (limit = 5) => (state: StoreState) => {
  // Get the most recent proposals based on release date
  return [...state.proposals]
    .sort((a, b) => 
      new Date(b.release_date).getTime() - new Date(a.release_date).getTime()
    )
    .slice(0, limit);
};

export const selectLatestActivityByDataSource = (state: StoreState) => 
  state.dataSources.map(source => ({
    id: source.id,
    name: source.name,
    lastActivity: source.lastScraped ? new Date(source.lastScraped) : null,
    proposalCount: source.proposalCount
  }))
  .sort((a, b) => {
    if (!a.lastActivity) return 1;
    if (!b.lastActivity) return -1;
    return b.lastActivity.getTime() - a.lastActivity.getTime();
  });

// Hook-based selectors for use in components
export const useActiveDataSources = () => useStore(selectActiveDataSources);
export const useInactiveDataSources = () => useStore(selectInactiveDataSources);
export const useTotalProposalsCount = () => useStore(selectTotalProposalsCount);
export const useRecentlyUpdatedSources = () => useStore(selectRecentlyUpdatedSources);
export const useDataSourceById = (id: number | string) => useStore(selectDataSourceById(id));
export const useProposalsTrend = () => useStore(selectProposalsTrend);
export const useDataSourcesHealth = () => useStore(selectDataSourcesHealth);
export const useRecentProposals = (limit = 5) => useStore(selectRecentProposals(limit));
export const useProposalsByDataSource = () => useStore(selectProposalsByDataSource);
export const useLatestActivityByDataSource = () => useStore(selectLatestActivityByDataSource);

// Combined selectors that compute derived data
export const useSourcesWithStats = () => {
  const dataSources = useStore(state => state.dataSources);
  const proposals = useStore(state => state.proposals);
  
  return dataSources.map(source => {
    const sourceProposals = proposals.filter(p => p.source_id === source.id);
    const proposalCount = sourceProposals.length;
    const latestProposal = sourceProposals.length > 0 
      ? sourceProposals.reduce((latest, p) => {
          const latestDate = latest.release_date ? new Date(latest.release_date) : new Date(0);
          const currentDate = p.release_date ? new Date(p.release_date) : new Date(0);
          return currentDate > latestDate ? p : latest;
        }, sourceProposals[0])
      : null;
    
    return {
      ...source,
      proposalCount,
      latestProposal
    };
  });
}; 