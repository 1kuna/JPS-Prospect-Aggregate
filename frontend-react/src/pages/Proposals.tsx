import { useEffect, useState, useRef, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { formatDate } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

// Create stable selectors outside the component
const selectProposals = (state: any) => state.proposals;
const selectProposalsPagination = (state: any) => state.proposalsPagination;
const selectProposalsLoading = (state: any) => state.loading.proposals;
const selectProposalsErrors = (state: any) => state.errors.proposals;
const selectFetchProposals = (state: any) => state.fetchProposals;
const selectLastUpdated = (state: any) => state.lastUpdated;

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
      console.log('Proposals component mounted, fetching data...');
      fetchProposals();
      isMounted.current = true;
    }
  }, []); // Empty dependency array to run only once on mount

  useEffect(() => {
    // Log when proposals data changes
    console.log('Proposals data updated:', proposals);
    console.log('Pagination:', proposalsPagination);
  }, [proposals, proposalsPagination]);

  // Memoize event handlers to prevent unnecessary re-renders
  const handleRefresh = useCallback(() => {
    console.log('Refreshing proposals...');
    fetchProposals({
      sortBy,
      sortOrder,
      page: proposalsPagination?.page || 1,
      perPage: proposalsPagination?.perPage || 50
    });
  }, [fetchProposals, sortBy, sortOrder, proposalsPagination]);

  const handlePageChange = useCallback((page: number) => {
    console.log('Changing to page:', page);
    fetchProposals({
      page,
      perPage: proposalsPagination?.perPage || 50,
      sortBy,
      sortOrder
    });
  }, [fetchProposals, sortBy, sortOrder, proposalsPagination]);

  const handleSort = useCallback((column: string) => {
    const newSortOrder = column === sortBy && sortOrder === 'asc' ? 'desc' : 'asc';
    console.log(`Sorting by ${column} ${newSortOrder}`);
    setSortBy(column);
    setSortOrder(newSortOrder);
    fetchProposals({
      sortBy: column,
      sortOrder: newSortOrder,
      page: proposalsPagination?.page || 1,
      perPage: proposalsPagination?.perPage || 50
    });
  }, [fetchProposals, sortBy, sortOrder, proposalsPagination]);

  return (
    <div>
      {/* Page header with title and last updated info */}
      <div className="flex justify-between mb-4">
        <h1 className="text-2xl font-bold">Proposals</h1>
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-sm text-muted">
              Last updated: {formatDate(lastUpdated)}
            </span>
          )}
          <button className="btn btn-primary" onClick={handleRefresh} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Error state */}
      {errors && (
        <div className="card mb-4" style={{backgroundColor: "var(--error-color)", color: "white"}}>
          <h3 className="font-bold">Error</h3>
          <p>{errors.message && errors.message}</p>
        </div>
      )}

      {/* Debug info */}
      <div className="card mb-4">
        <h3 className="font-bold mb-2">Debug Info:</h3>
        <p>Loading: {loading ? 'true' : 'false'}</p>
        <p>Proposals count: {proposals.length}</p>
        <p>Has pagination: {proposalsPagination ? 'true' : 'false'}</p>
        {proposalsPagination && (
          <div>
            <p>Page: {proposalsPagination.page}</p>
            <p>Per page: {proposalsPagination.perPage}</p>
            <p>Total count: {proposalsPagination.totalCount}</p>
            <p>Total pages: {proposalsPagination.totalPages}</p>
          </div>
        )}
      </div>

      {/* Loading state */}
      {loading && !proposals.length && (
        <div className="card">
          <div className="card-header">
            <Skeleton className="h-8 w-1/4 mb-2" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </div>
      )}

      {/* No data state */}
      {!loading && !proposals.length && (
        <div className="card mb-4">
          <h3 className="font-bold">No proposals available</h3>
          <p>There are currently no proposals in the system.</p>
        </div>
      )}

      {/* Proposals Table */}
      {proposals.length > 0 && (
        <div className="card mb-4">
          <div className="card-header">
            <h2 className="card-title">Proposals</h2>
            <p>
              {proposalsPagination && (
                <span>
                  Showing {proposals.length} of {proposalsPagination.totalCount} proposals
                </span>
              )}
            </p>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleSort('title')} style={{cursor: 'pointer'}}>
                    Title {sortBy === 'title' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('agency')} style={{cursor: 'pointer'}}>
                    Agency {sortBy === 'agency' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th>Source</th>
                  <th onClick={() => handleSort('release_date')} style={{cursor: 'pointer'}}>
                    Release Date {sortBy === 'release_date' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('status')} style={{cursor: 'pointer'}}>
                    Status {sortBy === 'status' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {proposals.map((proposal: any) => (
                  <tr key={proposal.id}>
                    <td className="font-medium">{proposal.title}</td>
                    <td>{proposal.agency}</td>
                    <td>{proposal.source_name}</td>
                    <td>{proposal.release_date ? formatDate(proposal.release_date) : 'N/A'}</td>
                    <td>
                      <span className={`status ${proposal.status?.toLowerCase().includes('new') ? 'status-new' : 
                                                 proposal.status?.toLowerCase().includes('exercise') ? 'status-exercise' : ''}`}>
                        {proposal.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {proposalsPagination && proposalsPagination.totalPages > 1 && (
            <div className="pagination">
              <button 
                className="pagination-item"
                onClick={() => handlePageChange(Math.max(1, (proposalsPagination?.page || 1) - 1))}
                disabled={proposalsPagination.page <= 1}
              >
                &lt; Previous
              </button>
              
              {Array.from({ length: Math.min(5, proposalsPagination.totalPages) }, (_, i) => {
                const pageNumber = i + 1;
                return (
                  <button 
                    key={pageNumber}
                    className={`pagination-item ${pageNumber === proposalsPagination.page ? 'active' : ''}`}
                    onClick={() => handlePageChange(pageNumber)}
                  >
                    {pageNumber}
                  </button>
                );
              })}
              
              <button 
                className="pagination-item"
                onClick={() => handlePageChange(Math.min(proposalsPagination.totalPages, (proposalsPagination?.page || 1) + 1))}
                disabled={proposalsPagination.page >= proposalsPagination.totalPages}
              >
                Next &gt;
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
} 