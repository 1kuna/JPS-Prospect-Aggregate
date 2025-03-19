import { useState, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  Spinner,
} from '@/components/ui';
import { useToast } from '@/hooks/use-toast';
import { Settings, AlertTriangle, Database, Archive, Trash, RefreshCcw } from 'lucide-react';

// Type for database operations
interface DbOperation {
  name: string;
  action: () => Promise<any>;
  confirmTitle: string;
  confirmDescription: string;
  successMessage: string;
  icon: React.ReactNode;
  variant?: 'default' | 'destructive' | 'warning';
  buttonText?: string;
}

// Selectors
const selectDatabaseOperationsLoading = (state: any) => state.loading.databaseOperations;
const selectRebuildDatabase = (state: any) => state.rebuildDatabase;
const selectInitializeDatabase = (state: any) => state.initializeDatabase;
const selectResetEverything = (state: any) => state.resetEverything;
const selectManageBackups = (state: any) => state.manageBackups;
const selectBackups = (state: any) => state.backups;

export function DatabaseOperations() {
  const loading = useStore(selectDatabaseOperationsLoading);
  const rebuildDatabase = useStore(selectRebuildDatabase);
  const initializeDatabase = useStore(selectInitializeDatabase);
  const resetEverything = useStore(selectResetEverything);
  const manageBackups = useStore(selectManageBackups);
  const backups = useStore(selectBackups);
  const { toast } = useToast();

  const [isBackupsDialogOpen, setIsBackupsDialogOpen] = useState(false);
  const [activeOperation, setActiveOperation] = useState<DbOperation | null>(null);
  const [selectedBackupId, setSelectedBackupId] = useState<string | null>(null);
  const [isRestoreConfirmOpen, setIsRestoreConfirmOpen] = useState(false);

  // Define operations
  const operations: DbOperation[] = [
    {
      name: 'Rebuild Database',
      action: rebuildDatabase,
      confirmTitle: 'Rebuild Database',
      confirmDescription: 'This will rebuild the database tables. Existing data will be preserved, but this operation may take some time. Are you sure you want to continue?',
      successMessage: 'Database has been rebuilt successfully.',
      icon: <AlertTriangle className="mr-2 h-4 w-4" />,
      variant: 'warning',
      buttonText: 'Rebuild'
    },
    {
      name: 'Initialize Database',
      action: initializeDatabase,
      confirmTitle: 'Initialize Database',
      confirmDescription: 'This will initialize the database tables. This operation may take some time. Are you sure you want to continue?',
      successMessage: 'Database has been initialized successfully.',
      icon: <Database className="mr-2 h-4 w-4" />,
      variant: 'warning',
      buttonText: 'Initialize'
    },
    {
      name: 'Reset Everything',
      action: resetEverything,
      confirmTitle: 'Reset Everything',
      confirmDescription: 'This will reset all data in the application. This action cannot be undone. Are you sure you want to continue?',
      successMessage: 'Everything has been reset successfully.',
      icon: <Trash className="mr-2 h-4 w-4" />,
      variant: 'destructive',
      buttonText: 'Reset'
    }
  ];

  const handleOperation = useCallback(async (operation: DbOperation) => {
    try {
      await operation.action();
      toast({
        title: 'Success',
        description: operation.successMessage,
        variant: 'success',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || `Failed to ${operation.name.toLowerCase()}.`,
        variant: 'destructive',
      });
    } finally {
      setActiveOperation(null);
    }
  }, [toast]);

  const handleOpenBackupsDialog = useCallback(async () => {
    try {
      await manageBackups('list');
      setIsBackupsDialogOpen(true);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to load backups.',
        variant: 'destructive',
      });
    }
  }, [manageBackups, toast]);

  const handleCreateBackup = useCallback(async () => {
    try {
      await manageBackups('create');
      await manageBackups('list');
      toast({
        title: 'Success',
        description: 'Backup created successfully.',
        variant: 'success',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to create backup.',
        variant: 'destructive',
      });
    }
  }, [manageBackups, toast]);

  const handleRestoreBackup = useCallback(async () => {
    if (!selectedBackupId) return;
    
    try {
      await manageBackups('restore', selectedBackupId);
      setIsRestoreConfirmOpen(false);
      toast({
        title: 'Success',
        description: 'Backup restored successfully.',
        variant: 'success',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to restore backup.',
        variant: 'destructive',
      });
    }
  }, [selectedBackupId, manageBackups, toast]);

  const getOperationButtonClass = (variant: string = 'default') => {
    switch (variant) {
      case 'destructive': return 'bg-red-500 hover:bg-red-600';
      case 'warning': return 'bg-amber-500 hover:bg-amber-600';
      default: return 'bg-blue-500 hover:bg-blue-600';
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="text-white hover:bg-blue-700">
            <Settings className="h-5 w-5" />
            <span className="sr-only">Advanced</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56 bg-white text-black">
          <DropdownMenuLabel>Database Operations</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            {operations.slice(0, 2).map(op => (
              <DropdownMenuItem 
                key={op.name}
                className={op.variant === 'destructive' ? 'text-red-500' : op.variant === 'warning' ? 'text-amber-500' : ''}
                onClick={() => setActiveOperation(op)}
                disabled={loading}
              >
                {op.icon}
                <span>{op.name}</span>
              </DropdownMenuItem>
            ))}
            <DropdownMenuItem 
              onClick={handleOpenBackupsDialog}
              disabled={loading}
            >
              <Archive className="mr-2 h-4 w-4" />
              <span>Manage Backups</span>
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem 
            className="text-destructive"
            onClick={() => setActiveOperation(operations[2])}
            disabled={loading}
          >
            <Trash className="mr-2 h-4 w-4" />
            <span>Reset Everything</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <div className="px-2 py-1.5 text-xs text-muted-foreground">
            These operations should only be used by administrators
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Operation Confirmation Dialog */}
      {activeOperation && (
        <AlertDialog open={!!activeOperation} onOpenChange={(open) => !open && setActiveOperation(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{activeOperation.confirmTitle}</AlertDialogTitle>
              <AlertDialogDescription>
                {activeOperation.confirmDescription}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction 
                onClick={() => handleOperation(activeOperation)}
                className={getOperationButtonClass(activeOperation.variant)}
              >
                {loading ? <Spinner className="mr-2" size="sm" /> : activeOperation.icon}
                {activeOperation.buttonText || activeOperation.name}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {/* Backups Dialog */}
      <Dialog open={isBackupsDialogOpen} onOpenChange={setIsBackupsDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Manage Backups</DialogTitle>
            <DialogDescription>
              Create and restore database backups.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <Button 
              onClick={handleCreateBackup}
              disabled={loading}
              className="mb-4"
            >
              {loading ? <Spinner className="mr-2" size="sm" /> : <Archive className="mr-2 h-4 w-4" />}
              Create Backup
            </Button>
            
            <div className="max-h-[200px] overflow-y-auto border rounded-md">
              {backups && backups.length > 0 ? (
                <ul className="divide-y">
                  {backups.map((backup: any) => (
                    <li key={backup.id} className="flex items-center justify-between p-3 hover:bg-gray-50">
                      <div>
                        <span className="block font-medium">{backup.filename}</span>
                        <span className="block text-sm text-gray-500">
                          {new Date(backup.created_at).toLocaleString()}
                        </span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedBackupId(backup.id);
                          setIsRestoreConfirmOpen(true);
                        }}
                      >
                        <RefreshCcw className="h-4 w-4 mr-1" />
                        Restore
                      </Button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-center py-4 text-gray-500">No backups available</p>
              )}
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsBackupsDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Restore Confirmation */}
      <AlertDialog open={isRestoreConfirmOpen} onOpenChange={setIsRestoreConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore Backup</AlertDialogTitle>
            <AlertDialogDescription>
              This will restore the database from the selected backup. Current data will be replaced.
              Are you sure you want to continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setSelectedBackupId(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleRestoreBackup}
              className="bg-blue-500 hover:bg-blue-600"
            >
              {loading ? <Spinner className="mr-2" size="sm" /> : <RefreshCcw className="mr-2 h-4 w-4" />}
              Restore
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
} 