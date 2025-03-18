import { useEffect, useState, useCallback, memo } from 'react';
import { formatDate } from '@/lib/utils';
import { useToast, useDataSourcesSelectors } from '@/hooks';
import {
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Spinner,
} from '@/components/ui';
import { DataPageLayout } from '@/components/layout';
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
  last_checked?: string; // API response format
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
const statusCheckIntervals: Record<number, NodeJS.Timeout> = {};

// Memoized PullButton component to prevent unnecessary rerenders
const PullButton = memo(({ 
  dataSource, 
  onPull 
}: { 
  dataSource: DataSource; 
  onPull: (dataSource: DataSource) => void;
}) => {
  // Get the pulling state from the store
  const pullingProgress = useStore(state => state.pullingProgress);
  const isPulling = pullingProgress[dataSource.id] || false;
  
  const handleClick = useCallback(() => {
    if (!isPulling) {
      onPull(dataSource);
    }
  }, [dataSource, isPulling, onPull]);
  
  return (
    <Button 
      variant="outline" 
      size="sm"
      onClick={handleClick}
      disabled={isPulling}
      className="min-w-[100px] relative transition-all duration-300 ease-in-out"
    >
      <span className="flex items-center justify-center w-full">
        {isPulling && <Spinner className="mr-2 h-4 w-4" />}
        {isPulling ? 'Pulling...' : 'Pull Source'}
      </span>
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

// Define data sources page component
export default function DataSources() {
  // Use the custom hook for data fetching and state management
  const { data: dataSources, loading, errors, refresh } = useStoreData({
    dataSelector: selectDataSources,
    loadingSelector: selectDataSourcesLoading,
    errorSelector: selectDataSourcesErrors,
    fetchAction: selectFetchDataSources
  });
  
  // Get additional actions from the store
  const createDataSource = useStore(selectCreateDataSource);
  const updateDataSource = useStore(selectUpdateDataSource);
  const pullDataSource = useStore(selectPullDataSource);
  const getScraperStatus = useStore(selectGetScraperStatus);
  const { toast } = useToast();
  
  // Local state
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingDataSource, setEditingDataSource] = useState<DataSource | null>(null);

  // Clear intervals on component unmount
  useEffect(() => {
    return () => {
      // Clean up any existing intervals when the component unmounts
      Object.values(statusCheckIntervals).forEach(interval => {
        clearInterval(interval);
      });
    };
  }, []);

  // Handle data source creation
  const handleCreateDataSource = async (data: any) => {
    try {
      await createDataSource(data);
      setIsDialogOpen(false);
      toast({
        title: "Success",
        description: "Data source created successfully",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to create data source",
        variant: "destructive",
      });
    }
  };

  // Handle data source update
  const handleUpdateDataSource = async (data: any) => {
    try {
      await updateDataSource({ id: editingDataSource?.id, ...data });
      setIsDialogOpen(false);
      setEditingDataSource(null);
      toast({
        title: "Success",
        description: "Data source updated successfully",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to update data source",
        variant: "destructive",
      });
    }
  };

  // Handle edit button click
  const handleEditDataSource = useCallback((dataSource: DataSource) => {
    setEditingDataSource(dataSource);
    setIsDialogOpen(true);
  }, []);

  // Handle dialog close - reset editing state
  const handleDialogOpenChange = useCallback((open: boolean) => {
    setIsDialogOpen(open);
    if (!open) {
      setEditingDataSource(null);
    }
  }, []);

  // Fetch scraper status periodically while pulling
  const createStatusChecker = useCallback((sourceId: number, sourceName: string) => {
    // Clear any existing interval for this source
    if (statusCheckIntervals[sourceId]) {
      clearInterval(statusCheckIntervals[sourceId]);
    }
    
    // Set up new status checking interval
    const statusInterval = setInterval(async () => {
      try {
        const response: ScraperStatusResponse = await getScraperStatus(sourceId);
        console.log('Status update for source:', sourceId, response);
        
        if (response.status === 'completed' || response.status === 'failed') {
          // Clear the interval when the task is done
          clearInterval(statusCheckIntervals[sourceId]);
          delete statusCheckIntervals[sourceId];
          
          // Update UI based on status
          if (response.status === 'completed') {
            toast({
              title: "Task completed",
              description: `Data source "${sourceName}" pull completed successfully`,
            });
          } else {
            toast({
              title: "Task failed",
              description: response.message || `Failed to pull data from "${sourceName}"`,
              variant: "destructive",
            });
          }
          
          // Refresh data sources list
          refresh();
        }
      } catch (error) {
        console.error('Error checking status:', error);
      }
    }, 2000); // Check every 2 seconds
    
    // Store the interval so we can clear it later
    statusCheckIntervals[sourceId] = statusInterval;
  }, [getScraperStatus, toast, refresh]);

  // Handle pull button click
  const handlePullDataSource = useCallback(async (dataSource: DataSource) => {
    try {
      // Update UI to show pulling state for this source
      console.log('Pulling data from source:', dataSource.id);
      
      // Call the API to start the pull
      const response = await pullDataSource(dataSource.id);
      console.log('Pull response:', response);
      
      toast({
        title: "Pull initiated",
        description: `Started pulling data from "${dataSource.name}"`,
      });
      
      // Start checking status periodically
      createStatusChecker(dataSource.id, dataSource.name);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || `Failed to pull data from "${dataSource.name}"`,
        variant: "destructive",
      });
    }
  }, [pullDataSource, toast, createStatusChecker]);

  // Define table columns
  const columns: Column<DataSource>[] = [
    {
      header: 'ID',
      accessorKey: 'id',
    },
    {
      header: 'Name',
      accessorKey: 'name',
    },
    {
      header: 'URL',
      accessorKey: 'url',
      cell: (dataSource) => {
        const url = dataSource.url;
        // Truncate long URLs for display
        const displayUrl = url.length > 30 ? url.substring(0, 30) + '...' : url;
        return (
          <a 
            href={url.startsWith('http') ? url : `https://${url}`} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline"
          >
            {displayUrl}
          </a>
        );
      },
    },
    {
      header: 'Description',
      accessorKey: 'description',
      cell: (dataSource) => dataSource.description || 'N/A',
    },
    {
      header: 'Last Checked',
      accessorKey: (row: DataSource) => {
        const date = row.lastChecked || row.last_checked;
        return date ? formatDate(date) : 'Never';
      }
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (dataSource) => dataSource.status || 'Unknown',
    },
    {
      header: 'Actions',
      accessorKey: 'id', // Use id as the accessor
      cell: (dataSource) => (
        <ActionCell 
          row={dataSource} 
          onPull={handlePullDataSource} 
          onEdit={handleEditDataSource}
        />
      ),
    },
  ];

  // The Dialog for creating/editing data sources
  const dataSourceDialog = (
    <Dialog open={isDialogOpen} onOpenChange={handleDialogOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>
            {editingDataSource ? 'Edit Data Source' : 'Create Data Source'}
          </DialogTitle>
        </DialogHeader>
        <DataSourceForm
          initialData={editingDataSource || undefined}
          onSubmit={editingDataSource ? handleUpdateDataSource : handleCreateDataSource}
          onCancel={() => setIsDialogOpen(false)}
        />
      </DialogContent>
    </Dialog>
  );

  return (
    <DataPageLayout
      title="Data Sources"
      data={dataSources}
      loading={loading}
      error={errors}
      onRefresh={refresh}
      emptyMessage="No data sources configured"
      renderHeader={() => (
        <>
          <p className="text-muted-foreground">
            {dataSources ? `${dataSources.length} data sources configured` : ''}
          </p>
          <div className="flex gap-2">
            <Button onClick={refresh}>Refresh</Button>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button>Add Data Source</Button>
              </DialogTrigger>
            </Dialog>
          </div>
        </>
      )}
      renderContent={(data) => (
        <>
          <DataTableComponent
            key="data-sources-table"
            data={data as DataSource[]}
            columns={columns}
            emptyMessage="No data sources configured"
            isLoading={loading}
          />
          {dataSourceDialog}
        </>
      )}
    />
  );
} 