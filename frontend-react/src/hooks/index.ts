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
  useDataSources,
} from './api/useDataSources';

export {
  useProposals,
  useProposalStatistics,
} from './api/useProposals';

// Explicitly export from App-specific hooks
// ... existing code ...