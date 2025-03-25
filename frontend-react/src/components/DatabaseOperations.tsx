import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Alert, AlertTitle, AlertDescription } from './ui/alert';
import { useDatabase } from '@/hooks/api/useDatabase';
import { toast } from '@/hooks/use-toast';

export function DatabaseOperations() {
  const [isConfirmingReset, setIsConfirmingReset] = useState(false);
  
  const { data: status, isLoading: statusLoading } = useDatabase.useStatus();
  const { data: backups, isLoading: backupsLoading } = useDatabase.useBackups();
  
  const { mutate: rebuildDatabase, isLoading: isRebuilding } = useDatabase.useRebuild();
  const { mutate: initializeDatabase, isLoading: isInitializing } = useDatabase.useInitialize();
  const { mutate: resetDatabase, isLoading: isResetting } = useDatabase.useReset();
  const { mutate: createBackup, isLoading: isBackingUp } = useDatabase.useCreateBackup();
  const { mutate: restoreBackup, isLoading: isRestoring } = useDatabase.useRestoreBackup();

  const handleRebuild = () => {
    rebuildDatabase(undefined, {
      onSuccess: () => {
        toast.success({ title: 'Success', description: 'Database rebuilt successfully' });
      }
    });
  };

  const handleInitialize = () => {
    initializeDatabase(undefined, {
      onSuccess: () => {
        toast.success({ title: 'Success', description: 'Database initialized successfully' });
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
      }
    });
  };

  const handleCreateBackup = () => {
    createBackup(undefined, {
      onSuccess: () => {
        toast.success({ title: 'Success', description: 'Backup created successfully' });
      }
    });
  };

  const handleRestoreBackup = (backupId: string) => {
    restoreBackup({ backupId }, {
      onSuccess: () => {
        toast.success({ title: 'Success', description: 'Backup restored successfully' });
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
      <CardContent className="space-y-4">
        {/* Database Status */}
        {status && (
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-sm text-muted-foreground">Database Size</p>
              <p className="text-lg font-semibold">{status.size}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Last Backup</p>
              <p className="text-lg font-semibold">{status.lastBackup || 'Never'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Uptime</p>
              <p className="text-lg font-semibold">{status.uptime}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Health</p>
              <p className="text-lg font-semibold">{status.health}</p>
            </div>
          </div>
        )}

        {/* Operation Buttons */}
        <div className="flex flex-wrap gap-2">
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
              <div className="flex gap-2 mt-2">
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
          <div className="mt-4">
            <h3 className="text-lg font-semibold mb-2">Available Backups</h3>
            <div className="space-y-2">
              {backups.map((backup) => (
                <div
                  key={backup.id}
                  className="flex items-center justify-between p-2 border rounded"
                >
                  <div>
                    <p className="font-medium">{new Date(backup.timestamp).toLocaleString()}</p>
                    <p className="text-sm text-muted-foreground">{backup.size}</p>
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