import { useQuery, useMutation } from './use-query';

export interface SystemStatus {
  version: string;
  uptime: number;
  databaseStatus: 'healthy' | 'warning' | 'error';
  lastBackup: string;
  scraperStatus: {
    active: boolean;
    lastRun: string;
    nextScheduledRun: string;
  };
}

export interface BackupConfig {
  enabled: boolean;
  schedule: string;
  retention: number;
  location: string;
}

export function useSystemStatus(options = {}) {
  return useQuery<SystemStatus>(
    ['system', 'status'],
    '/system/status',
    {
      staleTime: 60 * 1000, // 1 minute
      ...options
    }
  );
}

export function useRebuildDatabase() {
  return useMutation<void, void>(
    '/system/rebuild-db',
    'post',
    {
      successMessage: 'Database rebuilt successfully',
      errorMessage: 'Failed to rebuild database',
      invalidateQueries: ['system', 'statistics', 'proposals', 'dataSources']
    }
  );
}

export function useInitializeDatabase() {
  return useMutation<void, void>(
    '/system/init-db',
    'post',
    {
      successMessage: 'Database initialized successfully',
      errorMessage: 'Failed to initialize database',
      invalidateQueries: ['system', 'statistics', 'proposals', 'dataSources']
    }
  );
}

export function useResetSystem() {
  return useMutation<void, void>(
    '/system/reset',
    'post',
    {
      successMessage: 'System reset successfully',
      errorMessage: 'Failed to reset system',
      invalidateQueries: ['system', 'statistics', 'proposals', 'dataSources']
    }
  );
}

export function useBackupConfig() {
  return useQuery<BackupConfig>(
    ['system', 'backup-config'],
    '/system/backup-config',
    {
      staleTime: 5 * 60 * 1000 // 5 minutes
    }
  );
}

export function useUpdateBackupConfig() {
  return useMutation<void, BackupConfig>(
    '/system/backup-config',
    'put',
    {
      successMessage: 'Backup configuration updated successfully',
      errorMessage: 'Failed to update backup configuration',
      invalidateQueries: ['system', 'backup-config']
    }
  );
}

export function useCreateBackup() {
  return useMutation<void, void>(
    '/system/backup',
    'post',
    {
      successMessage: 'Backup created successfully',
      errorMessage: 'Failed to create backup',
      invalidateQueries: ['system', 'status']
    }
  );
} 