import { useEffect } from 'react';
import { 
  useAnalyticsSelectors, 
  useDataSourcesSelectors, 
  useUISelectors 
} from '@/hooks/useStoreSelectors';
import {
  useDataSourcesHealth,
  useTotalProposalsCount,
  useProposalsTrend,
  useLatestActivityByDataSource
} from '@/store/selectors';

export default function StoreDemo() {
  // Base selectors
  const { 
    fetchDataSources, 
    dataSources, 
    loading: dataSourcesLoading 
  } = useDataSourcesSelectors();
  
  const { 
    fetchStatistics, 
    statistics, 
    loading: statisticsLoading 
  } = useAnalyticsSelectors();
  
  const { addToast } = useUISelectors();
  
  // Computed selectors
  const dataSourcesHealth = useDataSourcesHealth();
  const totalProposals = useTotalProposalsCount();
  const proposalsTrend = useProposalsTrend();
  const latestActivity = useLatestActivityByDataSource();
  
  // Fetch data on component mount
  useEffect(() => {
    Promise.all([
      fetchDataSources().catch(error => {
        console.error('Failed to fetch data sources:', error);
        addToast({
          title: 'Error',
          description: 'Failed to load data sources',
          variant: 'destructive'
        });
      }),
      fetchStatistics().catch(error => {
        console.error('Failed to fetch statistics:', error);
        addToast({
          title: 'Error',
          description: 'Failed to load statistics',
          variant: 'destructive'
        });
      })
    ]);
  }, [fetchDataSources, fetchStatistics, addToast]);
  
  const isLoading = dataSourcesLoading || statisticsLoading;
  
  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold">Dashboard</h2>
      
      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
        </div>
      ) : (
        <>
          {/* Key metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <MetricCard 
              title="Total Data Sources" 
              value={dataSources.length} 
              subtitle="All configured sources"
              icon="📊"
            />
            <MetricCard 
              title="Total Proposals" 
              value={totalProposals} 
              subtitle="Across all sources"
              icon="📝"
            />
            <MetricCard 
              title="Data Source Health" 
              value={`${dataSourcesHealth.percentage}%`} 
              subtitle={`${dataSourcesHealth.healthy} healthy, ${dataSourcesHealth.issues} with issues`}
              icon={dataSourcesHealth.percentage > 80 ? "✅" : "⚠️"}
            />
          </div>
          
          {/* Recent activity */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-xl font-bold mb-4">Latest Activity</h3>
              <div className="overflow-y-auto max-h-64">
                <table className="min-w-full">
                  <thead>
                    <tr>
                      <th className="text-left pb-2">Source</th>
                      <th className="text-left pb-2">Last Activity</th>
                      <th className="text-left pb-2">Proposals</th>
                    </tr>
                  </thead>
                  <tbody>
                    {latestActivity.map(source => (
                      <tr key={source.id} className="border-t">
                        <td className="py-2">{source.name}</td>
                        <td className="py-2">
                          {source.lastActivity 
                            ? source.lastActivity.toLocaleString()
                            : 'Never'
                          }
                        </td>
                        <td className="py-2">{source.proposalCount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-xl font-bold mb-4">Proposals Trend</h3>
              {proposalsTrend.length > 0 ? (
                <div className="h-64 flex items-end justify-between gap-2">
                  {proposalsTrend.map((item, index) => {
                    const height = `${Math.max(10, (item.count / Math.max(...proposalsTrend.map(i => i.count))) * 100)}%`;
                    return (
                      <div key={index} className="flex flex-col items-center flex-1">
                        <div 
                          className="bg-blue-500 w-full rounded-t" 
                          style={{ height }}
                          title={`${item.count} proposals`}
                        />
                        <div className="text-xs mt-1 text-center">{item.month}</div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="flex justify-center items-center h-64 text-gray-500">
                  No proposal trend data available
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon?: string;
}

function MetricCard({ title, value, subtitle, icon }: MetricCardProps) {
  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex justify-between">
        <div>
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
          <p className="text-3xl font-bold mt-2">{value}</p>
          <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
        </div>
        {icon && (
          <div className="text-3xl">{icon}</div>
        )}
      </div>
    </div>
  );
} 