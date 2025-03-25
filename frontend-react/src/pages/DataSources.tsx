import { useState } from 'react';
import { DataPageLayout } from '@/components/layout';
import { DataTable } from '@/components/ui/DataTable';
import { Button } from '@/components/ui/button';
import { DataSourceForm } from '@/components/forms';
import { useDataSources, usePullDataSource } from '@/hooks/api/useDataSources';
import { DataSource } from '@/types';
import { toast } from '@/hooks/use-toast';

export default function DataSources() {
  const [editingDataSource, setEditingDataSource] = useState<DataSource | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);

  const {
    data: dataSources,
    isLoading,
    error
  } = useDataSources.useGetAll();

  const { mutate: createDataSource, isLoading: isCreating } = useDataSources.useCreate();
  const { mutate: updateDataSource, isLoading: isUpdating } = useDataSources.useUpdate();
  const { mutate: deleteDataSource } = useDataSources.useDelete();
  const { mutate: pullDataSource } = usePullDataSource();

  const handleCreate = async (data: Omit<DataSource, 'id'>) => {
    try {
      await createDataSource(data);
      setIsFormOpen(false);
      toast.success({ title: 'Success', description: 'Data source created successfully' });
    } catch (error) {
      toast.error({ title: 'Error', description: 'Failed to create data source' });
    }
  };

  const handleUpdate = async (id: number, data: Partial<DataSource>) => {
    try {
      await updateDataSource({ id, ...data });
      setEditingDataSource(null);
      toast.success({ title: 'Success', description: 'Data source updated successfully' });
    } catch (error) {
      toast.error({ title: 'Error', description: 'Failed to update data source' });
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteDataSource(id);
      toast.success({ title: 'Success', description: 'Data source deleted successfully' });
    } catch (error) {
      toast.error({ title: 'Error', description: 'Failed to delete data source' });
    }
  };

  const handlePull = async (id: number) => {
    try {
      await pullDataSource(id);
    } catch (error) {
      toast.error({ title: 'Error', description: 'Failed to pull data source' });
    }
  };

  const columns = [
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
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setEditingDataSource(row.original)}
          >
            Edit
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handlePull(row.original.id)}
          >
            Pull
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => handleDelete(row.original.id)}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <DataPageLayout
      title="Data Sources"
      subtitle="Manage your data source connections"
      data={dataSources?.data}
      loading={isLoading}
      error={error}
      renderHeader={() => (
        <Button onClick={() => setIsFormOpen(true)}>
          Add Data Source
        </Button>
      )}
      renderContent={(data) => (
        <>
          <DataTable
            data={data}
            columns={columns}
            loading={isLoading}
          />
          
          {(isFormOpen || editingDataSource) && (
            <DataSourceForm
              initialData={editingDataSource}
              onSubmit={editingDataSource ? handleUpdate : handleCreate}
              onCancel={() => {
                setIsFormOpen(false);
                setEditingDataSource(null);
              }}
              isLoading={isCreating || isUpdating}
            />
          )}
        </>
      )}
    />
  );
} 