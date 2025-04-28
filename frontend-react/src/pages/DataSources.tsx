import { useMemo } from 'react';
import { DataPageLayout } from '@/components/layout';
import { DataTable } from '@/components/data-display/DataTable';
import { useDataSources } from '@/hooks';

export default function DataSources() {
  const { data, isLoading, error, refetch } = useDataSources.useList();
  const { mutate: deleteDataSource } = useDataSources.useDelete();

  const handleDelete = async (id: number) => {
    deleteDataSource(id, {
      onSuccess: () => {
        refetch();
      },
      onError: () => {
        console.error('Failed to delete data source');
      }
    });
  };

  const columns = useMemo(() => [
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
      cell: ({ row }: { row: any }) => (
        <div>
          <button onClick={() => alert('Edit form disabled')}>Edit</button>
          <button onClick={() => handleDelete(row.original.id)}>Delete</button>
        </div>
      ),
    },
  ], [deleteDataSource]);

  return (
    <DataPageLayout
      title="Data Sources"
      data={data}
      loading={isLoading}
      error={error}
      onRefresh={refetch}
      renderContent={(pageData) => (
        <>
          <DataTable
            data={pageData}
            columns={columns as any[]}
            isLoading={isLoading}
          />
        </>
      )}
    />
  );
} 