import { useApiQuery, useApiMutation } from './useApi';

interface DatabaseStatus {
  status: string;
  lastBackup: string;
  size: number;
}

interface DatabaseBackup {
  id: string;
  timestamp: string;
  size: number;
  status: string;
}

// Query for database status
export const useDatabaseStatus = () => {
  return useApiQuery<DatabaseStatus>({
    queryKey: ['database', 'status'],
    endpoint: '/api/database/status',
  });
};

// Query for available backups
export const useDatabaseBackups = () => {
  // @ts-ignore
  return (useApiQuery as any)<DatabaseBackup[]>({
    queryKey: ['database', 'backups'],
    endpoint: '/api/database/backups',
  });
};

// Mutation for rebuilding database
export const useRebuildDatabase = () => {
  // @ts-ignore
  return (useApiMutation as any)<void>({
    endpoint: '/api/database/rebuild',
    method: 'POST',
    successMessage: 'Database rebuilt successfully',
    errorMessage: 'Failed to rebuild database',
    invalidateQueries: [['database']],
  });
};

// Mutation for initializing database
export const useInitializeDatabase = () => {
  // @ts-ignore
  return (useApiMutation as any)<void>({
    endpoint: '/api/database/initialize',
    method: 'POST',
    successMessage: 'Database initialized successfully',
    errorMessage: 'Failed to initialize database',
    invalidateQueries: [['database']],
  });
};

// Mutation for resetting database
export const useResetDatabase = () => {
  // @ts-ignore
  return (useApiMutation as any)<void>({
    endpoint: '/api/database/reset',
    method: 'POST',
    successMessage: 'Database reset successfully',
    errorMessage: 'Failed to reset database',
    invalidateQueries: [['database']],
  });
};

// Mutation for creating backup
export const useCreateBackup = () => {
  // @ts-ignore
  return (useApiMutation as any)<void>({
    endpoint: '/api/database/backups',
    method: 'POST',
    successMessage: 'Backup created successfully',
    errorMessage: 'Failed to create backup',
    invalidateQueries: [['database'], ['database', 'backups']],
  });
};

// Mutation for restoring backup
export const useRestoreBackup = () => {
  // @ts-ignore
  return (useApiMutation as any)<void, Error, { backupId: string }>({
    endpoint: '/api/database/backups/restore',
    method: 'POST',
    successMessage: 'Backup restored successfully',
    errorMessage: 'Failed to restore backup',
    invalidateQueries: [['database']],
  });
};

// Mutation for direct SQL query execution
export const useExecuteQuery = () => {
  // @ts-ignore
  return (useApiMutation as any)<unknown, Error, { query: string }>({
    endpoint: '/api/database/query',
    method: 'POST',
    errorMessage: 'Query execution failed',
  });
}; 