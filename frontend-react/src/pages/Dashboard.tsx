import { DataPageLayout } from '@/components/layout';
import { Card } from '@/components/ui/card';
import { useAnalytics } from '@/hooks/api/useAnalytics';
import { useProposals } from '@/hooks/api/useProposals';
import { useDataSources } from '@/hooks/api/useDataSources';
import { DashboardStats } from '@/components/dashboard/DashboardStats';
import { RecentProposals } from '@/components/dashboard/RecentProposals';
import { DataSourceHealth } from '@/components/dashboard/DataSourceHealth';

export default function Dashboard() {
  const {
    dashboard,
    statistics,
    isLoading,
    isError,
    error
  } = useAnalytics.useOverview();

  const { data: recentProposals } = useProposals.useRecent(5);
  const { data: dataSources } = useDataSources.useGetAll();

  return (
    <DataPageLayout
      title="Dashboard"
      subtitle="Overview of your data collection system"
      data={dashboard}
      loading={isLoading}
      error={error}
      renderContent={() => (
        <div className="space-y-6">
          {/* Statistics Overview */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <DashboardStats
                title="Total Proposals"
                value={statistics?.totalProposals}
                description="Total proposals collected"
              />
            </Card>
            <Card>
              <DashboardStats
                title="Active Sources"
                value={statistics?.activeDataSources}
                description="Currently active data sources"
              />
            </Card>
            <Card>
              <DashboardStats
                title="Success Rate"
                value={`${statistics?.successRate}%`}
                description="Successful data collection rate"
              />
            </Card>
          </div>

          {/* Recent Activity and Health */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <RecentProposals
                proposals={recentProposals?.data || []}
                isLoading={!recentProposals}
              />
            </Card>
            <Card>
              <DataSourceHealth
                dataSources={dataSources?.data || []}
                isLoading={!dataSources}
              />
            </Card>
          </div>
        </div>
      )}
    />
  );
} 