import { useCallback } from 'react';
import { useAnalytics } from '@/hooks';
import { formatDate, formatNumber } from '@/lib/utils';
import { PageLayout, StatsCard } from '@/components';
import { Alert, AlertTitle, AlertDescription, Button } from '@/components/ui';
import styles from './SimpleDashboard.module.css';

export default function SimpleDashboard() {
  const { 
    data: dashboardData,
    isLoading: loading,
    error: errors,
    refetch: fetchDashboardData
  } = useAnalytics();

  const handleRefresh = useCallback(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  if (loading && !dashboardData) {
    return (
      <PageLayout title="Simple Dashboard" isLoading={true}>
        <div>Loading dashboard data...</div>
      </PageLayout>
    );
  }

  // Error state
  if (errors && !dashboardData) {
    return (
      <div>
        <h1 className={styles.pageTitle}>Simple Dashboard</h1>
        <Alert variant="destructive">
          <AlertTitle>Error loading dashboard data</AlertTitle>
          <AlertDescription>{errors.message}</AlertDescription>
        </Alert>
        <Button onClick={handleRefresh}>Refresh</Button>
      </div>
    );
  }

  // If we have no data yet
  if (!dashboardData) {
    return (
      <PageLayout title="Simple Dashboard">
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
      title="Simple Dashboard" 
      subtitle={lastUpdated ? `Last updated: ${formatDate(lastUpdated)}` : undefined}
    >
      <div className={styles.contentWrapper}>
        {/* Stats Cards */}
        <div className={styles.statsGrid}>
          <StatsCard
            title="Total Proposals"
            value={formatNumber(stats.totalProposals)}
            description="All proposals in the system"
          />
          <StatsCard
            title="Active Sources"
            value={formatNumber(stats.activeSources)}
            description="Data sources currently active"
          />
          <StatsCard
            title="New This Week"
            value={formatNumber(stats.newThisWeek)}
            description="Proposals added in the last 7 days"
          />
          <StatsCard
            title="Success Rate"
            value={`${stats.successRate}%`}
            description="Successful scrapes"
          />
        </div>

        {/* Recent Activity */}
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>Recent Activity</h3>
          <div className={styles.activityList}>
            {stats.recentActivity?.map((activity: any, index: number) => (
              <div key={index} className={styles.activityItem}>
                <span>{activity.description}</span>
                <span className={styles.activityTimestamp}>{formatDate(activity.timestamp)}</span>
              </div>
            )) || (
              <p className={styles.mutedText}>No recent activity</p>
            )}
          </div>
        </div>

        {/* System Status */}
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>System Status</h3>
          <div className={styles.statusGrid}>
            <div>
              <p className={styles.statusLabel}>Database Size</p>
              <p className={styles.statusValue}>{stats.databaseSize}</p>
            </div>
            <div>
              <p className={styles.statusLabel}>Last Backup</p>
              <p className={styles.statusValue}>{stats.lastBackup ? formatDate(stats.lastBackup) : 'Never'}</p>
            </div>
            <div>
              <p className={styles.statusLabel}>System Uptime</p>
              <p className={styles.statusValue}>{stats.uptime}</p>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
} 