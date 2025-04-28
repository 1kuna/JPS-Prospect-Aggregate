import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  useDatabaseStatus,
  useDatabaseBackups,
  useRebuildDatabase,
  useInitializeDatabase,
  useResetDatabase,
  useCreateBackup,
  useRestoreBackup
} from '@/hooks/api/useDatabase';
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
        // Intentionally empty
      },
      onError: () => {
        // Intentionally empty
      }
    });
  };

  const handleInitialize = () => {
    initializeDatabase(undefined, {
      onSuccess: () => {
        // Intentionally empty
      },
      onError: () => {
        // Intentionally empty
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
        // Intentionally empty
        setIsConfirmingReset(false);
      },
      onError: () => {
        // Intentionally empty
        setIsConfirmingReset(false);
      }
    });
  };

  const handleCreateBackup = () => {
    createBackup(undefined, {
      onSuccess: () => {
        // Intentionally empty
      },
      onError: () => {
        // Intentionally empty
      }
    });
  };

  const handleRestoreBackup = (backupId: string) => {
    restoreBackup({ backupId }, {
      onSuccess: () => {
        // Intentionally empty
      },
      onError: () => {
        // Intentionally empty
      }
    });
  };

  const isLoading = statusLoading || backupsLoading || isRebuilding || 
                    isInitializing || isResetting || isBackingUp || isRestoring;

  return (
    <div className={styles.cardContainer}>
      <div className={styles.cardHeader}>
        <h2 className={styles.cardTitle}>Database Operations</h2>
      </div>
      <div className={styles.cardContent}>
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
          <div className={`${styles.alert} ${styles.alertDestructive}`}>
            <h4 className={styles.alertTitle}>Warning</h4>
            <p className={styles.alertDescription}>
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
            </p>
          </div>
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
              {backups.map((backup: any) => (
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
                    disabled={isRestoring}
                  >
                    {isRestoring ? 'Restoring...' : 'Restore'}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 