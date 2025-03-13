import { useEffect, useState, useRef, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { formatDate } from '@/lib/utils';
import {
  PageLayout,
  DataTable,
  Alert,
  AlertTitle,
  AlertDescription,
  Button,
} from '@/components';
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
  // Use individual selectors to prevent unnecessary re-renders
  const proposals = useStore(selectProposals);
  const proposalsPagination = useStore(selectProposalsPagination);
  const loading = useStore(selectProposalsLoading);
  const errors = useStore(selectProposalsErrors);
  const fetchProposals = useStore(selectFetchProposals);

  const [sortBy] = useState('release_date');
  const [sortOrder] = useState('desc');
  const isMounted = useRef(false);

  useEffect(() => {
    // Only fetch data if this is the first time the component is mounted
    if (!isMounted.current) {
      console.log('Proposals component mounted, fetching proposals...');
      fetchProposals().then(() => {
        console.log('Proposals fetched successfully in component');
      }).catch((error: Error) => {
        console.error('Error fetching proposals in component:', error);
      });
      isMounted.current = true;
    }
  }, [fetchProposals]); // Include fetchProposals in the dependency array

  // Log state changes for debugging
  useEffect(() => {
    console.log('Proposals component state:', { 
      proposals, 
      proposalsPagination, 
      loading, 
      errors 
    });
    
    // Log pagination data specifically for debugging
    if (proposalsPagination) {
      console.log('Pagination data:', {
        page: proposalsPagination.page,
        perPage: proposalsPagination.perPage,
        totalPages: proposalsPagination.totalPages,
        totalCount: proposalsPagination.totalCount
      });
    }
  }, [proposals, proposalsPagination, loading, errors]);

  // Memoize event handlers to prevent unnecessary re-renders
  const handlePageChange = useCallback((page: number) => {
    console.log('Changing page to:', page);
    fetchProposals({ page, sortBy, sortOrder });
  }, [fetchProposals, sortBy, sortOrder]);

  const handlePerPageChange = useCallback((perPage: number) => {
    console.log('Changing items per page to:', perPage);
    fetchProposals({ page: 1, perPage, sortBy, sortOrder });
  }, [fetchProposals, sortBy, sortOrder]);

  const handleRefresh = useCallback(() => {
    console.log('Refreshing proposals...');
    fetchProposals({ sortBy, sortOrder });
  }, [fetchProposals, sortBy, sortOrder]);

  if (loading && !proposals.length) {
    console.log('Rendering loading state...');
    return (
      <PageLayout title="Proposals" isLoading={true}>
        <div>Loading proposals...</div>
      </PageLayout>
    );
  }

  // Error state
  if (errors && !proposals.length) {
    console.log('Rendering error state:', errors);
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">Proposals</h1>
        <Alert variant="destructive">
          <AlertTitle>Error loading proposals</AlertTitle>
          <AlertDescription>{errors.message}</AlertDescription>
        </Alert>
        <Button onClick={handleRefresh}>Retry</Button>
      </div>
    );
  }

  console.log('Rendering proposals table with data:', proposals);

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
    totalItems: proposalsPagination?.totalCount || proposals.length
  };

  return (
    <PageLayout title="Proposals">
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <p className="text-muted-foreground">
              Showing {proposals.length} of {paginationInfo.totalItems} proposals
            </p>
          </div>
          <Button onClick={handleRefresh}>Refresh</Button>
        </div>

        <DataTable
          data={proposals}
          columns={columns}
          emptyMessage="No proposals found"
          pagination={paginationInfo}
          onPageChange={handlePageChange}
          onPerPageChange={handlePerPageChange}
        />
      </div>
    </PageLayout>
  );
} 