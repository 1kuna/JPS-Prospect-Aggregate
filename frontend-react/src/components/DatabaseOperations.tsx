import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Alert, AlertTitle, AlertDescription } from './ui/alert';
import {
  useDatabaseStatus,
  useDatabaseBackups,
  useRebuildDatabase,
  useInitializeDatabase,
  useResetDatabase,
  useCreateBackup,
  useRestoreBackup
} from '@/hooks/api/useDatabase';
import { toast } from '@/hooks/use-toast';
import styles from './DatabaseOperations.module.css'; // Import CSS module

export function DatabaseOperations() {
  const [isConfirmingReset, setIsConfirmingReset] = useState(false);
  
  const { data: status, isLoading: statusLoading } = useDatabaseStatus();
  const { data: backups, isLoading: backupsLoading } = useDatabaseBackups();
  
  const { mutate: rebuildDatabase, isLoading: isRebuilding } = useRebuildDatabase();
  const { mutate: initializeDatabase, isLoading: isInitializing } = useInitializeDatabase();
  const { mutate: resetDatabase, isLoading: isResetting } = useResetDatabase();
  const { mutate: createBackup, isLoading: isBackingUp } = useCreateBackup();
  const { mutate: restoreBackup, isLoading: isRestoring } = useRestoreBackup();

  const handleRebuild = () => {
    rebuildDatabase(undefined, {
      onSuccess: () => {
        toast.success({ title: 'Success', description: 'Database rebuilt successfully' });
      },
      onError: () => {
        toast.error({ title: 'Error', description: 'Failed to rebuild database' });
      }
    });
  };

  const handleInitialize = () => {
    initializeDatabase(undefined, {
      onSuccess: () => {
        toast.success({ title: 'Success', description: 'Database initialized successfully' });
      },
      onError: () => {
        toast.error({ title: 'Error', description: 'Failed to initialize database' });
      }
    });
  };

  const handleReset = () => {
    if (!isConfirmingReset) {
      setIsConfirmingReset(true);
      return;
    }

    resetDatabase(undefined, {
      onSuccess: () => {
        toast.success({ title: 'Success', description: 'Database reset successfully' });
        setIsConfirmingReset(false);
      },
      onError: () => {
        toast.error({ title: 'Error', description: 'Failed to reset database' });
        setIsConfirmingReset(false);
      }
    });
  };

  const handleCreateBackup = () => {
    createBackup(undefined, {
      onSuccess: () => {
        toast.success({ title: 'Success', description: 'Backup created successfully' });
      },
      onError: () => {
        toast.error({ title: 'Error', description: 'Failed to create backup' });
      }
    });
  };

  const handleRestoreBackup = (backupId: string) => {
    restoreBackup({ backupId }, {
      onSuccess: () => {
        toast.success({ title: 'Success', description: 'Backup restored successfully' });
      },
      onError: () => {
        toast.error({ title: 'Error', description: 'Failed to restore backup' });
      }
    });
  };

  const isLoading = statusLoading || backupsLoading || isRebuilding || 
                    isInitializing || isResetting || isBackingUp || isRestoring;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Database Operations</CardTitle>
      </CardHeader>
      <CardContent className={styles.cardContent}>
        {/* Database Status */}
        {status && (
          <div className={styles.statusGrid}>
            <div>
              <p className={styles.statusLabel}>Database Size</p>
              <p className={styles.statusValue}>{status.size}</p>
            </div>
            <div>
              <p className={styles.statusLabel}>Last Backup</p>
              <p className={styles.statusValue}>{status.lastBackup || 'Never'}</p>
            </div>
            <div>
              <p className={styles.statusLabel}>Uptime</p>
              <p className={styles.statusValue}>{status.uptime}</p>
            </div>
            <div>
              <p className={styles.statusLabel}>Health</p>
              <p className={styles.statusValue}>{status.health}</p>
            </div>
          </div>
        )}

        {/* Operation Buttons */}
        <div className={styles.buttonGroup}>
          <Button
            onClick={handleRebuild}
            disabled={isLoading}
          >
            {isRebuilding ? 'Rebuilding...' : 'Rebuild Database'}
          </Button>
          <Button
            onClick={handleInitialize}
            disabled={isLoading}
          >
            {isInitializing ? 'Initializing...' : 'Initialize Database'}
          </Button>
          <Button
            onClick={handleCreateBackup}
            disabled={isLoading}
            variant="outline"
          >
            {isBackingUp ? 'Creating Backup...' : 'Create Backup'}
          </Button>
        </div>

        {/* Reset Confirmation */}
        {isConfirmingReset ? (
          <Alert variant="destructive">
            <AlertTitle>Warning</AlertTitle>
            <AlertDescription>
              This will permanently delete all data. Are you sure?
              <div className={styles.confirmButtonGroup}>
                <Button
                  variant="destructive"
                  onClick={handleReset}
                  disabled={isLoading}
                >
                  {isResetting ? 'Resetting...' : 'Confirm Reset'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setIsConfirmingReset(false)}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        ) : (
          <Button
            variant="destructive"
            onClick={handleReset}
            disabled={isLoading}
          >
            Reset Everything
          </Button>
        )}

        {/* Backups List */}
        {backups && backups.length > 0 && (
          <div className={styles.backupsSection}>
            <h3 className={styles.sectionTitle}>Available Backups</h3>
            <div className={styles.backupsList}>
              {backups.map((backup) => (
                <div
                  key={backup.id}
                  className={styles.backupItem}
                >
                  <div>
                    <p className={styles.backupTimestamp}>{new Date(backup.timestamp).toLocaleString()}</p>
                    <p className={styles.statusLabel}>{backup.size}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRestoreBackup(backup.id)}
                    disabled={isLoading}
                  >
                    {isRestoring ? 'Restoring...' : 'Restore'}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
} 