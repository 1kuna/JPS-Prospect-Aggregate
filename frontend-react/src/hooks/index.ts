// Core hooks
// ... existing code ...

// Explicitly export from API hooks
export {
  useDatabaseStatus,
  useDatabaseBackups,
  useRebuildDatabase,
  useInitializeDatabase,
  useResetDatabase,
  useCreateBackup,
  useRestoreBackup,
  useExecuteQuery,
} from './api/useDatabase';
export {
  useListDataSources,
  useCreateDataSource,
  useUpdateDataSource,
  useDeleteDataSource,
} from './api/useDataSources';

export {
  useInfiniteProposals,
  useProposalStatistics,
  useCreateProposal,
  useUpdateProposal,
  useDeleteProposal,
} from './api/useProposals';

// Explicitly export from App-specific hooks
// ... existing code ...