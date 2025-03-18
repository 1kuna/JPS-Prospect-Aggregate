import { useState, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { formatDate } from '@/lib/utils';
import { useStoreData } from '@/hooks';
import {
  Button,
  DataTable,
} from '@/components';
import { DataPageLayout } from '@/components/layout';
import type { Column } from '@/components/data-display/DataTable';

// Create stable selectors outside the component
const selectProposals = (state: any) => state.proposals;
const selectProposalsPagination = (state: any) => state.proposalsPagination;
const selectProposalsLoading = (state: any) => state.loading.proposals;
const selectProposalsErrors = (state: any) => state.errors.proposals;
const selectFetchProposals = (state: any) => state.fetchProposals;

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

  // Use the custom hook for data fetching and state management
  const { data: proposals, loading, errors, refresh } = useStoreData({
    dataSelector: selectProposals,
    loadingSelector: selectProposalsLoading,
    errorSelector: selectProposalsErrors,
    fetchAction: selectFetchProposals,
    fetchParams: { sortBy, sortOrder },
    dependencies: [sortBy, sortOrder]
  });

  // Use individual selector for pagination
  const proposalsPagination = useStore(selectProposalsPagination);

  // Memoize event handlers to prevent unnecessary re-renders
  const handlePageChange = useCallback((page: number) => {
    console.log('Changing page to:', page);
    refresh();
  }, [refresh]);

  const handlePerPageChange = useCallback((perPage: number) => {
    console.log('Changing items per page to:', perPage);
    refresh();
  }, [refresh]);

  const columns: Column<Proposal>[] = [
    {
      header: 'ID',
      accessorKey: 'id',
    },
    {
      header: 'Title',
      accessorKey: 'title',
    },
    {
      header: 'Agency',
      accessorKey: 'agency',
    },
    {
      header: 'Source',
      accessorKey: 'source_name',
    },
    {
      header: 'Release Date',
      accessorKey: (row: Proposal) => row.release_date ? formatDate(row.release_date) : 'N/A',
    },
    {
      header: 'Status',
      accessorKey: 'status',
    },
    {
      header: 'Actions',
      accessorKey: 'id',
      cell: () => (
        <Button variant="outline" size="sm">View</Button>
      ),
    },
  ];

  // Ensure we have a valid pagination object even if the backend doesn't provide one
  const paginationInfo = {
    page: proposalsPagination?.page || 1,
    perPage: proposalsPagination?.perPage || 50,
    totalPages: proposalsPagination?.totalPages || 1,
    totalItems: proposalsPagination?.totalCount || (proposals?.length || 0)
  };

  return (
    <DataPageLayout
      title="Proposals"
      data={proposals}
      loading={loading}
      error={errors}
      onRefresh={refresh}
      emptyMessage="No proposals found"
      renderHeader={() => (
        <>
          <p className="text-muted-foreground">
            Showing {proposals?.length || 0} of {paginationInfo.totalItems} proposals
          </p>
          <Button onClick={refresh}>Refresh</Button>
        </>
      )}
      renderContent={(data) => (
        <DataTable
          data={data as Proposal[]}
          columns={columns}
          emptyMessage="No proposals found"
          pagination={paginationInfo}
          onPageChange={handlePageChange}
          onPerPageChange={handlePerPageChange}
          maxHeight="60vh" // Use viewport-relative height for better responsiveness
        />
      )}
    />
  );
} 