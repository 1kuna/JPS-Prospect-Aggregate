import { useEffect } from 'react';
import { useStatisticsSelectors, useUISelectors } from '@/hooks/useStoreSelectors';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  Button,
  Spinner,
  Card,
  CardContent,
} from '@/components/ui';
import { useProposalsTrend } from '@/store/selectors';

interface StatisticsProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Statistics({ isOpen, onClose }: StatisticsProps) {
  const { statistics, loading, errors, fetchStatistics } = useStatisticsSelectors();
  const { addToast } = useUISelectors();
  const proposalsTrend = useProposalsTrend();
  
  useEffect(() => {
    if (isOpen) {
      fetchStatistics().catch(error => {
        console.error('Failed to fetch statistics:', error);
        addToast({
          title: 'Error',
          description: 'Failed to load statistics. Please try again.',
          variant: 'destructive'
        });
      });
    }
  }, [isOpen, fetchStatistics, addToast]);
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Statistics</DialogTitle>
        </DialogHeader>
        
        {loading.statistics ? (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : errors.statistics ? (
          <div className="bg-red-100 p-4 rounded-md text-red-800">
            {errors.statistics.message || 'An error occurred while loading statistics'}
          </div>
        ) : !statistics ? (
          <div className="text-center py-8 text-gray-500">
            No statistics available
          </div>
        ) : (
          <div className="space-y-4">
            <Card>
              <CardContent className="pt-6">
                <h3 className="text-lg font-semibold mb-2">Overview</h3>
                <div className="grid grid-cols-2 gap-4">
                  <StatItem 
                    label="Total Proposals" 
                    value={statistics.total_proposals || 0} 
                  />
                  <StatItem 
                    label="Data Sources" 
                    value={statistics.total_sources || 0} 
                  />
                  <StatItem 
                    label="Active Sources" 
                    value={statistics.active_sources || 0} 
                  />
                  <StatItem 
                    label="Last Updated" 
                    value={formatDate(statistics.last_updated)} 
                  />
                </div>
              </CardContent>
            </Card>
            
            {proposalsTrend && proposalsTrend.length > 0 && (
              <Card>
                <CardContent className="pt-6">
                  <h3 className="text-lg font-semibold mb-2">Proposal Trends</h3>
                  <div className="h-40 flex items-end space-x-2">
                    {proposalsTrend.map((item, index) => {
                      const maxValue = Math.max(...proposalsTrend.map(i => i.count));
                      const height = `${Math.max(10, (item.count / maxValue) * 100)}%`;
                      
                      return (
                        <div key={index} className="flex flex-col items-center flex-1">
                          <div 
                            className="bg-blue-500 w-full rounded-t-sm" 
                            style={{ height }}
                            title={`${item.count} proposals`}
                          />
                          <div className="text-xs mt-1 text-center truncate w-full">
                            {item.month}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
            
            {statistics.top_sources && statistics.top_sources.length > 0 && (
              <Card>
                <CardContent className="pt-6">
                  <h3 className="text-lg font-semibold mb-2">Top Sources</h3>
                  <div className="space-y-2">
                    {statistics.top_sources.map((source, index) => (
                      <div key={index} className="flex justify-between items-center">
                        <span className="truncate max-w-[70%]">{source.name}</span>
                        <span className="font-medium">{source.count} proposals</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
        
        <DialogFooter>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface StatItemProps {
  label: string;
  value: string | number;
}

function StatItem({ label, value }: StatItemProps) {
  return (
    <div>
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}

function formatDate(dateString?: string): string {
  if (!dateString) return 'Never';
  
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    console.error('Error formatting date:', error);
    return 'Invalid date';
  }
} 