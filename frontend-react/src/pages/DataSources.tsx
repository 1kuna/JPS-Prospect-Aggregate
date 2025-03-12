import { useEffect, useState, useRef, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { formatDate } from '@/lib/utils';
import {
  PageLayout,
  PageSkeleton,
  DataTable,
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
const selectDeleteDataSource = (state: any) => state.deleteDataSource;

export default function DataSources() {
  // Use individual selectors to prevent unnecessary re-renders
  const dataSources = useStore(selectDataSources);
  const loading = useStore(selectDataSourcesLoading);
  const errors = useStore(selectDataSourcesErrors);
  const fetchDataSources = useStore(selectFetchDataSources);
  const createDataSource = useStore(selectCreateDataSource);
  const updateDataSource = useStore(selectUpdateDataSource);
  const deleteDataSource = useStore(selectDeleteDataSource);

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingDataSource, setEditingDataSource] = useState<DataSource | null>(null);
  const isMounted = useRef(false);

  useEffect(() => {
    // Only fetch data if this is the first time the component is mounted
    if (!isMounted.current) {
      fetchDataSources();
      isMounted.current = true;
    }
  }, []); // Empty dependency array to run only once on mount

  // Memoize event handlers
  const handleFormSubmit = useCallback((data: any) => {
    if (editingDataSource) {
      updateDataSource(editingDataSource.id.toString(), data).then(() => {
        setIsDialogOpen(false);
        setEditingDataSource(null);
        fetchDataSources();
      });
    } else {
      createDataSource(data).then(() => {
        setIsDialogOpen(false);
        fetchDataSources();
      });
    }
  }, [createDataSource, updateDataSource, fetchDataSources, editingDataSource]);

  const handleEdit = useCallback((dataSource: DataSource) => {
    setEditingDataSource(dataSource);
    setIsDialogOpen(true);
  }, []);

  const handleDelete = useCallback((id: string) => {
    if (window.confirm('Are you sure you want to delete this data source?')) {
      deleteDataSource(id).then(() => {
        fetchDataSources();
      });
    }
  }, [deleteDataSource, fetchDataSources]);

  const handleDialogClose = useCallback(() => {
    setIsDialogOpen(false);
    setEditingDataSource(null);
  }, []);

  const handleRefresh = () => {
    fetchDataSources();
  };

  // If loading and no data, show skeleton
  if (loading && dataSources.length === 0) {
    return <PageSkeleton cardCount={1} />;
  }

  // Define table columns with proper typing
  const columns = [
    { header: 'Name', accessor: 'name' as keyof DataSource },
    { 
      header: 'URL', 
      accessor: (dataSource: DataSource) => (
        <div className="max-w-[300px] truncate">
          <a 
            href={dataSource.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline"
          >
            {dataSource.url}
          </a>
        </div>
      )
    },
    { 
      header: 'Status', 
      accessor: (dataSource: DataSource) => (
        <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
          ${dataSource.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}
        >
          {dataSource.status || 'Unknown'}
        </div>
      )
    },
    { header: 'Proposals', accessor: 'proposalCount' as keyof DataSource },
    { 
      header: 'Last Scraped', 
      accessor: (dataSource: DataSource) => dataSource.lastScraped ? formatDate(dataSource.lastScraped) : 'Never'
    },
    { 
      header: 'Actions', 
      accessor: (dataSource: DataSource) => (
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleEdit(dataSource)}
          >
            Edit
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => handleDelete(dataSource.id.toString())}
          >
            Delete
          </Button>
        </div>
      )
    },
  ];

  // Create the add data source button
  const addDataSourceButton = (
    <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
      <DialogTrigger asChild>
        <Button onClick={() => setEditingDataSource(null)}>
          Add Data Source
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {editingDataSource ? 'Edit Data Source' : 'Add Data Source'}
          </DialogTitle>
        </DialogHeader>
        <DataSourceForm
          initialData={editingDataSource || undefined}
          onSubmit={handleFormSubmit}
          onCancel={handleDialogClose}
        />
      </DialogContent>
    </Dialog>
  );

  return (
    <PageLayout
      title="Data Sources"
      onRefresh={handleRefresh}
      isLoading={loading}
      error={errors}
      actions={addDataSourceButton}
    >
      {/* No data state */}
      {!loading && dataSources.length === 0 && (
        <Alert className="mb-6">
          <AlertTitle>No data sources available</AlertTitle>
          <AlertDescription>
            Click the "Add Data Source" button to create your first data source.
          </AlertDescription>
        </Alert>
      )}

      {/* Data table */}
      {dataSources.length > 0 && (
        <DataTable
          title="Data Sources"
          description="Manage your data sources for proposal aggregation"
          data={dataSources}
          columns={columns}
          keyField="id"
          emptyMessage={{
            title: 'No data sources found',
            description: 'There are currently no data sources in the system.',
          }}
        />
      )}
    </PageLayout>
  );
} 