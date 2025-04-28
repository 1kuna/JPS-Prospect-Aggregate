// Core hooks
// export * from './use-query'; // Still missing?
// export * from './use-toast'; // Not used

// Explicitly export from API hooks
/* // Removing all unused exports for now
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
*/
export {
  useDataSources,
  // useDataSourceHealth, // Not used
  // usePullDataSource, // Not used
} from './api/useDataSources';
/* // Removing all unused exports for now
export {
  useProposals,
  useProposalStatistics,
  useRecentProposals,
  // useInfiniteProposals, // Is missing
} from './api/useProposals';

// Analytics hooks removed as files were deleted

// Explicitly export from App-specific hooks
export {
    useSystemStatus, 
    // useShutdownServer, // Doesn't exist in use-system.ts?
    // useRestartServer, // Doesn't exist in use-system.ts?
    useBackupConfig, 
    useUpdateBackupConfig, 
    // useTriggerBackup // Doesn't exist in use-system.ts?
} from './use-system';
*/

// Comment out the old re-export blocks
// export * from './api'; 
// export * from './use-system';
// Remove the final aggregate export block as everything is exported above 