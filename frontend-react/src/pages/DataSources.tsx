import { useEffect, useState, useRef, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDate } from '@/lib/utils';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  getFilteredRowModel,
  ColumnFiltersState,
} from '@tanstack/react-table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
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

  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
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

  // Define table columns
  const columns: ColumnDef<DataSource>[] = [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => <div className="font-medium">{row.getValue('name')}</div>,
    },
    {
      accessorKey: 'url',
      header: 'URL',
      cell: ({ row }) => (
        <div className="max-w-[300px] truncate">
          <a 
            href={row.getValue('url')} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline"
          >
            {row.getValue('url')}
          </a>
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const status = row.getValue('status') as string;
        return (
          <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
            ${status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}
          >
            {status || 'Unknown'}
          </div>
        );
      },
    },
    {
      accessorKey: 'proposalCount',
      header: 'Proposals',
      cell: ({ row }) => row.getValue('proposalCount') || 0,
    },
    {
      accessorKey: 'lastScraped',
      header: 'Last Scraped',
      cell: ({ row }) => {
        const date = row.getValue('lastScraped');
        return date ? formatDate(date as string) : 'Never';
      },
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const dataSource = row.original;
        return (
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
        );
      },
    },
  ];

  // Initialize the table
  const table = useReactTable({
    data: dataSources,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    state: {
      sorting,
      columnFilters,
    },
  });

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

  // Show error state
  if (errors) {
    return (
      <div className="space-y-4">
        <Card className="border-red-300">
          <CardHeader>
            <CardTitle className="text-red-500">Error Loading Data Sources</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{errors.message && errors.message}</p>
            <Button 
              onClick={() => fetchDataSources()} 
              className="mt-4"
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Data Sources</h1>
        <div className="flex items-center gap-4">
          <Button onClick={() => fetchDataSources()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
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
        </div>
      </div>

      {/* Loading state */}
      {loading && dataSources.length === 0 && (
        <Card>
          <CardHeader>
            <Skeleton className="h-8 w-1/4 mb-2" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          </CardContent>
        </Card>
      )}

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
        <Card>
          <CardContent className="pt-6">
            <div className="rounded-md border">
              <table className="w-full">
                <thead>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <tr key={headerGroup.id} className="border-b bg-muted/50">
                      {headerGroup.headers.map((header) => (
                        <th
                          key={header.id}
                          className="h-12 px-4 text-left align-middle font-medium text-muted-foreground"
                        >
                          {header.isPlaceholder
                            ? null
                            : flexRender(
                                header.column.columnDef.header,
                                header.getContext()
                              )}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="border-b">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="p-4 align-middle">
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext()
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-end space-x-2 py-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              >
                Next
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
} 