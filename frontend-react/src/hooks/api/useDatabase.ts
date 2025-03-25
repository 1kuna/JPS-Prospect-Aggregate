import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { toast } from '../use-toast';

// Query for database status
export const useDatabaseStatus = () => {
  return useQuery({
    queryKey: ['database', 'status'],
    queryFn: async () => {
      const response = await apiClient.get('/api/database/status');
      return response.data;
    },
  });
};

// Query for available backups
export const useDatabaseBackups = () => {
  return useQuery({
    queryKey: ['database', 'backups'],
    queryFn: async () => {
      const response = await apiClient.get('/api/database/backups');
      return response.data;
    },
  });
};

// Mutation for rebuilding database
export const useRebuildDatabase = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/api/database/rebuild');
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Success',
        description: 'Database rebuilt successfully',
      });
      queryClient.invalidateQueries({ queryKey: ['database'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: 'Failed to rebuild database: ' + error.message,
        variant: 'destructive',
      });
    },
  });
};

// Mutation for initializing database
export const useInitializeDatabase = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/api/database/initialize');
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Success',
        description: 'Database initialized successfully',
      });
      queryClient.invalidateQueries({ queryKey: ['database'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: 'Failed to initialize database: ' + error.message,
        variant: 'destructive',
      });
    },
  });
};

// Mutation for resetting database
export const useResetDatabase = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/api/database/reset');
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Success',
        description: 'Database reset successfully',
      });
      queryClient.invalidateQueries({ queryKey: ['database'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: 'Failed to reset database: ' + error.message,
        variant: 'destructive',
      });
    },
  });
};

// Mutation for creating backup
export const useCreateBackup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/api/database/backups');
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Success',
        description: 'Backup created successfully',
      });
      queryClient.invalidateQueries({ queryKey: ['database'] });
      queryClient.invalidateQueries({ queryKey: ['database', 'backups'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: 'Failed to create backup: ' + error.message,
        variant: 'destructive',
      });
    },
  });
};

// Mutation for restoring backup
export const useRestoreBackup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (backupId: string) => {
      const response = await apiClient.post('/api/database/backups/restore', { backupId });
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Success',
        description: 'Backup restored successfully',
      });
      queryClient.invalidateQueries({ queryKey: ['database'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: 'Failed to restore backup: ' + error.message,
        variant: 'destructive',
      });
    },
  });
};

// Mutation for direct SQL query execution
export const useExecuteQuery = () => {
  return useMutation({
    mutationFn: async (query: string) => {
      const response = await apiClient.post('/api/database/query', { query });
      return response.data;
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: 'Query execution failed: ' + error.message,
        variant: 'destructive',
      });
    },
  });
}; 