import { useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { formatDate } from '@/lib/utils';
import { 
  PageLayout, 
  PageSkeleton,
  StatsCard, 
  StatsGrid, 
  DataTable,
  Alert,
  AlertTitle,
  AlertDescription
} from '@/components';

// Create stable selectors outside the component
const selectDashboardData = (state: any) => state.dashboardData;
const selectDashboardLoading = (state: any) => state.loading.dashboard;
const selectDashboardErrors = (state: any) => state.errors.dashboard;
const selectFetchDashboardData = (state: any) => state.fetchDashboardData;
const selectLastUpdated = (state: any) => state.lastUpdated;

export default function Dashboard() {
  // Use individual selectors to prevent unnecessary re-renders
  const dashboardData = useStore(selectDashboardData);
  const loading = useStore(selectDashboardLoading);
  const errors = useStore(selectDashboardErrors);
  const fetchDashboardData = useStore(selectFetchDashboardData);
  const lastUpdated = useStore(selectLastUpdated);

  useEffect(() => {
    // Fetch data on component mount
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleRefresh = () => {
    fetchDashboardData();
  };

  const handlePageChange = (page: number) => {
    fetchDashboardData({ page, perPage: dashboardData?.pagination?.per_page || 50 });
  };

  // If loading and no data, show skeleton
  if (loading && !dashboardData) {
    return <PageSkeleton cardCount={3} />;
  }

  // Define table columns
  const columns = [
    { header: 'Title', accessor: 'title' },
    { header: 'Agency', accessor: 'agency' },
    { header: 'Source', accessor: 'source_name' },
    { 
      header: 'Release Date', 
      accessor: (proposal: any) => proposal.release_date ? formatDate(proposal.release_date) : 'N/A' 
    },
    { header: 'Status', accessor: 'status' },
  ];

  // Define stats for summary card
  const summaryStats = [
    { label: 'Total Sources:', value: dashboardData?.active_sources || 0 },
    { label: 'Total Proposals:', value: dashboardData?.total_proposals || 0 },
    { 
      label: 'Last Run:', 
      value: dashboardData?.last_scrape ? formatDate(dashboardData.last_scrape) : 'Never' 
    },
  ];

  // Define stats for status card
  const statusStats = [
    { 
      label: 'System Status:', 
      value: dashboardData?.systemStatus || 'Unknown',
      className: dashboardData?.systemStatus === 'Running' ? 'text-green-500' : 'text-red-500'
    },
    { label: 'Active Jobs:', value: dashboardData?.activeJobs || 0 },
    { label: 'Pending Jobs:', value: dashboardData?.pendingJobs || 0 },
  ];

  return (
    <PageLayout
      title="Dashboard"
      lastUpdated={lastUpdated}
      onRefresh={handleRefresh}
      isLoading={loading}
      error={errors}
    >
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
        <>
          <StatsGrid columns={3}>
            {/* Summary Card */}
            <StatsCard
              title="Summary"
              description="Overview of all data sources"
              stats={summaryStats}
            />

            {/* Status Card */}
            <StatsCard
              title="Status"
              description="Current system status"
              stats={statusStats}
            />

            {/* Recent Activity Card */}
            <StatsCard
              title="Recent Activity"
              description="Latest system activities"
              stats={
                dashboardData.recentActivity && dashboardData.recentActivity.length > 0
                  ? dashboardData.recentActivity.slice(0, 5).map((activity: any) => ({
                      label: activity.action,
                      value: formatDate(activity.timestamp),
                    }))
                  : [{ label: 'No recent activity', value: '' }]
              }
            />
          </StatsGrid>

          {/* Proposals Table */}
          <DataTable
            title="Proposals"
            description="Recent proposals from all sources"
            data={dashboardData.proposals || []}
            columns={columns}
            keyField="id"
            pagination={
              dashboardData.pagination
                ? {
                    page: dashboardData.pagination.page,
                    perPage: dashboardData.pagination.per_page,
                    totalPages: dashboardData.pagination.total_pages,
                    totalItems: dashboardData.pagination.total_items,
                  }
                : undefined
            }
            onPageChange={handlePageChange}
            emptyMessage={{
              title: 'No proposals found',
              description: 'There are currently no proposals in the system.',
            }}
          />
        </>
      )}
    </PageLayout>
  );
} 