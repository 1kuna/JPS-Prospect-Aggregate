import { useState, useRef, useEffect } from 'react';
import { DataPageLayout } from '@/components/layout';
import { useInfiniteProspects, useProspectStatistics } from '@/hooks/api/useProspects';
import { ProspectFilters } from '@/types/prospects';
import { Button } from '@/components/ui';
import { formatDate } from '@/utils/dateUtils';
import { useTimezoneDate } from '@/hooks/useTimezoneDate';
import { LoadingButton } from '@/components/ui/LoadingButton';
import { ErrorDisplay } from '@/components/ui/ErrorDisplay';
import { CenteredSpinner } from '@/components/ui/LoadingSpinner';
import { useVirtualizer } from '@tanstack/react-virtual';
import { GoNoGoDecision } from '@/components/GoNoGoDecision';

export default function Prospects() {
  const [filters] = useState<ProspectFilters>({});
  const parentRef = useRef<HTMLDivElement>(null);
  const { formatUserDate } = useTimezoneDate();
  
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

  // Set up virtualization
  const virtualizer = useVirtualizer({
    count: prospects?.length || 0,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60, // Estimated row height in pixels
    overscan: 10, // Render 10 extra items above/below viewport for smooth scrolling
  });

  const handleLoadMore = () => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  };

  // Auto-load more data when scrolling near the end
  useEffect(() => {
    const [lastItem] = [...virtualizer.getVirtualItems()].reverse();
    
    if (!lastItem) return;
    
    if (
      lastItem.index >= prospects.length - 1 - 5 && // Load when 5 items from the end
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage();
    }
  }, [hasNextPage, fetchNextPage, isFetchingNextPage, virtualizer.getVirtualItems(), prospects.length]);


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
        {isLoading ? (
          <div className="flex justify-center py-8">
            <CenteredSpinner text="Loading prospects..." />
          </div>
        ) : isError ? (
          <ErrorDisplay error={error as Error} />
        ) : !prospects || prospects.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No prospects found.
          </div>
        ) : (
          <div className="rounded-md border">
            {/* Table Header */}
            <div className="grid grid-cols-6 gap-4 p-4 bg-gray-50 border-b font-medium text-sm text-gray-700">
              <div>Title</div>
              <div>Status</div>
              <div>Data Source</div>
              <div>Created</div>
              <div>Decision</div>
              <div>Actions</div>
            </div>
            
            {/* Virtualized Table Body */}
            <div
              ref={parentRef}
              className="h-[600px] overflow-auto"
              style={{
                contain: 'strict',
              }}
            >
              <div
                style={{
                  height: `${virtualizer.getTotalSize()}px`,
                  width: '100%',
                  position: 'relative',
                }}
              >
                {virtualizer.getVirtualItems().map((virtualItem) => {
                  const prospect = prospects[virtualItem.index];
                  return (
                    <div
                      key={virtualItem.key}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: `${virtualItem.size}px`,
                        transform: `translateY(${virtualItem.start}px)`,
                      }}
                      className="grid grid-cols-6 gap-4 p-4 border-b hover:bg-gray-50 items-center"
                    >
                      <div className="font-medium truncate">
                        {prospect?.title || 'Untitled'}
                      </div>
                      <div className="truncate">
                        {prospect?.status || 'N/A'}
                      </div>
                      <div className="truncate">
                        {prospect?.dataSource?.name || 'N/A'}
                      </div>
                      <div className="text-sm text-gray-600">
                        {formatUserDate(prospect?.createdAt, 'date')}
                      </div>
                      <div>
                        <GoNoGoDecision 
                          prospectId={prospect?.id} 
                          prospectTitle={prospect?.title}
                          compact={true} 
                        />
                      </div>
                      <div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => alert('View prospect details')}
                        >
                          View
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
        
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