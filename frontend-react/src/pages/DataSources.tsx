import { useEffect, useState, useCallback, memo } from 'react';
import { useStore } from '@/store/useStore';
import { formatDate } from '@/lib/utils';
import { useToast } from '@/hooks';
import {
  PageLayout,
  Alert,
  AlertTitle,
  AlertDescription,
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Spinner,
} from '@/components';
import { DataSourceForm } from '@/components/DataSourceForm';
import { DataTable as DataTableComponent } from '@/components/data-display/DataTable';
import type { Column } from '@/components/data-display/DataTable';

// Define the data source type
interface DataSource {
  id: number;
  name: string;
  url: string;
  description?: string;
  lastScraped?: string;
  lastChecked?: string;
  status?: string;
  proposalCount?: number;
}

// Define the scraper status response type
interface ScraperStatusResponse {
  status: string;
  data?: {
    status: string;
    message?: string;
    source_id: number;
    source_name: string;
    subtask_id?: string;
  };
  message?: string;
}

// Create stable selectors outside the component
const selectDataSources = (state: any) => state.dataSources;
const selectDataSourcesLoading = (state: any) => state.loading.dataSources;
const selectDataSourcesErrors = (state: any) => state.errors.dataSources;
const selectFetchDataSources = (state: any) => state.fetchDataSources;
const selectCreateDataSource = (state: any) => state.createDataSource;
const selectUpdateDataSource = (state: any) => state.updateDataSource;
const selectPullDataSource = (state: any) => state.pullDataSource;
const selectGetScraperStatus = (state: any) => state.getScraperStatus;

// Global state for tracking which sources are being pulled
// This ensures the state persists even if the component rerenders
const pullingSourceIds: Record<number, boolean> = {};
const statusCheckIntervals: Record<number, NodeJS.Timeout> = {};

// Memoized PullButton component to prevent unnecessary rerenders
const PullButton = memo(({ 
  dataSource, 
  onPull 
}: { 
  dataSource: DataSource; 
  onPull: (dataSource: DataSource) => void;
}) => {
  // Use local state that's initialized from the global state
  const [isPulling, setIsPulling] = useState(!!pullingSourceIds[dataSource.id]);
  
  // Update local state when global state changes
  useEffect(() => {
    const checkPullingState = () => {
      const newIsPulling = !!pullingSourceIds[dataSource.id];
      if (newIsPulling !== isPulling) {
        setIsPulling(newIsPulling);
      }
    };
    
    // Check immediately
    checkPullingState();
    
    // Set up an interval to check regularly
    const interval = setInterval(checkPullingState, 500);
    
    return () => clearInterval(interval);
  }, [dataSource.id, isPulling]);
  
  const handleClick = useCallback(() => {
    // Update local state immediately
    setIsPulling(true);
    // Call the parent handler
    onPull(dataSource);
  }, [dataSource, onPull]);
  
  return (
    <Button 
      variant="outline" 
      size="sm"
      onClick={handleClick}
      disabled={isPulling}
      className="min-w-[100px] transition-all duration-300 ease-in-out"
    >
      {isPulling ? (
        <span className="flex items-center justify-center w-full">
          <Spinner className="mr-2 h-4 w-4" />
          Pulling...
        </span>
      ) : (
        'Pull Source'
      )}
    </Button>
  );
});

PullButton.displayName = 'PullButton';

// Memoized ActionCell component to prevent unnecessary rerenders
const ActionCell = memo(({ 
  row, 
  onPull, 
  onEdit 
}: { 
  row: DataSource; 
  onPull: (dataSource: DataSource) => void;
  onEdit: (dataSource: DataSource) => void;
}) => {
  return (
    <div className="flex space-x-2">
      <PullButton dataSource={row} onPull={onPull} />
      <Button 
        variant="outline" 
        size="sm"
        onClick={() => onEdit(row)}
      >
        Edit
      </Button>
    </div>
  );
});

ActionCell.displayName = 'ActionCell';

