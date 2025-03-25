import React, { useState, useMemo, useCallback } from 'react';
import { z } from 'zod';
import { useDataSources } from '../hooks';
import { DataLoader } from '../components/ui/DataLoader';
import { DataTable, Column } from '../components/ui/DataTable';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '../components/ui/form';
import { toast } from '../hooks/use-toast';
import { DataSource } from '../types/api';

// Zod schema for validating form input
const dataSourceSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  url: z.string().url('Valid URL is required'),
  description: z.string().optional(),
  status: z.enum(['active', 'inactive']).default('active'),
});

type DataSourceFormValues = z.infer<typeof dataSourceSchema>;

/**
 * Data Sources page component
 */
export function DataSourcesPage() {
  // State for dialog
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingDataSource, setEditingDataSource] = useState<DataSource | null>(null);
  
  // Use React Query hooks
  const { 
    data: dataSources = [], 
    isLoading: dataSourcesLoading, 
    error: dataSourcesError,
    mutate: { create: createDataSource, update: updateDataSource, remove: deleteDataSource }
  } = useDataSources();
  
  // Handle opening the dialog for adding/editing
  const handleAddNew = useCallback(() => {
    setEditingDataSource(null);
    setIsDialogOpen(true);
  }, []);
  
  const handleEdit = useCallback((dataSource: DataSource) => {
    setEditingDataSource(dataSource);
    setIsDialogOpen(true);
  }, []);
  
  // Handle form submission
  const handleSubmit = useCallback(async (values: DataSourceFormValues) => {
    try {
      if (editingDataSource) {
        // Update existing data source
        await updateDataSource({ ...values, id: editingDataSource.id });
        toast({
          title: 'Data Source Updated',
          description: `${values.name} updated successfully`,
        });
      } else {
        // Create new data source
        await createDataSource(values);
        toast({
          title: 'Data Source Created',
          description: `${values.name} created successfully`,
        });
      }
      setIsDialogOpen(false);
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'An unknown error occurred',
        variant: 'destructive',
      });
    }
  }, [editingDataSource, updateDataSource, createDataSource]);
  
  // Handle delete
  const handleDelete = useCallback(async (id: number) => {
    if (window.confirm('Are you sure you want to delete this data source?')) {
      try {
        await deleteDataSource(id);
        toast({
          title: 'Data Source Deleted',
          description: 'Data source deleted successfully',
        });
      } catch (error) {
        toast({
          title: 'Error',
          description: error instanceof Error ? error.message : 'An unknown error occurred',
          variant: 'destructive',
        });
      }
    }
  }, [deleteDataSource]);
  
  // Configure table columns
  const columns = useMemo<Column<DataSource>[]>(() => [
    {
      key: 'name',
      header: 'Name',
      cell: (item) => item.name,
      sortable: true,
    },
    {
      key: 'url',
      header: 'URL',
      cell: (item) => (
        <a 
          href={item.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {item.url}
        </a>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      cell: (item) => (
        <span className={`px-2 py-1 rounded text-xs ${
          item.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
        }`}>
          {item.status}
        </span>
      ),
      width: '100px',
      align: 'center',
    },
    {
      key: 'proposal_count',
      header: 'Proposals',
      cell: (item) => item.proposal_count,
      width: '100px',
      align: 'center',
      sortable: true,
    },
    {
      key: 'actions',
      header: 'Actions',
      cell: (item) => (
        <div className="flex space-x-2 justify-center">
          <Button 
            variant="outline" 
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleEdit(item);
            }}
          >
            Edit
          </Button>
          <Button 
            variant="destructive" 
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(item.id);
            }}
          >
            Delete
          </Button>
        </div>
      ),
      width: '180px',
      align: 'center',
    },
  ], [handleEdit, handleDelete]);
  
  // Table header with add button
  const tableHeader = (
    <div className="flex justify-between items-center mb-4">
      <h2 className="text-xl font-semibold">Data Sources</h2>
      <Button onClick={handleAddNew}>Add Data Source</Button>
    </div>
  );
  
  // Empty state component
  const emptyState = (
    <div className="text-center p-8">
      <h3 className="text-lg font-medium">No Data Sources Found</h3>
      <p className="text-gray-500 mb-4">Get started by adding your first data source</p>
      <Button onClick={handleAddNew}>Add Data Source</Button>
    </div>
  );
  
  return (
    <div className="container mx-auto py-8">
      <DataLoader
        data={dataSources}
        isLoading={dataSourcesLoading}
        error={dataSourcesError}
        onRetry={() => {}}
        emptyComponent={emptyState}
      >
        {(data) => (
          <DataTable
            data={data}
            columns={columns}
            rowKey={(item) => item.id}
            onRowClick={handleEdit}
            headerContent={tableHeader}
          />
        )}
      </DataLoader>
      
      {/* Add/Edit Data Source Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingDataSource ? 'Edit Data Source' : 'Add Data Source'}
            </DialogTitle>
          </DialogHeader>
          
          <Form<DataSourceFormValues>
            defaultValues={editingDataSource ? {
              name: editingDataSource.name,
              url: editingDataSource.url,
              description: editingDataSource.description,
              status: editingDataSource.status as 'active' | 'inactive',
            } : {
              status: 'active',
            }}
            onSubmit={handleSubmit}
            schema={dataSourceSchema}
            onCancel={() => setIsDialogOpen(false)}
          >
            <FormField<DataSourceFormValues>
              name="name"
              label="Name"
              required
              placeholder="Enter data source name"
            />
            
            <FormField<DataSourceFormValues>
              name="url"
              label="URL"
              type="text"
              required
              placeholder="https://example.com"
            />
            
            <FormField<DataSourceFormValues>
              name="description"
              label="Description"
              type="textarea"
              placeholder="Enter a description"
            />
            
            <FormField<DataSourceFormValues>
              name="status"
              label="Status"
              type="select"
              options={[
                { label: 'Active', value: 'active' },
                { label: 'Inactive', value: 'inactive' },
              ]}
            />
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
} 