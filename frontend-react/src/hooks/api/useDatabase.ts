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
  return useApiQuery<DatabaseBackup[]>({
    queryKey: ['database', 'backups'],
    endpoint: '/api/database/backups',
  });
};

// Mutation for rebuilding database
export const useRebuildDatabase = () => {
  return useApiMutation<void>({
    endpoint: '/api/database/rebuild',
    method: 'POST',
    successMessage: 'Database rebuilt successfully',
    errorMessage: 'Failed to rebuild database',
    invalidateQueries: [['database']],
  });
};

// Mutation for initializing database
export const useInitializeDatabase = () => {
  return useApiMutation<void>({
    endpoint: '/api/database/initialize',
    method: 'POST',
    successMessage: 'Database initialized successfully',
    errorMessage: 'Failed to initialize database',
    invalidateQueries: [['database']],
  });
};

// Mutation for resetting database
export const useResetDatabase = () => {
  return useApiMutation<void>({
    endpoint: '/api/database/reset',
    method: 'POST',
    successMessage: 'Database reset successfully',
    errorMessage: 'Failed to reset database',
    invalidateQueries: [['database']],
  });
};

// Mutation for creating backup
export const useCreateBackup = () => {
  return useApiMutation<void>({
    endpoint: '/api/database/backups',
    method: 'POST',
    successMessage: 'Backup created successfully',
    errorMessage: 'Failed to create backup',
    invalidateQueries: [['database'], ['database', 'backups']],
  });
};

// Mutation for restoring backup
export const useRestoreBackup = () => {
  return useApiMutation<void, { backupId: string }>({
    endpoint: '/api/database/backups/restore',
    method: 'POST',
    successMessage: 'Backup restored successfully',
    errorMessage: 'Failed to restore backup',
    invalidateQueries: [['database']],
  });
};

// Mutation for direct SQL query execution
export const useExecuteQuery = () => {
  return useApiMutation<unknown, { query: string }>({
    endpoint: '/api/database/query',
    method: 'POST',
    errorMessage: 'Query execution failed',
  });
}; 