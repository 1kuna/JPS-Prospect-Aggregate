import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { formatDate, formatNumber } from '@/lib/utils';
import { PageLayout, StatsCard } from '@/components';
import { Alert, AlertTitle, AlertDescription, Button } from '@/components/ui';

// Create stable selectors
const selectDashboardData = (state: any) => state.dashboardData;
const selectDashboardLoading = (state: any) => state.loading.dashboard;
const selectDashboardErrors = (state: any) => state.errors.dashboard;
const selectFetchDashboardData = (state: any) => state.fetchDashboardData;

export default function Dashboard() {
  // Use individual selectors to prevent unnecessary re-renders
  const dashboardData = useStore(selectDashboardData);
  const loading = useStore(selectDashboardLoading);
  const errors = useStore(selectDashboardErrors);
  const fetchDashboardData = useStore(selectFetchDashboardData);
  
  const isMounted = useRef(false);

  useEffect(() => {
    // Only fetch data if this is the first time the component is mounted
    if (!isMounted.current) {
      fetchDashboardData();
      isMounted.current = true;
    }
  }, [fetchDashboardData]);

  const handleRefresh = useCallback(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  if (loading && !dashboardData) {
    return (
      <PageLayout title="Dashboard" isLoading={true}>
        <div>Loading dashboard data...</div>
      </PageLayout>
    );
  }

  // Error state
  if (errors && !dashboardData) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <Alert variant="destructive">
          <AlertTitle>Error loading dashboard data</AlertTitle>
          <AlertDescription>{errors.message}</AlertDescription>
        </Alert>
        <Button onClick={handleRefresh}>Retry</Button>
      </div>
    );
  }

  // If we have no data yet
  if (!dashboardData) {
    return (
      <PageLayout title="Dashboard">
        <Alert>
          <AlertTitle>No dashboard data available</AlertTitle>
          <AlertDescription>
            Dashboard data is being loaded or has not been generated yet.
          </AlertDescription>
        </Alert>
        <Button onClick={handleRefresh} className="mt-4">Refresh</Button>
      </PageLayout>
    );
  }

  const { stats, lastUpdated } = dashboardData;

  return (
    <PageLayout 
      title="Dashboard" 
      subtitle={lastUpdated ? `Last updated: ${formatDate(lastUpdated)}` : undefined}
    >
      <div className="space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Total Proposals"
            value={formatNumber(stats.totalProposals)}
            description="All proposals in the system"
            trend={stats.proposalsTrend}
          />
          <StatsCard
            title="Active Sources"
            value={formatNumber(stats.activeSources)}
            description="Data sources currently active"
            trend={stats.sourcesTrend}
          />
          <StatsCard
            title="New This Week"
            value={formatNumber(stats.newThisWeek)}
            description="Proposals added in the last 7 days"
            trend={stats.newTrend}
          />
          <StatsCard
            title="Success Rate"
            value={`${stats.successRate}%`}
            description="Successful scrapes"
            trend={stats.successTrend}
          />
        </div>

        {/* Recent Proposals */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium mb-4">Recent Activity</h3>
          <div className="space-y-2">
            {stats.recentActivity?.map((activity: any, index: number) => (
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
              <p className="text-xl font-semibold">{stats.databaseSize}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Last Backup</p>
              <p className="text-xl font-semibold">{stats.lastBackup ? formatDate(stats.lastBackup) : 'Never'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">System Uptime</p>
              <p className="text-xl font-semibold">{stats.uptime}</p>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
} 