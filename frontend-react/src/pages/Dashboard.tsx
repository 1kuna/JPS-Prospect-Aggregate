import { formatDate, formatNumber } from '@/lib/utils';
import { useStoreData } from '@/hooks';
import { StatsCard } from '@/components';
import { DataPageLayout } from '@/components/layout';

// Create stable selectors
const selectDashboardData = (state: any) => state.dashboardData;
const selectDashboardLoading = (state: any) => state.loading.dashboard;
const selectDashboardErrors = (state: any) => state.errors.dashboard;
const selectFetchDashboardData = (state: any) => state.fetchDashboardData;

export default function Dashboard() {
  // Use the custom hook for data fetching and state management
  const { data: dashboardData, loading, errors, refresh } = useStoreData({
    dataSelector: selectDashboardData,
    loadingSelector: selectDashboardLoading,
    errorSelector: selectDashboardErrors,
    fetchAction: selectFetchDashboardData
  });

  // Get additional formatted data
  const lastUpdatedText = dashboardData?.lastUpdated 
    ? `Last updated: ${formatDate(dashboardData.lastUpdated)}` 
    : undefined;

  return (
    <DataPageLayout
      title="Dashboard"
      subtitle={lastUpdatedText}
      data={dashboardData}
      loading={loading}
      error={errors}
      onRefresh={refresh}
      emptyMessage="Dashboard data is being loaded or has not been generated yet."
      renderContent={(data) => (
        <div className="space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatsCard
              title="Total Proposals"
              value={formatNumber(data.stats.totalProposals)}
              description="All proposals in the system"
              trend={data.stats.proposalsTrend}
            />
            <StatsCard
              title="Active Sources"
              value={formatNumber(data.stats.activeSources)}
              description="Data sources currently active"
              trend={data.stats.sourcesTrend}
            />
            <StatsCard
              title="New This Week"
              value={formatNumber(data.stats.newThisWeek)}
              description="Proposals added in the last 7 days"
              trend={data.stats.newTrend}
            />
            <StatsCard
              title="Success Rate"
              value={`${data.stats.successRate}%`}
              description="Successful scrapes"
              trend={data.stats.successTrend}
            />
          </div>

          {/* Recent Proposals */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium mb-4">Recent Activity</h3>
            <div className="space-y-2">
              {data.stats.recentActivity?.map((activity: any, index: number) => (
                <div key={index} className="flex justify-between items-center py-2 border-b last:border-0">
                  <span>{activity.description}</span>
                  <span className="text-sm text-muted-foreground">{formatDate(activity.timestamp)}</span>
                </div>
              )) || (
                <p className="text-muted-foreground">No recent activity</p>
              )}
            </div>
          </div>

          {/* System Status */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium mb-4">System Status</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Database Size</p>
                <p className="text-xl font-semibold">{data.stats.databaseSize}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Last Backup</p>
                <p className="text-xl font-semibold">{data.stats.lastBackup ? formatDate(data.stats.lastBackup) : 'Never'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">System Uptime</p>
                <p className="text-xl font-semibold">{data.stats.uptime}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    />
  );
} 