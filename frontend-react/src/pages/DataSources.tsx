import { useEffect, useState } from 'react';
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
  id: string;
  name: string;
  url: string;
  api_key?: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export default function DataSources() {
  const { 
    dataSources, 
    loading, 
    errors, 
    fetchDataSources,
    createDataSource,
    updateDataSource,
    deleteDataSource
  } = useStore(state => ({
    dataSources: state.dataSources,
    loading: state.loading.dataSources,
    errors: state.errors.dataSources,
    fetchDataSources: state.fetchDataSources,
    createDataSource: state.createDataSource,
    updateDataSource: state.updateDataSource,
    deleteDataSource: state.deleteDataSource
  }));

  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingDataSource, setEditingDataSource] = useState<DataSource | null>(null);

  useEffect(() => {
    // Fetch data on component mount
    fetchDataSources();
  }, [fetchDataSources]);

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
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => {
        const status = row.getValue('is_active') as boolean;
        return (
          <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
            ${status ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
          >
            {status ? 'Active' : 'Inactive'}
          </div>
        );
      },
    },
    {
      accessorKey: 'updated_at',
      header: 'Last Updated',
      cell: ({ row }) => formatDate(row.getValue('updated_at')),
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
              onClick={() => handleDelete(dataSource.id)}
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

  // Handle form submission
  const handleFormSubmit = (data: any) => {
    if (editingDataSource) {
      updateDataSource(editingDataSource.id, data).then(() => {
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
  };

  // Handle edit button click
  const handleEdit = (dataSource: DataSource) => {
    setEditingDataSource(dataSource);
    setIsDialogOpen(true);
  };

  // Handle delete button click
  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this data source?')) {
      deleteDataSource(id).then(() => {
        fetchDataSources();
      });
    }
  };

  // Handle dialog close
  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setEditingDataSource(null);
  };

  // Show error state
  if (errors) {
    return (
      <div className="space-y-4">
        <Card className="border-red-300">
          <CardHeader>
            <CardTitle className="text-red-500">Error Loading Data Sources</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{errors.message}</p>
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
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      )}

      {/* No data state */}
      {!loading && dataSources.length === 0 && (
        <Alert className="mb-6">
          <AlertTitle>No data sources available</AlertTitle>
          <AlertDescription>
            Click the "Add New Source" button to create a new data source.
          </AlertDescription>
        </Alert>
      )}

      {/* Data sources table */}
      {dataSources.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Data Sources</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  {table.getHeaderGroups().map((headerGroup) => (
                    <tr key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <th
                          key={header.id}
                          scope="col"
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          {header.isPlaceholder ? null : (
                            <div
                              {...{
                                className: header.column.getCanSort()
                                  ? 'cursor-pointer select-none'
                                  : '',
                                onClick: header.column.getToggleSortingHandler(),
                              }}
                            >
                              {flexRender(
                                header.column.columnDef.header,
                                header.getContext()
                              )}
                              {{
                                asc: ' 🔼',
                                desc: ' 🔽',
                              }[header.column.getIsSorted() as string] ?? null}
                            </div>
                          )}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id}>
                      {row.getVisibleCells().map((cell) => (
                        <td
                          key={cell.id}
                          className="px-6 py-4 whitespace-nowrap text-sm"
                        >
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
            <div className="flex items-center justify-between space-x-2 py-4">
              <div className="flex-1 text-sm text-muted-foreground">
                Showing {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} to{' '}
                {Math.min(
                  (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
                  table.getFilteredRowModel().rows.length
                )}{' '}
                of {table.getFilteredRowModel().rows.length} entries
              </div>
              <div className="space-x-2">
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
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
} 