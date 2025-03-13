import { useState } from 'react';
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
import { Settings, AlertTriangle, Database, Archive, Trash } from 'lucide-react';

// Create stable selectors
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
  const [isRebuildConfirmOpen, setIsRebuildConfirmOpen] = useState(false);
  const [isInitConfirmOpen, setIsInitConfirmOpen] = useState(false);
  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);
  const [isRestoreConfirmOpen, setIsRestoreConfirmOpen] = useState(false);
  const [selectedBackupId, setSelectedBackupId] = useState<string | null>(null);

  const handleRebuildDatabase = async () => {
    try {
      await rebuildDatabase();
      toast({
        title: 'Success',
        description: 'Database has been rebuilt successfully.',
        variant: 'success',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to rebuild database.',
        variant: 'destructive',
      });
    }
  };

  const handleInitializeDatabase = async () => {
    try {
      await initializeDatabase();
      toast({
        title: 'Success',
        description: 'Database has been initialized successfully.',
        variant: 'success',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to initialize database.',
        variant: 'destructive',
      });
    }
  };

  const handleResetEverything = async () => {
    try {
      await resetEverything();
      toast({
        title: 'Success',
        description: 'Everything has been reset successfully.',
        variant: 'success',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to reset everything.',
        variant: 'destructive',
      });
    }
  };

  const handleOpenBackupsDialog = async () => {
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
  };

  const handleCreateBackup = async () => {
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
  };

  const handleRestoreBackup = async () => {
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
            <DropdownMenuItem 
              className="text-amber-500"
              onClick={() => setIsRebuildConfirmOpen(true)}
              disabled={loading}
            >
              <AlertTriangle className="mr-2 h-4 w-4" />
              <span>Rebuild Database</span>
            </DropdownMenuItem>
            <DropdownMenuItem 
              className="text-amber-500"
              onClick={() => setIsInitConfirmOpen(true)}
              disabled={loading}
            >
              <AlertTriangle className="mr-2 h-4 w-4" />
              <span>Initialize Database</span>
            </DropdownMenuItem>
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
            onClick={() => setIsResetConfirmOpen(true)}
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

      {/* Rebuild Database Confirmation */}
      <AlertDialog open={isRebuildConfirmOpen} onOpenChange={setIsRebuildConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rebuild Database</AlertDialogTitle>
            <AlertDialogDescription>
              This will rebuild the database tables. Existing data will be preserved, but this operation may take some time.
              Are you sure you want to continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={() => {
                setIsRebuildConfirmOpen(false);
                handleRebuildDatabase();
              }}
              className="bg-amber-500 hover:bg-amber-600"
            >
              {loading ? <Spinner className="mr-2" size="sm" /> : <AlertTriangle className="mr-2 h-4 w-4" />}
              Rebuild
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Initialize Database Confirmation */}
      <AlertDialog open={isInitConfirmOpen} onOpenChange={setIsInitConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Initialize Database</AlertDialogTitle>
            <AlertDialogDescription>
              This will initialize the database tables. This operation may take some time.
              Are you sure you want to continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={() => {
                setIsInitConfirmOpen(false);
                handleInitializeDatabase();
              }}
              className="bg-amber-500 hover:bg-amber-600"
            >
              {loading ? <Spinner className="mr-2" size="sm" /> : <AlertTriangle className="mr-2 h-4 w-4" />}
              Initialize
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reset Everything Confirmation */}
      <AlertDialog open={isResetConfirmOpen} onOpenChange={setIsResetConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reset Everything</AlertDialogTitle>
            <AlertDialogDescription>
              This will reset the entire application, including all database tables and data.
              This action cannot be undone. Are you sure you want to continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={() => {
                setIsResetConfirmOpen(false);
                handleResetEverything();
              }}
              className="bg-destructive hover:bg-destructive/90"
            >
              {loading ? <Spinner className="mr-2" size="sm" /> : <Trash className="mr-2 h-4 w-4" />}
              Reset Everything
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Manage Backups Dialog */}
      <Dialog open={isBackupsDialogOpen} onOpenChange={setIsBackupsDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Manage Backups</DialogTitle>
            <DialogDescription>
              Create, view, and restore database backups.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            {loading ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : (
              <div className="space-y-4">
                <Button onClick={handleCreateBackup} className="w-full">
                  <Archive className="mr-2 h-4 w-4" />
                  Create New Backup
                </Button>
                
                <div className="border rounded-md overflow-hidden">
                  <div className="bg-muted px-4 py-2 font-medium">Available Backups</div>
                  {backups && backups.length > 0 ? (
                    <div className="divide-y">
                      {backups.map((backup: any) => (
                        <div key={backup.id} className="px-4 py-3 flex justify-between items-center">
                          <div>
                            <div className="font-medium">{new Date(backup.created_at).toLocaleString()}</div>
                            <div className="text-sm text-muted-foreground">{backup.id}</div>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedBackupId(backup.id);
                              setIsRestoreConfirmOpen(true);
                            }}
                          >
                            Restore
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="px-4 py-3 text-center text-muted-foreground">
                      No backups available
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsBackupsDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Restore Backup Confirmation */}
      <AlertDialog open={isRestoreConfirmOpen} onOpenChange={setIsRestoreConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore Backup</AlertDialogTitle>
            <AlertDialogDescription>
              This will restore the database from the selected backup.
              Current data will be replaced. Are you sure you want to continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setSelectedBackupId(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleRestoreBackup}
              className="bg-amber-500 hover:bg-amber-600"
            >
              {loading ? <Spinner className="mr-2" size="sm" /> : <Database className="mr-2 h-4 w-4" />}
              Restore Backup
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
} 