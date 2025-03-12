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
} from '@/components';

// Create stable selectors outside the component
const selectProposals = (state: any) => state.proposals;
const selectProposalsPagination = (state: any) => state.proposalsPagination;
const selectProposalsLoading = (state: any) => state.loading.proposals;
const selectProposalsErrors = (state: any) => state.errors.proposals;
const selectFetchProposals = (state: any) => state.fetchProposals;
const selectLastUpdated = (state: any) => state.lastUpdated;

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
  const lastUpdated = useStore(selectLastUpdated);

  const [sortBy, setSortBy] = useState('release_date');
  const [sortOrder, setSortOrder] = useState('desc');
  const isMounted = useRef(false);

  useEffect(() => {
    // Only fetch data if this is the first time the component is mounted
    if (!isMounted.current) {
      fetchProposals();
      isMounted.current = true;
    }
  }, []); // Empty dependency array to run only once on mount

  // Memoize event handlers to prevent unnecessary re-renders
  const handleRefresh = useCallback(() => {
    fetchProposals({
      sortBy,
      sortOrder,
      page: proposalsPagination?.page || 1,
      perPage: proposalsPagination?.perPage || 50
    });
  }, [fetchProposals, sortBy, sortOrder, proposalsPagination]);

  const handlePageChange = useCallback((page: number) => {
    fetchProposals({
      page,
      perPage: proposalsPagination?.perPage || 50,
      sortBy,
      sortOrder
    });
  }, [fetchProposals, sortBy, sortOrder, proposalsPagination]);

  const handleSort = useCallback((column: string) => {
    const newSortOrder = column === sortBy && sortOrder === 'asc' ? 'desc' : 'asc';
    setSortBy(column);
    setSortOrder(newSortOrder);
    fetchProposals({
      sortBy: column,
      sortOrder: newSortOrder,
      page: proposalsPagination?.page || 1,
      perPage: proposalsPagination?.perPage || 50
    });
  }, [fetchProposals, sortBy, sortOrder, proposalsPagination]);

  // If loading and no data, show skeleton
  if (loading && !proposals.length) {
    return <PageSkeleton cardCount={1} />;
  }

  // Define table columns with sorting
  const columns = [
    { 
      header: `Title ${sortBy === 'title' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}`, 
      accessor: 'title' as keyof Proposal,
      className: 'cursor-pointer',
      onClick: () => handleSort('title')
    },
    { 
      header: `Agency ${sortBy === 'agency' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}`, 
      accessor: 'agency' as keyof Proposal,
      className: 'cursor-pointer',
      onClick: () => handleSort('agency')
    },
    { 
      header: 'Source', 
      accessor: 'source_name' as keyof Proposal 
    },
    { 
      header: `Release Date ${sortBy === 'release_date' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}`, 
      accessor: (proposal: Proposal) => proposal.release_date ? formatDate(proposal.release_date) : 'N/A',
      className: 'cursor-pointer',
      onClick: () => handleSort('release_date')
    },
    { 
      header: `Status ${sortBy === 'status' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}`, 
      accessor: (proposal: Proposal) => (
        <span className={`status ${proposal.status?.toLowerCase().includes('new') ? 'status-new' : 
                           proposal.status?.toLowerCase().includes('exercise') ? 'status-exercise' : ''}`}>
          {proposal.status}
        </span>
      ),
      className: 'cursor-pointer',
      onClick: () => handleSort('status')
    },
  ];

  return (
    <PageLayout
      title="Proposals"
      lastUpdated={lastUpdated}
      onRefresh={handleRefresh}
      isLoading={loading}
      error={errors}
    >
      {/* No data state */}
      {!loading && !proposals.length && (
        <Alert className="mb-6">
          <AlertTitle>No proposals available</AlertTitle>
          <AlertDescription>
            There are currently no proposals in the system.
          </AlertDescription>
        </Alert>
      )}

      {/* Proposals Table */}
      {proposals.length > 0 && (
        <DataTable
          title="Proposals"
          description={proposalsPagination ? `Showing ${proposals.length} of ${proposalsPagination.totalCount} proposals` : undefined}
          data={proposals}
          columns={columns}
          keyField="id"
          pagination={
            proposalsPagination
              ? {
                  page: proposalsPagination.page,
                  perPage: proposalsPagination.perPage,
                  totalPages: proposalsPagination.totalPages,
                  totalItems: proposalsPagination.totalCount,
                }
              : undefined
          }
          onPageChange={handlePageChange}
          emptyMessage={{
            title: 'No proposals found',
            description: 'There are currently no proposals in the system.',
          }}
        />
      )}
    </PageLayout>
  );
} 