export default function DataSources() {
  // Use store selectors
  const dataSources = useStore(selectDataSources);
  const loading = useStore(selectDataSourcesLoading);
  const errors = useStore(selectDataSourcesErrors);
  const fetchDataSources = useStore(selectFetchDataSources);
  const createDataSource = useStore(selectCreateDataSource);
  const updateDataSource = useStore(selectUpdateDataSource);
  const pullDataSource = useStore(selectPullDataSource);
  const getScraperStatus = useStore(selectGetScraperStatus);
  const { toast } = useToast();

  // Local state
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingDataSource, setEditingDataSource] = useState<DataSource | null>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  // Fetch data sources on component mount
  useEffect(() => {
    if (isInitialLoad) {
      fetchDataSources()
        .then(() => setIsInitialLoad(false))
        .catch(() => setIsInitialLoad(false));
    }
  }, [fetchDataSources, isInitialLoad]);

  // Function to start polling for a data source
  const startPolling = useCallback((dataSource: DataSource) => {
    const id = dataSource.id;
    
    // Clear any existing interval
    if (statusCheckIntervals[id]) {
      clearInterval(statusCheckIntervals[id]);
    }
    
    // Set up a new interval
    let checkCount = 0;
    let lastStatus = "";
    let subtaskId = ""; // Track the subtask ID
    
    console.log(`[DataSources] Setting up polling for source ${id}`);
    
    statusCheckIntervals[id] = setInterval(async () => {
      try {
        checkCount++;
        console.log(`[DataSources] Checking status for source ${id} (check #${checkCount})`);
        
        const statusResponse: ScraperStatusResponse = await getScraperStatus(String(id));
        console.log(`[DataSources] Status response for source ${id}:`, statusResponse);
        
        // Extract the actual status from the response
        // The API returns nested status information
        const actualStatus = statusResponse.data?.status || statusResponse.status;
        const statusMessage = statusResponse.data?.message || statusResponse.message || "";
        
        // Check if we have a subtask ID
        if (statusResponse.data?.subtask_id && !subtaskId) {
          subtaskId = statusResponse.data.subtask_id;
          console.log(`[DataSources] Found subtask ID: ${subtaskId} for source ${id}`);
        }
        
        console.log(`[DataSources] Actual status for source ${id}: ${actualStatus}, message: ${statusMessage}`);
        
        // If the status hasn't changed, don't do anything
        if (actualStatus === lastStatus && checkCount > 1) {
          console.log(`[DataSources] Status hasn't changed for source ${id}, continuing to poll`);
          return;
        }
        
        // Update the last status
        lastStatus = actualStatus;
        
        // If the scraper is no longer running, update UI
        if (actualStatus !== "running" && actualStatus !== "pending") {
          console.log(`[DataSources] Source ${id} is no longer running (${actualStatus}), updating state`);
          
          // Clear the interval
          clearInterval(statusCheckIntervals[id]);
          delete statusCheckIntervals[id];
          
          // Update the global state
          pullingSourceIds[id] = false;
          
          // Show appropriate toast
          const sourceName = dataSource.name || `Source #${id}`;
          
          if (actualStatus === "completed" || actualStatus === "success" || actualStatus === "working") {
            console.log(`[DataSources] Source ${id} completed successfully, showing toast`);
            toast({
              title: "Success!",
              description: `Successfully pulled data from ${sourceName}`,
              variant: "success",
              duration: 10000
            });
            
            // Refresh data sources
            fetchDataSources().catch(() => {});
          } else {
            console.log(`[DataSources] Source ${id} failed (${actualStatus}), showing error toast`);
            toast({
              title: "Error pulling data",
              description: statusMessage || "An unknown error occurred",
              variant: "destructive",
              duration: 15000
            });
          }
        } else if (checkCount >= 150) {
          // After 5 minutes (150 checks at 2-second intervals), force stop polling
          console.log(`[DataSources] Source ${id} polling timeout after ${checkCount} checks`);
          
          // Clear the interval
          clearInterval(statusCheckIntervals[id]);
          delete statusCheckIntervals[id];
          
          // Update the global state
          pullingSourceIds[id] = false;
          
          // Show timeout toast
          toast({
            title: "Operation taking too long",
            description: `The operation for ${dataSource.name} is still running in the background, but we've stopped checking its status. You can check the status later by refreshing the page.`,
            variant: "default",
            duration: 15000
          });
        }
      } catch (error) {
        console.error(`[DataSources] Error checking status for source ${id}:`, error);
        
        // If we've been polling for a while and still getting errors, stop polling
        if (checkCount > 10) {
          console.log(`[DataSources] Too many errors checking status for source ${id}, stopping polling`);
          clearInterval(statusCheckIntervals[id]);
          delete statusCheckIntervals[id];
          
          // Update the global state
          pullingSourceIds[id] = false;
          
          // Show error toast
          toast({
            title: "Error checking status",
            description: `Failed to check status for ${dataSource.name || `Source #${id}`}`,
            variant: "destructive",
            duration: 10000
          });
        }
      }
    }, 2000); // Poll every 2 seconds
  }, [getScraperStatus, toast, fetchDataSources]);

  // Handle pulling data from a source
  const handlePullDataSource = useCallback(async (dataSource: DataSource) => {
    const id = dataSource.id;
    
    // Prevent pulling if already in progress
    if (pullingSourceIds[id]) {
      console.log(`[DataSources] Source ${id} is already being pulled, ignoring request`);
      return;
    }
    
    console.log(`[DataSources] Starting pull for source ${id}`);
    
    // Update the global state immediately
    pullingSourceIds[id] = true;
    
    // Show toast notification
    console.log(`[DataSources] Showing toast for source ${id}`);
    toast({
      title: "Pulling data",
      description: `Starting to pull data from ${dataSource.name}. This may take a while...`,
      variant: "default",
      duration: 30000
    });
    
    try {
      // Call the API
      console.log(`[DataSources] Calling pullDataSource API for source ${id}`);
      const response = await pullDataSource(String(id));
      console.log(`[DataSources] API call successful for source ${id}:`, response);
      
      // Start polling for status updates
      startPolling(dataSource);
    } catch (error) {
      // Show error toast
      console.error(`[DataSources] Error pulling source ${id}:`, error);
      toast({
        title: "Error pulling data",
        description: `An unexpected error occurred: ${(error as Error).message}`,
        variant: "destructive",
        duration: 15000
      });
      
      // Reset the global state
      pullingSourceIds[id] = false;
    }
  }, [pullDataSource, toast, startPolling]);

  // Clean up intervals when component unmounts
  useEffect(() => {
    return () => {
      console.log('[DataSources] Cleaning up all intervals');
      Object.keys(statusCheckIntervals).forEach(id => {
        clearInterval(statusCheckIntervals[Number(id)]);
        delete statusCheckIntervals[Number(id)];
      });
    };
  }, []);

  const handleRefresh = useCallback(() => {
    fetchDataSources().catch(() => {});
  }, [fetchDataSources]);

  const handleCreateDataSource = useCallback(async (data: Omit<DataSource, 'id'>) => {
    try {
      await createDataSource(data);
      setIsDialogOpen(false);
    } catch (error) {
      console.error('Failed to create data source:', error);
    }
  }, [createDataSource]);

  const handleUpdateDataSource = useCallback(async (data: DataSource) => {
    try {
      await updateDataSource(String(data.id), data);
      setIsDialogOpen(false);
      setEditingDataSource(null);
    } catch (error) {
      console.error('Failed to update data source:', error);
    }
  }, [updateDataSource]);

  const handleEditDataSource = useCallback((dataSource: DataSource) => {
    setEditingDataSource(dataSource);
    setIsDialogOpen(true);
  }, []);

  const handleCloseDialog = useCallback(() => {
    setIsDialogOpen(false);
    setEditingDataSource(null);
  }, []);

  // Show loading state during initial load
  if ((isInitialLoad || loading) && !dataSources.length) {
    return (
      <PageLayout title="Data Sources" isLoading={true}>
        <div>Loading data sources...</div>
      </PageLayout>
    );
  }

  // Error state
  if (errors && !isInitialLoad && !dataSources.length) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
        <Alert variant="destructive">
          <AlertTitle>Error loading data sources</AlertTitle>
          <AlertDescription>{errors.message}</AlertDescription>
        </Alert>
        <Button onClick={handleRefresh}>Retry</Button>
      </div>
    );
  }

  // Define table columns
  const columns: Column<DataSource>[] = [
    {
      header: 'Name',
      accessorKey: 'name',
    },
    {
      header: 'URL',
      accessorKey: 'url',
    },
    {
      header: 'Status',
      accessorKey: 'status',
    },
    {
      header: 'Last Checked',
      accessorKey: (row: DataSource) => row.lastChecked ? formatDate(row.lastChecked) : 'Never',
    },
    {
      header: 'Proposals',
      accessorKey: (row: DataSource) => row.proposalCount?.toString() || '0',
    },
    {
      header: 'Actions',
      accessorKey: 'id',
      cell: (row: DataSource) => (
        <ActionCell 
          row={row} 
          onPull={handlePullDataSource} 
          onEdit={handleEditDataSource} 
        />
      ),
    },
  ];

  return (
    <PageLayout title="Data Sources">
      <div className="space-y-4 min-h-[500px] bg-background transition-all duration-300">
        <div className="flex justify-between items-center">
          <p className="text-muted-foreground">
            {dataSources.length} data sources configured
          </p>
          <div className="flex gap-2">
            <Button onClick={handleRefresh}>Refresh</Button>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button>Add Data Source</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>
                    {editingDataSource ? 'Edit Data Source' : 'Add Data Source'}
                  </DialogTitle>
                </DialogHeader>
                <DataSourceForm
                  initialData={editingDataSource ? {
                    id: editingDataSource.id,
                    name: editingDataSource.name,
                    url: editingDataSource.url,
                    description: editingDataSource.description
                  } : undefined}
                  onSubmit={(data) => {
                    if (editingDataSource) {
                      handleUpdateDataSource({
                        ...data,
                        id: editingDataSource.id
                      });
                    } else {
                      handleCreateDataSource(data);
                    }
                  }}
                  onCancel={handleCloseDialog}
                />
              </DialogContent>
            </Dialog>
          </div>
        </div>

        <DataTableComponent
          key="data-sources-table"
          data={dataSources}
          columns={columns}
          emptyMessage="No data sources configured"
          isLoading={loading || isInitialLoad}
        />
      </div>
    </PageLayout>
  );
} 