import { useState } from 'react';
import { DataPageLayout } from '@/components/layout';
import { useInfiniteProspects, useProspectStatistics } from '@/hooks/api/useProspects';
import { ProspectFilters } from '@/types/prospects';
import { Button } from '@/components/ui';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate } from '@/utils/dateUtils';
import { LoadingButton } from '@/components/ui/LoadingButton';
import { ErrorDisplay } from '@/components/ui/ErrorDisplay';
import { CenteredSpinner } from '@/components/ui/LoadingSpinner';

export default function Prospects() {
  const [filters] = useState<ProspectFilters>({});
  
  const {
    data: prospects,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error
  } = useInfiniteProspects(filters);

  // Log prospects data in Prospects.tsx
  console.log('[Prospects.tsx] prospects data from useInfiniteProspects:', prospects);
  console.log('[Prospects.tsx] isLoading:', isLoading, 'isError:', isError, 'error:', error);

  const { data: statisticsData, isLoading: isLoadingStats } = useProspectStatistics();

  const handleLoadMore = () => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  };


  const pageError = isError ? (error as Error) : null;
  const totalProspects = statisticsData?.data?.total ?? 0;

  return (
    <DataPageLayout
      title="Prospects"
      subtitle={`Total: ${totalProspects} prospects`}
      data={prospects ?? []}
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
                  <TableCell colSpan={5} className="h-24">
                    <CenteredSpinner text="Loading prospects..." />
                  </TableCell>
                </TableRow>
              ) : isError ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24">
                    <ErrorDisplay error={error as Error} />
                  </TableCell>
                </TableRow>
              ) : !prospects || prospects.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center">
                    No prospects found.
                  </TableCell>
                </TableRow>
              ) : (
                prospects.map((prospect) => (
                  <TableRow key={prospect.id}>
                    <TableCell className="font-medium">
                      {prospect.title || 'Untitled'}
                    </TableCell>
                    <TableCell>{prospect.status || 'N/A'}</TableCell>
                    <TableCell>
                      {prospect.dataSource?.name || 'N/A'}
                    </TableCell>
                    <TableCell>
                      {formatDate(prospect.createdAt, { format: 'date' })}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => alert('View prospect details')}
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
            <LoadingButton
              onClick={handleLoadMore}
              isLoading={isFetchingNextPage}
              loadingText="Loading..."
            >
              Load More
            </LoadingButton>
          </div>
        )}
      </div>
    </DataPageLayout>
  );
}