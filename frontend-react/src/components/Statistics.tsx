import { useEffect } from 'react';
import { useStore } from '@/store/useStore';
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

// Create stable selectors
const selectStatistics = (state: any) => state.statistics;
const selectStatisticsLoading = (state: any) => state.loading.statistics;
const selectStatisticsErrors = (state: any) => state.errors.statistics;
const selectFetchStatistics = (state: any) => state.fetchStatistics;

interface StatisticsProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Statistics({ isOpen, onClose }: StatisticsProps) {
  const statistics = useStore(selectStatistics);
  const loading = useStore(selectStatisticsLoading);
  const errors = useStore(selectStatisticsErrors);
  const fetchStatistics = useStore(selectFetchStatistics);

  useEffect(() => {
    if (isOpen && !statistics) {
      fetchStatistics();
    }
  }, [isOpen, statistics, fetchStatistics]);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Data Statistics</DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex flex-col items-center justify-center py-8">
            <Spinner size="lg" />
            <p className="mt-4 text-muted-foreground">Loading statistics...</p>
          </div>
        )}

        {errors && (
          <div className="bg-destructive/10 p-4 rounded-md">
            <p className="text-destructive font-medium">Error loading statistics</p>
            <p className="text-sm text-destructive/80">{errors.message}</p>
          </div>
        )}

        {!loading && statistics && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4">
              <Card>
                <CardContent className="pt-6 text-center">
                  <h2 className="text-3xl font-bold">{statistics.total_proposals || 0}</h2>
                  <p className="text-muted-foreground">Total Proposals</p>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-medium">Proposals by Data Source</h3>
              <div className="border rounded-md">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="px-4 py-2 text-left font-medium">Source</th>
                      <th className="px-4 py-2 text-left font-medium">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statistics.source_stats?.map((source: any, index: number) => (
                      <tr key={index} className={index % 2 === 0 ? 'bg-background' : 'bg-muted/30'}>
                        <td className="px-4 py-2">{source.name}</td>
                        <td className="px-4 py-2">{source.count}</td>
                      </tr>
                    )) || (
                      <tr>
                        <td colSpan={2} className="px-4 py-2 text-center text-muted-foreground">
                          No data available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h3 className="text-lg font-medium">Top Agencies</h3>
                <div className="border rounded-md">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="px-4 py-2 text-left font-medium">Agency</th>
                        <th className="px-4 py-2 text-left font-medium">Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {statistics.agency_stats?.map((agency: any, index: number) => (
                        <tr key={index} className={index % 2 === 0 ? 'bg-background' : 'bg-muted/30'}>
                          <td className="px-4 py-2">{agency.name}</td>
                          <td className="px-4 py-2">{agency.count}</td>
                        </tr>
                      )) || (
                        <tr>
                          <td colSpan={2} className="px-4 py-2 text-center text-muted-foreground">
                            No data available
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-medium">Proposals by Status</h3>
                <div className="border rounded-md">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="px-4 py-2 text-left font-medium">Status</th>
                        <th className="px-4 py-2 text-left font-medium">Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {statistics.status_stats?.map((status: any, index: number) => (
                        <tr key={index} className={index % 2 === 0 ? 'bg-background' : 'bg-muted/30'}>
                          <td className="px-4 py-2">{status.name}</td>
                          <td className="px-4 py-2">{status.count}</td>
                        </tr>
                      )) || (
                        <tr>
                          <td colSpan={2} className="px-4 py-2 text-center text-muted-foreground">
                            No data available
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 