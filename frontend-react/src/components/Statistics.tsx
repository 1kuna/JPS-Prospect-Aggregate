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
      <DialogContent 
        className="max-w-4xl max-h-[90vh] overflow-y-auto" 
        style={{ 
          backgroundColor: 'white', 
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          border: '2px solid #e5e7eb'
        }}
      >
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-gray-900">Data Statistics</DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex flex-col items-center justify-center py-8">
            <Spinner size="lg" />
            <p className="mt-4 text-gray-600">Loading statistics...</p>
          </div>
        )}

        {errors && (
          <div className="bg-red-50 p-4 rounded-md border border-red-200">
            <p className="text-red-600 font-medium">Error loading statistics</p>
            <p className="text-sm text-red-500">{errors.message}</p>
          </div>
        )}

        {!loading && statistics && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4">
              <Card className="border-2 border-blue-100 bg-white">
                <CardContent className="pt-6 text-center">
                  <h2 className="text-3xl font-bold text-blue-600">{statistics.total_proposals || 0}</h2>
                  <p className="text-gray-600">Total Proposals</p>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900">Proposals by Data Source</h3>
              <div className="border rounded-md overflow-hidden bg-white">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-gray-100">
                      <th className="px-4 py-2 text-left font-medium text-gray-700">Source</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-700">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statistics.source_stats?.map((source: any, index: number) => (
                      <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-4 py-2 text-gray-800">{source.name}</td>
                        <td className="px-4 py-2 text-gray-800">{source.count}</td>
                      </tr>
                    )) || (
                      <tr>
                        <td colSpan={2} className="px-4 py-2 text-center text-gray-500">
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
                <h3 className="text-lg font-medium text-gray-900">Top Agencies</h3>
                <div className="border rounded-md overflow-hidden bg-white">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b bg-gray-100">
                        <th className="px-4 py-2 text-left font-medium text-gray-700">Agency</th>
                        <th className="px-4 py-2 text-left font-medium text-gray-700">Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {statistics.agency_stats?.map((agency: any, index: number) => (
                        <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-4 py-2 text-gray-800">{agency.name}</td>
                          <td className="px-4 py-2 text-gray-800">{agency.count}</td>
                        </tr>
                      )) || (
                        <tr>
                          <td colSpan={2} className="px-4 py-2 text-center text-gray-500">
                            No data available
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Proposals by Status</h3>
                <div className="border rounded-md overflow-hidden bg-white">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b bg-gray-100">
                        <th className="px-4 py-2 text-left font-medium text-gray-700">Status</th>
                        <th className="px-4 py-2 text-left font-medium text-gray-700">Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {statistics.status_stats?.map((status: any, index: number) => (
                        <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-4 py-2 text-gray-800">{status.name}</td>
                          <td className="px-4 py-2 text-gray-800">{status.count}</td>
                        </tr>
                      )) || (
                        <tr>
                          <td colSpan={2} className="px-4 py-2 text-center text-gray-500">
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
          <Button onClick={onClose} className="mt-4 bg-blue-600 hover:bg-blue-700 text-white">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 