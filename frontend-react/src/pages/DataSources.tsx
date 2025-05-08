import { useMemo } from 'react';
import { DataPageLayout } from '@/components/layout';
import { DataTable, Column } from '@/components/data-display';
import { useListDataSources, useDeleteDataSource } from '@/hooks/api/useDataSources';
import { DataSource } from '@/types';
import { Button } from '@/components/ui';

export default function DataSources() {
  const {
    data,
    isLoading,
    isError,
    error,
    refetch
  } = useListDataSources();

  const deleteMutation = useDeleteDataSource();

  const handleDelete = async (id: DataSource['id']) => {
    try {
      await deleteMutation.mutateAsync(id);
    } catch (err) {
      console.error('Failed to delete data source:', err);
    }
  };

  const columns: Column<DataSource>[] = useMemo(() => [
    {
      header: 'Name',
      accessorKey: 'name',
    },
    {
      header: 'Type',
      accessorKey: 'type',
    },
    {
      header: 'Status',
      accessorKey: 'status',
    },
    {
      header: 'Actions',
      cell: ({ row }: { row: DataSource }) => (
        <div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => alert('Edit form placeholder')}
          >
            Edit
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => handleDelete(row.id)}
            disabled={deleteMutation.isLoading && deleteMutation.variables === row.id}
          >
            {deleteMutation.isLoading && deleteMutation.variables === row.id ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      ),
    },
  ], [deleteMutation.isLoading, deleteMutation.variables, handleDelete]);

  const pageError = isError ? (error as Error) : null;

  return (
    <DataPageLayout
      title="Data Sources"
      data={data ?? []}
      loading={isLoading}
      error={pageError}
      onRefresh={refetch}
    >
      <>
        <DataTable
          data={data ?? []}
          columns={columns}
          isLoading={isLoading}
        />
      </>
    </DataPageLayout>
  );
} 