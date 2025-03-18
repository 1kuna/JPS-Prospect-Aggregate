import { useState, useCallback, useEffect } from 'react';
import { useProposalsSelectors } from '@/hooks';
import { formatDate } from '@/lib/utils';
import {
  Button,
  DataTable,
} from '@/components';
import { DataPageLayout } from '@/components/layout';
import type { Column } from '@/components/data-display/DataTable';

interface Proposal {
  id: number | string;
  title: string;
  agency: string;
  source_name: string;
  release_date: string | null;
  status: string;
}

export default function Proposals() {
  const [sortBy] = useState('release_date');
  const [sortOrder] = useState('desc');

  // Use the typed selector hook for proposals
  const {
    proposals,
    pagination,
    loading,
    errors,
    fetchProposals
  } = useProposalsSelectors();
  
  // Fetch proposals when component mounts or sort params change
  useEffect(() => {
    fetchProposals({ sortBy, sortOrder });
  }, [fetchProposals, sortBy, sortOrder]);

  // Memoize event handlers to prevent unnecessary re-renders
  const handlePageChange = useCallback((page: number) => {
    console.log('Changing page to:', page);
    fetchProposals({ 
      page,
      sortBy, 
      sortOrder,
      perPage: pagination?.perPage || 10
    });
  }, [fetchProposals, sortBy, sortOrder, pagination?.perPage]);

  const handlePerPageChange = useCallback((perPage: number) => {
    console.log('Changing per page to:', perPage);
    fetchProposals({
      page: 1,
      perPage,
      sortBy,
      sortOrder
    });
  }, [fetchProposals, sortBy, sortOrder]);

  // Define columns for the data table
  const columns: Column<Proposal>[] = [
    {
      accessorKey: 'title',
      header: 'Title',
    },
    {
      accessorKey: 'agency',
      header: 'Agency',
    },
    {
      accessorKey: 'source_name',
      header: 'Source',
    },
    {
      accessorKey: 'release_date',
      header: 'Release Date',
      cell: ({ row }) => formatDate(row.original.release_date),
    },
    {
      accessorKey: 'status',
      header: 'Status',
    },
  ];

  return (
    <DataPageLayout title="Proposals" subtitle="View all proposals from your data sources">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">All Proposals</h2>
          <Button onClick={() => fetchProposals({ sortBy, sortOrder })}>
            Refresh
          </Button>
        </div>

        <DataTable
          data={proposals || []}
          columns={columns}
          isLoading={loading}
          pagination={{
            page: pagination?.page || 1,
            pageCount: pagination?.totalPages || 1,
            perPage: pagination?.perPage || 10,
            total: pagination?.totalCount || 0,
            onPageChange: handlePageChange,
            onPerPageChange: handlePerPageChange,
          }}
        />

        {errors && (
          <div className="p-4 text-red-500 bg-red-50 rounded-md">
            Error: {errors.message || 'Unknown error occurred'}
          </div>
        )}
      </div>
    </DataPageLayout>
  );
} 