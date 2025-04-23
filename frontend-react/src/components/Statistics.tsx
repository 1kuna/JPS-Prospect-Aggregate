import { useEffect } from 'react';
import { useAnalytics } from '@/hooks';
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
import { useToast } from '@/hooks/use-toast';
import styles from './Statistics.module.css';

interface StatisticsProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Statistics({ isOpen, onClose }: StatisticsProps) {
  const { data: statistics, isLoading, error, refetch: fetchStatistics } = useAnalytics();
  const { toast } = useToast();
  
  useEffect(() => {
    if (isOpen) {
      fetchStatistics().catch(fetchError => {
        console.error('Failed to fetch statistics:', fetchError);
        toast({
          title: 'Error',
          description: 'Failed to load statistics. Please try again.',
          variant: 'destructive'
        });
      });
    }
  }, [isOpen, fetchStatistics, toast]);
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Statistics</DialogTitle>
        </DialogHeader>
        
        {isLoading ? (
          <div className={styles.loadingWrapper}>
            <Spinner size="lg" />
          </div>
        ) : error ? (
          <div className={styles.errorBox}>
            {error.message || 'An error occurred while loading statistics'}
          </div>
        ) : !statistics ? (
          <div className={styles.noDataMessage}>
            No statistics available
          </div>
        ) : (
          <div className={styles.contentWrapper}>
            <Card>
              <CardContent className="pt-6">
                <h3 className={styles.sectionTitle}>Overview</h3>
                <div className={styles.overviewGrid}>
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
            
            {statistics.proposals_trend && statistics.proposals_trend.length > 0 && (
              <Card>
                <CardContent className="pt-6">
                  <h3 className={styles.sectionTitle}>Proposal Trends</h3>
                  <div className={styles.trendChartWrapper}>
                    {statistics.proposals_trend.map((item, index) => {
                      const maxValue = Math.max(...statistics.proposals_trend.map(i => i.count));
                      const height = `${Math.max(10, (item.count / maxValue) * 100)}%`;
                      
                      return (
                        <div key={index} className={styles.trendBarWrapper}>
                          <div 
                            className={styles.trendBar}
                            style={{ height }}
                            title={`${item.count} proposals`}
                          />
                          <div className={styles.trendBarLabel}>
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
                  <h3 className={styles.sectionTitle}>Top Sources</h3>
                  <div className={styles.topSourcesList}>
                    {statistics.top_sources.map((source, index) => (
                      <div key={index} className={styles.sourceItem}>
                        <span className={styles.sourceName}>{source.name}</span>
                        <span className={styles.sourceCount}>{source.count} proposals</span>
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
      <p className={styles.statLabel}>{label}</p>
      <p className={styles.statValue}>{value}</p>
    </div>
  );
}

function formatDate(dateString?: string): string {
  if (!dateString) return 'Never';
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
        return 'Invalid date';
    }
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