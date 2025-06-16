import { useState } from 'react';
import { DataPageLayout } from '@/components/layout';
import { useInfiniteProposals, useProposalStatistics } from '@/hooks/api/useProposals';
import { ProposalFilters } from '@/types/proposals';
import { Button } from '@/components/ui';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function Proposals() {
  const [filters] = useState<ProposalFilters>({});
  
  const {
    data: proposals,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error
  } = useInfiniteProposals(filters);

  // Log proposals data in Proposals.tsx
  console.log('[Proposals.tsx] proposals data from useInfiniteProposals:', proposals);
  console.log('[Proposals.tsx] isLoading:', isLoading, 'isError:', isError, 'error:', error);

  const { data: statisticsData, isLoading: isLoadingStats } = useProposalStatistics();

  const handleLoadMore = () => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  };


  const pageError = isError ? (error as Error) : null;
  const totalProposals = statisticsData?.data?.total ?? 0;

  return (
    <DataPageLayout
      title="Proposals"
      subtitle={`Total: ${totalProposals} proposals`}
      data={proposals ?? []}
      loading={isLoading || isLoadingStats}
      error={pageError}
    >
      <div className="space-y-4">
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Data Source</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center">
                    Loading...
                  </TableCell>
                </TableRow>
              ) : !proposals || proposals.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center">
                    No proposals found.
                  </TableCell>
                </TableRow>
              ) : (
                proposals.map((proposal) => (
                  <TableRow key={proposal.id}>
                    <TableCell className="font-medium">
                      {proposal.title || 'Untitled'}
                    </TableCell>
                    <TableCell>{proposal.status || 'N/A'}</TableCell>
                    <TableCell>
                      {proposal.dataSource?.name || 'N/A'}
                    </TableCell>
                    <TableCell>
                      {new Date(proposal.createdAt).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => alert('View proposal details')}
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
        
        {hasNextPage && (
          <div className="flex justify-center">
            <Button
              onClick={handleLoadMore}
              disabled={isFetchingNextPage}
            >
              {isFetchingNextPage ? 'Loading...' : 'Load More'}
            </Button>
          </div>
        )}
      </div>
    </DataPageLayout>
  );
} 