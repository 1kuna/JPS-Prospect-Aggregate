import { useEffect, useState, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { formatDate } from '@/lib/utils';
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

export default function DataSources() {
  // Use individual selectors to prevent unnecessary re-renders
  const dataSources = useStore(selectDataSources);
  const loading = useStore(selectDataSourcesLoading);
  const errors = useStore(selectDataSourcesErrors);
  const fetchDataSources = useStore(selectFetchDataSources);
  const createDataSource = useStore(selectCreateDataSource);
  const updateDataSource = useStore(selectUpdateDataSource);

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