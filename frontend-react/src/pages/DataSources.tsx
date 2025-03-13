import { useEffect, useState, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { formatDate } from '@/lib/utils';
import { useToast } from '@/hooks';
import { useGlobalToast } from '@/context/ToastContext';
import { useToastContainer } from '@/components/ui/ToastContainer';
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

// Create stable selectors outside the component
const selectDataSources = (state: any) => state.dataSources;
const selectDataSourcesLoading = (state: any) => state.loading.dataSources;
const selectDataSourcesErrors = (state: any) => state.errors.dataSources;
const selectFetchDataSources = (state: any) => state.fetchDataSources;
const selectCreateDataSource = (state: any) => state.createDataSource;
const selectUpdateDataSource = (state: any) => state.updateDataSource;
const selectPullDataSource = (state: any) => state.pullDataSource;
const selectGetScraperStatus = (state: any) => state.getScraperStatus;
const selectPullingProgress = (state: any) => state.pullingProgress;
const selectSetPullingProgress = (state: any) => state.setPullingProgress;

export default function DataSources() {
  // Use individual selectors to prevent unnecessary re-renders
  const dataSources = useStore(selectDataSources);
  const loading = useStore(selectDataSourcesLoading);
  const errors = useStore(selectDataSourcesErrors);
  const fetchDataSources = useStore(selectFetchDataSources);
  const createDataSource = useStore(selectCreateDataSource);
  const updateDataSource = useStore(selectUpdateDataSource);
  const pullDataSource = useStore(selectPullDataSource);
  const getScraperStatus = useStore(selectGetScraperStatus);
  const pullingProgress = useStore(selectPullingProgress);
  const setPullingProgress = useStore(selectSetPullingProgress);
  const { toast } = useToast();
  const { addToast } = useGlobalToast();
  const { addToast: addSimpleToast } = useToastContainer();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingDataSource, setEditingDataSource] = useState<DataSource | null>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  // Fetch data sources on component mount - ALWAYS fetch fresh data
  useEffect(() => {
    console.log('DataSources component mounted, fetching data sources...');
    
    // Force a fresh fetch of data sources
    fetchDataSources()
      .then(() => {
        console.log('Data sources fetched successfully in component');
        setIsInitialLoad(false);
      })
      .catch((error: Error) => {
        console.error('Error fetching data sources in component:', error);
        setIsInitialLoad(false);
      });
      
    // Cleanup function
    return () => {
      console.log('DataSources component unmounting');
    };
  }, [fetchDataSources]);

  // Check the status of all data sources with pullingProgress set to true
  useEffect(() => {
    if (!dataSources.length) return;

    // Get all data sources that are currently being pulled
    const runningDataSources = dataSources.filter((ds: DataSource) => pullingProgress[ds.id]);
    
    if (runningDataSources.length === 0) return;
    
    console.log('Found running data sources:', runningDataSources);
    
    // Set up intervals to check the status of each running data source
    const intervals: NodeJS.Timeout[] = [];
    
    // Track start times for each running scraper
    const startTimes: Record<number, number> = {};
    const MAX_SCRAPER_RUNTIME_MS = 3 * 60 * 1000; // 3 minutes maximum runtime (reduced from 5)
    
    runningDataSources.forEach((dataSource: DataSource) => {
      // Initialize start time for this scraper
      startTimes[dataSource.id] = Date.now();
      
      const interval = setInterval(async () => {
        try {
          // Check if we've exceeded the maximum runtime
          const elapsedTime = Date.now() - startTimes[dataSource.id];
          if (elapsedTime > MAX_SCRAPER_RUNTIME_MS) {
            clearInterval(interval);
            
            const timeoutMessage = `Scraper timed out after ${Math.floor(elapsedTime / 60000)} minutes. The operation may still be running in the background.`;
            
            // Show timeout error in toast
            toast({
              title: "Scraper Timeout",
              description: timeoutMessage,
              variant: "destructive",
              duration: 15000
            });
            
            // Refresh the data sources to show updated information
            await fetchDataSources();
            
            // Clear loading state in the global store
            setPullingProgress(dataSource.id, false);
            return;
          }
          
          const statusResult = await getScraperStatus(String(dataSource.id));
          console.log(`Status check for source ID ${dataSource.id}:`, statusResult);
          
          // If the scraper is no longer running, clear the interval and update UI
          if (statusResult.status !== "running") {
            clearInterval(interval);
            
            // Update UI based on final status
            if (statusResult.status === "success") {
              const successMessage = `Successfully pulled data from ${dataSource.name}`;
              
              toast({
                title: "Success!",
                description: successMessage,
                variant: "success",
                duration: 10000
              });
            } else {
              toast({
                title: "Error pulling data",
                description: statusResult.message,
                variant: "destructive",
                duration: 15000
              });
            }
            
            // Refresh the data sources to show updated information
            await fetchDataSources();
            
            // Clear loading state in the global store
            setPullingProgress(dataSource.id, false);
          }
        } catch (error) {
          console.error('Error checking scraper status:', error);
        }
      }, 1000); // Check every 1 second (reduced from 2 seconds)
      
      intervals.push(interval);
    });
    
    // Clean up intervals on unmount
    return () => {
      intervals.forEach(interval => clearInterval(interval));
    };
  }, [dataSources, pullingProgress, getScraperStatus, fetchDataSources, toast, setPullingProgress]);

  // Log state changes for debugging
  useEffect(() => {
    console.log('DataSources component state:', { 
      dataSources, 
      loading, 
      errors,
      isInitialLoad
    });
  }, [dataSources, loading, errors, isInitialLoad]);

  const handleRefresh = useCallback(() => {
    console.log('Manually refreshing data sources...');
    setIsInitialLoad(true);
    fetchDataSources()
      .then(() => {
        console.log('Data sources refreshed successfully');
        setIsInitialLoad(false);
      })
      .catch((error: Error) => {
        console.error('Error refreshing data sources:', error);
        setIsInitialLoad(false);
      });
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

  const handlePullDataSource = useCallback(async (dataSource: DataSource) => {
    try {
      // Set loading state for this specific data source in the global store
      setPullingProgress(dataSource.id, true);
      
      // Show toast notifications that we're starting to pull
      const startMessage = `Starting to pull data from ${dataSource.name}. This may take a while...`;
      
      // Global toast for persistent status
      addToast({
        title: "Pulling data",
        description: startMessage,
        variant: "default",
        duration: 0 // 0 means it won't auto-dismiss
      });
      
      // Simple toast for additional visibility
      addSimpleToast({
        title: "Pulling data",
        message: startMessage,
        type: 'info'
      });
      
      console.log(`Starting to pull data from source ID ${dataSource.id}: ${dataSource.name}`);
      
      // Call the API to pull the data source
      const result = await pullDataSource(String(dataSource.id));
      
      console.log(`Pull initiated for source ID ${dataSource.id}:`, result);
      
      // Set up a polling interval to check the status
      let statusCheckInterval: NodeJS.Timeout | null = setInterval(async () => {
        try {
          // Call our new status endpoint
          const statusResult = await getScraperStatus(String(dataSource.id));
          console.log(`Status check for source ID ${dataSource.id}:`, statusResult);
          
          // Update toast with current status
          addToast({
            title: `Status: ${statusResult.status}`,
            description: statusResult.message,
            variant: statusResult.status === "running" ? "default" : 
                     statusResult.status === "completed" ? "success" : "destructive",
            duration: statusResult.status === "running" ? 0 : 10000
          });
          
          // If the scraper is no longer running or has timed out, clear the interval and update UI
          if (statusResult.status !== "running") {
            if (statusCheckInterval) {
              clearInterval(statusCheckInterval);
              statusCheckInterval = null;
            }
            
            // Update UI based on final status
            if (statusResult.status === "completed") {
              const successMessage = `Successfully pulled data from ${dataSource.name}`;
              
              // Show success in other toasts
              toast({
                title: "Success!",
                description: successMessage,
                variant: "success",
                duration: 10000
              });
              
              addSimpleToast({
                title: "Success!",
                message: successMessage,
                type: 'success'
              });
            } else if (statusResult.status === "timeout") {
              // Show timeout message
              toast({
                title: "Scraper Timeout",
                description: statusResult.message,
                variant: "destructive",
                duration: 15000
              });
              
              addSimpleToast({
                title: "Scraper Timeout",
                message: statusResult.message,
                type: 'error',
                duration: 15000
              });
            } else {
              // Show error in other toasts
              toast({
                title: "Error pulling data",
                description: statusResult.message,
                variant: "destructive",
                duration: 15000
              });
              
              addSimpleToast({
                title: "Error pulling data",
                message: statusResult.message,
                type: 'error',
                duration: 15000
              });
            }
            
            // Refresh the data sources to show updated information
            await fetchDataSources();
            
            // Clear loading state in the global store
            setPullingProgress(dataSource.id, false);
          }
        } catch (error) {
          console.error('Error checking scraper status:', error);
        }
      }, 1000); // Check every 1 second
      
      // Clean up the interval if the component unmounts
      return () => {
        if (statusCheckInterval) {
          clearInterval(statusCheckInterval);
        }
      };
    } catch (error: any) {
      console.error('Failed to pull data source:', error);
      
      // Get a more detailed error message
      const errorMessage = error.response?.data?.message || error.message || "An unknown error occurred";
      
      // Show error in toasts
      toast({
        title: "Error pulling data",
        description: errorMessage,
        variant: "destructive",
        duration: 15000
      });
      
      addSimpleToast({
        title: "Error pulling data",
        message: errorMessage,
        type: 'error',
        duration: 15000
      });
      
      // Clear loading state in the global store
      setPullingProgress(dataSource.id, false);
    }
  }, [pullDataSource, getScraperStatus, fetchDataSources, toast, addToast, addSimpleToast, setPullingProgress]);

  const handleCloseDialog = useCallback(() => {
    setIsDialogOpen(false);
    setEditingDataSource(null);
  }, []);

  // Show loading state during initial load or when explicitly loading
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
        <div className="flex space-x-2">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => handlePullDataSource(row)}
            disabled={pullingProgress[row.id]}
          >
            {pullingProgress[row.id] ? (
              <span className="flex items-center">
                <Spinner className="mr-2 h-4 w-4" />
                Pulling...
              </span>
            ) : (
              'Pull Source'
            )}
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => handleEditDataSource(row)}
          >
            Edit
          </Button>
        </div>
      ),
    },
  ];

  return (
    <PageLayout title="Data Sources">
      <div className="space-y-4">
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
          data={dataSources}
          columns={columns}
          emptyMessage="No data sources configured"
          isLoading={loading || isInitialLoad}
        />
      </div>
    </PageLayout>
  );
} 