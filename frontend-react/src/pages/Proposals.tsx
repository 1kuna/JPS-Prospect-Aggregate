import { useState } from 'react';
import { DataPageLayout } from '@/components/layout';
import { DataTable } from '@/components/ui/DataTable';
import { Button } from '@/components/ui/button';
import { useProposals } from '@/hooks/api/useProposals';
import { ProposalFilters } from '@/components/filters';
import { Proposal } from '@/types';
import { toast } from '@/hooks/use-toast';

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
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => window.open(row.original.url, '_blank')}
          >
            View
          </Button>
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
            <div className="flex justify-center mt-4">
              <Button
                onClick={handleLoadMore}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? 'Loading...' : 'Load More'}
              </Button>
            </div>
          )}
        </>
      )}
    />
  );
} 