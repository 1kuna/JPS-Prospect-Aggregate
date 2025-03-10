import { useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDate } from '@/lib/utils';

export default function Dashboard() {
  const { 
    dashboardData, 
    loading, 
    errors, 
    lastUpdated,
    fetchDashboardData 
  } = useStore(state => ({
    dashboardData: state.dashboardData,
    loading: state.loading.dashboard,
    errors: state.errors.dashboard,
    lastUpdated: state.lastUpdated,
    fetchDashboardData: state.fetchDashboardData
  }));

  useEffect(() => {
    // Fetch data on component mount
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleRefresh = () => {
    fetchDashboardData();
  };

  return (
    <div className="container mx-auto py-6">
      {/* Page header with title and last updated info */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-sm text-muted-foreground">
              Last updated: {formatDate(lastUpdated)}
            </span>
          )}
          <Button onClick={handleRefresh} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Error state */}
      {errors && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{errors.message}</AlertDescription>
        </Alert>
      )}

      {/* Loading state */}
      {loading && !dashboardData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-8 w-3/4 mb-2" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-24 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* No data state */}
      {!loading && !dashboardData && (
        <Alert className="mb-6">
          <AlertTitle>No data available</AlertTitle>
          <AlertDescription>
            Click the refresh button to load data.
          </AlertDescription>
        </Alert>
      )}

      {/* Dashboard content */}
      {dashboardData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
              <CardDescription>Overview of all data sources</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Total Sources:</span>
                  <span className="font-medium">{dashboardData.totalSources || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Active Sources:</span>
                  <span className="font-medium">{dashboardData.activeSources || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Last Run:</span>
                  <span className="font-medium">
                    {dashboardData.lastRun ? formatDate(dashboardData.lastRun) : 'Never'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Status Card */}
          <Card>
            <CardHeader>
              <CardTitle>Status</CardTitle>
              <CardDescription>Current system status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>System Status:</span>
                  <span className={`font-medium ${dashboardData.systemStatus === 'Running' ? 'text-green-500' : 'text-red-500'}`}>
                    {dashboardData.systemStatus || 'Unknown'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Active Jobs:</span>
                  <span className="font-medium">{dashboardData.activeJobs || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Pending Jobs:</span>
                  <span className="font-medium">{dashboardData.pendingJobs || 0}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity Card */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest system activities</CardDescription>
            </CardHeader>
            <CardContent>
              {dashboardData.recentActivity && dashboardData.recentActivity.length > 0 ? (
                <ul className="space-y-2">
                  {dashboardData.recentActivity.slice(0, 5).map((activity: any, index: number) => (
                    <li key={index} className="text-sm">
                      <div className="font-medium">{activity.action}</div>
                      <div className="text-muted-foreground">{formatDate(activity.timestamp)}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">No recent activity</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
} 