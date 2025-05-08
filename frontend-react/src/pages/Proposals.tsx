import { useState } from 'react';
import { DataPageLayout } from '@/components/layout';
import { DataTable, Column } from '@/components/data-display';
import { useInfiniteProposals, useProposalStatistics } from '@/hooks/api/useProposals';
import { Proposal, ProposalFilters } from '@/types/proposals';
import styles from './Proposals.module.css';
import { Button } from '@/components/ui';

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

  const { data: statisticsData, isLoading: isLoadingStats } = useProposalStatistics();

  const handleLoadMore = () => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  };

  const columns: Column<Proposal>[] = [
    {
      header: 'Title',
      accessorKey: 'title',
    },
    {
      header: 'Status',
      accessorKey: 'status',
    },
    {
      header: 'Data Source',
      accessorKey: 'dataSource.name',
    },
    {
      header: 'Created',
      accessorKey: 'createdAt',
      cell: ({ row }: { row: Proposal }) => 
        new Date(row.createdAt).toLocaleDateString(),
    },
    {
      header: 'Actions',
      cell: ({ row }: { row: Proposal }) => (
        <div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => row.url && window.open(row.url, '_blank')}
          >
            View
          </Button>
        </div>
      ),
    },
  ];

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
      <>
        <DataTable
          data={proposals?.pages.flatMap(page => page.data) ?? []}
          columns={columns}
          isLoading={isLoading}
        />
        
        {hasNextPage && (
          <div className={styles.loadMoreContainer}>
            <Button
              onClick={handleLoadMore}
              disabled={isFetchingNextPage}
            >
              {isFetchingNextPage ? 'Loading...' : 'Load More'}
            </Button>
          </div>
        )}
      </>
    </DataPageLayout>
  );
} 