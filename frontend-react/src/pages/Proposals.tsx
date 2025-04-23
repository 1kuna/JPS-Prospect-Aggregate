import { useState } from 'react';
import { DataPageLayout } from '@/components/layout';
import { DataTable } from '@/components/data-display/DataTable';
import { useProposals } from '@/hooks/api/useProposals';
import { ProposalFilters } from '@/components/filters';
import { Proposal } from '@/types';
import styles from './Proposals.module.css';

export default function Proposals() {
  const [filters, setFilters] = useState<ProposalFilters>({});
  
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error
  } = useProposals.useInfiniteList(filters);

  const { data: statistics } = useProposals.useStatistics();

  const handleLoadMore = () => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  };

  // Flatten pages of data for the table
  const proposals = data?.pages.flatMap(page => page.data) ?? [];

  const columns = [
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
      cell: ({ row }) => new Date(row.original.createdAt).toLocaleDateString(),
    },
    {
      header: 'Actions',
      cell: ({ row }) => (
        <div>
          <button
            className={styles.actionButton}
            onClick={() => window.open(row.original.url, '_blank')}
          >
            View
          </button>
        </div>
      ),
    },
  ];

  return (
    <DataPageLayout
      title="Proposals"
      subtitle={`Total: ${statistics?.data.total ?? 0} proposals`}
      data={proposals}
      loading={isLoading}
      error={error}
      renderHeader={() => (
        <ProposalFilters
          filters={filters}
          onChange={setFilters}
          statistics={statistics?.data}
        />
      )}
      renderContent={(data) => (
        <>
          <DataTable
            data={data}
            columns={columns}
            loading={isLoading}
          />
          
          {hasNextPage && (
            <div className={styles.loadMoreContainer}>
              <button
                className={styles.loadMoreButton}
                onClick={handleLoadMore}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </>
      )}
    />
  );
} 